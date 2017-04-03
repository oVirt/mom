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

from .vdsmCommon import memoize

from mom.HypervisorInterfaces.vdsmxmlrpcInterface import XmlRpcVdsmInterface, \
    CACHE_EXPIRATION

from mom.optional import Optional

class XmlRpcVdsmBulkInterface(XmlRpcVdsmInterface):
    """
    XmlRpcVdsmBulkInterface extends the XmlRpcVdsmInterface and
    overrides the getIoTune and getIoTunePolicy methods so that
    the new vdsm api can be utilized
    """

    def __init__(self):
        super(XmlRpcVdsmBulkInterface, self).__init__()

    @memoize(expiration=CACHE_EXPIRATION)
    def getAllVmIoTunePolicies(self):
        try:
            ret = self.vdsm_api.getAllVmIoTunePolicies()
            self._check_status(ret)
        except socket.error as e:
            self.handle_connection_error(e)
            return Optional.empty()
        except vdsmException as e:
            e.handle_exception()
            return Optional.empty()

        vms = ret['io_tune_policies_dict']
        return Optional(vms)

    def getVmIoTunePolicy(self, vmId):
        vm_io_tune_policy_info = self.getAllVmIoTunePolicies()
        result = vm_io_tune_policy_info[vmId]['policy']
        return result.orNone()

    def getVmIoTune(self, vmId):
        vm_io_tune_policy_info = self.getAllVmIoTunePolicies()
        result = vm_io_tune_policy_info[vmId]['current_values']
        return result.orNone()

def instance(config):
    return XmlRpcVdsmBulkInterface()
