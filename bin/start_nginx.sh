#!/bin/bash
#
# Copyright (c) 2017 Tencent Inc. All Rights Reserved
#
# File: start_nginx.sh
# Author: root@tencent.com
# Date: 2023/12/15 09:12:24
# Brief: 
sudo systemctl start nginx
#查看启动情况,active表示成功
#sudo systemctl status nginx
#查看8888端口占用情况sudo lsof -i :8888
