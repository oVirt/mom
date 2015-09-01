# Memory Overcommitment Manager
# Copyright (C) 2012 Mark Wu, IBM Corporation
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

import sys
sys.path.append('/usr/share/vdsm')
import API
import supervdsm
import logging
import traceback
from mom.HypervisorInterfaces.HypervisorInterface import HypervisorInterface, \
    HypervisorInterfaceError


class vdsmInterface(HypervisorInterface):
    """
    vdsmInterface provides a wrapper for the VDSM API so that VDSM-
    related error handling can be consolidated in one place.  An instance of
    this class provides a single VDSM connection that can be shared by all
    threads.
    """

    def __init__(self):
        self.logger = logging.getLogger('mom.vdsmInterface')
        try:
            self.vdsm_api = API.Global()
            response = self.vdsm_api.ping()
            self._check_status(response)
        except vdsmException, e:
            e.handle_exception()

    def _check_status(self, response):
        if response['status']['code']:
            raise vdsmException(response, self.logger)

    def _vmIsRunning(self, vm):
        if vm['status'] == 'Up':
            return True
        else:
            return False

    def getVmName(self, uuid):
        try:
            response = self.vdsm_api.getVMList(True, [uuid])
            self._check_status(response)
            return response['vmList'][0]['vmName']
        except vdsmException, e:
            e.handle_exception()
            return None

    def getVmPid(self, uuid):
        try:
            response = self.vdsm_api.getVMList(True, [uuid])
            self._check_status(response)
            return response['vmList'][0]['pid']
        except vdsmException, e:
            e.handle_exception()
            return None

    def getVmList(self):
        vmIds = []
        try:
            response = self.vdsm_api.getVMList()
            self._check_status(response)
            vm_list = response['vmList']
            for vm in vm_list:
                if self._vmIsRunning(vm):
                    vmIds.append(vm['vmId'])
            self.logger.debug('VM List: %s', vmIds)
            return vmIds
        except vdsmException, e:
            e.handle_exception()
            return None

    def getVmMemoryStats(self, uuid):
        ret = {}
        try:
            vm = API.VM(uuid)
            response = vm.getStats()
            self._check_status(response)
            usage = int(response['statsList'][0]['memUsage'])
            if usage == 0:
                msg = "VM %s - The ovirt-guest-agent is not active" % uuid
                raise HypervisorInterfaceError(msg)
            stats = response['statsList'][0]['memoryStats']
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
        except vdsmException, e:
            raise HypervisorInterfaceError(e.msg)

    def setVmBalloonTarget(self, uuid, target):
        try:
            vm = API.VM(uuid)
            response = vm.setBalloonTarget(target)
            self._check_status(response)
        except vdsmException, e:
            e.handle_exception()

    def getVmInfo(self, id):
        data = {}
        data['uuid'] = id
        data['pid'] = self.getVmPid(id)
        data['name'] = self.getVmName(id)
        if None in data.values():
            return None
        return data

    def getStatsFields(self=None):
        return set(['mem_available', 'mem_unused', 'mem_free',
                    'major_fault', 'minor_fault', 'swap_in', 'swap_out',
                    'swap_total', 'swap_usage'])

    def getVmBalloonInfo(self, uuid):
        try:
            vm = API.VM(uuid)
            response = vm.getStats()
            self._check_status(response)
            balloon_info = response['statsList'][0]['balloonInfo']
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
        except vdsmException, e:
            e.handle_exception()

    def getVmCpuTuneInfo(self, uuid):
        try:
            ret = {}
            vm = API.VM(uuid)
            response = vm.getStats()
            self._check_status(response)

            # Get user selection for vCPU limit
            vcpuUserLimit = response['statsList'][0].get('vcpuUserLimit', 100)
            ret['vcpu_user_limit'] = vcpuUserLimit

            # Get current vcpu tuning info
            vcpuQuota = response['statsList'][0].get('vcpuQuota', 0)
            ret['vcpu_quota'] = vcpuQuota
            vcpuPeriod = response['statsList'][0].get('vcpuPeriod', 0)
            ret['vcpu_period'] = vcpuPeriod

            #Get num of vCPUs
            vcpuCount = response['statsList'][0].get('vcpuCount', None)
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
        except vdsmException, e:
            e.handle_exception()

    def setVmCpuTune(self, uuid, quota, period):
        vm = API.VM(uuid)
        try:
            response = vm.setCpuTuneQuota(quota)
            self._check_status(response)
        except vdsmException, e:
            e.handle_exception()
        try:
            response = vm.setCpuTunePeriod(period)
            self._check_status(response)
        except vdsmException, e:
            e.handle_exception()

    def ksmTune(self, tuningParams):
        # When MOM is lauched by vdsm, it's running without root privileges.
        # So we need resort to supervdsm to set the KSM parameters.
        superVdsm = supervdsm.getProxy()
        superVdsm.ksmTune(tuningParams)


class vdsmException(Exception):

    def __init__(self, response, logger):
        try:
            self.msg = response['status'].get('message', response)
        except (AttributeError, KeyError):
            self.msg = response
        self.logger = logger

    def handle_exception(self):
        self.logger.error(self.msg)
        self.logger.error(traceback.format_exc())


def instance(config):
    return vdsmInterface()
