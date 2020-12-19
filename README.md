dcnnt
=====

Yet another tool to connect Android phone with desktop similar to KDE Connect.

Features
--------

* Works in background
* Controlled via phone app 
* Сonfigurable via JSON files
* Configuration overrides
* Upload files from phone to desktop
* Download files from pre-defined directories at desktop to phone
* Show phone notification
* Execute pre-defined commands on desktop

Install
-------

From git repository:

    git clone https://github.com/cyanomiko/dcnnt-py.git
    cd dcnnt-py
    python3 setup.py sdist bdist_wheel
    pip3 install dist/dcnnt-0.3.7-py3-none-any.whl

From PyPI:

    pip3 install dcnnt

Usage
-----

Run as daemon:

    dcnnt start

Stop daemon:

    dcnnt stop

Run in foreground mode:

    dcnnt foreground
    
Plugins: [doc/plugins.md](doc/plugins.md) (https://github.com/cyanomiko/dcnnt-py/blob/master/doc/plugins.md)  
Configuring: [doc/config.md](doc/config.md) (https://github.com/cyanomiko/dcnnt-py/blob/master/doc/config.md)
