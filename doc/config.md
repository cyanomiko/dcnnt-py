dcnnt configuration
===================

Structure
---------

Configuration of **dcnnt** stored in JSON files located at `$HOME/.config/dcnnt`. 
It is possible to change configuration directory using `-c` command argument (example: `dcnnt -c test/config.d`).

Structure of config directory:  

`conf.json` - main configuration file.  
`devices/` - directory to store credentials of known devices. 
Credentials stored in files like `*.device.json`, other files will be ignored. 
For automatically created files using names `${uin}.device.json`. 
It is recommended to use such naming for manually created files too.   
`plugins/` - plugins configs and device-specific plugin config overrides stored in this directory.
Plugin main configs have names like `${4_character_plugin_mark}.conf.json`.
Device-specific overrides for plugin configs have names like `*.${4_character_plugin_mark}.conf.json`.
It is recommended to use device UIN as prefix for device-specific override.

Example:

    .
    |-conf.json - main dcnnt config
    |-devices - credentials of known devices
    | |-1337.device.json
    | |-phone.device.json
    | |-12309.device.json
    |-plugins - configs for plugins
      |-file.conf.json
      |-1337.file.conf.json
      |-12309.device.json
      |-nots.conf.json
      |-rcmd.conf.json
      |-my_phone.rcmd.conf.json
      |-1337.rcmd.conf.json

Devices
-------

Device configuration is simple JSON dictionary contains data:

* *uin* - unique identifier of device, integer from 0x0F to 0x0FFFFFFF 
* *name* - name of device, string 1 to 40 characters length
* *description* - verbose description of device, string 0 to 200 characters length
* *role* - string constant, must be `client` 
* *password* - access password, string 0 to 4096 characters length

Yes, passwords stored in plain text now. 

Example:

    {
      "description": "UIN is not 0xFFFF",
      "name": "Phone",
      "password": "very c0mpleks pAccv0rd",
      "role": "client",
      "uin": 65543
    }

Plugins
-------

There are two types of configuration files for plugins: 
* base plugin configs,
* device-specific overrides. 

Overrides used to replace configuration of plugin for one specific device.
Main plugin config and overrides have same basic format with one mandatory option:  

* *device* - must be `null` for base plugin config or UIN of device for device-specific override

Example:

Base config `file.conf.json`:

    {
      "device": null,
      "download_directory": "$HOME/Downloads/dcnnt",
      "shared_dirs": [
        {
          "path": "$HOME/Shared",
          "glob": "*.jpg",
          "name": "Shared diretory",
          "deep": 100
        }
      ]
    }

Override `my_phone.file.conf.json`:

    {
      "device": 65543,
      "download_directory": "$HOME/Downloads/dcnnt",
      "shared_dirs": [
        {
          "path": "$HOME/Shared",
          "glob": "*",
          "name": "Shared diretory",
          "deep": 100
        }
      ]
    }

Here device with UIN `65543` has access to any file in directory `Shared` 
while other devices have access to JPG photos only.

