import time
import subprocess
from typing import List, Tuple

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
        self.rpc_send(RPCResponse(request.id, tuple(str(i['path']) for i in entries)))

    def flat_fs(self, path: str) -> List[Tuple[str, int, bool]]:
        """Get directory subtree as list"""
        res = list()
        for root, dirs, files in os.walk(path):
            for entry in dirs:
                res.append((os.path.join(root, entry), 0, True))
            for entry in files:
                p = os.path.join(root, entry)
                res.append((p, int(os.stat(p).st_mtime * 1000), True))
        return res

    _ret = Tuple[List[str], List[str], List[str], List[str]]

    def process_dir_list(self, base: str, mode: str, data: List[Tuple[str, int, bool]]) -> _ret:
        """Process initial dir sync data"""
        to_create, to_backup, to_download, to_upload = list(), list(), list(), list()
        by_name = dict()
        for sub_path, ts, is_dir in data:
            by_name[sub_path] = (sub_path, ts, is_dir)
            path = os.path.join(base, sub_path)
            if is_dir:
                if not os.path.exists(path):
                    to_create.append(sub_path)
                elif not os.path.isdir(path):
                    to_backup.append(sub_path)
                    to_create.append(sub_path)
            else:
                if os.path.isfile(path):
                    if ts <= int(os.path.getmtime(path) * 1000 + .5):
                        to_backup.append(sub_path)
                        to_download.append(sub_path)
                elif os.path.isdir(path):
                    to_backup.append(sub_path)
                    to_download.append(sub_path)
                else:
                    to_download.append(sub_path)
        length_base = len(base)
        for root, dirs, files in os.walk(base):
            for entry in dirs:
                sub_path = os.path.join(root, entry)[length_base:]
                if sub_path not in by_name:
                    to_backup.append(sub_path)
            for entry in files:
                sub_path = os.path.join(root, entry)[length_base:]
                if sub_path not in by_name:
                    to_upload.append(sub_path)
                    to_backup.append(sub_path)
        return to_create, to_backup, to_download, to_upload

    def handle_dir_list(self, request: RPCRequest):
        """Initialize directory sync session"""
        data = request.params.get('data')
        mode = request.params.get('mode')
        path = request.params.get('path')
        if not isinstance(mode, str):
            raise PluginFail('No "mode" param in request')
        if not isinstance(path, str):
            raise PluginFail('No "path" param in request')
        if path not in tuple(str(i['path']) for i in self.conf(('dir', ))):
            raise PluginFail('Unknown target path')
        to_create, to_backup, to_download, to_upload = self.process_dir_list(path, mode, data)
        if mode in {'download', 'sync'}:
            self.rpc_send(RPCResponse(request.id, dict(session_id=f'{time.time()}.{id(request)}',
                                                       code=0, message='OK', data=self.flat_fs(path))))
        else:
            self.rpc_send(RPCResponse(request.id, dict(session_id=f'{time.time()}.{id(request)}',
                                                       code=0, message='OK', data=())))

    def process_request(self, request: RPCRequest):
        if request.method == 'get_targets':
            self.handle_targets(request)
        if request.method == 'dir_list':
            self.handle_dir_list(request)
