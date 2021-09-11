import subprocess

from .base import BaseFilePlugin, PluginFail
from ..common import *


class SyncPlugin(BaseFilePlugin):
    """Sync files and other data between client and server"""
    MARK = b'sync'
    NAME = 'SyncPlugin'
    MAIN_CONF = dict()
    DEVICE_CONFS = dict()
    DIR_CONFIG_SCHEMA = DictEntry('directory', 'Directory, available for sync', False, entries=(
        StringEntry('name', 'Short name for directory', False, 0, 60, 'Some dir'),
        DirEntry('path', 'Directory to store files and data to show', False, '/tmp/dcnnt', True, False),
        TemplateEntry('on_done', 'Template of command executed on sync task completion',
                      True, 0, 4096, None, replacements=(Rep('path', 'Path to saved file', True),)),
    ))
    DIR_CONFIG_DEFAULT = (dict(name='Temporary', path='/tmp/dcnnt', on_done=None), )
    CONFIG_SCHEMA = DictEntry('sync.conf.json', 'Common configuration for sync plugin', False, entries=(
        IntEntry('uin', 'UIN of device for which config will be applied', True, 1, 0xFFFFFFF, None),
        ListEntry('dir', 'List of directories available for sync', False, 0, 0xFFFF,
                  DIR_CONFIG_DEFAULT, entry=DIR_CONFIG_SCHEMA),
    ))

    def handle_targets(self, request: RPCRequest):
        """Return list of sync entries to device"""
        sub = request.params.get('sub')
        if not isinstance(sub, str):
            raise PluginFail('No "sub" param in request')
        entries = self.conf((sub, ))
        print(type(entries))
        print(entries)
        self.rpc_send(RPCResponse(request.id, tuple(str(i['path']) for i in entries)))

    def process_request(self, request: RPCRequest):
        if request.method == 'get_targets':
            self.handle_targets(request)
