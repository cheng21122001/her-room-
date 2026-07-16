#!/bin/bash
cd "$(dirname "$0")"

PIDS=$(lsof -i :5001 -sTCP:LISTEN -t 2>/dev/null)

if [ -n "$PIDS" ]; then
  kill $PIDS
  echo "已停止《与她的房间》服务。"
else
  echo "没有正在运行的服务。"
fi

sleep 2
