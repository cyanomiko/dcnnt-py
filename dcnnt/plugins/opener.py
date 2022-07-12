import subprocess

from .base import BaseFilePlugin, PluginFail
from ..common import *


class OpenerPlugin(BaseFilePlugin):
    """Open files, URLs and other data from client"""
    MARK = b'open'
    NAME = 'OpenerPlugin'
    MAIN_CONF = dict()
    DEVICE_CONFS = dict()
    FILE_CONFIG_SCHEMA = DictEntry('file', 'Configuration for file opener', False, entries=(
        DirEntry('download_directory', 'Directory to store files and data to show',
                 False, '/tmp/dcnnt/to_open', True, False),
        TemplateEntry('default_cmd', 'Default command to open file', False, 0, 4096, 'xdg-open "{path}"',
                      replacements=(Rep('path', 'Path to saved file', True),)),
    ))
    LINK_CONFIG_SCHEMA = DictEntry('link', 'Configuration for web link opener', False, entries=(
        TemplateEntry('default_cmd', 'Default command to open web URL', False, 0, 4096, 'xdg-open "{url}"',
                      replacements=(Rep('url', 'Web URL (like http://example.com)', True),)),
    ))
    CONFIG_SCHEMA = DictEntry('open.conf.json', 'Common configuration for opener plugin', False, entries=(
        IntEntry('uin', 'UIN of device for which config will be applied', True, 1, 0xFFFFFFF, None),
        FILE_CONFIG_SCHEMA, LINK_CONFIG_SCHEMA
    ))

    def handle_open_file(self, request):
        """Receive and show file from client"""
        path = self.receive_file(request, self.conf(('file', 'download_directory')))
        on_download = self.conf(('file', 'default_cmd'))
        command = on_download.format(path=path)
        self.log('Execute: "{}"'.format(command))
        subprocess.call(command, shell=True)

    def handle_open_link(self, request):
        """Open URL received from client"""
        url = request.params.get('link')
        if not isinstance(url, str):
            raise PluginFail('No "link" param in request')
        self.rpc_send(RPCResponse(request.id, dict(code=0, message='OK')))
        command = self.conf(('link', 'default_cmd')).format(url=url)
        self.log('Execute: "{}"'.format(command))
        subprocess.call(command, shell=True)

    def process_request(self, request: RPCRequest):
        if request.method == 'open_file':
            self.handle_open_file(request)
        elif request.method == 'open_link':
            self.handle_open_link(request)
