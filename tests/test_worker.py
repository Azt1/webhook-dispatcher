import tempfile
import unittest
from pathlib import Path

from webhook_dispatcher.delivery import DeliveryResult
from webhook_dispatcher.queue import EventQueue
from webhook_dispatcher.worker import run_once


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.queue = EventQueue(Path(self.directory.name) / "events.db")
        self.queue.add("http://localhost:9000", {"event": "order.created"})
        self.now = self.queue.list()[0]["created_at"]

    def run_worker(self, code, **kwargs):
        return run_once(self.queue, sender=lambda event: DeliveryResult(code),
                        clock=lambda: self.now, **kwargs)

    def test_success_is_not_sent_twice(self):
        self.assertEqual(self.run_worker(200)["delivered"], 1)
        self.assertEqual(self.run_worker(200)["delivered"], 0)
        self.assertEqual(self.queue.list()[0]["attempts"], 1)

    def test_server_error_retries_with_increasing_delay(self):
        self.run_worker(503)
        self.assertEqual(self.queue.list()[0]["next_attempt"], self.now + 30)
        self.assertEqual(self.run_worker(503)["pending"], 0)
        self.now += 30
        self.run_worker(503)
        self.assertEqual(self.queue.list()[0]["next_attempt"], self.now + 60)
        self.now += 60
        self.assertEqual(self.run_worker(503)["failed"], 1)
        self.assertEqual(self.queue.list()[0]["attempts"], 3)

    def test_client_error_fails_without_retry(self):
        self.assertEqual(self.run_worker(400)["failed"], 1)

    def test_network_error_is_retryable(self):
        self.assertEqual(self.run_worker(None)["pending"], 1)

    def test_rate_limit_is_retryable(self):
        self.assertEqual(self.run_worker(429)["pending"], 1)

    def test_invalid_retry_settings_are_rejected(self):
        with self.assertRaises(ValueError):
            self.run_worker(200, max_attempts=0)
