dcnnt
=====

**NO WAR**

Yet another tool to connect Android phone with desktop similar to KDE Connect.

Features
--------

* Works in background
* Controlled via phone app 
* Configurable via JSON files
* Configuration overrides
* Upload files from phone to desktop
* Download files from pre-defined directories at desktop to phone
* Open files and web URLs from phone on desktop
* Show phone notification
* Execute pre-defined commands on desktop
* Periodically running sync tasks (directories, contacts)

Install
-------

From git repository:

    git clone https://github.com/cyanomiko/dcnnt-py.git
    cd dcnnt-py
    python3 setup.py sdist bdist_wheel
    pip3 install dist/dcnnt-0.9.2-py3-none-any.whl

From PyPI:

    pip3 install dcnnt

Usage
-----

Pairing mode:

    dcnnt pair

Run as daemon:

    dcnnt start

Stop daemon:

    dcnnt stop

Run in foreground mode:

    dcnnt foreground
    
Plugins: [doc/plugins.md](doc/plugins.md) (https://github.com/cyanomiko/dcnnt-py/blob/master/doc/plugins.md)  
Configuring: [doc/config.md](doc/config.md) (https://github.com/cyanomiko/dcnnt-py/blob/master/doc/config.md)
