#!/bin/bash
cd "$(dirname "$0")"

if ! lsof -i :5001 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "正在启动《与她的房间》……"
  source .venv/bin/activate
  nohup python app.py > /tmp/her_room.log 2>&1 &
  sleep 1.5
else
  echo "服务已在运行。"
fi

open http://127.0.0.1:5001/
echo "已在浏览器打开，这个窗口可以直接关闭。"
sleep 2
