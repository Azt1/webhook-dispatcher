import tempfile
import unittest
from pathlib import Path

from webhook_dispatcher.queue import EventQueue


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "nested" / "events.db"
        self.queue = EventQueue(self.path)

    def test_preserves_events_after_reopening(self):
        event_id = self.queue.add("http://localhost:9000/events", {"order": 42})
        events = EventQueue(self.path).list()
        self.assertEqual(events[0]["id"], event_id)
        self.assertEqual(events[0]["status"], "pending")

    def test_does_not_store_invalid_events(self):
        with self.assertRaises(ValueError):
            self.queue.add("file:///tmp", {})
        self.assertEqual(self.queue.list(), [])

    def test_delivered_event_leaves_pending_queue(self):
        event_id = self.queue.add("http://localhost:9000", {})
        self.queue.record(event_id, "delivered", 204)
        self.assertEqual(self.queue.ready(), [])
        self.assertEqual(self.queue.list()[0]["attempts"], 1)

    def test_retry_waits_for_scheduled_time(self):
        event_id = self.queue.add("http://localhost:9000", {})
        self.queue.record(event_id, "pending", 503, "HTTP 503", next_attempt=100)
        self.assertEqual(self.queue.ready(now=99), [])
        self.assertEqual(len(self.queue.ready(now=100)), 1)

    def test_unknown_id_is_rejected(self):
        with self.assertRaises(ValueError):
            self.queue.record("missing", "delivered")

    def test_list_filters_by_status_without_changing_events(self):
        pending_id = self.queue.add("http://localhost:9000", {"order": 1})
        delivered_id = self.queue.add("http://localhost:9000", {"order": 2})
        failed_id = self.queue.add("http://localhost:9000", {"order": 3})
        self.queue.record(delivered_id, "delivered", 204)
        self.queue.record(failed_id, "failed", 400, "HTTP 400")
        before = self.queue.list()
        for status, event_id in [("pending", pending_id), ("delivered", delivered_id),
                                 ("failed", failed_id)]:
            with self.subTest(status=status):
                self.assertEqual([event["id"] for event in self.queue.list(status)], [event_id])
        self.assertEqual(self.queue.list(), before)

    def test_list_rejects_invalid_status(self):
        with self.assertRaises(ValueError):
            self.queue.list("unknown")
