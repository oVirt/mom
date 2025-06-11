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
import threading
import time
import tempfile
import os
import os.path
from unittest import mock
import configparser
import xmlrpc.client

import pytest
import mom

@pytest.fixture
def mom_instance():
    config = configparser.ConfigParser()
    config.add_section('logging')
    config.set('logging', 'verbosity', 'error')
    mom_instance = start_mom(config)
    return mom_instance

@pytest.fixture
def mom_with_config():
    policies = {
            '01_foo': '(+ 1 1)',
            '02_bar': '(- 2 1)'
    }
    policy_dir = tempfile.mkdtemp()
    for name, policy in list(policies.items()):
        with open(os.path.join(policy_dir, name + '.policy'), 'w') as f:
            f.write(policy)
    config = configparser.ConfigParser()
    config.add_section('main')
    config.set('main', 'policy-dir', policy_dir)
    config.add_section('logging')
    config.set('logging', 'verbosity', 'critical')
    mom_with_config = start_mom(config)
    return mom_with_config

@pytest.fixture
def mom_funcs():
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

    mom_funcs = mom.MOMFuncs(None, threads)
    return mom_funcs

def start_mom(config=None):
    mom_instance = mom.MOM("", config)
    t = threading.Thread(target=mom_instance.run)
    t.daemon = True
    t.start()
    while True:
        if not t.is_alive():
            return None
        try:
            mom_instance.setVerbosity('critical')
            break
        except AttributeError:
            time.sleep(1)

    return mom_instance

def test_query(mom_instance):
    assert mom_instance.ping() is True, "MOM should respond to ping"
    assert 'host' in mom_instance.getStatistics()
    assert isinstance(mom_instance.getActiveGuests(),list)

def test_policy_api(mom_instance):
    assert mom_instance.getPolicy() == '0'

    bad_policy = "("
    assert mom_instance.setPolicy(bad_policy) is False
    assert mom_instance.getPolicy() == '0'

    good_policy = "(+ 1 1)"
    assert mom_instance.setPolicy(good_policy) is True
    assert mom_instance.getPolicy() == good_policy

    assert mom_instance.setPolicy(None) is True
    assert mom_instance.getPolicy() == '0'

def test_multiple_policies(mom_instance):
    assert len(list(mom_instance.getNamedPolicies().keys())) == 0

    mom_instance.setNamedPolicy("10_test", "(+ 1 1)")
    mom_instance.setNamedPolicy("20_test", "(- 1 1)")
    policies = mom_instance.getNamedPolicies()
    assert policies["10_test"] == "(+ 1 1)"
    assert policies["20_test"] == "(- 1 1)"

    mom_instance.setNamedPolicy("20_test", None)
    policies = mom_instance.getNamedPolicies()
    assert "20_test" not in policies

def test_multiple_policies_with_config(mom_with_config):
    policies = mom_with_config.getNamedPolicies()
    assert policies['01_foo'] == '(+ 1 1)'
    assert policies['02_bar'] == '(- 2 1)'

    mom_with_config.setNamedPolicy('02_bar', None)
    mom_with_config.setNamedPolicy('03_baz', '(/ 10 5)')
    assert mom_with_config.getPolicy() == "(+ 1 1)\n(/ 10 5)"
    mom_with_config.resetPolicies()
    assert policies['01_foo'] == '(+ 1 1)'
    assert policies['02_bar'] == '(- 2 1)'
    assert '03_baz' not in iter(policies.keys())

def test_big_numbers_in_stats(mom_funcs):
    data = mom_funcs.getStatistics()

    mom.enable_i8()
    packet = xmlrpc.client.dumps((data,))
    (reply,), func = xmlrpc.client.loads(packet)

    assert data == reply
