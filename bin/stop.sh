#!/bin/bash
#
# File: stop.sh
# Author: jackietan
# Date: 2023/12/15 10:12:25
# Brief: 


# 获取正在运行的程序的进程 ID（PID）
PID=$(ps aux | grep "streamlit run snowchat.py" | grep -v grep | awk '{print $2}')

# 检查进程是否存在
if [ -n "$PID" ]; then
    # 杀死进程
    kill $PID
    echo "程序已停止，进程 ID: $PID"
else
    echo "程序未在运行"
fi
