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

class HostCpu(Collector):
    """
    This Collector uses the /proc/cpuinfo file to retrieve CPU info for the host.
    Currently it only retrieve the number of CPUs in the host into 'cpu_count'
    """

    def __init__(self, properties):
        self.cpuinfo = open_datafile("/proc/cpuinfo")

    def __del__(self):
        if self.cpuinfo is not None:
            self.cpuinfo.close()

    def collect(self):
        self.cpuinfo.seek(0)

        contents = self.cpuinfo.read()
        cpu_count = count_occurrences("^processor.*:.*", contents)

        data = { 'cpu_count': cpu_count }
        return data

    def getFields(self=None):
        return set(['cpu_count'])
