import unittest
from mom.optional import Optional


class OptionalTests(unittest.TestCase):
    def test_missing(self):
        self.assertEqual(False, Optional.missing().present)

    def test_missing_none(self):
        self.assertEqual(None, Optional.missing().orNone())

    def test_missing_else(self):
        self.assertEqual(False, Optional.missing().orElse(False))

    def test_missing_raise(self):
        with self.assertRaises(RuntimeError):
            Optional.missing().orRaise(RuntimeError, "error")

    def test_missing_map(self):
        self.assertEqual(False, Optional.missing().map(lambda val: 5/0).present)

    def test_missing_get(self):
        self.assertEqual(False, Optional.missing().get("key").present)

    def test_missing_item(self):
        self.assertEqual(False, Optional.missing()["key"].present)

    def test_missing_iter(self):
        self.assertRaises(StopIteration, iter(Optional.missing()).next)

    def test_value(self):
        self.assertEqual(True, Optional("val").present)
        self.assertEqual("val", Optional("val").value)

    def test_raise(self):
        self.assertEqual(Optional("val").orRaise(RuntimeError, "error"), "val")

    def test_map(self):
        self.assertEqual("VAL", Optional("val").map(str.upper).value)

    def test_get(self):
        self.assertEqual("val", Optional({"key": "val"}).get("key").value)

    def test_get_default(self):
        self.assertEqual("default", Optional({"key": "val"}).get("key2", "default").value)

    def test_item(self):
        self.assertEqual("val", Optional({"key": "val"})["key"].value)

    def test_get_default_item(self):
        self.assertEqual(False, Optional({"key": "val"})["key2"].present)

    def test_iter(self):
        self.assertEqual("val", iter(Optional(["val"])).next())
