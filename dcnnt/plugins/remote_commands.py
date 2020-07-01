import subprocess

from .base import Plugin
from ..common import *


class RemoteCommandsPlugin(Plugin):
    """Receive file from phone"""
    MARK = b'rcmd'
    NAME = 'RemoteCommandsPlugin'
    MAIN_CONF = dict()
    DEVICE_CONFS = dict()
    CONFIG_SCHEMA = DictEntry('rcmd.conf.json', 'Configuration for remote commands file', False, entries=(
        IntEntry('uin', 'UIN of device for which config will be applied', True, 1, 0xFFFFFFF, None),
        ListEntry('menu', 'List of remote commands', False, 0, 1073741824, (),
                  entry=DictEntry('menu[]', 'Description of shared directory', False, entries=(
                      StringEntry('name', 'Displayed name for remote command', False, 0, 60, 'Do nothing'),
                      StringEntry('method', 'Method to execute command', True, 0, 1024, None),
                      StringEntry('cmd', 'Remote called command itself', True, 0, 1073741824, None),
                  )))
    ))
    PART = 65532

    def __init__(self, app, handler, device):
        super().__init__(app, handler, device)
        self.remote_commands = dict()
        self.remote_commands_index = list()
        for command in self.conf('menu'):
            name, description, cmd, method = map(command.get, ('name', 'description', 'cmd', 'method'))
            if cmd is not None and method is not None:
                identifier = str(hash(cmd + method))
                self.remote_commands[identifier] = command
            else:
                identifier = None
            self.remote_commands_index.append(dict(index=identifier, name=name, description=description))

    def handle_exec(self, request):
        """Run command and send message with bool execution result"""
        command = self.remote_commands.get(request.params.get('index', None))
        if command is None:
            self.rpc_send(RPCResponse(request.id, dict(result=False, message='No such command')))
        else:
            method, cmd = command.get('method'), command.get('cmd')
            if method == 'shell':
                self.log('Execute shell command: "{}"'.format(cmd))
                try:
                    subprocess.check_call(cmd, shell=True)
                except Exception as e:
                    self.logger.exception(e)
                    self.rpc_send(RPCResponse(request.id, dict(result=False, message='Failed')))
                else:
                    self.rpc_send(RPCResponse(request.id, dict(result=True, message='OK')))
            else:
                self.rpc_send(RPCResponse(request.id, dict(result=False, message='No such method')))

    def main(self):
        while True:
            request = self.rpc_read()
            self.log(request)
            if request is None:
                self.log('No more requests, stop handler')
                return
            if request.method == 'list':
                self.rpc_send(RPCResponse(request.id, self.remote_commands_index))
            elif request.method == 'exec':
                self.handle_exec(request)
