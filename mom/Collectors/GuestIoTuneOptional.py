from mom.Collectors.GuestIoTune import GuestIoTune


class GuestIoTuneOptional(GuestIoTune):
    """
    This Collector gets IoTune statistics in the same way GuestIoTune does.
    The only difference is that it reports all the fields as optional and thus
    allows the policy to be evaluated even when the balloon device unavailable.
    """

    def getFields(self):
        return set()

    def getOptionalFields(self):
        return GuestIoTune.getFields(self).union(
                GuestIoTune.getOptionalFields(self))
