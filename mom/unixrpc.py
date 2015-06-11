import os
import SocketServer
import SimpleXMLRPCServer
from xmlrpclib import ServerProxy, Transport
import httplib
import socket
import string
import base64

class UnixXmlRpcHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    disable_nagle_algorithm = False

# This class implements a XML-RPC server that binds to a UNIX socket. The path
# to the UNIX socket to create methods must be provided.
class UnixXmlRpcServer(SocketServer.UnixStreamServer,
                       SimpleXMLRPCServer.SimpleXMLRPCDispatcher):
    address_family = socket.AF_UNIX
    allow_address_reuse = True

    def __init__(self, sock_path, request_handler=UnixXmlRpcHandler,
                 logRequests=0):
        if os.path.exists(sock_path):
            os.unlink(sock_path)
        self.logRequests = logRequests
        SimpleXMLRPCServer.SimpleXMLRPCDispatcher.__init__(self,
                                                           encoding=None,
                                                           allow_none=1)
        SocketServer.UnixStreamServer.__init__(self, sock_path,
                                               request_handler)

# This class implements a XML-RPC client that connects to a UNIX socket. The
# path to the UNIX socket to create must be provided.
class UnixXmlRpcClient(ServerProxy):
    def __init__(self, sock_path):
        # We can't pass funny characters in the host part of a URL, so we
        # encode the socket path in base16.
        ServerProxy.__init__(self, 'http://' + base64.b16encode(sock_path),
                             transport=UnixXmlRpcTransport(),
                             allow_none=1)

class UnixXmlRpcTransport(Transport):
    def make_connection(self, host):
        return UnixXmlRpcHttpConnection(host)

class UnixXmlRpcHttpConnection(httplib.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(base64.b16decode(self.host))


