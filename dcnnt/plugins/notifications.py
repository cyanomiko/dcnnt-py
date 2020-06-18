import logging
import subprocess

from .base import Plugin
from ..common import *


class NotificationsPlugin(Plugin):
    """Receive notifications from phone"""
    MARK = b'nots'
    NAME = 'NotificationsPlugin'
    MAIN_CONF = dict()
    DEVICE_CONFS = dict()
    CONFIG_SCHEMA = DictEntry('rcmd.conf.json', 'Configuration for remote commands file', False, entries=(
        IntEntry('uin', 'UIN of device for which config will be applied', True, 1, 0xFFFFFFF, None),
        FileEntry('icon_path', 'Path to save notification icon', False, '/tmp/dc-icon.png', True, False),
        TemplateEntry('cmd', 'Template of notification show command',
                      False, 0, 4096, "notify-send -i '{icon}' '{title}' '{text}'", replacements=(
                Rep('icon', 'Path to saved notification icon', True),
                Rep('title', 'Title of notification', True),
                Rep('text', 'Main content of notification', True),
            ))
    ))

    def __init__(self, app, handler, device):
        super().__init__(app, handler, device)

    def main(self):
        while True:
            request = self.rpc_read()
            self.log(request)
            if request is None:
                self.log('No more requests, stop handler')
                return
            if request.method == 'notification':
                if request.params.get('event') == 'posted':
                    cmd = self.conf('cmd')
                    icon_path = self.conf('icon_path')
                    text = request.params.get('text')
                    if text is None:
                        text = ''
                    if request.params.get('packageIcon', False):
                        icon_data = self.read()
                        if icon_path:
                            try:
                                open(icon_path, 'wb').write(icon_data)
                            except Exception as e:
                                self.log(e, logging.WARNING)
                    if cmd:
                        command = cmd.format(icon=icon_path, text=text, title=request.params.get('title', 'NULL'))
                        self.log('Execute: "{}"'.format(command))
                        subprocess.call(command, shell=True)
