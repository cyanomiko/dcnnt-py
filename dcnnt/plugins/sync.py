import logging
import shutil
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
        DirEntry('path', 'Directory to store files and data to show', False, '/tmp/dcnnt/sync/files', True, False),
        TemplateEntry('on_done', 'Template of command executed on sync task completion',
                      True, 0, 4096, None, replacements=(Rep('path', 'Path to saved file', True),)),
    ))
    DIR_CONFIG_DEFAULT = (dict(name='Temporary', path='/tmp/dcnnt/sync/files', on_done=None), )
    FILE_CONFIG_SCHEMA = DictEntry('file', 'File, available for sync', False, entries=(
        StringEntry('name', 'Short name for file', False, 0, 60, 'Some dir'),
        FileEntry('path', 'Path to file', False, '/tmp/dcnnt/sync/dcnnt-example.txt', False, False),
        TemplateEntry('on_merge', 'Template of command executed on merge task to merge local and remote files',
                      True, 0, 4096, default='cat "{local}" "{remote}" > "{output}"',
                      replacements=(Rep('local', 'Path to local version of file', True),
                                    Rep('remote', 'Path to remote version of file', True),
                                    Rep('output', 'Path to save merged file', True),)),
        TemplateEntry('on_done', 'Template of command executed on sync task completion',
                      True, 0, 4096, None, replacements=(Rep('path', 'Path to saved file', True),)),
    ))
    FILE_CONFIG_DEFAULT = (dict(name='Example', path='/tmp/dcnnt/sync/dcnnt-example-file.txt',
                                on_merge='cat "{local}" "{remote}" > "{output}"',
                                on_done='true'),)
    CONFIG_SCHEMA = DictEntry('sync.conf.json', 'Common configuration for sync plugin', False, entries=(
        IntEntry('uin', 'UIN of device for which config will be applied', True, 1, 0xFFFFFFF, None),
        DirEntry('working_directory', 'Directory to store temporary files',
                 True, '/tmp/dcnnt/sync_tmp', True, False),
        ListEntry('dir', 'List of directories available for sync', False, 0, 0xFFFF,
                  DIR_CONFIG_DEFAULT, entry=DIR_CONFIG_SCHEMA),
        ListEntry('file', 'List of files available for sync', False, 0, 0xFFFF,
                  FILE_CONFIG_DEFAULT, entry=FILE_CONFIG_SCHEMA),
        DictEntry('contacts', 'Contacts sync settings', False, entries=(
            DirEntry('path', 'Directory to store vcard files', False, '/tmp/dcnnt/sync/contacts', True, False),
            IntEntry('backup_count', 'Count of backup files', False, 0, 4096, 3),
            TemplateEntry('on_done', 'Template of command executed on sync task completion',
                          True, 0, 4096, None, replacements=(Rep('path', 'Path to saved file', True),)),
        )),
        DictEntry('messages', 'SMS sync settings', True, entries=(
            DirEntry('path', 'Directory to store messages files', False, '/tmp/dcnnt/sync/messages', True, False),
            IntEntry('backup_count', 'Count of backup files', False, 0, 4096, 3),
            TemplateEntry('on_done', 'Template of command executed on sync task completion',
                          True, 0, 4096, None, replacements=(Rep('path', 'Path to the last saved file', True),)),
        ))
    ))

    def __init__(self, app, handler, device):
        super().__init__(app, handler, device)

    def handle_targets(self, request: RPCRequest):
        """Return list of sync entries to device"""
        sub = request.params.get('sub')
        if not isinstance(sub, str):
            raise PluginFail('No "sub" param in request')
        entries = self.conf((sub, ))
        self.rpc_send(RPCResponse(request.id, tuple(str(i['path']) for i in entries)))

    @staticmethod
    def get_flat_fs(base: str) -> Dict[str, Tuple[str, int, bool, int]]:
        """Get directory subtree as list"""
        res = dict()
        tree_stop_set = {'', '/', os.path.normpath(base)}
        for root, dirs, files in os.walk(base):
            for d in dirs:
                path = os.path.join(root, d)
                name = os.path.relpath(path, base)
                ts = int(os.stat(path).st_mtime * 1000)
                res[name] = name, ts, True, -2
            for f in files:
                path = os.path.join(root, f)
                name = os.path.relpath(path, base)
                ts = int(os.stat(path).st_mtime * 1000)
                res[name] = name, ts, False, -2
                dir_name = os.path.dirname(path)
                # Here timestamp of directory equals timestamp of newest file
                while dir_name not in tree_stop_set:
                    dir_entry = res.get(dir_name)
                    if dir_entry:
                        _, dir_ts, _ = dir_entry
                        if ts > dir_ts:
                            res[dir_name] = dir_name, ts, True, -2
                    dir_name = os.path.dirname(dir_name)
        return res

    @staticmethod
    def rename_with_mark(base: str, name: str, mark: Union[str, int]) -> Optional[str]:
        """Rename directory sync entry using timestamp"""
        path = os.path.join(base, name)
        if not os.path.exists(path):
            return
        directory = os.path.dirname(path)
        filename = os.path.basename(name)
        s = filename.rsplit('.', maxsplit=1)
        if len(s) == 2:
            name_part, extension = s
        else:
            name_part, extension = filename, ''
        for suffix in ('', '-1', '-2', '-3', '-4', '-5'):
            new_path = os.path.join(directory, f'{name_part}-{mark}{suffix}.{extension}')
            if not os.path.exists(new_path):
                os.rename(path, new_path)
                return new_path[len(base):]
        raise PluginFail(f'No safe name to rename "{path}"')

    @staticmethod
    def ensure_removed(base: str, name: str):
        """Delete FS entry if exists"""
        path = os.path.join(base, name)
        if os.path.exists(path):
            if os.path.isdir(path):
                os.rmdir(path)
            else:
                os.unlink(path)

    def handle_dir_list(self, request: RPCRequest):
        """Initialize directory sync session"""
        args = 'data', 'mode', 'path', 'on_conflict', 'on_delete'
        flat_list_c, mode, path, on_conflict, on_delete = map(request.params.get, args)
        for name, value in zip(args[1:], (mode, path, on_conflict, on_delete)):
            if not isinstance(value, str):
                raise PluginFail(f'No correct "{name}" param in request')
        if path not in tuple(str(i['path']) for i in self.conf(('dir', ))):
            raise PluginFail('Unknown target path')
        do_upload = mode in {'upload', 'sync'}
        do_download = mode in {'download', 'sync'}
        do_delete = on_delete == 'delete'
        self.log(f'Process {len(flat_list_c)} names, mode: "{mode}", target: "{path}", '
                 f'on conflict: "{on_conflict}", on delete: "{on_delete}"')
        # Lists of entries by actions
        to_upload, to_download, to_create_c, to_create_s = list(), list(), list(), list()
        to_rename_c, to_rename_s, to_delete_c, to_delete_s = list(), list(), list(), list()
        # Flat data of FS subtree for server and client
        flat_c: Dict[str, Tuple[str, int, bool, int]] = {i[0]: (i[0], i[1], i[2] == -1, i[2]) for i in flat_list_c}
        flat_s: Dict[str, Tuple[str, int, bool, int]] = self.get_flat_fs(path)
        # flat_list_s = tuple(flat_s.values())
        self.log(f'Created local FS flat data: {len(flat_s)} names')
        # Compare FS subtrees
        names_c, names_s = frozenset(flat_c.keys()), frozenset(flat_s.keys())
        names_client_only = names_c - names_s
        names_server_only = names_s - names_c
        names_both = names_c & names_s
        self.log(f'Names compared: client only: {len(names_client_only)},'
                 f' server only: {len(names_server_only)}, in conflict: {len(names_both)}')
        self.log('Client only:')
        for name in sorted(names_client_only):
            self.log(f'    {name}')
        self.log('Server only:')
        for name in sorted(names_server_only):
            self.log(f'    {name}')
        self.log('In conflict:')
        for name in sorted(names_both):
            self.log(f'    {name}')
        # Process 3 groups of names
        for name in names_client_only:
            if do_upload:
                if flat_c[name][2]:
                    to_create_s.append(name)
                else:
                    to_upload.append(name)
            elif do_delete:  # download only and deletion allowed
                to_delete_c.append(name)
        for name in names_server_only:
            if do_download:
                if flat_s[name][2]:
                    to_create_c.append(name)
                else:
                    to_download.append(name)
            elif do_delete:  # upload only and deletion allowed
                to_delete_s.append(name)
        if on_conflict in {'replace', 'new', 'both'}:  # if conflicts ignored - do nothing
            for name in names_both:
                _, ts_c, is_dir_c, crc_c = flat_c[name]
                _, ts_s, is_dir_s, crc_s = flat_s[name]
                if is_dir_c and is_dir_s:  # both dir already exists, just skip
                    continue
                if mode == 'download':  # from server to client
                    to_c_list = to_create_c if is_dir_s else to_download
                    if on_conflict == 'replace':
                        to_delete_c.append(name)
                        to_c_list.append(name)
                    elif on_conflict == 'new':
                        if ts_s > ts_c:
                            to_delete_c.append(name)
                            to_c_list.append(name)
                    elif on_conflict == 'both':
                        to_rename_c.append(name)
                        to_c_list.append(name)
                elif mode == 'upload':  # from client to server - sort of mirror for previous
                    to_s_list = to_create_s if is_dir_c else to_upload
                    if on_conflict == 'replace':
                        to_delete_s.append(name)
                        to_s_list.append(name)
                    elif on_conflict == 'new':
                        if ts_c > ts_s:
                            to_delete_s.append(name)
                            to_s_list.append(name)
                    elif on_conflict == 'both':
                        to_rename_s.append(name)
                        to_s_list.append(name)
                elif mode == 'sync':  # priority for client here
                    to_c_list = to_create_c if is_dir_s else to_download
                    to_s_list = to_create_s if is_dir_c else to_upload
                    if on_conflict == 'replace':  # replace on client
                        to_delete_c.append(name)
                        to_c_list.append(name)
                    elif on_conflict == 'new':
                        if ts_c > ts_s:
                            to_delete_s.append(name)
                            to_s_list.append(name)
                        else:
                            to_delete_c.append(name)
                            to_c_list.append(name)
                    elif on_conflict == 'both':
                        if is_dir_c != is_dir_s:
                            # Don't know what to do in this case
                            raise PluginFail('Dir-file name conflict')
                        if (not is_dir_c) and (not is_dir_s):
                            srv_ts = flat_s[name][1]
                            new_name_srv = self.rename_with_mark(path, name, f'srv-{srv_ts}')
                            to_upload.append(name)
                            to_download.append(new_name_srv)
        # Print some info to logs
        self.log('To upload from client to server:')
        for name in to_upload:
            self.log(f'    {name}')
        self.log('To download from server to client:')
        for name in to_download:
            self.log(f'    {name}')
        self.log('To delete on client:')
        for name in to_delete_c:
            self.log(f'    {name}')
        self.log('To rename on client:')
        for name in to_rename_c:
            self.log(f'    {name}')
        self.log('Dirs to create on client:')
        for name in to_create_c:
            self.log(f'    {name}')
        self.log('To delete on server:')
        for name in to_delete_s:
            self.log(f'    {name}')
        self.log('To rename on server:')
        for name in to_rename_s:
            self.log(f'    {name}')
        self.log('Dirs to create on server:')
        for name in to_create_s:
            self.log(f'    {name}')
        # Do FS modifications on server
        for name in sorted(to_rename_s):
            new_name = self.rename_with_mark(path, name, flat_s[name][1])
            if path:
                self.log(f'Renamed "{name}" -> "{new_name}"')
        for name in reversed(sorted(to_delete_s)):  # reversed order to ensure files removed before parent dirs
            self.ensure_removed(path, name)
            self.log(f'Removed "{name}"')
        for name in to_create_s:
            os.makedirs(os.path.join(path, name), exist_ok=True)
            self.log(f'Created directory "{name}"')
        # Send response to server
        session_id = f'{time.time()}.{id(request)}'
        self.rpc_send(RPCResponse(request.id, dict(upload=to_upload, download=to_download, create=to_create_c,
                                                   delete=to_delete_c, rename=to_rename_c, session=session_id)))

    def handle_dir_upload(self, request: RPCRequest):
        """Process uploading file on dir sync"""
        print(request.params)
        base = request.params.get('path')
        if base not in tuple(str(i['path']) for i in self.conf(('dir',))):
            raise PluginFail('Unknown target path')
        self.receive_file(request, base)

    def handle_dir_download(self, request: RPCRequest):
        """Process downloading file on dir sync"""
        base = request.params.get('path')
        name = request.params.get('name')
        if base not in tuple(str(i['path']) for i in self.conf(('dir',))):
            raise PluginFail('Unknown target path')
        if not isinstance(name, str):
            raise PluginFail('Incorrect arg "name"')
        path = os.path.join(base, name)
        self.send_file(request, path)

    def common_upload_handler(self, entity_type: str, request: RPCRequest):
        """Process any backup uploading"""
        directory = self.conf((entity_type, 'path'))
        backup_count = self.conf((entity_type, 'backup_count'))
        on_done = self.conf((entity_type, 'on_done'))
        fn = request.params['name']
        total = request.params.get('total')
        index = request.params.get('index')
        is_last_entry = (total is None) and (index is None)
        if isinstance(total, int) and isinstance(index, int):
            if total - index == 1:  # indexes starts from 0 on client
                is_last_entry = True
        if backup_count > 0:
            suffixes = tuple(f'.{i}.bak' for i in reversed(range(backup_count))) + ('', )
            for i in range(len(suffixes) - 1):
                src = os.path.join(directory, fn + suffixes[i + 1])
                dst = os.path.join(directory, fn + suffixes[i])
                if os.path.isfile(src):
                    shutil.copy(src, dst)
        res = self.receive_file(request, directory)
        if on_done and is_last_entry:
            command = on_done.format(path=res)
            self.log(f'Execute: "{command}"')
            subprocess.call(command, shell=True)

    def handle_contacts_upload(self, request: RPCRequest):
        """Process contacts backup uploading"""
        return self.common_upload_handler('contacts', request)

    def handle_messages_upload(self, request: RPCRequest):
        """Process messages backup uploading"""
        return self.common_upload_handler('messages', request)

    def ensure_file_syncable(self, path: str) -> Optional[str]:
        """Check if file in list of sync files and return on_merge option, raise exception otherwise"""
        for i in self.conf('file'):
            if path in i['path']:
                return i.get('on_merge')
        raise PluginFail('No file in sync list')

    def handle_file_info(self, request: RPCRequest):
        """Send some info about sync file to client"""
        path = str(request.params['path'])
        self.ensure_file_syncable(path)
        exists = os.path.isfile(path)
        ts = int(os.path.getmtime(path) * 1000 + .5) if exists else 0
        self.rpc_send(RPCResponse(request.id, {'exists': exists, 'ts': ts}))

    def handle_file_upload(self, request: RPCRequest):
        """Process uploading file on file sync"""
        path = str(request.params.get('path'))
        merge_mode = bool(request.params.get('merge'))
        on_merge = self.ensure_file_syncable(path)
        if merge_mode:
            if on_merge is None:
                raise PluginFail('No merge script set')
            random = str(int(time.time() * 1000)) + str(id(path))
            directory = os.path.join(self.conf('working_directory'), random)
            os.makedirs(directory)
            name = os.path.basename(path)
            server_file_path = os.path.join(directory, f'server-{name}')
            client_file_path = os.path.join(directory, f'client-{name}')
            shutil.copy(path, server_file_path)
            self.receive_file_to_path(request, client_file_path)
            command = on_merge.format(local=server_file_path, remote=client_file_path, output=path)
            self.log(f'Execute: "{command}"')
            subprocess.call(command, shell=True)
        else:
            self.receive_file_to_path(request, path)

    def handle_file_download(self, request: RPCRequest):
        """Process downloading file on file sync"""
        path = request.params.get('path')
        self.ensure_file_syncable(path)
        self.send_file(request, path)

    def process_request(self, request: RPCRequest):
        if request.method == 'get_targets':
            self.handle_targets(request)
        elif request.method == 'dir_list':
            self.handle_dir_list(request)
        elif request.method == 'dir_upload':
            self.handle_dir_upload(request)
        elif request.method == 'dir_download':
            self.handle_dir_download(request)
        elif request.method == 'contacts_upload':
            self.handle_contacts_upload(request)
        elif request.method == 'messages_upload':
            self.handle_messages_upload(request)
        elif request.method == 'file_info':
            self.handle_file_info(request)
        elif request.method == 'file_upload':
            self.handle_file_upload(request)
        elif request.method == 'file_download':
            self.handle_file_download(request)
