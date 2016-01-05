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

import threading
import os.path
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
from unixrpc import UnixXmlRpcServer
from xmlrpclib import Marshaller
from types import IntType, LongType

from LogUtils import *

def big_int_marshaller(m, value, writer):
    if value >= 2**31 or value <= -2**31:
        writer("<value><i8>%d</i8></value>" % value)
    else:
        writer("<value><int>%d</int></value>" % value)

def enable_i8():
    """
    Enable i8 extension
    Python 2.7 knows how to read it, but sending needs to be configured
    """
    Marshaller.dispatch[IntType] = big_int_marshaller
    Marshaller.dispatch[LongType] = big_int_marshaller

class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

class RPCServer(threading.Thread):
    """
    The RPCServer thread provides an API for external programs to interact
    with MOM.
    """
    def __init__(self, config, momFuncs):
        threading.Thread.__init__(self, name="RPCServer")
        self.setDaemon(True)
        self.config = config
        self.momFuncs = momFuncs
        self.logger = logging.getLogger('mom.RPCServer')
        self.server = None
        self.start()

    def thread_ok(self):
        if self.server is None:
            return True
        return self.isAlive()

    def create_server(self):
        try:
            unix_port = None
            port = self.config.getint('main', 'rpc-port')
        except ValueError:
            port = None
            unix_port = self.config.get('main', 'rpc-port')
            self.logger.info("Using unix socket "+unix_port)

        if unix_port is None and (port is None or port < 0):
            return None

        if unix_port:
            self.server = UnixXmlRpcServer(unix_port)
        else:
            self.server = SimpleXMLRPCServer(("localhost", port),
                            requestHandler=RequestHandler, logRequests=0)

        self.server.register_introspection_functions()
        self.server.register_instance(self.momFuncs)

    def shutdown(self):
        if self.server is not None:
            self.server.shutdown()

    def run(self):
        try:
            self.create_server()
            if self.server is not None:
                self.logger.info("RPC Server starting")
                self.server.serve_forever()
                self.logger.info("RPC Server ending")
            else:
                self.logger.info("RPC Server is disabled")
        except Exception as e:
            self.logger.error("RPC Server crashed", exc_info=True)
