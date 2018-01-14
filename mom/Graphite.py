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

import time
import ConfigParser
import socket
import logging

class Graphite:
    def __init__(self, graphite_host, graphite_port, name):
        self.sock = socket.socket()
        try:
            self.sock.connect((graphite_host, graphite_port))
            self.vmname = name
        except Exception as e:
            logger = logging.getLogger('mom.Graphite')
            logger.warn("something's wrong with %s:%d. Exception is %s" % (graphite_host, graphite_port, e))

    def __del__(self):
        if self.sock is not None:
            self.sock.close()

    def sendToGraphite(self, data):
        if self.sock is None:
            return

        for key,value in data.items():
           timestamp = int(time.time())
           gr_path = socket.getfqdn() + ".mom." + self.vmname + "." + key
           self.sock.send("%s %d %d\n" % (gr_path, int(value), timestamp))
