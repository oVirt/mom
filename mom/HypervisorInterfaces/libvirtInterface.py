# Memory Overcommitment Manager
# Copyright (C) 2010 Adam Litke, IBM Corporation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

import libvirt
import re
import logging
from subprocess import *
from mom.HypervisorInterfaces.HypervisorInterface import *
from xml.etree import ElementTree
from xml.dom.minidom import parseString as _domParseStr

_METADATA_VM_TUNE_URI = 'http://ovirt.org/vm/tune/1.0'

class libvirtInterface(HypervisorInterface):
    """
    libvirtInterface provides a wrapper for the libvirt API so that libvirt-
    related error handling can be consolidated in one place.  An instance of
    this class provides a single libvirt connection that can be shared by all
    threads.  If the connection is broken, an attempt will be made to reconnect.
    """
    def __init__(self, config):
        self.conn = None
        self.uri = config.get('main', 'libvirt-hypervisor-uri')
        self.interval = config.getint('main', 'guest-monitor-interval')
        self.logger = logging.getLogger('mom.libvirtInterface')
        libvirt.registerErrorHandler(self._error_handler, None)
        self._connect()
        self._setStatsFields()

    def __del__(self):
        if self.conn is not None:
            self.conn.close()

    # Older versions of the libvirt python bindings required an extra parameter.
    # Hence 'dummy'.
    def _error_handler(self, ctx, error, dummy=None):
        pass

    def _connect(self):
        try:
            self.conn = libvirt.open(self.uri)
        except libvirt.libvirtError, e:
            self.logger.error("libvirtInterface: error setting up " \
                    "connection: %s", e)

    def _reconnect(self):
        try:
            self.conn.close()
        except libvirt.libvirtError:
            pass # The connection is in a strange state so ignore these
        try:
            self._connect()
        except libvirt.libvirtError, e:
            self.logger.error("libvirtInterface: Exception while " \
                    "reconnecting: %s", e);


    def _getDomainFromID(self, dom_id):
        try:
            dom = self.conn.lookupByID(dom_id)
        except libvirt.libvirtError, e:
            self._handleException(e)
            return None
        else:
            return dom

    def _getDomainFromUUID(self, dom_uuid):
        try:
            dom = self.conn.lookupByUUIDString(dom_uuid)
        except libvirt.libvirtError, e:
            self._handleException(e)
            return None
        else:
            return dom

    def _domainIsRunning(self, domain):
        try:
            if domain.info()[0] == libvirt.VIR_DOMAIN_RUNNING:
                return True
        except libvirt.libvirtError, e:
            self._handleException(e)
        return False

    def _domainGetName(self, domain):
        try:
            name = domain.name()
        except libvirt.libvirtError, e:
            self._handleException(e)
            return None
        return name

    def _domainGetUUID(self, domain):
        try:
            uuid = domain.UUIDString()
        except libvirt.libvirtError, e:
            self._handleException(e)
            return None
        return uuid

    def _domainGetInfo(self, domain):
        try:
            info = domain.info()
        except libvirt.libvirtError, e:
            self._handleException(e)
            return None
        return info

    def _domainGetPid(self, uuid):
        """
        This is an ugly way to find the pid of the qemu process associated with
        this guest.  Scan ps output looking for our uuid and record the pid.
        Something is probably wrong if more or less than 1 match is returned.
        """
        p1 = Popen(["ps", "axww"], stdout=PIPE).communicate()[0]
        matches = re.findall("^\s*(\d+)\s+.*" + uuid, p1, re.M)
        if len(matches) < 1:
            self.logger.warn("No matching process for domain with uuid %s", \
                             uuid)
            return None
        elif len(matches) > 1:
            self.logger.warn("Too many process matches for domain with uuid %s",\
                             uuid)
            return None
        return int(matches[0])

    def _domainSetMemoryStatsPeriod(self, domain, period):
        try:
            domain.setMemoryStatsPeriod(period)
        except libvirt.libvirtError, e:
            self._handleException(e)
        except AttributeError, e:
            pass # Older versions of libvirt don't have the method

    def _domainGetMemoryStats(self, domain):
        try:
            stats = domain.memoryStats()
        except libvirt.libvirtError, e:
            self._handleException(e)
            return None
        return stats


    def _handleException(self, e):
        reconnect_errors = (libvirt.VIR_ERR_SYSTEM_ERROR,libvirt.VIR_ERR_INVALID_CONN)
        do_nothing_errors = (libvirt.VIR_ERR_NO_DOMAIN,)
        error = e.get_error_code()
        if error in reconnect_errors:
            self.logger.warn('libvirtInterface: connection lost, reconnecting.')
            self._reconnect()
        elif error in do_nothing_errors:
            pass
        else:
            self.logger.warn('libvirtInterface: Unhandled libvirt exception '\
                             '(%i).', error)

    def _domainSetBalloonTarget(self, domain, target):
        try:
            return domain.setMemory(target)
        except libvirt.libvirtError, e:
            self._handleException(e)
            return False

    def getVmList(self):
        try:
            dom_list = self.conn.listDomainsID()
        except libvirt.libvirtError, e:
            self._handleException(e)
            return []
        return dom_list

    def getVmInfo(self, id):
        data = {}
        guest_domain = self._getDomainFromID(id)
        data['uuid'] = self._domainGetUUID(guest_domain)
        data['name'] = self._domainGetName(guest_domain)
        data['pid'] = self._domainGetPid(data['uuid'])
        if None in data.values():
            return None
        return data

    def startVmMemoryStats(self, uuid):
        domain = self._getDomainFromUUID(uuid)
        self._domainSetMemoryStatsPeriod(domain, self.interval)

    def getVmMemoryStats(self, uuid):
        domain = self._getDomainFromUUID(uuid)
        # Try to collect memory stats.  This function may not be available
        info = self._domainGetMemoryStats(domain)
        ret = {}
        if info is None or len(info.keys()) == 0:
            raise HypervisorInterfaceError('libvirt memoryStats() '
                                           'is not active')
        for key in set(self.mem_stats.keys()) & set(info.keys()):
            ret[self.mem_stats[key]] = info[key]
        return ret

    def _setStatsFields(self):
        """
        The following additional statistics may be available depending on the
        libvirt version, qemu version, and guest operation system version:
            mem_available - Total amount of memory available (kB)
            mem_unused - Amount of free memory not including caches (kB)
            major_fault - Total number of major page faults
            minor_fault - Total number of minor page faults
            swap_in - Total amount of memory swapped in (kB)
            swap_out - Total amount of memory swapped out (kB)
        """
        self.mem_stats = { 'available': 'mem_available', 'unused': 'mem_unused',
                      'major_fault': 'major_fault', 'minor_fault': 'minor_fault',
                      'swap_in': 'swap_in', 'swap_out': 'swap_out' }

    def getStatsFields(self):
        return set(self.mem_stats.values())

    def _getGuaranteedMemory(self, domain):
        """
        Get the DOM XML for domain and return the minimum guaranteed
        memory (KiB) defined there. If the element is missing, return 0
        """
        xml_domain = ElementTree.fromstring(domain.XMLDesc(0))
        elements = xml_domain.findall("./memtune/min_guarantee")
        if elements:
            return elements[0].text
        else:
            return 0

    def getVmBalloonInfo(self, uuid):
        domain = self._getDomainFromUUID(uuid)
        info = self._domainGetInfo(domain)
        if info is None:
            self.logger.error('Failed to get domain info')
            return None
        ret =  {'balloon_max': info[1], 'balloon_cur': info[2],
                'balloon_min': self._getGuaranteedMemory(domain) }
        return ret

    def getVmCpuTuneInfo(self, uuid):
        ret = {}
        domain = self._getDomainFromUUID(uuid)

        # Get the user selection for vcpuLimit from the metadata
        metadataCpuLimit = None
        try:
            metadataCpuLimit = domain.metadata(
                libvirt.VIR_DOMAIN_METADATA_ELEMENT, _METADATA_VM_TUNE_URI, 0)
        except libvirt.libvirtError as e:
            if e.get_error_code() != libvirt.VIR_ERR_NO_DOMAIN_METADATA:
                self.logger.error("Failed to retrieve QoS metadata")

        if metadataCpuLimit:
            metadataCpuLimitXML = _domParseStr(metadataCpuLimit)
            nodeList = \
                metadataCpuLimitXML.getElementsByTagName('vcpuLimit')
            ret['vcpu_user_limit'] = nodeList[0].childNodes[0].data
        else:
            ret['vcpu_user_limit'] = 100

        # Retrieve the current cpu tuning params
        ret.update(domain.schedulerParameters())

        if ret['vcpu_quota'] == None:
            ret['vcpu_quota'] = 0

        if ret['vcpu_period'] == None:
            ret['vcpu_period'] = 0

        # Get the number of vcpus
        vcpuCount = domain.vcpusFlags(libvirt.VIR_DOMAIN_VCPU_CURRENT)
        if vcpuCount != -1:
            ret['vcpu_count'] =  vcpuCount
        else:
            self.logger.error('Failed to get VM cpu count')
            return None

        return ret

    def setVmBalloonTarget(self, uuid, target):
        dom = self._getDomainFromUUID(uuid)
        if dom is not None:
            if self._domainSetBalloonTarget(dom, target):
                name = self._domainGetName(dom)
                self.logger.warn("Error while ballooning guest:%i", name)

    def setVmCpuTune(self, uuid, quota, period):
        dom = self._getDomainFromUUID(uuid)
        try:
            dom.setSchedulerParameters({ 'vcpu_quota': quota, 'vcpu_period': period})
        except libvirt.libvirtError, e:
            self.logger.error("libvirtInterface: Exception while " \
                    "setSchedulerParameters: %s", e);

    def ksmTune(self, tuningParams):
        def write_value(fname, value):
            try:
                with open(fname, 'w') as f:
                    f.write(str(value))
            except IOError, (errno, strerror):
                self.logger.warn("KSM: Failed to write %s: %s", fname, strerror)

        for (key, val) in tuningParams.items():
            write_value('/sys/kernel/mm/ksm/%s' % key, val)

    def qemuAgentCommand(self, uuid, command, timeout=10):
        import libvirt_qemu
        dom = self._getDomainFromUUID(uuid)
        if dom is None:
            return None
        return libvirt_qemu.qemuAgentCommand(dom, command, timeout, 0)

def instance(config):
    return libvirtInterface(config)
