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

from mom.Collectors.Collector import *
from mom.HypervisorInterfaces.HypervisorInterface import *


class GuestMemory(Collector):
    """
    This Collector uses hypervisor interface to collect guest memory statistics
    """
    def getFields(self):
        return set(( 'mem_available', 'mem_unused', 'major_fault', 'minor_fault',
                     'swap_in', 'swap_out' ))

    def getOptionalFields(self):
        return set(["swap_total", "swap_usage"])

    def __init__(self, properties):
        self.hypervisor_iface = properties['hypervisor_iface']
        self.uuid = properties['uuid']
        self.logger = logging.getLogger('mom.Collectors.GuestMemory')
        self.hypervisor_iface.startVmMemoryStats(self.uuid)
        self.memstats_available = True

    def stats_error(self, msg):
        """
        Only print stats interface errors one time when we first discover a
        problem.  Otherwise the log will be overrun with noise.
        """
        if self.memstats_available:
            self.logger.warn(msg)
        self.memstats_available = False

    def collect(self):
        try:
            stat = self.hypervisor_iface.getVmMemoryStats(self.uuid)
        except HypervisorInterfaceError, e:
            self.stats_error('getVmMemoryStats(): %s' % e)
            # We don't raise a CollectionError here because a different
            # Collector (such as GuestQemuAgent) may be able to get them.
            # If not, the Monitor's collect method will detect the missing
            # fields anyway.
            return {}
        else:
            self.memstats_available = True
            return stat
