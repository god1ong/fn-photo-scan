# 使用官方 Python 3.9 Alpine 镜像
FROM python:3.9-alpine

# 安装 tini
RUN apk add --no-cache ca-certificates dcron tini && update-ca-certificates

# 安装 cron 和其他系统依赖
RUN apk add --no-cache \
    ca-certificates \
    curl \
    && update-ca-certificates

# 安装 cron（Alpine 使用 dcron）
RUN apk add --no-cache dcron

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用文件
COPY fnPhotoScan.py .
COPY sdk/ ./sdk/

# 设置脚本为可执行
RUN chmod +x fnPhotoScan.py

# 创建日志目录
RUN mkdir -p /var/log

# 创建非 root 用户
RUN adduser -D -s /bin/sh fnos-user

# 创建启动脚本
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 切换到非 root 用户
#USER fnos-user

# 使用 tini 作为入口
ENTRYPOINT ["/sbin/tini", "--", "/app/entrypoint.sh"]