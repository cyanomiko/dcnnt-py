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
        DirEntry('icon_dir', 'Directory to notification icons', True, '$DCNNT_RUNTIME_DIR', True, False),
        TemplateEntry('cmd', 'Template of notification show command',
                      False, 0, 4096, "notify-send -i '{icon}' '{title}' '{text}'", replacements=(
                          Rep('uin', 'UIN of device which send notification', True),
                          Rep('name', 'Name of device which send notification', True),
                          Rep('package', 'Name of Android package  which create notification', True),
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
            cmd = self.conf('cmd')
            if not cmd:
                return
            if request.method == 'notification':
                icon_data = self.read() if request.params.get('packageIcon', False) else None
                if request.params.get('event') == 'posted':
                    text, package = map(request.params.get, ('text', 'package'))
                    title = request.params.get('title', 'NULL')
                    name, uin = self.device.name, self.device.uin
                    if text is None:
                        text = ''
                    icon_path = os.path.join(self.conf('icon_dir'), f'{package}.{self.device.uin}.icon.png')
                    if bool(icon_data):
                        try:
                            open(icon_path, 'wb').write(icon_data)
                        except Exception as e:
                            self.log(e, logging.WARNING)
                    icon = icon_path if icon_data else ''
                    command = cmd.format(uin=uin, name=name, icon=icon, text=text, title=title, package=package)
                    self.log('Execute: "{}"'.format(command))
                    subprocess.call(command, shell=True)
