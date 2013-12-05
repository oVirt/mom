# Memory Overcommitment Manager
# Copyright (C) 2010 Adam Litke, IBM Corporation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

import threading
import time
import logging
import os
from Policy.Policy import Policy, PolicyError

class PolicyEngine(threading.Thread):
    """
    At a regular interval, this thread triggers system reconfiguration by
    sampling host and guest data, evaluating the policy and reporting the
    results to all enabled Controller plugins.
    """
    def __init__(self, config, hypervisor_iface, host_monitor, guest_manager):
        threading.Thread.__init__(self, name="PolicyEngine")
        self.setDaemon(True)
        self.config = config
        self.logger = logging.getLogger('mom.PolicyEngine')
        self.properties = {
            'hypervisor_iface': hypervisor_iface,
            'host_monitor': host_monitor,
            'guest_manager': guest_manager,
        }

        self.policy = Policy()
        self.load_policy()
        self.start()

    def load_policy(self):
        def read_policy(file_name, policy_name):
            try:
                with open(file_name, 'r') as f:
                    policyStr = f.read()
            except IOError, e:
                self.logger.warn("Unable to read policy file: %s" % e)
                return False
            return self.policy.set_policy(policy_name, policyStr)

        fname = self.config.get('main', 'policy')
        if fname:
            return read_policy(fname, None)

        policy_dir = self.config.get('main', 'policy-dir')
        if policy_dir:
            try:
                names = sorted(os.listdir(policy_dir))
            except OSError, e:
                self.logger.warn("Unable to read directory '%s': %s" % (
                                    policy_dir, e.strerror))
                return False
            for name in names:
                if name.startswith('.') or not name.endswith('.policy'):
                    continue
                fname = os.path.join(policy_dir, name)
                read_policy(fname, name.split('.policy')[0])
            return True

    def rpc_reset_policy(self):
        self.policy.clear_policy()
        return self.load_policy()

    def rpc_get_policy(self):
        return self.policy.get_string()

    def rpc_set_policy(self, policyStr):
        self.policy.clear_policy()
        return self.policy.set_policy(None, policyStr)

    def rpc_get_named_policies(self):
        return self.policy.get_strings()

    def rpc_set_named_policy(self, name, policyStr):
        return self.policy.set_policy(name, policyStr)

    def get_controllers(self):
        """
        Initialize the Controllers called for in the config file.
        """
        self.controllers = []
        config_str = self.config.get('main', 'controllers')
        for name in config_str.split(','):
            name = name.lstrip()
            if name == '':
                continue
            try:
                module = __import__('mom.Controllers.' + name, None, None, name)
                self.logger.debug("Loaded %s controller", name)
            except ImportError:
                self.logger.warn("Unable to import controller: %s", name)
                continue
            self.controllers.append(getattr(module, name)(self.properties))

    def do_controls(self):
        """
        Sample host and guest data, process the rule set and feed the results
        into each configured Controller.
        """
        host = self.properties['host_monitor'].interrogate()
        if host is None:
            return
        guest_list = self.properties['guest_manager'].interrogate().values()

        ret = self.policy.evaluate(host, guest_list)
        if ret is False:
            return
        for c in self.controllers:
            c.process(host, guest_list)

    def run(self):
        try:
            self.logger.info("Policy Engine starting")
            self.get_controllers()
            interval = self.config.getint('main', 'policy-engine-interval')
            while self.config.getint('__int__', 'running') == 1:
                time.sleep(interval)
                self.do_controls()
        except Exception as e:
            self.logger.error("Policy Engine crashed", exc_info=True)
        else:
            self.logger.info("Policy Engine ending")

