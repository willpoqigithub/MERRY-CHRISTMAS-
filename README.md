# MERRY CHRISTMAS

A Christmas-themed single-page site with Telegram notifications.
Built with Python (Flask) on the server and plain HTML/CSS/JS on the front end.

## Features

- Animated Christmas tree with blinking colored lights and garlands
- Falling snow and twinkling stars background
- Jingle Bells song synthesized in the browser (Web Audio API, royalty-free, public domain melody)
- Rotating "Merry Christmas" wishes on screen
- Visitor info notification: when a visitor opens the page, basic device
  information is sent to the site owner's Telegram bot (disclosed in the page)
- Consent-gated sharing: a visitor may choose to send a photo or video to the
  owner; nothing is shared unless the visitor clicks "Yes, I agree" and picks a
  file. The server rejects any upload without the consent flag.

## Files

| File | Purpose |
|------|---------|
| app.py | Flask server: routes, Telegram helpers, visitor-info formatter |
| templates/index.html | Christmas page: tree, lights, snow, song, wishes, uploads |
| mock_server.py | Standalone mock of api.telegram.org for local testing |
| test_e2e.py | End-to-end tests against the mock Telegram API |
| start_test.sh | Launches the app on port 5055 with the mock API |
| requirements.txt | Python dependencies |

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Get your bot token from @BotFather on Telegram and your chat ID from
   @userinfobot.

3. Run:

   ```bash
   python3 app.py
   ```

   You will be asked for the bot token and chat ID (or set the BOT_TOKEN and
   CHAT_ID environment variables). The app listens on port 5000 by default;
   override with PORT=5055. Set NO_TUNNEL=1 to skip the optional cloudflared
   tunnel.

## Routes

| Route | Method | Purpose |
|-------|--------|---------|
| / | GET | Christmas page |
| /api/send | POST | Visitor info forwarded to Telegram |
| /upload/image | POST | Photo upload (requires consent flag) |
| /upload/video | POST | Video upload (requires consent flag) |

## Testing

With the mock Telegram API:

```bash
bash start_test.sh        # app on :5055 + mock api.telegram.org on :5056
python3 test_e2e.py       # end-to-end suite
```

## Notes

- Telegram bot API file limit: 50 MB per upload.
- ipapi.co free tier is rate-limited; geo lookup may occasionally fail, in
  which case only basic device info is sent.
- Battery information is only available in Chrome/Chromium on Android.
- Browsers block audio autoplay, so the song starts when the visitor clicks
  the play button.
