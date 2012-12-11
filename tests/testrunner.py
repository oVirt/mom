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

import logging
import sys
import os

import unittest
from nose import config
from nose import core
from nose import result

import mom

class MomTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.log = logging.getLogger(self.__class__.__name__)

def run():
    argv = sys.argv
    stream = sys.stdout
    verbosity = 3
    testdir = os.path.dirname(os.path.abspath(__file__))

    conf = config.Config(stream=stream,
                      env=os.environ,
                      verbosity=verbosity,
                      workingDir=testdir,
                      plugins=core.DefaultPluginManager())

    sys.exit(not core.run(config=conf, argv=argv))


if __name__ == '__main__':
    run()
