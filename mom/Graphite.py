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
    def __init__(self, graphite_host, graphite_port, graphite_protocol, name):
    
      self.graphite_host = graphite_host
      self.graphite_port = graphite_port
      self.graphite_protocol = graphite_protocol
      self.vmname = name

      if graphite_protocol == "TCP":
         self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
         try:
            self.sock.connect((graphite_host, graphite_port))
         except Exception as e:
            logger = logging.getLogger('mom.Graphite')
            logger.warn("something's wrong with %s:%d. Exception is %s" % (graphite_host, graphite_port, e))

      elif graphite_protocol == "UDP":
         self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


    def __del__(self):
        if self.sock is not None:
            self.sock.close()

    def sendToGraphite(self, data):
        if self.sock is None:
            return

        for key,value in data.items():
           if self.graphite_protocol == "TCP":
              timestamp = int(time.time())
              gr_path = "direct." + socket.getfqdn() + ".mom." + self.vmname + "." + key
              self.sock.send("%s %d %d\n" % (gr_path, int(value), timestamp))
           elif self.graphite_protocol == "UDP":
              timestamp = int(time.time())
              gr_path = "direct." + socket.getfqdn() + ".mom." + self.vmname + "." + key
              self.sock.sendto( gr_path + " " + str(value) + " " + str(timestamp) + "\n" , (self.graphite_host, self.graphite_port) )

