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
import ConfigParser
import mom


def start_mom():
    config = ConfigParser.SafeConfigParser()
    config.add_section('logging')
    config.set('logging', 'verbosity', 'critical')

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
