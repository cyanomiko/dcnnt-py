Plugins
=======

Plugin is part of **dcnnt** implementing one user function such as:
* file transmission;
* remote commands;
* notification sync.

File transmission
-----------------

Plugin id: `file`

File transmission plugin allows to download files from shared directories to client
 and upload files from client to server. 

Options:

* *download_directory* - files uploaded from device stored here
* *shared_dirs* - list of shared directory info entries contains options:
  * *path* - path to directory
  * *glob* - UNIX glob of files that will be visible for device
  * *name* - visible name of directory `null` replaced with name from *path* option
  * *deep* - how many levels of subdirectories are visible for device, integer from 1 to 1024

Example `file.conf.json`:

    {
      "device": null,
      "download_directory": "$HOME/Downloads/dcnnt",
      "shared_dirs": [
        {
          "path": ""$HOME/Shared",
          "glob": "*",
          "name": null,
          "deep": 100
        }
      ]
    }

Notifications
-------------

Plugin id: `nots`

Notification plugin using to show phone notifications on desktop screen. 
Icon are sent from device as PNG and saved to temporary file.
Other notification data such as title, text, etc sent as JSON then substituted to notification show shell command.


Options:

* *icon_dir* - directory for notification icons temporary files
* *cmd* - shell command that invoked on every received notification with some replacements:
  * `{uin}` - replaced with UIN of device which send notification
  * `{name}` - replaced with name of device which send notification
  * `{package}` - replaced with name of Android package which create notification (e.g. `org.example.messages`)
  * `{icon}` - replaced with path to icon temporary file
  * `{title}` - replaced with notification title text
  * `{text}` - replaced with notification text

If option *icon_dir* not defined, value `$DCNNT_RUNTIME_DIR` will be used instead.  
Value of `$DCNNT_RUNTIME_DIR` is one of next variants:  
1. `$XDG_RUNTIME_DIR/dcnnt` - if `XDG_RUNTIME_DIR` env var defined
2. `/var/run/user/$UID/dcnnt` - if directory `/var/run/user/$UID` exists or may be created
3. `/tmp/dcnnt` - otherwise 

Example `nots.conf.json`:

    {
      "device": null,
      "icon_dir": "$DCNNT_RUNTIME_DIR",
      "cmd": "notify-send -i '{icon}' '{title}' '{text}'"
    }

Remote commands
---------------

Plugin id: `rcmd`

This plugin allows user to invoke some pre-defined commands on server using client UI.

There are only one available option - *menu*. It is list of commands entries.
Each command entry may have options:

* *name* - short label for command button in client UI, string 0 to 60 characters length
* *method* - string, only `shell` value are correct now
* *cmd* - shell command to remote run

If options *method* and *shell* are not defined, button in client UI will be rendered as text line.
This may be used to create header/separator for button groups   

Example `rcmd.conf.json`:

    {
      "device": null,
      "menu": [
        {
          "name": "Screensaver"
        },
        {
          "name": "Lock screen",
          "method": "shell",
          "cmd": "$HOME/.local/bin/screensaver-control.sh lock"
        },
        {
          "name": "Unlock screen",
          "method": "shell",
          "cmd": "$HOME/.local/bin/screensaver-control.sh unlock"
        },
        {
          "name": "Player"
        },
        {
          "name": "Start/stop",
          "method": "shell",
          "cmd": "$HOME/.local/bin/player-control.sh toggle"
        },
        {
          "name": "Prev",
          "method": "shell",
          "cmd": "$HOME/.local/bin/player-control.sh prev"
        },
        {
          "name": "Next",
          "method": "shell",
          "cmd": "$HOME/.local/bin/player-control.sh next"
        }
      ]
    }

Data sync plugin
----------------

Plugin id: `sync`

Use this plugin to set periodically running tasks for data sync.
Only directory sync tasks supported now, so only one option in config - *menu*.
This option is list of directory descriptions - info about directories available for sync operations.

Structure of directory description:

* *name* - short label for directory
* *path* - path of directory in filesystem
* *on_done* - shell command to run after sync done - **not implemented now**

Example `sync.conf.json`:

    {
      "device": null,
      "dir": [
        {
          "name": "Saved maps",
          "path": "$HOME/Download/Maps",
          "on_done": null
        },
        {
          "name": "Photos backup",
          "path": "$HOME/Photos/Phone",
          "on_done": "$HOME/.local/bin/update-gallery-db.sh"
        },
      ]
    }

