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
    |-devices - credentials of known devices in files "<uin>.device.json"
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
