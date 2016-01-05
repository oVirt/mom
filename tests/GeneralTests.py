# Memory Overcommitment Manager
# Copyright (C) 2012 Adam Litke, IBM Corporation
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

from testrunner import MomTestCase as TestCaseBase

import threading
import time
import tempfile
import os
import os.path
import shutil
import ConfigParser
import mom
import mock
import xmlrpclib

def start_mom(config=None):
    if not config:
        config = ConfigParser.SafeConfigParser()
        config.add_section('logging')
        config.set('logging', 'verbosity', 'error')

    mom_instance = mom.MOM("", config)
    t = threading.Thread(target=mom_instance.run)
    t.setDaemon(True)
    t.start()
    while True:
        if not t.isAlive():
            return None
        try:
            mom_instance.setVerbosity('critical')
            break
        except AttributeError:
            time.sleep(1)

    return mom_instance


class GeneralTests(TestCaseBase):
    def setUp(self):
        self.mom_instance = start_mom()

    def tearDown(self):
        self.mom_instance.shutdown()

    def testQuery(self):
        self.assertTrue(self.mom_instance.ping())
        self.assertTrue('host' in self.mom_instance.getStatistics())
        self.assertTrue(isinstance(self.mom_instance.getActiveGuests(),
                                     list))
    def testPolicyAPI(self):
        self.assertEquals('0', self.mom_instance.getPolicy())

        badPolicy = "("
        self.assertFalse(self.mom_instance.setPolicy(badPolicy))
        self.assertEquals('0', self.mom_instance.getPolicy())

        goodPolicy = "(+ 1 1)"
        self.assertTrue(self.mom_instance.setPolicy(goodPolicy))
        self.assertEquals(goodPolicy, self.mom_instance.getPolicy())

        self.assertTrue(self.mom_instance.setPolicy(None))
        self.assertEquals('0', self.mom_instance.getPolicy())

    def testMultiplePolicies(self):
        self.assertEquals(0, len(self.mom_instance.getNamedPolicies().keys()))

        self.mom_instance.setNamedPolicy("10_test", "(+ 1 1)")
        self.mom_instance.setNamedPolicy("20_test", "(- 1 1)")
        policies = self.mom_instance.getNamedPolicies()
        self.assertEquals("(+ 1 1)", policies["10_test"])
        self.assertEquals("(- 1 1)", policies["20_test"])

        self.mom_instance.setNamedPolicy("20_test", None)
        policies = self.mom_instance.getNamedPolicies()
        self.assertFalse("20_test" in policies)

class ConfigTests(TestCaseBase):
    def testMultiplePolicies(self):
        policies = {
            '01_foo': '(+ 1 1)',
            '02_bar': '(- 2 1)'
        }
        policy_dir = tempfile.mkdtemp()
        for name, policy in policies.items():
            with open(os.path.join(policy_dir, name + '.policy'), 'w') as f:
                f.write(policy)


        config = ConfigParser.SafeConfigParser()
        config.add_section('main')
        config.set('main', 'policy-dir', policy_dir)
        config.add_section('logging')
        config.set('logging', 'verbosity', 'critical')
        mom_instance = start_mom(config)

        try:
            policies = mom_instance.getNamedPolicies()
            self.assertEquals('(+ 1 1)', policies['01_foo'])
            self.assertEquals('(- 2 1)', policies['02_bar'])

            mom_instance.setNamedPolicy('02_bar', None)
            mom_instance.setNamedPolicy('03_baz', '(/ 10 5)')
            self.assertEquals("(+ 1 1)\n(/ 10 5)", mom_instance.getPolicy())
            mom_instance.resetPolicies()
            self.assertEquals('(+ 1 1)', policies['01_foo'])
            self.assertEquals('(- 2 1)', policies['02_bar'])
            self.assertTrue('03_baz' not in policies.iterkeys())
        finally:
            shutil.rmtree(policy_dir)


class RpcTests(TestCaseBase):
    def testBigNumbersInStats(self):
        host_monitor = mock.Mock()
        host_monitor.interrogate.return_value.statistics = [{
            "ksm_run": 1,
            "ksm_pages": 100,
            "huge_number": 2**31 + 2**10
        }]

        vm1 = mock.Mock()
        vm1.properties = {"name": "vm1"}
        vm1.statistics = [{
            "free_mem": 25 * 2**30 # 25 TiB (in KiB)
        }]

        vm2 = mock.Mock()
        vm2.properties = {"name": "vm2"}
        vm2.statistics = [{
            "free_mem": 30 * 2**20 # 30 GiB (in KiB)
        }]

        guest_manager = mock.Mock()
        guest_manager.interrogate.return_value.values.return_value = [
            vm1, vm2
        ]

        threads = {
            "host_monitor": host_monitor,
            "guest_manager": guest_manager
        }

        funcs = mom.MOMFuncs(None, threads)
        data = funcs.getStatistics()

        mom.enable_i8()
        packet = xmlrpclib.dumps((data,))
        (reply,), func = xmlrpclib.loads(packet)

        self.assertEqual(data, reply)
