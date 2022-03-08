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

from collections import namedtuple
import threading
import time
import logging
from mom.GuestMonitor import GuestMonitor
from mom.GuestMonitor import GuestMonitorThread


GuestData = namedtuple('GuestData', ['monitor', 'thread'])


def is_running(guest):
    # in this the guest manager must manage the guest
    # monitors, so they are always 'running'
    if guest.thread is None:
        return True
    return guest.thread.is_alive()


class GuestManager(threading.Thread):
    """
    The GuestManager thread maintains a list of currently active guests on the
    system.  When a new guest is discovered, a new GuestMonitor is spawned.
    When GuestMonitors stop running, they are removed from the list.
    """
    def __init__(self, config, hypervisor_iface):
        threading.Thread.__init__(self, name='GuestManager')
        self.daemon = True
        self.config = config
        self.hypervisor_iface = hypervisor_iface
        self.logger = logging.getLogger('mom.GuestManager')
        self.guests = {}
        self.guests_lock = threading.Lock()
        self._threaded = config.getboolean('main',
                                           'guest-manager-multi-thread')

    def interrogate(self):
        """
        Interrogate all active GuestMonitors
        Return: A dictionary of Entities, indexed by guest id
        """
        ret = {}
        with self.guests_lock:
            for id, guest in self.guests.items():
                entity = guest.monitor.interrogate()
                if entity is not None:
                    ret[id] = entity

        return ret

    def rpc_get_active_guests(self):
        ret = []
        with self.guests_lock:
            for id, guest in self.guests.items():
                if guest.monitor.isReady():
                    name = guest.monitor.getGuestName()
                    if name is not None:
                        ret.append(name)

        return ret

    def run(self):
        try:
            self.logger.info("Guest Manager starting: %s",
                "multi-thread" if self._threaded else "single-thread");
            interval = self.config.getint('main', 'guest-manager-interval')
            while self.config.getint('__int__', 'running') == 1:
                domain_list = self.hypervisor_iface.getVmList()
                if domain_list is not None:
                    self._spawn_guest_monitors(domain_list)
                    self._check_guest_monitors(domain_list)

                if not self._threaded:
                    self._collect_from_guest_monitors()

                time.sleep(interval)

            if self._threaded:
                self._wait_for_guest_monitors()
        except Exception as e:
            self.logger.error("Guest Manager crashed", exc_info=True)
        else:
            self.logger.info("Guest Manager ending")

    def _spawn_guest_monitors(self, domain_list):
        """
        Get the list of running domains and spawn GuestMonitors for any guests
        we are not already tracking.  The GuestMonitor constructor might block
        so don't hold guests_sem while calling it.
        """
        with self.guests_lock:
            spawn_list = set(domain_list) - set(self.guests)

        new_guests = {}
        for id in spawn_list:
            info = self.hypervisor_iface.getVmInfo(id)
            if info is None:
                self.logger.error("Failed to get guest:%s information -- monitor "\
                    "can't start", id)
                continue

            new_guests[id] = self._create_monitor(info)

        if new_guests:
            with self.guests_lock:
                for id, guest in new_guests.items():
                    if is_running(guest):
                        self._register_guest(id, guest)

    def _create_monitor(self, info):
        guest = GuestMonitor(self.config, info, self.hypervisor_iface)
        if self._threaded:
            thread = GuestMonitorThread(info, guest)
            thread.start()
        else:
            thread = None
        return GuestData(guest, thread)

    def _wait_for_guest_monitors(self):
        """
        Wait for GuestMonitors to exit
        """
        while True:
            with self.guests_lock:
                if self.guests:
                    id, guest = self.guests.popitem()
                else:
                    id = None

            if id is not None:
                if guest.thread is not None:
                    guest.thread.join(0)
            else:
                break

    def _check_guest_monitors(self, domain_list):
        """
        Check for stale and/or deceased guest monitors and remove them.
        """
        with self.guests_lock:
            # Iterating over a copy of dictionary, otherwise
            # deleting an element will raise RuntimeError
            for id, guest in self.guests.copy().items():
                if guest.thread is None:
                    # no thread to babysit
                    # but maybe a Monitor to shutdown
                    if id not in domain_list:
                        self._unregister_guest(id)
                # Check if the thread has died
                elif not guest.thread.is_alive():
                    del self.guests[id]
                # Check if the domain has ended according to hypervisor interface
                elif id not in domain_list:
                    self._unregister_guest(id)

    def _collect_from_guest_monitors(self):
        with self.guests_lock:
            for uuid, guest in self.guests.items():
                if guest.monitor.should_run():
                    guest.monitor.collect()

    def _register_guest(self, uuid, guest):
        if uuid not in self.guests:
            self.logger.debug('added monitor for guest %s', uuid)
            self.guests[uuid] = guest
        else:
            del guest

    def _unregister_guest(self, uuid):
        if uuid in self.guests:
            guest = self.guests.pop(uuid)
            self.logger.debug('removed monitor for guest %s', uuid)
            guest.monitor.terminate()
