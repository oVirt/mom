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
import datetime
from mom.Collectors.Collector import *

class HostTime(Collector):
    """
    This Collector returns host time statistics using python datetime module.
    These stats would be useful for creating a time based policy.
    Time interval at which this collector is run is controlled in config file.
    It provides the following stats -
        time_year, time_month, time_day, time_hour,
        time_minute, time_second, time_microsecond
    """
    def __init__(self, properties):
        pass

    def collect(self):
        now = datetime.datetime.now()
        data = { 'time_year': now.year, 'time_month': now.month, \
                 'time_day': now.day, 'time_hour': now.hour, 'time_minute': now.minute, \
                 'time_second': now.second, 'time_microsecond': now.microsecond }
        return data

    def getFields(self=None):
        return set(['time_year', 'time_month', 'time_day', 'time_hour', \
                   'time_minute', 'time_second', 'time_microsecond'])
