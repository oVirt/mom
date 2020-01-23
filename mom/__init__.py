from six.moves import configparser
import os
import time
import re
import logging.handlers
from mom.LogUtils import *
from mom.HostMonitor import HostMonitor
from mom.HypervisorInterfaces.HypervisorInterface import ConnectionError
from mom.GuestManager import GuestManager
from mom.PolicyEngine import PolicyEngine
from mom.RPCServer import RPCServer, enable_i8
from mom.MOMFuncs import MOMFuncs, EXPORTED_ATTRIBUTE

class MOM:
    def __init__(self, conf_file, conf_overrides=None):
        self._load_config(conf_file, conf_overrides)
        self.logger = self._configure_logger()

    def run(self):
        if not self._validate_config():
            self.logger.error("Invalid configuration.  Unable to start")
            return

        # Start threads
        self.logger.info("MOM starting")
        self.config.set('__int__', 'running', '1')
        try:
            host_monitor = HostMonitor(self.config)
            hypervisor_iface = self.get_hypervisor_interface()
            if not hypervisor_iface:
                self.shutdown()
            guest_manager = GuestManager(self.config, hypervisor_iface)
            guest_manager.start()
            policy_engine = PolicyEngine(self.config, hypervisor_iface,
                                         host_monitor, guest_manager)

            threads = {'host_monitor': host_monitor,
                       'guest_manager': guest_manager,
                       'policy_engine': policy_engine}
            momFuncs = MOMFuncs(self.config, threads)
            self._setupAPI(momFuncs)
            rpc_server = RPCServer(self.config, momFuncs)
        except ConnectionError as e:
            self.logger.error(
                "Cannot connect to VDSM. "
                "This can happen when VDSM is starting. Error: %s",
                str(e)
            )
            return
        except Exception as e:
            self.logger.exception("Failed to initialize MOM threads")
            return

        interval = self.config.getint('main', 'main-loop-interval')
        while self.config.getint('__int__', 'running') == 1:
            time.sleep(interval)
            if not self._threads_ok((host_monitor,guest_manager,policy_engine)):
                self.config.set('__int__', 'running', '0')
            # Check the RPC server separately from the other threads since it
            # can be disabled.
            if not rpc_server.thread_ok():
                self.config.set('__int__', 'running', '0')

        self.logger.info("Shutting down RPC server.")
        rpc_server.shutdown()

        self.logger.info("Waiting for RPC server thread.")
        self._wait_for_thread(rpc_server, 5)

        self.logger.info("Waiting for policy engine thread.")
        self._wait_for_thread(policy_engine, 10)

        self.logger.info("Waiting for guest manager thread.")
        self._wait_for_thread(guest_manager, 5)

        self.logger.info("Waiting for host monitor thread.")
        self._wait_for_thread(host_monitor, 5)

        self.logger.info("MOM ending")

    def shutdown(self):
        self.config.set('__int__', 'running', '0')

    def _setupAPI(self, funcs):
        """
        Initialize the public API in the MOMFuncs class and add its members to
        this MOM instance so they can be called by our owner as well.
        """

        for funcName in dir(funcs):
            funcObj = getattr(funcs, funcName)
            if hasattr(funcObj, EXPORTED_ATTRIBUTE) and callable(funcObj):
                setattr(self, funcName, funcObj)

    def _load_config(self, fname, overrides):
        self.config = configparser.SafeConfigParser()

        # Set built-in defaults
        self.config.add_section('main')
        self.config.set('main', 'main-loop-interval', '5')
        self.config.set('main', 'host-monitor-interval', '5')
        self.config.set('main', 'guest-manager-interval', '5')
        self.config.set('main', 'hypervisor-interface', 'libvirt')
        self.config.set('main', 'guest-monitor-interval', '5')
        self.config.set('main', 'policy-engine-interval', '10')
        self.config.set('main', 'sample-history-length', '10')
        self.config.set('main', 'libvirt-hypervisor-uri', '')
        self.config.set('main', 'controllers', 'Balloon')
        self.config.set('main', 'plot-dir', '')
        self.config.set('main', 'rpc-port', '-1')
        self.config.set('main', 'policy', '')
        self.config.set('main', 'policy-dir', '')
        self.config.set('main', 'guest-manager-multi-thread', 'true')
        self.config.add_section('logging')
        self.config.set('logging', 'log', 'stdio')
        self.config.set('logging', 'verbosity', 'info')
        self.config.set('logging', 'max-bytes', '2097152')
        self.config.set('logging', 'backup-count', '5')
        self.config.add_section('host')
        self.config.set('host', 'collectors', 'HostMemory')
        self.config.add_section('guest')
        self.config.set('guest', 'collectors', 'GuestQemuProc, GuestMemory')

        # Override defaults from the config file
        self.config.read(fname)

        # Process configuration overrides from our owner.  For example, momd
        # allows certain settings to be overriden via its command line.
        if overrides is not None:
            for sect in overrides.sections():
                if sect not in self.config.sections():
                    continue
                for (item, value) in overrides.items(sect):
                    self.config.set(sect, item, value)

        # Add non-customizable thread-global variables
        # The supplied config file must not contain a '__int__' section
        if self.config.has_section('__int__'):
            self.config.remove_section('__int__')
        self.config.add_section('__int__')
        self.config.set('__int__', 'running', '0')
        plot_subdir = self._get_plot_subdir(self.config.get('main', 'plot-dir'))
        self.config.set('__int__', 'plot-subdir', plot_subdir)

    def _validate_config(self):
        policy = self.config.get('main', 'policy')
        policy_dir = self.config.get('main', 'policy-dir')
        if policy and policy_dir:
            self.logger.error("Only one of 'policy' and 'policy-dir' may be"
                               "specified")
            return False
        return True

    def _configure_logger(self):
        logger = logging.getLogger('mom')
        # MOM is a module with its own logging facility. Don't impact any
        # logging that might be done by the program that loads this.
        logger.propagate = False

        verbosity = self.config.get('logging', 'verbosity').lower()
        level = log_set_verbosity(logger, verbosity)

        log = self.config.get('logging', 'log')
        if log.lower() == 'stdio':
            handler = logging.StreamHandler()
        else:
            bytes = self.config.getint('logging', 'max-bytes')
            backups = self.config.getint('logging', 'backup-count')
            handler = logging.handlers.RotatingFileHandler(log, 'a', bytes, backups)
        handler.setLevel(level)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _get_plot_subdir(self, basedir):
        """
        Create a new directory for plot files inside basedir.  The name is in the
        format: momplot-NNN where NNN is an ascending sequence number.
        Return: The new directory name or '' on error.
        """
        if basedir == '':
            return ''

        regex = re.compile(r'^momplot-(\d{3})$')
        try:
            names = os.listdir(basedir)
        except OSError as e:
            self.logger.warn("Cannot read plot-basedir %s: %s", basedir, e.strerror)
            return ''
        seq_num = -1
        for name in names:
            m = regex.match(name)
            if m is not None:
                num =  int(m.group(1))
                if num > seq_num:
                    seq_num = num
        seq_num = seq_num + 1
        dir = "%s/momplot-%03d" % (basedir, seq_num)
        if seq_num > 999:
            self.logger.warn("Cannot create plot-dir because the sequence number "\
                  "is out of range.  Clear the directory or choose a different one")
            return ''
        try:
            os.mkdir(dir)
        except OSError as e:
            self.logger.warn("Cannot create plot-dir %s: %s", dir, e.strerror)
            return ''
        return dir

    def _threads_ok(self, threads):
        """
        Check to make sure a list of expected threads are still alive
        """
        for t in threads:
            if not t.is_alive():
                self.logger.error("Thread '%s' has exited" % t.getName())
                return False
        return True

    def _wait_for_thread(self, t, timeout):
        """
        Join a thread only if it is still running
        """
        if t.is_alive():
            t.join(timeout)

    def get_hypervisor_interface(self):

        name = self.config.get('main', 'hypervisor-interface').lower()
        self.logger.info("hypervisor interface %s",name)
        try:
            module = __import__('mom.HypervisorInterfaces.' + name + 'Interface', None, None, name)
            return module.instance(self.config)
        except ImportError:
            self.logger.error("Unable to import hypervisor interface: %s", name)
            return None
