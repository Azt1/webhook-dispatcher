import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from webhook_dispatcher.delivery import send
from webhook_dispatcher.queue import EventQueue
from webhook_dispatcher.worker import run_once


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.received = []
        received = self.received

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                received.append((json.loads(body), self.headers["Idempotency-Key"]))
                code = {"/ok": 204, "/retry": 503, "/bad": 400, "/redirect": 307}[self.path]
                self.send_response(code)
                if code == 307:
                    self.send_header("Location", "/ok")
                self.end_headers()

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def event(self, path):
        return {"id": "event-123", "url": f"http://127.0.0.1:{self.server.server_port}{path}",
                "payload": json.dumps({"message": "Olá"}, ensure_ascii=False)}

    def test_delivers_payload_and_idempotency_key(self):
        result = send(self.event("/ok"))
        self.assertTrue(result.delivered)
        self.assertEqual(self.received, [({"message": "Olá"}, "event-123")])

    def test_reports_server_error(self):
        result = send(self.event("/retry"))
        self.assertFalse(result.delivered)
        self.assertEqual(result.status_code, 503)

    def test_reports_client_error(self):
        self.assertEqual(send(self.event("/bad")).status_code, 400)

    def test_does_not_follow_redirects(self):
        result = send(self.event("/redirect"))
        self.assertEqual(result.status_code, 307)
        self.assertEqual(len(self.received), 1)

    def test_complete_delivery_updates_saved_history(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = EventQueue(Path(directory) / "events.db")
            event_id = queue.add(self.event("/ok")["url"], {"order_id": "PED-1042"})
            self.assertEqual(run_once(queue)["delivered"], 1)
            row = EventQueue(queue.path).list()[0]
            self.assertEqual(row["status"], "delivered")
            self.assertEqual(row["http_status"], 204)
            self.assertEqual(row["attempts"], 1)
            self.assertEqual(self.received[0], ({"order_id": "PED-1042"}, event_id))
