import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Receiver(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/events":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 65536:
                self.send_error(413)
                return
            event = json.loads(self.rfile.read(size))
        except (ValueError, UnicodeDecodeError):
            self.send_error(400)
            return
        print(json.dumps(event, ensure_ascii=False, indent=2), flush=True)
        print("Evento:", self.headers.get("Idempotency-Key"), flush=True)
        self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    print("Recebendo eventos em http://127.0.0.1:9000/events", flush=True)
    with HTTPServer(("127.0.0.1", 9000), Receiver) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Receptor encerrado.")
