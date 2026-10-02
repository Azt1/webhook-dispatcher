import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from webhook_dispatcher.cli import main
from webhook_dispatcher.queue import EventQueue


class CliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.db = self.root / "events.db"
        self.payload = self.root / "event.json"
        self.payload.write_text('{"customer": "João"}', encoding="utf-8-sig")

    def invoke(self, *args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--db", str(self.db), *args])
        self.assertEqual(code, 0)
        return output.getvalue()

    def test_enqueue_and_list(self):
        event_id = self.invoke("enqueue", "http://localhost:9000", str(self.payload)).strip()
        event = json.loads(self.invoke("list"))[0]
        self.assertEqual(event["id"], event_id)
        self.assertEqual(event["status"], "pending")
        self.assertNotIn("customer", event)
        self.assertNotIn("payload", event)
        self.assertNotIn("url", event)

    def test_empty_queue(self):
        self.assertEqual(json.loads(self.invoke("run")), {"delivered": 0, "pending": 0, "failed": 0})

    def test_invalid_json_returns_error(self):
        self.payload.write_text("broken", encoding="utf-8")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(["--db", str(self.db), "enqueue", "http://localhost:9000", str(self.payload)])
        self.assertEqual(error.exception.code, 1)

    def test_missing_file_returns_error(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(["--db", str(self.db), "enqueue", "http://localhost:9000", str(self.root / "missing.json")])
        self.assertEqual(error.exception.code, 1)

    def test_zero_attempts_returns_usage_error(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(["--db", str(self.db), "run", "--attempts", "0"])
        self.assertEqual(error.exception.code, 2)

    def test_list_filters_failed_events_and_handles_no_matches(self):
        self.invoke("enqueue", "http://localhost:9000", str(self.payload))
        failed_id = self.invoke("enqueue", "http://localhost:9000", str(self.payload)).strip()
        EventQueue(self.db).record(failed_id, "failed", 400, "HTTP 400")
        events = json.loads(self.invoke("list", "--status", "failed"))
        self.assertEqual([event["id"] for event in events], [failed_id])
        self.assertEqual(events[0]["last_error"], "HTTP 400")
        self.assertNotIn("payload", events[0])
        self.assertNotIn("url", events[0])
        self.assertEqual(json.loads(self.invoke("list", "--status", "delivered")), [])
        self.assertEqual(len(json.loads(self.invoke("list"))), 2)

    def test_list_rejects_invalid_status(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(["--db", str(self.db), "list", "--status", "unknown"])
        self.assertEqual(error.exception.code, 2)
