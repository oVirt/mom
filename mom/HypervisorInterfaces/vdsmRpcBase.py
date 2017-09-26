# Memory Overcommitment Manager
# Copyright (C) 2017 Martin Sivak, Red Hat
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

from .HypervisorInterface import \
    HypervisorInterface, HypervisorInterfaceError


class VdsmRpcBase(HypervisorInterface):
    def __init__(self):
        self._logger = logging.getLogger('mom.VdsmRpcBase')

    def getVmList(self):
        vmIds = []
        vm_list = self.getAllVmStats().values()
        for vm in vm_list:
            if vm['status'] == 'Up':
                vmIds.append(vm['vmId'])

        self._logger.debug('VM List: %s', vmIds)
        return vmIds

    def getVmMemoryStats(self, uuid):
        vm = self._getVmStats(uuid)

        usage = int(vm['memUsage'])
        if usage == 0:
            msg = "The ovirt-guest-agent is not active"
            raise HypervisorInterfaceError(msg)
        stats = vm['memoryStats']
        if not stats:
            msg = "Detailed guest memory stats are not available, " \
                  "please upgrade guest agent"
            raise HypervisorInterfaceError(msg)

        ret = {}
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

        self._logger.debug('Memory stats: %s', ret)
        return ret

    def getVmInfo(self, uuid):
        vm = self._getVmStats(uuid)

        data = {}
        data['uuid'] = uuid
        if 'pid' in vm:
            data['pid'] = vm['pid']

        data['name'] = vm['vmName']
        if None in data.values():
            return None
        return data

    def getVmBalloonInfo(self, uuid):
        vm = self._getVmStats(uuid)

        balloon_info = vm.get('balloonInfo', {})
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
        vm = self._getVmStats(uuid)

        ret = {}
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
        if vcpuCount is None:
            return None

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
        raise NotImplementedError()

    def getVmIoTunePolicy(self, vmId):
        raise NotImplementedError()

    def getVmIoTune(self, vmId):
        raise NotImplementedError()

    def setVmIoTune(self, vmId, tunables):
        raise NotImplementedError()

    def setVmBalloonTarget(self, uuid, target):
        raise NotImplementedError()

    def ksmTune(self, tuningParams):
        raise NotImplementedError()

    def getAllVmStats(self):
        raise NotImplementedError()

    def _getVmStats(self, vmId):
        try:
            return self.getAllVmStats()[vmId]
        except KeyError:
            raise HypervisorInterfaceError("VM %s does not exist" % vmId)
