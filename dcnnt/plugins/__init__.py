from .base import PluginInitializer
from .file_transfer import FileTransferPlugin
from .remote_commands import RemoteCommandsPlugin
from .notifications import NotificationsPlugin
from .opener import OpenerPlugin
from .sync import SyncPlugin
from .clipboard import ClipboardPlugin


PLUGINS = FileTransferPlugin, OpenerPlugin, RemoteCommandsPlugin, NotificationsPlugin, SyncPlugin, ClipboardPlugin
