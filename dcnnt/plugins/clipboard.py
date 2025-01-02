import subprocess
from typing import List

from .base import Plugin, HandlerExit, HandlerFail
from ..common import *


class ClipboardPlugin(Plugin):
    """Send/receive clipboard content to/from phone"""
    MARK = b'clip'
    NAME = 'ClipboardPlugin'
    MAIN_CONF = dict()
    DEVICE_CONFS = dict()
    DEFAULT_SHARED_DIRS = (dict(path='/tmp/dcnnt/files', name='Shared', glob='*', deep=1024), )
    CLIPBOARD_CONFIG_SCHEMA = DictEntry('clip', 'Clipboards, available for sync', False, entries=(
        StringEntry('name', 'Short name for clipboard', False, 1, 60, 'Clipboard'),
        StringEntry('clipboard', 'System name of clipboard, using in read/write command', False, 0, 0xFFFF, 'clipboard'),
        TemplateEntry('read', 'Template of clipboard read command', False, 0, 0xFFFF, None, replacements=(
            Rep('clipboard', 'System name of using clipboard', True),
        )),
        TemplateEntry('write', 'Template of clipboard write command', False, 0, 0xFFFF, None,  replacements=(
            Rep('clipboard', 'System name of using clipboard', True),
        )),
    ))
    CLIPBOARD_CONFIG_DEFAULT = (dict(name='Clipboard',
                                     clipboard='clipboard',
                                     read='xclip -selection "{clipboard}" -o',
                                     write='xclip -selection "{clipboard}" -i'),)
    CLIPBOARDS_LIST_KEY = 'clipboards'
    CONFIG_SCHEMA = DictEntry('clip.conf.json', 'Common configuration for clipboard plugin', False, entries=(
        ListEntry(CLIPBOARDS_LIST_KEY, 'List of clipboards available for sync', False, 0, 0xFFFF,
                  CLIPBOARD_CONFIG_DEFAULT, entry=CLIPBOARD_CONFIG_SCHEMA),
    ))

    def __init__(self, app, handler, device):
        super().__init__(app, handler, device)
        self.clipboards_index: Dict[str, Dict[str, str]] = dict()
        self.clipboards_list: List[Dict[str, str]] = []
        for clipboard_conf_entry in self.conf(self.CLIPBOARDS_LIST_KEY):
            key = str(id(clipboard_conf_entry))
            self.clipboards_index[key] = clipboard_conf_entry
            self.clipboards_list.append({'key': key, 'name': clipboard_conf_entry['name'],
                                         'readable': bool(clipboard_conf_entry['read']),
                                         'writeable': bool(clipboard_conf_entry['write'])})

    def handle_list(self, request: RPCRequest):
        """Return list of clipboards to client"""
        return self.rpc_send(RPCResponse(request.id, self.clipboards_list))

    def _get_clipboard_command(self, request: RPCRequest, command_name: str) -> str:
        """Get and format some clipboard action command from index"""
        key: str = str(request.params['clipboard'])
        if key not in self.clipboards_index:
            raise HandlerExit.new(request, 1, 'No such clipboard')
        clipboard_entry = self.clipboards_index[key]
        return clipboard_entry[command_name].format(clipboard=clipboard_entry['clipboard'])

    def handle_read(self, request: RPCRequest):
        """Read text content from clipboard and send back to client"""
        cmd = self._get_clipboard_command(request, 'read')
        text = subprocess.check_output(cmd, timeout=15, shell=True).decode(errors='ignore')
        return self.rpc_send(RPCResponse(request.id, {'code': 0, 'text': text}))

    def handle_write(self, request: RPCRequest):
        """Write text content from client to clipboard"""
        cmd = self._get_clipboard_command(request, 'write')
        try:
            subprocess.run(cmd, shell=True, timeout=15, input=request.params['text'].encode(errors='ignore'))
        except Exception as e:
            return self.rpc_send(RPCResponse(request.id, {'code': 2, 'message': f'Error: {e}'}))
        return self.rpc_send(RPCResponse(request.id, {'code': 0, 'message': 'OK'}))

    def process_request(self, request: RPCRequest):
        if request.method == 'list':
            self.handle_list(request)
        elif request.method == 'read':
            self.handle_read(request)
        elif request.method == 'write':
            self.handle_write(request)
        else:
            raise HandlerFail(f'Unknown method "{request.method}"')