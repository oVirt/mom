
from mom.Collectors.Collector import *
import copy

class GuestIoTune(Collector):
    """
    This Collector uses hypervisor interface to collect guest IO tune info
    """

    class IoTune:
        class IoTuneVals:
            def __init__(self, vals):
                self.vals = vals

            def __getattr__(self, item):
                try:
                    return self.vals[item]
                except KeyError as e:
                    raise AttributeError


        def __init__(self, name, path, guaranteed, maximum, current):
            self.name = name
            self.path = path
            self.guaranteed = self.IoTuneVals(guaranteed)
            self.maximum = self.IoTuneVals(maximum)
            self.current = self.IoTuneVals(current)

        def ioTune(self):
            return {'name': self.name, 'path':self.path, 'ioTune':self.current.vals}

        def setTotalBytesSec(self, val):
            self.current.vals['total_bytes_sec'] = val

        def setReadBytesSec(self, val):
            self.current.vals['read_bytes_sec'] = val

        def setWriteBytesSec(self, val):
            self.current.vals['write_bytes_sec'] = val

        def setTotalIopsSec(self, val):
            self.current.vals['total_iops_sec'] = val

        def setReadIopsSec(self, val):
            self.current.vals['read_iops_sec'] = val

        def setWriteIopsSec(self, val):
            self.current.vals['write_iops_sec'] = val


    def __init__(self, properties):
        self.hypervisor_iface = properties['hypervisor_iface']
        self.uuid = properties['uuid']
        self.logger = logging.getLogger('mom.Collectors.IoTuneInfo')
        self.info_available = True

    def getFields(self=None):
        return set(['io_tune', 'io_tune_current'])

    def stats_error(self, msg):
        if self.info_available:
            self.logger.debug(msg)
        self.info_available = False

    def collect(self):
        policyList = self.hypervisor_iface.getVmIoTunePolicy(self.uuid)
        if not policyList:
            self.stats_error('getVmIoTunePolicy() is not ready')
            return None

        # Ignore IoTune when the current status list is empty
        stateList = self.hypervisor_iface.getVmIoTune(self.uuid)
        if not stateList:
            self.stats_error('getVmIoTune() is not ready')
            return None

        self.info_available = True

        currentList = []
        resList = []

        def findState(name, path):
            for state in stateList:
                sPath = state.get('path')
                if path == sPath:
                    return state

                if (path is None or sPath is None) and (name == state.get('name')):
                    return state

            return None

        for policyLimits in policyList:
            name = policyLimits.get('name')
            path = policyLimits.get('path')
            state = findState(name, path)

            # Ignore policy if device does not exist
            if state is None:
                continue

            resList.append(self.IoTune(
                state['name'],
                state['path'],
                policyLimits['guaranteed'],
                policyLimits['maximum'],
                state['ioTune']))

            currentList.append(copy.deepcopy(state))

        return {'io_tune': resList, 'io_tune_current': currentList}

