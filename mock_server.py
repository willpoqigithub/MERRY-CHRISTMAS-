#!/usr/bin/env python3
"""Standalone mock of api.telegram.org for local testing.

Logs every request it receives to stdout, always replies {"ok": true}.
Run on port 5056:  python3 mock_server.py
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def _ok(self):
        body = json.dumps({"ok": True, "result": {"message_id": 1}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        print(f"\n>>> {self.path}")
        print(f"    content-type: {self.headers.get('Content-Type')}")
        print(f"    bytes: {len(raw)}")
        if b"multipart" in self.headers.get("Content-Type", "").encode():
            print("    (binary file upload)")
        else:
            print(f"    body: {raw.decode(errors='replace')[:400]}")
        self._ok()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("[*] Mock Telegram API on http://127.0.0.1:5056")
    HTTPServer(("127.0.0.1", 5056), Handler).serve_forever()
