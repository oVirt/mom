# Memory Overcommitment Manager
# Copyright (C) 2015 Martin Sivak, Red Hat
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

import logging
import traceback
import time
import functools
import socket
import threading

from vdsm import vdscli
from mom.HypervisorInterfaces.HypervisorInterface import HypervisorInterface, \
    HypervisorInterfaceError

# Time validity of the cache in seconds
CACHE_EXPIRATION = 5

# Cache return values with expiration
def memoize(expiration):
    def decorator(obj):
        lock = threading.Lock()
        cache = obj._cache = {}
        timestamps = obj._timestamps = {}

        @functools.wraps(obj)
        def memoizer(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = time.time()

            # use absolute value of the time difference to avoid issues
            # with time changing to the past

            with lock:
                if key not in cache or abs(now - timestamps[key]) > expiration:
                    cache[key] = obj(*args, **kwargs)
                    timestamps[key] = now
                return cache[key]
        return memoizer
    return decorator


class XmlRpcVdsmInterface(HypervisorInterface):
    """
    vdsmInterface provides a wrapper for the VDSM API so that VDSM-
    related error handling can be consolidated in one place.  An instance of
    this class provides a single VDSM connection that can be shared by all
    threads.
    """

    def __init__(self):
        self.logger = logging.getLogger('mom.vdsmInterface')
        try:
            self.vdsm_api = vdscli.connect()
            response = self.vdsm_api.ping()
            self._check_status(response)
        except socket.error as e:
            self.handle_connection_error(e)
        except vdsmException, e:
            e.handle_exception()

    def _check_status(self, response):
        if response['status']['code']:
            raise vdsmException(response, self.logger)

    @memoize(expiration=CACHE_EXPIRATION)
    def getAllVmStats(self):
        vms = {}

        try:
            ret = self.vdsm_api.getAllVmStats()
            self._check_status(ret)
        except socket.error as e:
            self.handle_connection_error(e)
            return vms
        except vdsmException as e:
            e.handle_exception()
            return vms

        for vm in ret['statsList']:
            vms[vm['vmId']] = vm
        return vms

    def getVmStats(self, vmId):
        return self.getAllVmStats()[vmId]

    def _vmIsRunning(self, vm):
        if vm['status'] == 'Up':
            return True
        else:
            return False

    def getVmList(self):
        vmIds = []
        vm_list = self.getAllVmStats().values()
        for vm in vm_list:
            if self._vmIsRunning(vm):
                vmIds.append(vm['vmId'])
        self.logger.debug('VM List: %s', vmIds)
        return vmIds

    def getVmMemoryStats(self, uuid):
        ret = {}
        try:
            vm = self.getVmStats(uuid)
        except KeyError as e:
            raise HypervisorInterfaceError("VM %s does not exist" % uuid)

        usage = int(vm['memUsage'])
        if usage == 0:
            msg = "The ovirt-guest-agent is not active"
            raise HypervisorInterfaceError(msg)
        stats = vm['memoryStats']
        if not stats:
            msg = "Detailed guest memory stats are not available, " \
                    "please upgrade guest agent"
            raise HypervisorInterfaceError(msg)

        ret['mem_available'] = int(stats['mem_total'])
        ret['mem_unused'] = int(stats['mem_unused'])
        ret['mem_free'] = int(stats['mem_free'])
        ret['major_fault'] = int(stats['majflt'])
        ret['minor_fault'] = int(stats['pageflt']) - int(stats['majflt'])
        ret['swap_in'] = int(stats['swap_in'])
        ret['swap_out'] = int(stats['swap_out'])

        # get swap size and usage information if available
        ret['swap_total'] = int(stats.get('swap_total', 0))
        ret['swap_usage'] = int(stats.get('swap_usage', 0))

        self.logger.debug('Memory stats: %s', ret)
        return ret

    def setVmBalloonTarget(self, uuid, target):
        try:
            response = self.vdsm_api.setBalloonTarget(uuid, target)
            self._check_status(response)
        except socket.error as e:
            self.handle_connection_error(e)
        except vdsmException, e:
            e.handle_exception()

    def getVmInfo(self, uuid):
        try:
            vm = self.getVmStats(uuid)
        except KeyError as e:
            raise HypervisorInterfaceError("VM %s does not exist" % uuid)

        data = {}
        data['uuid'] = uuid
        data['pid'] = vm['pid']
        data['name'] = vm['vmName']
        if None in data.values():
            return None
        return data

    def getStatsFields(self=None):
        return set(['mem_available', 'mem_unused', 'mem_free',
                    'major_fault', 'minor_fault', 'swap_in', 'swap_out',
                    'swap_total', 'swap_usage'])

    def getVmBalloonInfo(self, uuid):
        try:
            vm = self.getVmStats(uuid)
        except KeyError as e:
            raise HypervisorInterfaceError("VM %s does not exist" % uuid)

        balloon_info = vm['balloonInfo']
        if balloon_info:
            # Make sure the values are numbers, VDSM is using str
            # to avoid xml-rpc issues
            # We are modifying the dict keys inside the loop so
            # iterate over copy of the list with keys, also use
            # list() to make this compatible with Python 3
            for key in list(balloon_info.keys()):
                # Remove keys that are not important to MoM to make sure
                # the HypervisorInterface stays consistent between
                # libvirt and vdsm platforms.
                if key not in ("balloon_max", "balloon_min", "balloon_cur"):
                    del balloon_info[key]
                    continue
                balloon_info[key] = int(balloon_info[key])
            return balloon_info


    def getVmCpuTuneInfo(self, uuid):
        try:
            ret = {}
            vm = self.getVmStats(uuid)
        except KeyError as e:
            raise HypervisorInterfaceError("VM %s does not exist" % uuid)

        # Get user selection for vCPU limit
        vcpuUserLimit = vm.get('vcpuUserLimit', 100)
        ret['vcpu_user_limit'] = vcpuUserLimit

        # Get current vcpu tuning info
        vcpuQuota = vm.get('vcpuQuota', 0)
        ret['vcpu_quota'] = vcpuQuota
        vcpuPeriod = vm.get('vcpuPeriod', 0)
        ret['vcpu_period'] = vcpuPeriod

        #Get num of vCPUs
        vcpuCount = vm.get('vcpuCount', None)
        if vcpuCount == None:
            return None
        else:
            ret['vcpu_count'] = vcpuCount

        # Make sure the values are numbers, VDSM is using str
        # to avoid xml-rpc issues
        # We are modifying the dict keys inside the loop so
        # iterate over copy of the list with keys, also use
        # list() to make this compatible with Python 3
        for key in list(ret.keys()):
            ret[key] = int(ret[key])
        return ret

    def setVmCpuTune(self, uuid, quota, period):
        try:
            response = self.vdsm_api.vmSetCpuTuneQuota(uuid, quota)
            self._check_status(response)
        except socket.error as e:
            self.handle_connection_error(e)
        except vdsmException, e:
            e.handle_exception()
        try:
            response = self.vdsm_api.vmSetCpuTunePeriod(uuid, period)
            self._check_status(response)
        except socket.error as e:
            self.handle_connection_error(e)
        except vdsmException, e:
            e.handle_exception()

    def ksmTune(self, tuningParams):
        try:
            response = self.vdsm_api.setKsmTune(tuningParams)
            self._check_status(response)
        except socket.error as e:
            self.handle_connection_error(e)
        except vdsmException, e:
            e.handle_exception()

    def handle_connection_error(self, e):
        self.logger.error("Cannot connect to VDSM! {0}".format(e))


class vdsmException(Exception):

    def __init__(self, response, logger):
        try:
            self.msg = response['status'].get('message', response)
        except (AttributeError, KeyError):
            self.msg = response
        self.logger = logger

    def handle_exception(self):
        "Handle exception in a nice way. Just report the message and try again later."
        self.logger.error(self.msg)
        self.logger.debug(traceback.format_exc())

def instance(config):
    return XmlRpcVdsmInterface()
