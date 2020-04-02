import os
import sys
import time
import atexit
import signal


class Daemon:
    """Set of daemon functions"""

    def __init__(self):
        self.pidfile = self.pidfile_path()

    @staticmethod
    def pidfile_path():
        """Try to determine pidfile path"""
        os.getuid()
        run_dir = os.path.join('/', 'var', 'run', 'user', str(os.getuid()))
        if os.path.isdir(run_dir):
            return os.path.join(run_dir, 'dcnnt.pid')
        else:
            return os.path.join(os.environ['HOME'], '.dcnnt.pid')

    def daemonize(self):
        """Deamonize class. UNIX double fork mechanism."""
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as err:
            sys.stderr.write('fork #1 failed: {0}\n'.format(err))
            sys.exit(1)
        # decouple from parent environment
        os.setsid()
        os.umask(0)
        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as err:
            sys.stderr.write('fork #2 failed: {0}\n'.format(err))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        with open(self.pidfile, 'w+') as f:
            f.write(pid + '\n')

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """Start the daemon."""
        # Check for a pidfile to see if the daemon already runs
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if pid:
            message = "pidfile {0} already exist. " + \
                      "Daemon already running?\n"
            sys.stderr.write(message.format(self.pidfile))
            sys.exit(1)
        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """Stop the daemon."""
        # Get the pid from the pidfile
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None
        if not pid:
            message = "pidfile {0} does not exist. " + \
                      "Daemon not running?\n"
            sys.stderr.write(message.format(self.pidfile))
            return  # not an error in a restart
        # Try killing the daemon process	
        try:
            while True:
                os.kill(pid, signal.SIGINT)
                time.sleep(.5)
        except OSError as e:
            error_s = str(e.args)
            if 'No such process' in error_s:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
                return pid
            else:
                print(error_s)
                sys.exit(1)

    def run(self):
        """You should override this method when you subclass Daemon.
        It will be called after the process has been daemonized by 
        start() or restart()."""

