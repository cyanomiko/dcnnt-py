import os
import sys
import time
import atexit
import signal


class Daemon:
    """Set of daemon functions"""

    def __init__(self):
        self.pidfile = os.path.join(os.environ['HOME'], '.dcnnt.pid')

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

    def check(self):
        """Check if daemon is not already running"""
        if not os.path.isfile(self.pidfile):
            return
        with open(self.pidfile, 'r') as pf:
            try:
                pid = int(pf.read().strip())
            except ValueError:
                sys.stderr.write(f'Incorrect content of pidfile "{self.pidfile}", move to "{self.pidfile}.bak"\n')
                os.rename(self.pidfile, f'{self.pidfile}.bak')
                return
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            sys.stderr.write(f'Pidfile "{self.pidfile}" exists, but no process with PID {pid} found\n')
            return
        except Exception:
            pass
        sys.stderr.write(f'Pidfile "{self.pidfile}" and process with PID {pid} exist. '
                         f'Daemon already running?\n')
        sys.exit(1)

    def stop(self):
        """Stop the daemon."""
        pid = None
        if os.path.isfile(self.pidfile):
            with open(self.pidfile, 'r') as pf:
                try:
                    pid = int(pf.read().strip())
                except ValueError:
                    sys.stderr.write(f'Incorrect content of pidfile "{self.pidfile}"\n')
                    return
        if not pid:
            sys.stderr.write(f'Pidfile "{self.pidfile} does not exist. Daemon not running?"\n')
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

