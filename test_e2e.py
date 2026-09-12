#!/usr/bin/env python3
"""End-to-end tests for MERRY CHRISTMAS against a mock Telegram API."""

import io
import json
import os
import sys
import threading
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

# Point the app at the mock server before importing it
os.environ["TELEGRAM_API_BASE"] = "http://127.0.0.1:5058"
os.environ["BOT_TOKEN"] = "123:TEST"
os.environ["CHAT_ID"] = "67890"

import app as app_module  # noqa: E402

PORT = 5057
BASE = f"http://127.0.0.1:{PORT}"

received = {"messages": [], "photos": [], "videos": []}


class MockTG(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _ok(self):
        body = json.dumps({"ok": True, "result": {"message_id": 1}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        ctype = self.headers.get("Content-Type", "")
        path = self.path
        if "multipart/form-data" in ctype:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            boundary = ctype.split("boundary=")[1].encode()
            parts = raw.split(b"--" + boundary)
            fields = {}
            files = {}
            for part in parts:
                if len(part) < 50:
                    continue
                seg = part.split(b"\r\n\r\n", 1)
                if len(seg) != 2:
                    continue
                head, content = seg
                content = content.rsplit(b"\r\n", 1)[0]
                name = None
                filename = None
                for line in head.decode(errors="ignore").split("\r\n"):
                    if 'name="' in line:
                        name = line.split('name="')[1].split('"')[0]
                    if 'filename="' in line:
                        filename = line.split('filename="')[1].split('"')[0]
                if name and filename:
                    files[name] = content
                elif name:
                    fields[name] = content.decode(errors="ignore")
            if "sendPhoto" in path:
                received["photos"].append({"fields": fields, "file": files.get("photo")})
            elif "sendVideo" in path:
                received["videos"].append({"fields": fields, "file": files.get("video")})
            self._ok()
            return
        # urlencoded / json body
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode()
        if "sendMessage" in path:
            from urllib.parse import parse_qs
            data = {k: v[0] for k, v in parse_qs(raw).items()}
            received["messages"].append(data)
        self._ok()


def start_mock():
    srv = HTTPServer(("127.0.0.1", 5058), MockTG)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def get(path):
    return urllib.request.urlopen(BASE + path, timeout=10)


def post(path, payload, ctype="application/json"):
    if ctype == "application/json":
        data = json.dumps(payload).encode()
    else:
        data = payload
    req = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": ctype}
    )
    return urllib.request.urlopen(req, timeout=10)


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # silence the banner print noise on import? banner already printed.
        cls.client = app_module.app.test_client()

    def test_01_page(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        for needle in [
            "MERRY CHRISTMAS",
            "Play Jingle Bells",
            "Share a photo or video?",
            "Yes, I agree",
            "/api/send",
        ]:
            self.assertIn(needle, html)

    def test_02_send_message(self):
        r = self.client.post(
            "/api/send",
            json={
                "ip": "1.2.3.4",
                "city": "Quezon City",
                "region": "Metro Manila",
                "country": "Philippines",
                "isp": "Globe Telecom",
                "timezone": "Asia/Manila",
                "mobile": True,
                "screen": "412x915",
                "browser": "TestAgent/1.0",
            },
        )
        self.assertEqual(r.status_code, 200)
        time.sleep(0.3)
        self.assertTrue(len(received["messages"]) >= 1)
        msg = received["messages"][-1]
        self.assertIn("67890", msg.get("chat_id", ""))
        self.assertIn("MERRY CHRISTMAS - Visitor Info", msg.get("text", ""))

    def test_03_no_consent_image(self):
        r = self.client.post("/upload/image", json={"original": "data:image/png;base64,AAAA"})
        self.assertEqual(r.status_code, 400)

    def test_04_no_consent_video(self):
        r = self.client.post("/upload/video", data={"consent": "false"}, follow_redirects=True)
        self.assertEqual(r.status_code, 400)

    def test_05_upload_image(self):
        # 1x1 red PNG
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d494844520000000100000001080200000090"
            "7753de0000000c4944415408d763f8cfc0f01f0000030101a5f4"
            "ec5d9f0000000049454e44ae426082"
        )
        b64 = "data:image/png;base64," + __import__("base64").b64encode(png).decode()
        r = self.client.post(
            "/upload/image", json={"original": b64, "consent": True}
        )
        self.assertEqual(r.status_code, 200)
        time.sleep(0.3)
        self.assertTrue(len(received["photos"]) >= 1)
        p = received["photos"][-1]
        self.assertEqual(p["fields"].get("chat_id"), "67890")
        self.assertEqual(p["file"], png)

    def test_06_upload_video(self):
        fake = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 40
        r = self.client.post(
            "/upload/video",
            data={"original": (io.BytesIO(fake), "clip.mp4"), "consent": "true"},
            content_type="multipart/form-data",
        )
        self.assertEqual(r.status_code, 200)
        time.sleep(0.3)
        self.assertTrue(len(received["videos"]) >= 1)
        v = received["videos"][-1]
        self.assertEqual(v["fields"].get("chat_id"), "67890")
        self.assertEqual(v["file"], fake)


if __name__ == "__main__":
    start_mock()
    time.sleep(0.3)
    unittest.main(verbosity=2)
