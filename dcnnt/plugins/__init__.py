from .base import PluginInitializer
from .file_transfer import FileTransferPlugin
from .remote_commands import RemoteCommandsPlugin
from .notifications import NotificationsPlugin


PLUGINS = FileTransferPlugin, RemoteCommandsPlugin, NotificationsPlugin
