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

class CpuTune:
    """
    Controller that uses the hypervisor interface to manipulate
    the cpu tuning parameters.
    The current parameters that can be set are:
    vcpu_quota: The optional quota element specifies the maximum allowed bandwidth(unit: microseconds).
    vcpu_period: The optional period element specifies the enforcement interval(unit: microseconds).
    For more: http://libvirt.org/formatdomain.html#elementsCPUTuning
    """
    def __init__(self, properties):
        self.hypervisor_iface = properties['hypervisor_iface']
        self.logger = logging.getLogger('mom.Controllers.Cputune')

    def get_changed_val(self, val, prev_val):
        return val if val != prev_val and val is not None else prev_val

    def process_guest(self, guest):
        quota = guest.GetControl('vcpu_quota')
        period = guest.GetControl('vcpu_period')
        prev_quota = guest.vcpu_quota
        prev_period = guest.vcpu_period
        quota = self.get_changed_val(quota, prev_quota)
        period = self.get_changed_val(period, prev_period)
        # is something changed, tune the cpu parameters
        if quota != prev_quota or period != prev_period:
            quota = int(quota)
            period = int(period)
            uuid = guest.Prop('uuid')
            name = guest.Prop('name')
            self.logger.info("CpuTune guest:%s from quota:%s period:%s to quota:%s period:%s", \
                    name, prev_quota, prev_period, quota, period)
            self.hypervisor_iface.setVmCpuTune(uuid, quota, period)

    def process(self, host, guests):
        for guest in guests:
            self.process_guest(guest)
