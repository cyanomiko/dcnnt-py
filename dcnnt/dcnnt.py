#!/usr/bin/env python3
import os
import sys
import argparse

from .app import DConnectApp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--doc', help='Print conf doc and exit', action='store_true')
    parser.add_argument('-c', '--configuration-directory', help='Path to configuration directory',
                        default=os.path.join(os.environ['HOME'], '.config', 'dcnnt'))
    parser.add_argument('mode', choices=('doc', 'foreground', 'pair', 'start', 'stop', 'restart'),
                        nargs='?', default='start',
                        help='Mode to run program: doc - just print config documentation and exit, '
                             'foreground - run program in current tty, '
                             'start/stop/restart - run and stop program as daemon')
    args = parser.parse_args(sys.argv[1:])
    if args.mode == 'doc':
        print(str(DConnectApp.CONFIG_SCHEMA))
        print(DConnectApp.CONFIG_SCHEMA.get_default())
    elif args.mode == 'foreground':
        app = DConnectApp(args.configuration_directory, True)
        app.init()
        app.run()
        input('Press Enter to stop app...\n')
        app.shutdown()
    else:
        app = DConnectApp(args.configuration_directory, False)
        if args.mode == 'start':
            app.check()
            app.init()
            print(f'Starting in background, pidfile: {app.pidfile}')
            app.daemonize()
            app.run()
        elif args.mode == 'pair':
            app.check()
            app.pair()
        elif args.mode == 'stop':
            pid = app.stop()
            if pid:
                print(f'Process {pid} stopped')
        elif args.mode == 'restart':
            pid = app.stop()
            if pid:
                print(f'Process {pid} stopped')
            app.check()
            app.init()
            print(f'Restarting, pidfile: {app.pidfile}')
            app.daemonize()
            app.run()
        else:
            print('Incorrect "mode" argument', file=sys.stderr)
            sys.exit(2)
