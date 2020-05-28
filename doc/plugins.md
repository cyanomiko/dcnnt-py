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

* *icon_path* - path to save icon data to
* *cmd* - shell command that invoked on every received notification with some replacements:
  * `{icon}` - replaced with *icon_path*
  * `{title}` - replaced with notification title text
  * `{text}` - replaced with notification text

Example `nots.conf.json`:

    {
      "device": null,
      "icon_path": "/tmp/dcnnt-notification-icon.png,
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

