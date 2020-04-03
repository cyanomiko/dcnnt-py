dcnnt
=====

Yet another tool to connect Android phone with desktop similar to KDE Connect.

Build and install
-----------------

    git clone https://github.com/cyanomiko/dcnnt-py.git
    cd dcnnt-py
    python3 setup.py sdist bdist_wheel
    pip3 install dist/dcnnt-0.3.3-py3-none-any.whl

Usage
-----

Run as daemon:

    dcnnt start

Stop daemon:

    dcnnt stop

Run in foreground mode:

    dcnnt foreground
