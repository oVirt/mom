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

from .vdsmCommon import memoize

from mom.HypervisorInterfaces.vdsmjsonrpcInterface import JsonRpcVdsmInterface, \
    CACHE_EXPIRATION

class JsonRpcVdsmBulkInterface(JsonRpcVdsmInterface):
    """
    JsonRpcVdsmBulkInterface extends the JsonRpcVdsmInterface and
    overrides the getIoTune and getIoTunePolicy methods so that
    the new vdsm api can be utilized
    """
    def __init__(self):
        super(JsonRpcVdsmBulkInterface, self).__init__()

    @memoize(expiration=CACHE_EXPIRATION)
    def getAllVmIoTunePolicies(self):
        ret = self.checked_call(self._vdsm_api.getAllVmIoTunePolicies)
        return ret

    def getVmIoTunePolicy(self, vmId):
        vm_io_tune_policy_info = self.getAllVmIoTunePolicies()
        result = vm_io_tune_policy_info[vmId]['policy']
        return result.orNone()

    def getVmIoTune(self, vmId):
        vm_io_tune_policy_info = self.getAllVmIoTunePolicies()
        result = vm_io_tune_policy_info[vmId]['current_values']
        return result.orNone()

def instance(config):
    return JsonRpcVdsmBulkInterface()

