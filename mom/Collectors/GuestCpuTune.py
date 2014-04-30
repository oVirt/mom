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
class GuestCpuTune(Collector):
    """
    This Collector uses hypervisor interface to collect guest cpu info

    vcpu_quota - Libvirt's vcpu_quota (http://libvirt.org/formatdomain.html#elementsCPUTuning)
    vcpu_period - Libvirt's vcpu_period (http://libvirt.org/formatdomain.html#elementsCPUTuning)
    vcpu_user_limit - The user selected value for limiting the vm cpu
        consumption, this number refers to a percentage value [0 -100].
    vcpu_count - Number of cpus on the vm.
    """
    def getFields(self=None):
        return set(['vcpu_quota', 'vcpu_period', 'vcpu_user_limit', 'vcpu_count'])

    def __init__(self, properties):
        self.hypervisor_iface = properties['hypervisor_iface']
        self.uuid = properties['uuid']
        self.logger = logging.getLogger('mom.Collectors.CpuTuneInfo')
        self.cpu_tune_info_available = True

    def stats_error(self, msg):
        """
        Only print stats interface errors one time when we first discover a
        problem.  Otherwise the log will be overrun with noise.
        """
        if self.cpu_tune_info_available:
            self.logger.debug(msg)
        self.cpu_tune_info_available = False

    def collect(self):
        stat = self.hypervisor_iface.getVmCpuTuneInfo(self.uuid)

        if stat == None:
            self.stats_error('getVmCpuTuneInfo() is not ready')
        else:
            self.cpu_tune_info_available = True

        return stat
