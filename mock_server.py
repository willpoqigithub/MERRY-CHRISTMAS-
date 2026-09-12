#!/usr/bin/env python3
"""Standalone mock Telegram API (para sa local testing lang).
Gumagaya sa api.telegram.org: sinusunod ang request at nagla-log."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote_plus

REQUESTS = []

class MockTG(BaseHTTPRequestHandler):
    def do_POST(self):
        method = self.path.rsplit("/", 1)[-1]
        ctype = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        entry = {"method": method, "chat_id": None, "text": None,
                 "caption": None, "file_bytes": 0}
        if b"multipart/form-data" in ctype.encode():
            boundary = ctype.split("boundary=")[1].split(";")[0]
            for p in raw.split(b"--" + boundary.encode()):
                if b'name="' not in p:
                    continue
                header, _, content = p.partition(b"\r\n\r\n")
                name = header.split(b'name="')[1].split(b'"')[0].decode()
                value = content.rsplit(b"\r\n", 1)[0]
                if name == "chat_id":
                    entry["chat_id"] = value.decode()
                elif name == "caption":
                    entry["caption"] = value.decode()
                elif name == "text":
                    entry["text"] = value.decode()
                else:
                    entry["file_bytes"] = len(value)
                    entry["file_kind"] = name
        else:
            for pair in raw.decode().split("&"):
                k, _, v = pair.partition("=")
                v = unquote_plus(v)
                if k in ("chat_id", "text", "caption"):
                    entry[k] = v

        REQUESTS.append(entry)
        print(f"[MOCK TG] {method}: chat_id={entry['chat_id']} "
              f"file={entry.get('file_kind')}({entry['file_bytes']}B)", flush=True)

        body = json.dumps({"ok": True, "result": {"message_id": len(REQUESTS)}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    srv = HTTPServer(("127.0.0.1", 5056), MockTG)
    print("Mock Telegram API on http://127.0.0.1:5056", flush=True)
    srv.serve_forever()
