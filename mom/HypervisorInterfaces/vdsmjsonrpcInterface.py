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

import socket

from vdsm import jsonrpcvdscli

from .vdsmCommon import memoize, vdsmException
from .vdsmRpcBase import VdsmRpcBase

from mom.optional import Optional

# Time validity of the cache in seconds
CACHE_EXPIRATION = 5


class JsonRpcVdsmInterface(VdsmRpcBase):
    """
    vdsmInterface provides a wrapper for the VDSM API so that VDSM-
    related error handling can be consolidated in one place.  An instance of
    this class provides a single VDSM connection that can be shared by all
    threads.
    """

    def __init__(self):
        super(JsonRpcVdsmInterface, self).__init__()
        self._vdsm_api = self.checked_call(jsonrpcvdscli.connect)\
                .orRaise(RuntimeError, 'No connection to VDSM.')

        self.checked_call(self._vdsm_api.ping)

    def _check_status(self, response):
        try:
            if response['status']['code']:
                raise vdsmException(response, self._logger)

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

    def setVmBalloonTarget(self, uuid, target):
        self.checked_call(self._vdsm_api.setBalloonTarget, uuid, target)

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
            self._logger.error("Cannot connect to VDSM! {0}".format(e))
            return Optional.missing()
        except vdsmException as e:
            e.handle_exception()
            return Optional.missing()
        except jsonrpcvdscli.JsonRpcNoResponseError as e:
            self._logger.error("No response from VDSM arrived! {0}".format(e))
            return Optional.missing()


def instance(config):
    return JsonRpcVdsmInterface()
