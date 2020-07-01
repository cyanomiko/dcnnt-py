"""Management of known devices and their authentication data"""

import fnmatch

from .common import derive_key
from .common.jsonconf import *


class Device:
    """Known device representation, using to manage preferences device info and key"""

    def __init__(self, uin, name, description='', role='client', password=None):
        self.uin, self.name, self.description, self.role, self.password = uin, name, description, role, password
        self.key_send = self.key_recv = self.ip = None

    def init_keys(self, app_uin, app_password):
        """Init both encrypt end decrypt keys for device"""
        self.key_recv = derive_key(''.join(map(str, (app_uin, self.uin, app_password, self.password))))
        self.key_send = derive_key(''.join(map(str, (self.uin, app_uin, self.password, app_password))))

    def dict(self):
        """Get dictionary to dump to JSON file"""
        return dict(uin=self.uin, name=self.name, description=self.description, role=self.role, password=self.password)

    def __repr__(self):
        return 'Device(UIN={}, name={}, role={}, password={})'.format(self.uin, self.name, self.role, self.password)


class DeviceManager(dict):
    """Object to control list of known devices"""
    JSON_SCHEMA = DictEntry('*.device.json', 'Device description and login data', True, entries=(
        IntEntry('uin', 'UIN of device for which config will be applied', False, 1, 0xFFFFFFF, None),
        StringEntry('name', 'Short name of device', False, 1, 40, 'Unknown'),
        StringEntry('description', 'Verbose description of device', True, 0, 200, ''),
        StringEntry('role', 'Client/server/proxy', True, 0, 40, 'client'),
        StringEntry('password', 'Access password', True, 0, 4096, ''),
    ))
    FILENAME_TEMPLATE = '{}.device.json'

    def __init__(self, app, directory):
        super().__init__()
        self.app, self.log, self.directory = app, app.log, directory

    def find_files(self, directory):
        """Find files in directory self.directory by wildcard"""
        return fnmatch.filter(os.listdir(directory), self.FILENAME_TEMPLATE.format('*'))

    def load(self):
        """Load all items using self.directory to search"""
        if os.path.isdir(self.directory):
            file_list = self.find_files(self.directory)
            for filename in file_list:
                path = os.path.join(self.directory, filename)
                self.log.info('Loading device data from file "{}"'.format(path))
                uin_item_pair = self.load_item(path)
                if uin_item_pair:
                    self[uin_item_pair[0]] = uin_item_pair[1]
                    uin_item_pair[1].init_keys(self.app.dev.uin, self.app.dev.password)
                else:
                    self.log.warning("Couldn't load device data from file '{}'".format(filename))
        else:
            self.log.warning("Devices directory '{}' not found - creating".format(self.directory))
            try:
                os.makedirs(self.directory, exist_ok=True)
            except OSError as e:
                self.log.error(f'Could not create devices directory "{self.directory}"')
                self.log.exception(e)

    def load_item(self, path):
        """Load device file data and create device object"""
        device_dict = ConfigLoader(self.app.environment, path, self.JSON_SCHEMA, False).load()
        if isinstance(device_dict, dict):
            return device_dict['uin'], Device(**device_dict)
        self.log.warning(device_dict)

    def dump_device(self, device):
        """Save device to JSON file, using self.directory and DEVICE_FILENAME_TEMPLATE as path (WARN: plaintext pswd)"""
        filename = self.FILENAME_TEMPLATE.format(device.uin)
        path = os.path.join(self.directory, filename)
        with open(path, 'w') as f:
            json.dump(device.dict(), f, sort_keys=True, indent=2)

    def dump(self):
        """Dump all devices to files in directory self.directory"""
        for address, device in self.items():
            self.dump_device(device)

    def update_device(self, uin, ip, name=None, role=None):
        """Update current network address for known device or add new device"""
        device = self.get(uin)
        if device is None:
            self.log.info("New device found. UIN: '{}', IP: '{}'".format(uin, ip))
            if isinstance(name, str) and isinstance(role, str):
                device = self[uin] = Device(uin=uin, name=name, role=role)
                device.ip = ip
                self.dump_device(device)
            else:
                self.log.error('No role or name presented for new device')
        else:
            device.ip = ip

    def ip(self, uin):
        """Return network address for device or None if one not found"""
        device = self.get(uin)
        return None if device is None else device.ip
