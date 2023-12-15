# AstroChat
create -n chatglm python=3.10
conda activate chatglm
pip install -r requirements.txt

# About Nginx
sudo yum install nginx
启动nginx，sudo systemctl start nginx
查看启动状态，sudo systemctl status nginx，active表示启动成功
修改代理，vim /etc/nginx/nginx.conf
查看8888端口占用情况，无返回表示未占用，sudo lsof -i :8888

## 关于用nginx 代理本机的 streamlit 程序
如果您想使用 Nginx 代理本机上运行的 Streamlit 程序，您可以使用 Nginx 的 stream 模块来实现。以下是一个示例配置：

1、打开 Nginx 配置文件 `/etc/nginx/nginx.conf`，找到 `http` 部分，并添加以下内容：
```
stream {
    server {
        listen 80;
        proxy_pass your_streamlit_server;
    }
}
```

将 your_streamlit_server 替换为您本机上运行 Streamlit 程序的地址和端口。例如，如果 Streamlit 程序在本机的端口 8501 上运行，您可以将 your_streamlit_server 设置为 127.0.0.1:8501。

2、检查 Nginx 配置是否正确：
> nginx -t -c /etc/nginx/nginx.conf

如果没有错误提示，则表示配置正确。

3. 重新加载 Nginx 配置：
> sudo systemctl reload nginx

> sudo service nginx reload

现在，Nginx 将会代理来自端口 80 的流量到您本机上运行的 Streamlit 程序。您可以通过访问服务器的 IP 地址或域名来访问 Streamlit 程序。请确保您的 Streamlit 程序已经正确配置并运行，并且防火墙允许流量通过所使用的端口。

