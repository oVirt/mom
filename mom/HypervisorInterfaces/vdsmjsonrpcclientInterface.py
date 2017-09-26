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

from vdsm import client

from .vdsmCommon import memoize
from .vdsmRpcBase import VdsmRpcBase

from mom.optional import Optional

# Time validity of the cache in seconds
CACHE_EXPIRATION = 5


class JsonRpcVdsmClientInterface(VdsmRpcBase):
    def __init__(self):
        super(JsonRpcVdsmClientInterface, self).__init__()
        self._vdsm_api = client.connect(host="localhost")
        self.checked_call(self._vdsm_api.Host.ping2)

    @memoize(expiration=CACHE_EXPIRATION)
    def getAllVmStats(self):
        ret = self.checked_call(self._vdsm_api.Host.getAllVmStats)
        return {vm['vmId']: vm for vm in ret}

    @memoize(expiration=CACHE_EXPIRATION)
    def getAllVmIoTunePolicies(self):
        return self.checked_call(self._vdsm_api.Host.getAllVmIoTunePolicies)

    def setVmBalloonTarget(self, uuid, target):
        self.checked_call(
            self._vdsm_api.VM.setBalloonTarget,
            vmID=uuid,
            target=target
        )

    def setVmCpuTune(self, uuid, quota, period):
        self.checked_call(
            self._vdsm_api.VM.setCpuTuneQuota,
            vmID=uuid,
            quota=quota
        )
        self.checked_call(
            self._vdsm_api.VM.setCpuTunePeriod,
            vmID=uuid,
            period=period
        )

    def getVmIoTunePolicy(self, vmId):
        vm_io_tune_policy_info = self.getAllVmIoTunePolicies()
        result = vm_io_tune_policy_info[vmId]['policy']
        return result.orNone()

    def getVmIoTune(self, vmId):
        vm_io_tune_policy_info = self.getAllVmIoTunePolicies()
        result = vm_io_tune_policy_info[vmId]['current_values']
        return result.orNone()

    def setVmIoTune(self, vmId, tunables):
        self.checked_call(
            self._vdsm_api.VM.setIoTune,
            vmID=vmId,
            tunables=tunables
        )

    def ksmTune(self, tuningParams):
        self.checked_call(
            self._vdsm_api.Host.setKsmTune,
            tuningParams=tuningParams
        )

    def checked_call(self, vdsm_method, *args, **kwargs):
        try:
            return Optional(vdsm_method(*args, **kwargs))

        except client.ServerError as e:
            self._logger.error(str(e))

        return Optional.missing()


def instance(config):
    return JsonRpcVdsmClientInterface()
