import glob
from abc import ABC
from logging import Logger, DEBUG, INFO, WARNING, ERROR

from ..common import *


class PluginInitializer:
    """Facility to set some static variables for plugin classes"""

    def __init__(self, environment, plugin_dir, log, cls):
        self.environment, self.plugin_dir, self.log, self.cls = environment, plugin_dir, log, cls

    def init_plugin(self):
        """Load plugin configurations and set up class to using in app"""
        name = self.cls.NAME
        mark = self.cls.MARK.decode('ascii')
        main_conf_path = os.path.join(self.plugin_dir, '{}.conf.json'.format(mark))
        res = ConfigLoader(self.environment, main_conf_path, self.cls.CONFIG_SCHEMA, True).load()
        if isinstance(res, str):
            self.log.error(f'Plugin "{name}" init fail: {res}')
            return False
        self.cls.MAIN_CONF = res
        for path in glob.glob(os.path.join(self.plugin_dir, '*.{}.conf.json'.format(mark))):
            res = ConfigLoader(self.environment, path, self.cls.CONFIG_SCHEMA, False).load()
            if isinstance(res, str):
                self.log.warning(f'Plugin "{name}" dev conf fail: {res}')
            else:
                if res.get('device') is not None:
                    self.cls.DEVICE_CONFS[res['device']] = res
                else:
                    self.log.warning(f'Plugin "{name}" dev conf fail: no UIN set in device config')
        try:
            return self.cls.post_init()
        except Exception as e:
            self.log.error('Initialization error for plugin {}'.format(name))
            self.log.exception(e)
        return False


class HandlerExit(Exception):
    """Raising of this exception causes RPC handler exit and normal response sending"""

    def __init__(self, response: RPCResponse):
        self.response = response
        self.message = response.result.get('message', str(response.result))

    @classmethod
    def new(cls, request: RPCRequest, code: int, message: str):
        """Create typical HandlerExit with code-message result response"""
        return cls(RPCResponse(request.id, dict(code=code, message=message)))


class HandlerFail(Exception):
    """Raising of this exception causes RPC handler exit, no any response sent"""

    def __init__(self, message: str):
        self.message = message


class PluginFail(HandlerFail):
    """Raising of this exception causes plugin loop exit, no any response sent"""


class Plugin:
    """Base plugin class"""
    MARK = b'\0\0\0\0'
    NAME = ''
    CONF_SCHEMA = None
    DEFAULT_CONF = dict(device=None)
    MAIN_CONF = dict()
    DEVICE_CONFS = dict()

    def __init__(self, app, handler, device):
        self.app, self.logger, self.handler, self.sock, self.device = app, app.log, handler, handler.sock, device

    def log(self, message, level: int = INFO):
        """Make log record with specified level"""
        self.logger.log(level, f'[{self.NAME}] {message}')

    @classmethod
    def post_init(cls):
        """Plugin-specific initialization, this function is called by plugin manager in the end of plugin init"""
        return True

    def conf(self, path):
        """Get value from config using path - key or key sequence.
        If uin is integer - try get from device-specific conf"""
        uin = self.device.uin
        conf = self.DEVICE_CONFS.get(uin, self.MAIN_CONF)
        if not isinstance(path, (tuple, list)):
            path = (path, )
        node = conf
        for i in path:
            try:
                node = node[i]
            except (KeyError, IndexError):
                return
            except TypeError:
                self.log('TypeError in plugin {} while config value {}'.format(self.NAME, path), ERROR)
                return
        return node

    def read(self) -> Optional[bytes]:
        """Read message from socket"""
        size_raw = self.handler.recv(4)
        if size_raw is None:
            return None
        encrypted = self.handler.recv(int.from_bytes(size_raw, 'big'))
        if encrypted is None:
            return
        # key = SHA256.new(self.device.key_recv + self.handler.salt_recv)
        key = self.device.key_recv
        return decrypt(encrypted, key)

    def send(self, buf: bytes):
        """Send message to socket"""
        # key = SHA256.new(self.device.key_send + self.handler.salt_send)
        self.sock.sendall((len(buf) + 32).to_bytes(4, 'big') + encrypt(buf, self.device.key_send))

    def rpc_read(self) -> Optional[RPCRequest]:
        """Read JSON-RPC 2.0 requests/notifications"""
        request_raw = self.read()
        if request_raw is None:
            return
        self.log(request_raw, DEBUG)
        try:
            return RPCRequest.from_dict(json.loads(request_raw.decode()))
        except BaseException as e:
            self.log(e, WARNING)

    def rpc_send(self, obj: RPCObject):
        """Send JSON-RPC 2.0 response, notification or request"""
        try:
            serialized_obj = json.dumps(obj.to_dict())
            self.send(serialized_obj.encode())
            self.log("Sent: {}".format(serialized_obj), DEBUG)
        except BaseException as e:
            self.log(e, WARNING)

    def process_request(self, request: RPCRequest):
        """Process one RPC request"""
        raise NotImplementedError

    def main(self):
        """Entry point for plugins called in TCP handler"""
        while True:
            request = self.rpc_read()
            self.log(request)
            if request is None:
                self.log('No more requests, stop handler')
                return
            try:
                self.process_request(request)
            except HandlerExit as e:
                self.log(f'Handler exit: {e.message}')
                self.rpc_send(e.response)
            except PluginFail as e:
                self.log(f'Plugin fail: {e.message}')
                return
            except HandlerFail as e:
                self.log(f'Handler fail: {e.message}')
            except BaseException as e:
                self.logger.error(f'Exception {e}')
                self.logger.exception(e)
                return


class BaseFilePlugin(Plugin, ABC):
    """Common option for files with file transfer support"""
    PART = 65532

    def receive_file(self, request: RPCRequest, download_directory: str) -> str:
        """Receive and save file from client device"""
        try:
            name, size = request.params['name'], request.params['size']
        except KeyError as e:
            raise HandlerFail(f'KeyError {e}')
        path = os.path.join(download_directory, name)
        self.log(f'Receiving {size} bytes to file {path}')
        self.rpc_send(RPCResponse(request.id, dict(code=0, message='OK')))
        wrote = 0
        with open(path, 'wb') as f:
            while wrote < size:
                buf = self.read()
                if buf is None:
                    raise HandlerFail(f'File receiving aborted ({wrote} bytes received)')
                if len(buf) == 0:
                    req = self.rpc_read()
                    if req.method == "cancel":
                        raise HandlerExit.new(request, 1, 'Canceled')
                wrote += len(buf)
                f.write(buf)
        self.log(f'File received ({wrote} bytes)', INFO)
        self.rpc_send(RPCResponse(request.id, dict(code=0, message='OK')))
        return path

    def send_file(self, request: RPCRequest, path: str, size: Optional[int] = None):
        """Common function to send file to client"""
        if not os.path.isfile(path):
            raise HandlerExit.new(request, 2, 'No such file')
        file_size = os.path.getsize(path)
        result_init = dict(code=0, message='OK')
        if size is not None:
            if file_size != size:
                raise HandlerExit.new(request, 2, 'Size mismatch')
        else:
            result_init['size'] = file_size
        self.rpc_send(RPCResponse(request.id, result_init))
        with open(path, 'rb') as f:
            self.log('Start file transmission')
            while True:
                chunk = f.read(self.PART)
                if len(chunk) == 0:
                    break
                self.send(chunk)
                # self.log('Sent {} bytes...'.format(len(chunk)))

