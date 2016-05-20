from mom.Collectors.GuestBalloon import GuestBalloon


class GuestBalloonOptional(GuestBalloon):
    """
    This Collector gets balloon statistics in the same way GuestBalloon does.
    The only difference is that it reports all the fields as optional and thus
    allows the policy to be evaluated even when the balloon device unavailable.
    """

    def getFields(self):
        return set()

    def getOptionalFields(self):
        return GuestBalloon.getFields(self).union(
                GuestBalloon.getOptionalFields(self))
