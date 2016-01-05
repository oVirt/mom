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

import logging
from LogUtils import *
import numbers

EXPORTED_ATTRIBUTE = "__mom_exported__"


def exported(f):
    setattr(f, EXPORTED_ATTRIBUTE, True)
    return f


class MOMFuncs(object):
    def __init__(self, config, threads):
        self.config = config
        self.threads = threads
        self.logger = logging.getLogger('mom.RPCServer')

    @exported
    def ping(self):
        self.logger.info("ping()")
        return True

    @exported
    def resetPolicies(self):
        self.logger.info('resetPolicyies()')
        return self.threads['policy_engine'].rpc_reset_policy()

    @exported
    def setPolicy(self, policy):
        self.logger.info("setPolicy()")
        self.logger.debug("New Policy:\n %s", policy)
        return self.threads['policy_engine'].rpc_set_policy(policy)

    @exported
    def setNamedPolicy(self, name, policy):
        self.logger.info("setNamedPolicy()")
        return self.threads['policy_engine'].rpc_set_named_policy(name, policy)

    @exported
    def getPolicy(self):
        self.logger.info("getPolicy()")
        return self.threads['policy_engine'].rpc_get_policy()

    @exported
    def getNamedPolicies(self):
        self.logger.info("getNamedPolicies()")
        return self.threads['policy_engine'].rpc_get_named_policies()

    @exported
    def setVerbosity(self, verbosity):
        self.logger.info("setVerbosity()")
        logger = logging.getLogger()
        log_set_verbosity(logger, verbosity)
        return True

    @exported
    def getStatistics(self):
        self.logger.info("getStatistics()")
        host_stats = self.threads['host_monitor'].interrogate().statistics[-1]
        guest_stats = {}
        guest_entities = self.threads['guest_manager'].interrogate().values()
        for entity in guest_entities:
            guest_stats[entity.properties['name']] = entity.statistics[-1]
        ret = {'host': host_stats, 'guests': guest_stats}
        return ret

    @exported
    def getActiveGuests(self):
        self.logger.info("getActiveGuests()")
        return self.threads['guest_manager'].rpc_get_active_guests()
