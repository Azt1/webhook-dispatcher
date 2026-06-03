import unittest

from webhook_dispatcher.events import validate_event


class EventTests(unittest.TestCase):
    def test_accepts_json_with_accents(self):
        self.assertIn("João", validate_event("https://example.com/events", {"name": "João"}))

    def test_rejects_invalid_destinations(self):
        for url in ["", "file:///tmp/event", "https://", "https://user:secret@example.com",
                    "https://example.com/#token", "https://example.com:bad", "http://localhost:0"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_event(url, {})

    def test_rejects_non_object_payload(self):
        with self.assertRaises(ValueError):
            validate_event("https://example.com", [])

    def test_rejects_non_json_values(self):
        for payload in [{"n": float("nan")}, {"value": object()}]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_event("https://example.com", payload)
