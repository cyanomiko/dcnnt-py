import os
import json
from string import Template
from typing import Optional, Iterable, Union, Any, Dict


class ConfEntryBase:
    """Basic class of simple configuration file value"""
    HOME_DIR = os.environ['HOME']

    def __init__(self, name: str, description: str, optional: bool, default):
        self.name, self.description, self.optional = name, description, optional
        self.default = default() if callable(default) else default

    def pre_process(self, value, environment: Optional[Dict[str, str]] = None) -> Any:
        """Process data from JSON before check"""
        return self.default if value is None and self.optional else value

    def check(self, value, environment: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Check if value is OK"""
        raise NotImplementedError

    def get_default(self):
        """Get default value for this entry"""
        return self.default


class IntEntry(ConfEntryBase):
    """Description of integer config entry"""

    def __init__(self, name: str, description: str, optional: bool,
                 min: int, max: int, default: Optional[int]):
        super().__init__(name, description, optional, default)
        self.min, self.max = min, max

    def __str__(self):
        return f'{self.name} - integer{", optional" if self.optional else ""}\n' \
               f'    default: {self.default}\n' \
               f'    min: {self.min}\n' \
               f'    max: {self.max}\n' \
               f'    {self.description}\n'

    def check(self, value, environment: Optional[Dict[str, str]] = None):
        if self.optional and value is None:
            return
        if not isinstance(value, int):
            return f'Type of "{self.name}" is {type(value)}, integer expected'
        if value > self.max:
            return f'Value of "{self.name}" ({value}) is more than max value ({self.max})'
        if value < self.min:
            return f'Value of "{self.name}" ({value}) is less than min value ({self.max})'


class StringEntry(ConfEntryBase):
    """Description of string config entry"""

    def __init__(self, name: str, description: str, optional: bool,
                 min_length: int, max_length: int, default: Optional[str]):
        super().__init__(name, description, optional, default)
        self.min_length, self.max_length = min_length, max_length

    def __str__(self):
        return f'{self.name} - string{", optional" if self.optional else ""}\n' \
               f'    default: {self.default}\n' \
               f'    min length: {self.min_length}\n' \
               f'    max length: {self.max_length}\n' \
               f'    {self.description}\n'

    def check(self, value, environment: Optional[Dict[str, str]] = None):
        if self.optional and value is None:
            return
        if not isinstance(value, str):
            return f'Type of "{self.name}" is {type(value)}, integer expected'
        length = len(value)
        if length > self.max_length:
            return f'Length of "{self.name}" ({length}) is more than max ({self.max_length})'
        if length < self.min_length:
            return f'Length of "{self.name}" ({length}) is less than min ({self.max_length})'


class Rep:
    """Description for replaced part of template"""
    
    def __init__(self, name: str, description: str, optional: bool):
        self.name, self.description, self.optional = name, description, optional

    def __str__(self):
        return f'{self.name}{" (optional)" if self.optional else ""} - {self.description}'
        

class TemplateEntry(StringEntry):
    """Description of sting-template config entry"""
    
    def __init__(self, name: str, description: str, optional: bool, min_length: int,
                 max_length: int, default: Optional[str], replacements: Iterable[Rep]):
        super().__init__(name, description, optional, min_length, max_length, default)
        self.replacements = replacements

    def __str__(self):
        replacement_description = '        \n'.join(tuple(map(str, self.replacements)))
        return f'{self.name} - template string{", optional" if self.optional else ""}\n' \
               f'    default: {self.default}\n' \
               f'    min length: {self.min_length}\n' \
               f'    max length: {self.max_length}\n' \
               f'    replacements:\n' \
               f'        {replacement_description}\n' \
               f'    {self.description}\n'

    def check(self, value, environment: Optional[Dict[str, str]] = None):
        res = super().check(value, environment)
        if res is None:
            if value is None and self.optional:
                return
            test_dict = {i.name: '%TEST%' for i in self.replacements}
            try:
                value.format(**test_dict)
            except KeyError as e:
                return f'Template key failed {str(e)}, required keys: {tuple(test_dict.keys())}'
            for key in filter(lambda x: not x.optional, self.replacements):
                if '{' + key.name not in value:
                    return f'Key "{key.name}" not vound in template, required keys: {tuple(test_dict.keys())}'
        else:
            return res


class FileEntry(StringEntry):
    """Description of filesystem path config entry"""

    def __init__(self, name: str, description: str, optional: bool, default: Optional[str],
                 make_dirs: bool, exists: bool):
        super().__init__(name, description, optional, 0, 16384, default)
        self.make_dirs, self.exists = make_dirs, exists

    def __str__(self):

        return f'{self.name} - file path{", optional" if self.optional else ""}\n' \
               f'    default: {self.default}\n' \
               f'    min length: {self.min_length}\n' \
               f'    max length: {self.max_length}\n' \
               f'    must exist: {self.exists}\n' \
               f'    directories created automatically: {self.make_dirs}\n' \
               f'    {self.description}\n'

    def pre_process(self, value, environment: Optional[Dict[str, str]] = None):
        return Template(super().pre_process(value, environment)).safe_substitute(environment)

    def check(self, value, environment: Optional[Dict[str, str]] = None):
        res = super().check(value, environment)
        if res is not None:
            return res
        if not os.path.isfile(value):
            if self.exists:
                return f'File "{value}" not found'
            else:
                dir_path = os.path.dirname(value)
                if dir_path == '':
                    dir_path = '.'
                if not os.path.isdir(dir_path):
                    if self.make_dirs:
                        try:
                            os.makedirs(dir_path, exist_ok=True)
                        except OSError as e:
                            return f'Could not create dir "{dir_path}" ({e})'
                    else:
                        return f'Directory not found "{dir_path}"'


class DirEntry(StringEntry):
    """Description of directory path config entry"""

    def __init__(self, name: str, description: str, optional: bool, default: Optional[str],
                 make_dirs: bool, exists: bool):
        super().__init__(name, description, optional, 0, 16384, default)
        self.make_dirs, self.exists = make_dirs, exists

    def __str__(self):

        return f'{self.name} - directory path{", optional" if self.optional else ""}\n' \
               f'    default: {self.default}\n' \
               f'    min length: {self.min_length}\n' \
               f'    max length: {self.max_length}\n' \
               f'    must exist: {self.exists}\n' \
               f'    directories created automatically: {self.make_dirs}\n' \
               f'    {self.description}\n'

    def pre_process(self, value, environment: Optional[Dict[str, str]] = None):
        return Template(super().pre_process(value, environment)).safe_substitute(environment)

    def check(self, value, environment: Optional[Dict[str, str]] = None):
        res = super().check(value, environment)
        if res is not None:
            return res
        if not os.path.isdir(value):
            if self.exists:
                return f'Directory "{value}" not found'
            else:
                if not os.path.isdir(value):
                    if self.make_dirs:
                        try:
                            os.makedirs(value, exist_ok=True)
                        except OSError as e:
                            return f'Could not create dir "{value}" ({e})'
                    else:
                        return f'Directory not found "{value}"'


class ListEntry(ConfEntryBase):
    """Description of string config entry"""

    def __init__(self, name: str, description: str, optional: bool,
                 min_length: int, max_length: int,  default: tuple, entry: ConfEntryBase):
        super().__init__(name, description, optional, default)
        self.min_length, self.max_length, self.entry = min_length, max_length, entry

    def __str__(self):
        return f'{self.name} - string{", optional" if self.optional else ""}\n' \
               f'    default: {self.default}\n' \
               f'    min length: {self.min_length}\n' \
               f'    max length: {self.max_length}\n' \
               f'    {self.description}\n' \
               f'    entries: \n{str(self.entry)}\n'

    def check(self, value, environment: Optional[Dict[str, str]] = None):
        if self.optional and value is None:
            return
        if not isinstance(value, list):
            return f'Type of "{self.name}" is {type(value)}, list expected'
        length = len(value)
        if length > self.max_length:
            return f'Length of "{self.name}" ({length}) is more than max ({self.max_length})'
        if length < self.min_length:
            return f'Length of "{self.name}" ({length}) is less than min ({self.max_length})'
        for i in range(len(value)):
            value[i] = self.entry.pre_process(value[i], environment)
            res = self.entry.check(value[i], environment)
            if res is not None:
                return res


class DictEntry(ConfEntryBase):
    """Description of string config entry"""

    def __init__(self, name: str, description: str, optional: bool, entries: Iterable[ConfEntryBase]):
        super().__init__(name, description, optional, None)
        self.entries = entries

    def __str__(self):
        entries_description = '    ' + '\n    '.join(tuple(i.replace('\n', '\n    ') for i in map(str, self.entries)))
        return f'{self.name} - dictionary{", optional" if self.optional else ""}\n' \
               f'    {self.description}\n' \
               f'    entries: \n\n{entries_description}\n'

    def check(self, value, environment: Optional[Dict[str, str]] = None):
        if self.optional and value is None:
            return
        if not isinstance(value, dict):
            return f'Type of "{self.name}" is {type(value)}, dictionary expected'
        for entry in self.entries:
            name = entry.name
            if name not in value and not entry.optional:
                return f'Entry "{entry.name}" not found in "{self.name}" dictionary'
            value[name] = entry.pre_process(value.get(name), environment)
            res = entry.check(value[name], environment)
            if res is not None:
                return res

    def get_default(self):
        return {i.name: i.get_default() for i in self.entries if not i.optional}


class ConfigLoader:
    """Loading and check facility for JSON configs, can also create default one"""

    def __init__(self, environment: Dict[str, str], path: str, schema: DictEntry, create_defult: bool):
        self.environment, self.path, self.schema, self.create_default = environment, path, schema, create_defult

    def load(self) -> Union[dict, str]:
        """Load and check configuration, create default optionally"""
        if not os.path.isfile(self.path):
            if self.create_default:
                try:
                    os.makedirs(os.path.dirname(self.path), exist_ok=True)
                    with open(self.path, 'w') as f:
                        json.dump(self.schema.get_default(), f, indent=2)
                except BaseException as e:
                    return f'Could not write default configuration to file {self.path} ({e})'
            else:
                return f'File {self.path} not found'
        try:
            conf = json.load(open(self.path))
            if not isinstance(conf, dict):
                return f'JSON config file {self.path} must contain dictionary'
            res = self.schema.check(conf, self.environment)
            if res is not None:
                return f'Error in configuration file {self.path}: {res}'
            return conf
        except IOError:
            return f'Could not open file {self.path}'
        except UnicodeDecodeError:
            return f'None UTF-8 file {self.path}'
        except json.JSONDecodeError:
            return f'JSON error in file {self.path}'
        except BaseException as e:
            return f'Unknown error ({e}) in file {self.path}'
