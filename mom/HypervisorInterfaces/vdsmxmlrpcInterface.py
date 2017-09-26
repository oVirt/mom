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

import socket

from vdsm import vdscli

from .vdsmCommon import memoize, vdsmException
from .vdsmRpcBase import VdsmRpcBase

# Time validity of the cache in seconds
CACHE_EXPIRATION = 5


class XmlRpcVdsmInterface(VdsmRpcBase):
    """
    vdsmInterface provides a wrapper for the VDSM API so that VDSM-
    related error handling can be consolidated in one place.  An instance of
    this class provides a single VDSM connection that can be shared by all
    threads.
    """

    def __init__(self):
        super(XmlRpcVdsmInterface, self).__init__()
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
            raise vdsmException(response, self._logger)

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

    def setVmBalloonTarget(self, uuid, target):
        try:
            response = self.vdsm_api.setBalloonTarget(uuid, target)
            self._check_status(response)
        except socket.error as e:
            self.handle_connection_error(e)
        except vdsmException, e:
            e.handle_exception()

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

    def getVmIoTunePolicy(self, vmId):
        try:
            result = self.vdsm_api.getIoTunePolicy(vmId)
            self._check_status(result)
        except socket.error as e:
            self.handle_connection_error(e)
            return None
        except vdsmException, e:
            e.handle_exception()
            return None

        return result.get('ioTunePolicy', [])

    def getVmIoTune(self, vmId):
        try:
            result = self.vdsm_api.getIoTune(vmId)
            self._check_status(result)
        except socket.error as e:
            self.handle_connection_error(e)
            return None
        except vdsmException, e:
            e.handle_exception()
            return None

        return result.get('ioTune', [])

    def setVmIoTune(self, vmId, tunables):
        try:
            response = self.vdsm_api.setIoTune(vmId, tunables)
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
        self._logger.error("Cannot connect to VDSM! {0}".format(e))

def instance(config):
    return XmlRpcVdsmInterface()
