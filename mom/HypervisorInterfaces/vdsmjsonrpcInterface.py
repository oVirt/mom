# Memory Overcommitment Manager
# Copyright (C) 2016 Martin Sivak, Red Hat
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
import socket

from vdsm import jsonrpcvdscli

from mom.HypervisorInterfaces.HypervisorInterface import HypervisorInterface, \
    HypervisorInterfaceError

from .vdsmxmlrpcInterface import memoize, vdsmException

from mom.optional import Optional

# Time validity of the cache in seconds
CACHE_EXPIRATION = 5

class JsonRpcVdsmInterface(HypervisorInterface):
    """
    vdsmInterface provides a wrapper for the VDSM API so that VDSM-
    related error handling can be consolidated in one place.  An instance of
    this class provides a single VDSM connection that can be shared by all
    threads.
    """

    def __init__(self):
        self.logger = logging.getLogger('mom.vdsmInterface')
        self._vdsm_api = self.checked_call(jsonrpcvdscli.connect)\
                .orRaise(RuntimeError, 'No connection to VDSM.')

        self.checked_call(self._vdsm_api.ping)

    def _check_status(self, response):
        try:
            if response['status']['code']:
                raise vdsmException(response, self.logger)

        # This does not look as RPC response, ignore this check
        except (AttributeError, TypeError):
            pass


    @memoize(expiration=CACHE_EXPIRATION)
    def getAllVmStats(self):
        vms = {}
        ret = self.checked_call(self._vdsm_api.getAllVmStats)

        # the possible missing key is handled
        # by the Optional result type transparently
        for vm in ret['result']:
            vms[vm['vmId']] = vm

        for vm in ret['items']:
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
        self.checked_call(self._vdsm_api.setBalloonTarget, uuid, target)

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
        self.checked_call(self._vdsm_api.setCpuTuneQuota, uuid, quota)
        self.checked_call(self._vdsm_api.setCpuTunePeriod, uuid, period)

    def getVmIoTunePolicy(self, vmId):
        result = self.checked_call(self._vdsm_api.getIoTunePolicy, vmId)
        return result.get('items', []).orNone()

    def getVmIoTune(self, vmId):
        result = self.checked_call(self._vdsm_api.getIoTune, vmId)
        return result.get('items', []).orNone()

    def setVmIoTune(self, vmId, tunables):
        self.checked_call(self._vdsm_api.setIoTune, vmId, tunables)

    def ksmTune(self, tuningParams):
        self.checked_call(self._vdsm_api.setKsmTune, tuningParams)

    def checked_call(self, vdsm_method, *args, **kwargs):
        try:
            response = vdsm_method(*args, **kwargs)
            self._check_status(response)
            return Optional(response)
        except socket.error as e:
            self.logger.error("Cannot connect to VDSM! {0}".format(e))
            return Optional.missing()
        except vdsmException as e:
            e.handle_exception()
            return Optional.missing()
        except jsonrpcvdscli.JsonRpcNoResponseError as e:
            self.logger.error("No response from VDSM arrived! {0}".format(e))
            return Optional.missing()


def instance(config):
    return JsonRpcVdsmInterface()
