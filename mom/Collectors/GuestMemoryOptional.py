from mom.Collectors.GuestMemory import GuestMemory


class GuestMemoryOptional(GuestMemory):
    """
    This Collector gets memory statistics in the same way GuestMemory does.
    The only difference is that it reports all the fields as optional and thus
    allows the policy to be evaluated even when the guest agent is not running.
    """

    def getFields(self):
        return set()

    def getOptionalFields(self):
        return GuestMemory.getFields(self).union(
            GuestMemory.getOptionalFields(self))
