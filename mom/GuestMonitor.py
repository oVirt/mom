# Memory Overcommitment Manager
# Copyright (C) 2010 Adam Litke, IBM Corporation
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

import six
import threading
import time
import logging
from mom.Monitor import Monitor
from mom.Collectors import Collector


class GuestMonitor(Monitor):
    """
    A GuestMonitor thread collects and reports statistics about 1 running guest
    """
    def __init__(self, config, info, hypervisor_iface):
        self.config = config
        self.logger = logging.getLogger('mom.GuestMonitor')
        self.interval = self.config.getint('main', 'guest-monitor-interval')

        Monitor.__init__(self, config, info['name'])
        with self.data_lock:
            self.properties.update(info)
            self.properties['hypervisor_iface'] = hypervisor_iface

        collector_list = self.config.get('guest', 'collectors')
        self.collectors = Collector.get_collectors(collector_list,
                            self.properties, self.config)
        if self.collectors is None:
            self.logger.error("Guest Monitor initialization failed")

    def getGuestName(self):
        """
        Provide structured access to the guest name without calling hypervisor
        interface.
        """
        return self.properties.get('name')


class GuestMonitorThread(threading.Thread):
    def __init__(self, info, monitor):
        threading.Thread.__init__(self)

        name = "GuestMonitor-%s" % info['name']
        if six.PY2:
            # In python 2 the name should not have type 'unicode'.
            # The name is only used for logging, so it should
            # be safe to represent it in utf-8 encoding.
            name = name.encode('utf-8')

        self.setName(name)
        self.daemon = True
        self.logger = logging.getLogger('mom.GuestMonitor.Thread')

        self._mon = monitor

    def run(self):
        try:
            self.logger.info("%s starting", self.name)
            while self._mon.should_run():
                self._mon.collect()
                time.sleep(self._mon.interval)
        except Exception:
            self.logger.exception("%s crashed", self.name)
        else:
            self.logger.info("%s ending", self.name)
