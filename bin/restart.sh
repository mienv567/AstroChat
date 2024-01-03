#!/bin/bash
#
# Copyright (c) 2017 Tencent Inc. All Rights Reserved
#
# File: sh/restart.sh
# Author: root@tencent.com
# Date: 2023/12/15 10:12:23
# Brief: 

# 获取正在运行的程序的进程 ID（PID）
PID=$(ps aux | grep "streamlit run snowchat.py" | grep -v grep | awk '{print $2}')

# 检查进程是否存在
if [ -n "$PID" ]; then
    # 杀死进程
    kill $PID
    echo "程序已停止，进程 ID: $PID"
fi

# 启动程序
nohup streamlit run snowchat.py --server.port 8888 > stdout.log 2>&1 &
NEW_PID=$!
echo "程序已启动，新进程 ID: $NEW_PID"
