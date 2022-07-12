#!/usr/bin/env python3

"""DConnect application class"""

import sys
import signal
import socket
import logging.handlers
from random import randint
from threading import Thread
from socketserver import ThreadingUDPServer, UDPServer

from .device_manager import DeviceManager, Device
from .server_search import ServerSearchHandler
from .tcp_server import DConnectThreadingTCPServer, DConnectHandler
from .plugins import PLUGINS, PluginInitializer
from .common.jsonconf import *
from .common.daemon import Daemon


class DConnectApp(Daemon):
    """Main application class band all components together"""
    CONFIG_SCHEMA = DictEntry('conf.json', 'Main configuration of dconnect server', False, entries=(
        DictEntry('log', 'Logger configuration', False, entries=(
            FileEntry('path', 'Path to first log file', False, '$HOME/.log/dcnnt.log', True, False),
            IntEntry('size', 'Maximum size of log file', False, 1024, 1073741824, 262144),
            IntEntry('count', 'Count of log files', False, 0, 1024, 3),
        )),
        DictEntry('self', 'Configuration of server device', False, entries=(
            IntEntry('uin', 'Unique identifier of device in network', False, 1, 0xFFFFFFF, randint(0, 1024)),
            StringEntry('name', 'Name of device in network', False, 1, 60, socket.gethostname()),
            StringEntry('description', 'Arbitrary description of device', False, 0, 200, ''),
            StringEntry('password', 'Password to access to device from clients', False, 0, 4096,
                        default=''.join(tuple(chr(randint(ord('a'), ord('z'))) for _ in range(10)))),
        )),
        IntEntry('port', 'Port for UDP and TCP sockets', False, 1, 0xFFFF, 5040),
        FileEntry('pidfile', 'Path to pidfile for daemon mode', True, '', False, False)
    ))

    def __init__(self, directory: str, foreground: bool):
        super().__init__()
        self.dev = None
        self.xdg_runtime_dir = '/tmp'
        self.directory = directory
        self.foreground = foreground
        self.environment = self.init_environment()
        self.conf = self.init_conf(os.path.join(directory, 'conf.json'))
        conf_pidfile = self.conf.get('pidfile')
        self.pidfile = conf_pidfile if conf_pidfile else os.path.join(self.xdg_runtime_dir, 'dcnnt.pid')
        self.log = self.init_logger()
        self.dm = self.plugins = self.udp = self.tcp = self.udp_thread = self.tcp_thread = None

    def pair(self):
        """Start app in pairing mode"""
        self.log.setLevel(logging.WARNING)
        self.dm = self.init_dm()
        code = str(randint(100000, 999999))
        print('App running in pairing mode')
        print(f'Pair code:\n\n    {code[:3]}-{code[3:]}    \n')
        udp = UDPServer(('0.0.0.0', self.conf['port']), ServerSearchHandler)
        udp.app = self
        udp.pairing_code = code
        udp.paired_uin = None
        signal.signal(signal.SIGINT, lambda a, b: Thread(name='Thread-UDP-Main-Shutdown', target=udp.shutdown).start())
        udp.serve_forever(0.25)
        paired_uin = udp.paired_uin
        print(f'Successful pairing with device {paired_uin}' if paired_uin else 'Pairing failed')
        udp.server_close()
        del udp
        sys.exit(0 if paired_uin else 1)

    def init(self):
        """Create various app internal entities"""
        self.dm = self.init_dm()
        self.plugins = self.init_plugins()
        self.udp = self.init_udp()
        self.tcp = self.init_tcp()
        self.udp_thread = self.tcp_thread = None

    def init_environment(self):
        """Load environment variables, add some local variables and set current directory to config dir"""
        env = {k: v for k, v in os.environ.items()}
        xdg_runtime_dir = env.get('XDG_RUNTIME_DIR', os.path.join('/', 'var', 'run', 'user', str(os.getuid())))
        if not os.path.isdir(xdg_runtime_dir):
            xdg_runtime_dir = '/tmp'
            runtime_dir = os.path.join(xdg_runtime_dir, 'dcnnt')
            os.makedirs(runtime_dir, exist_ok=True)
        else:
            runtime_dir = os.path.join(xdg_runtime_dir, 'dcnnt')
            os.makedirs(runtime_dir, exist_ok=True)
        self.xdg_runtime_dir = xdg_runtime_dir
        env['DCNNT_RUNTIME_DIR'] = runtime_dir
        env['DCNNT_CONFIG_DIR'] = self.directory
        return env

    def init_logger(self):
        """Create console and rotating file logger with parameters specified in configuration"""
        conf = self.conf['log']
        logger = logging.getLogger('dcnnt')
        logger.setLevel(logging.DEBUG)
        if conf['count'] > 0:
            logger.addHandler(logging.handlers.RotatingFileHandler(
                conf['path'], maxBytes=conf['size'], backupCount=conf['count']))
        if self.foreground:
            logger.addHandler(logging.StreamHandler(sys.stdout))
        return logger

    def init_conf(self, path):
        """Load configuration from JSON file"""
        res = ConfigLoader(self.environment, path, self.CONFIG_SCHEMA, True).load()
        if isinstance(res, dict):
            info = res['self']
            dev = Device(info['uin'], info['name'], info['description'], 'server', info['password'])
            self.dev = dev
            return res
        else:
            raise ValueError(f'Main configuration error: {res}')

    def init_dm(self):
        """Init device manager"""
        dm = DeviceManager(self, os.path.join(self.directory, 'devices'))
        dm.load()
        return dm

    def init_plugins(self):
        """Init selected plugins and load settings"""
        plugins = dict()
        plugins_dir = os.path.join(self.directory, 'plugins')
        for plg in PLUGINS:
            initer = PluginInitializer(self.environment, plugins_dir, self.log, plg)
            if initer.init_plugin():
                plugins[plg.MARK] = plg
        return plugins

    def init_udp(self):
        """Init and start UDP server"""
        server = ThreadingUDPServer(('0.0.0.0', self.conf['port']), ServerSearchHandler)
        server.app = self
        return server

    def init_tcp(self):
        """Init and start TCP server"""
        server = DConnectThreadingTCPServer(self, ('0.0.0.0', self.conf['port']), DConnectHandler)
        return server

    def on_sigint(self, *args):
        """SIGINT handler"""
        signal.signal(signal.SIGINT, lambda a, b: None)
        self.shutdown()

    def run(self):
        """Start application"""
        if not self.foreground:
            signal.signal(signal.SIGINT, self.on_sigint)
        self.log.info('START APP')
        self.udp_thread = Thread(None, self.udp.serve_forever, 'UDP-Server-Thread')
        self.log.debug('Starting UDP server...')
        self.udp_thread.start()
        self.log.debug('Starting TCP server...')
        self.tcp_thread = Thread(None, self.tcp.serve_forever, 'TCP-Server-Thread')
        self.tcp_thread.start()
        if not self.foreground:
            self.tcp_thread.join()

    def shutdown(self):
        """Stop all threads and whole application"""
        self.log.info('STOP APP')
        self.log.debug('Shutdown UDP and TCP servers')
        self.udp.shutdown()
        self.tcp.shutdown()
        self.log.debug('Waiting UDP server stop...')
        self.udp_thread.join()
        self.log.debug('Waiting TCP server stop...')
        self.tcp_thread.join()
        self.log.debug('Close TCP socket...')
        self.tcp.server_close()
        self.log.debug('Close UDP socket...')
        self.udp.server_close()
        sys.exit(0)
