#!/bin/bash
# Launch MERRY CHRISTMAS on port 5055 for manual testing.
# Uses the supervisor-managed mock Telegram API on port 5056
# (log: /var/log/supervisor/5056_python3.out.log).
# Usage: bash start_test.sh

cd "$(dirname "$0")"

# stop anything already on our app port
fuser -k 5055/tcp 2>/dev/null
sleep 1

# start the app pointing at the mock API
BOT_TOKEN="123:TEST" CHAT_ID="67890" \
TELEGRAM_API_BASE="http://127.0.0.1:5056" \
NO_TUNNEL=1 PORT=5055 \
nohup python3 app.py > app.log 2>&1 &

sleep 2
echo "--- app.log ---"
cat app.log
echo "--- page check ---"
curl -s http://127.0.0.1:5055/ | grep -o "MERRY CHRISTMAS\|Share a photo or video?\|Yes, I agree\|Play Jingle Bells" | sort -u
echo "--- mock api check ---"
curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:5056/bot123:TEST/sendMessage -d "chat_id=67890&text=ping" || echo " (mock not responding)"
echo ""
