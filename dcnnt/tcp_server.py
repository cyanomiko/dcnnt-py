import time
import socket
from socketserver import TCPServer, ThreadingMixIn, BaseRequestHandler

from .common import encrypt, decrypt


class DConnectThreadingTCPServer(ThreadingMixIn, TCPServer):
    """Python TCP server with link to app class"""

    def __init__(self, app, address, handler_cls):
        self.allow_reuse_address = True
        super().__init__(address, handler_cls)
        self.app = app


class DConnectHandler(BaseRequestHandler):
    """Parse header, do authentication routines, then create plugin instance to work with connection"""
    TIMEOUT = 10

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)
        self.salt_send = bytes((0, ) * 32)  # get_random_bytes(32)
        self.salt_recv = None
        self.sock = self.request

    def recv(self, length):
        """Receive @length bytes from socket"""
        buf = bytearray()
        left = length
        timeout = 60
        start = time.time()
        while left > 0:
            try:
                data = self.sock.recv(left)
            except socket.timeout:
                return
            buf += data
            left = length - len(buf)
            if left > 0:
                if time.time() - start > timeout:
                    return
                time.sleep(.00001)
        return None if left else bytes(buf)

    def setup(self):
        self.sock = self.request
        self.sock.settimeout(self.TIMEOUT)

    def create_header(self, dev_self, plugin_mark, source):
        """Create connection header to send to device as auth response"""
        # Header format:
        #     ver - 8B, enc - 8B, dst - 4B, src - 4B, plg - 36B
        return b''.join((b'\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0',
                         source.uin.to_bytes(4, 'big'),
                         dev_self.uin.to_bytes(4, 'big'),
                         encrypt(plugin_mark, source.key_send)))

    def finish(self):
        """Close connection and free socket address"""
        self.sock.close()

    def handle(self):
        # Header format:
        #     ver - 8B, enc - 8B, dst - 4B, src - 4B, plg - 36B
        app = self.server.app
        log = app.log
        try:
            header = self.recv(60)  # 60 - length of header
            if header is None:
                log.warning('Header receive timeout')
                return
            dst = int.from_bytes(header[16:20], 'big')
            src = int.from_bytes(header[20:24], 'big')
            if dst != app.dev.uin:
                log.warning('Destination UIN != app UIN: {} != {}'.format(dst, app.dev.uin))
                return
            source = app.dm.get(src)
            if source is None:
                log.warning('Unknown source UIN: {}'.format(src))
                return
            if source.key_recv is None:
                log.warning('No key specified for device with UIN: {}'.format(src))
                return
            plg = decrypt(header[24:], source.key_recv)
            if plg is None:
                log.warning('Incorrect password for device with UIN: {}'.format(src))
                return
            plugin = app.plugins.get(plg)
            if plugin is None:
                log.warning('Unknown plugin mark: {}'.format(plg))
                return
            response = self.create_header(app.dev, plg, source)
            log.debug('Send header response - {} bytes'.format(len(response)))
            self.sock.sendall(response)
            log.debug('Enter plugin: "{}"'.format(plugin.NAME))
            plugin(app, self, source).main()
            log.debug('Exit plugin: "{}"'.format(plugin.NAME))
        except Exception as e:
            self.server.app.log.exception(e)
            self.finish()
            raise e
