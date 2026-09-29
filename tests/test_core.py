import logging
import logging.handlers
import unittest

from log_record_attribute_injector import AttributeInjector


def _make_record(msg="hello", **extra):
    """Build a LogRecord the way logging.Logger does."""
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="/app/example.py",
        lineno=10,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for k, v in extra.items():
        setattr(record, k, v)
    return record


class AttributeInjectorTests(unittest.TestCase):
    def test_injects_attributes(self):
        inj = AttributeInjector({"request_id": "abc-123", "env": "staging"})
        rec = _make_record()
        self.assertTrue(inj.filter(rec))
        self.assertEqual(rec.request_id, "abc-123")
        self.assertEqual(rec.env, "staging")

    def test_filter_returns_true(self):
        inj = AttributeInjector({"request_id": "r1"})
        rec = _make_record()
        self.assertIs(inj.filter(rec), True)

    def test_overwrites_existing_attribute(self):
        """If a record already has the attribute, it is overwritten."""
        inj = AttributeInjector({"request_id": "injected"})
        rec = _make_record(request_id="pre-existing")
        inj.filter(rec)
        self.assertEqual(rec.request_id, "injected")

    def test_attribute_names_sorted(self):
        inj = AttributeInjector({"zeta": 1, "alpha": 2, "mid": 3})
        self.assertEqual(inj.attribute_names, ("alpha", "mid", "zeta"))

    def test_empty_attributes(self):
        inj = AttributeInjector({})
        rec = _make_record()
        self.assertTrue(inj.filter(rec))
        self.assertEqual(inj.attribute_names, ())

    def test_with_hostname_explicit(self):
        inj = AttributeInjector.with_hostname(
            hostname="web-01.local", request_id="r9"
        )
        rec = _make_record()
        inj.filter(rec)
        self.assertEqual(rec.hostname, "web-01.local")
        self.assertEqual(rec.request_id, "r9")

    def test_with_hostname_resolves(self):
        """with_hostname without an explicit value populates hostname."""
        inj = AttributeInjector.with_hostname()
        rec = _make_record()
        inj.filter(rec)
        self.assertTrue(hasattr(rec, "hostname"))
        self.assertIsInstance(rec.hostname, str)
        self.assertTrue(len(rec.hostname) > 0)

    def test_rejects_non_dict(self):
        with self.assertRaises(TypeError):
            AttributeInjector([("request_id", "x")])

    def test_rejects_non_str_key(self):
        with self.assertRaises(TypeError):
            AttributeInjector({1: "x"})

    def test_rejects_invalid_identifier(self):
        with self.assertRaises(ValueError):
            AttributeInjector({"bad-name": "x"})

    def test_rejects_reserved_field(self):
        with self.assertRaises(ValueError):
            AttributeInjector({"msg": "overridden"})

    def test_rejects_another_reserved_field(self):
        with self.assertRaises(ValueError):
            AttributeInjector({"levelno": 99})

    def test_reserved_check_covers_created(self):
        with self.assertRaises(ValueError):
            AttributeInjector({"created": 0.0})

    def test_does_not_touch_unrelated_fields(self):
        """Reserved fields keep their original values after filtering."""
        inj = AttributeInjector({"request_id": "r1"})
        rec = _make_record(msg="original message")
        original_created = rec.created
        original_levelno = rec.levelno
        inj.filter(rec)
        self.assertEqual(rec.msg, "original message")
        self.assertEqual(rec.levelno, original_levelno)
        self.assertEqual(rec.created, original_created)

    def test_works_as_logging_filter(self):
        """Plug into a real handler/logger to confirm integration."""
        logger = logging.getLogger("attribute.injector.test")
        logger.setLevel(logging.DEBUG)
        handler = logging.handlers.MemoryHandler(capacity=10)
        handler.setLevel(logging.DEBUG)
        inj = AttributeInjector({"request_id": "integration-1"})
        handler.addFilter(inj)
        logger.addHandler(handler)

        logger.info("a message")

        self.assertEqual(len(handler.buffer), 1)
        rec = handler.buffer[0]
        self.assertEqual(rec.request_id, "integration-1")

        logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
