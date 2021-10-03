import fnmatch
import logging
import subprocess

from .base import BaseFilePlugin, HandlerExit, HandlerFail
from ..common import *


class FileTransferPlugin(BaseFilePlugin):
    """Receive file from phone"""
    MARK = b'file'
    NAME = 'FileTransferPlugin'
    MAIN_CONF = dict()
    DEVICE_CONFS = dict()
    CONFIG_SCHEMA = DictEntry('file.conf.json', 'Common configuration for file transfer plugin', False, entries=(
        IntEntry('uin', 'UIN of device for which config will be applied', True, 1, 0xFFFFFFF, None),
        DirEntry('download_directory', 'Directory to save downloaded files', False, '/tmp/dconnect', True, False),
        TemplateEntry('on_download', 'Template of command executed for every saved file',
                      True, 0, 4096, None, replacements=(Rep('path', 'Path to saved file', True),)),
        ListEntry('shared_dirs', 'Directories shared to client', False, 0, 1073741824, (),
                  entry=DictEntry('shared_dirs[]', 'Description of shared directory', False, entries=(
                      DirEntry('path', 'Path to shared directory', False, '/tmp/dconnect', True, False),
                      StringEntry('name', 'Name using for directory instead of path', True, 0, 60, 'Shared'),
                      StringEntry('glob', 'UNIX glob to filter visible files in directory', False, 0, 1073741824, '*'),
                      IntEntry('deep', 'Recursion deep for subdirectories', False, 1, 1024, 1)
                  )))
    ))
    shared_files_index = list()

    @staticmethod
    def check_file_filter(path: str, glob_str: str) -> bool:
        """Check if file allowed for sharing by filter"""
        return fnmatch.fnmatch(path, glob_str)

    def shared_directory_list(self, directory: str, filter_data, max_deep, current_deep):
        """Create information node for one shared directory"""
        res = list()
        try:
            dir_list = os.listdir(directory)
        except (PermissionError, OSError) as e:
            self.log(f'Could not list content of directory "{directory}" ({e})')
            return res
        for name in dir_list:
            path = os.path.join(directory, name)
            if os.path.isdir(path):
                if current_deep < max_deep and max_deep > 0:
                    dir_list = self.shared_directory_list(path, filter_data, max_deep, current_deep + 1)
                    res.append(dict(name=name, node_type='directory', size=len(dir_list), children=dir_list))
            elif os.path.isfile(path):
                if self.check_file_filter(path, filter_data):
                    self.shared_files_index.append(path)
                    index = len(self.shared_files_index) - 1
                    res.append(dict(name=name, node_type='file', size=os.path.getsize(path), index=index))
        return res

    def shared_files_info(self) -> list:
        """Create tree structure of shared directories"""
        self.shared_files_index.clear()
        res = list()
        names = dict()
        for shared_dir in self.conf('shared_dirs'):
            path, name = shared_dir['path'], shared_dir['name']
            if not os.path.isdir(path):
                self.log('Shared directory "{}" not found'.format(path), logging.WARN)
                continue
            if name is None:
                name = os.path.basename(path)
            if name in names:
                names[name] += 1
                name += ' ({})'.format(names[name])
            else:
                names[name] = 0
            dir_list = self.shared_directory_list(path, shared_dir['glob'], shared_dir.get('deep', 0), 1)
            res.append(dict(name=name, node_type='directory', size=len(dir_list), children=dir_list))
        return res

    def handle_upload(self, request: RPCRequest):
        """Receive and save file from client"""
        path = self.receive_file(request, self.conf('download_directory'))
        on_download = self.conf('on_download')
        if isinstance(on_download, str):
            command = on_download.format(path=path)
            self.log('Execute: "{}"'.format(command))
            subprocess.call(command, shell=True)

    def handle_list_shared(self, request: RPCRequest):
        """Create shared files info and return as JSON"""
        try:
            result = self.shared_files_info()
        except Exception as e:
            self.logger.exception('[FileTransferPlugin] {}'.format(e))
            result = INTERNAL_ERROR
        self.rpc_send(RPCResponse(request.id, result))

    def handle_download(self, request):
        """Handle try of device to download file from server"""
        try:
            index, size = request.params['index'], request.params['size']
        except KeyError as e:
            self.log('KeyError {}'.format(e), logging.WARN)
        else:
            self.log('Download request is correct')
            if 0 <= index < len(self.shared_files_index):
                path = self.shared_files_index[index]
                self.send_file(request, path, size)
            else:
                self.rpc_send(RPCResponse(request.id, dict(code=1, message='No such index: {}'.format(index))))

    def process_request(self, request: RPCRequest):
        if request.method == 'list':
            self.handle_list_shared(request)
        elif request.method == 'download':
            self.handle_download(request)
        elif request.method == 'upload':
            self.handle_upload(request)
