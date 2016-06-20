
import logging

class IoTune:
    """
    Controller that uses the hypervisor interface to manipulate
    the IO tuning parameters
    """

    def __init__(self, properties):
        self.hypervisor_iface = properties['hypervisor_iface']
        self.logger = logging.getLogger('mom.Controllers.IoTune')

    def process_guest(self, guest):
        ioTune = guest.io_tune
        ioTune_prev = guest.io_tune_current

        if not ioTune or not ioTune_prev:
            return

        changedList = []
        for i in xrange(len(ioTune)):
            tune = ioTune[i].ioTune()
            tune_prev = ioTune_prev[i]

            # nothing changed
            if tune['ioTune'] == tune_prev['ioTune']:
                continue

            changedList.append(tune)

        uuid = guest.Prop('uuid')
        name = guest.Prop('name')
        if changedList:
            self.hypervisor_iface.setVmIoTune(uuid, changedList)

    def process(self, host, guests):
        for guest in guests:
            self.process_guest(guest)
