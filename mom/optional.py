class Optional(object):
    """A class that should make it easier to handle "missing" return values."""

    def __init__(self, value, set=True):
        self._value = value
        self._set = set

    @classmethod
    def missing(cls):
        return cls(None, set=False)

    @property
    def value(self):
        return self._value

    @property
    def present(self):
        return self._set

    def orNone(self):
        return self.value if self._set else None

    def orElse(self, default):
        return self.value if self._set else default

    def orRaise(self, exception, *args, **kwargs):
        if not self._set:
            raise exception(*args, **kwargs)

        return self.value

    def map(self, func):
        return Optional(func(self.value)) if self._set else Optional.missing()

    def get(self, key, default=None):
        return Optional(self.value.get(key, default)) if self._set else Optional.missing()

    def __getitem__(self, key):
        if not self._set:
            return Optional.missing()
        try:
            return Optional(self.value[key])
        except KeyError:
            return Optional.missing()

    def __iter__(self):
        return iter(self.orElse(()))
