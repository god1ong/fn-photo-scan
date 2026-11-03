#!/bin/sh
set -e

if [ -n "${CRON_SCHEDULE}" ]; then
    echo "⏰ 配置 cron 作业: ${CRON_SCHEDULE}"

    # dcron does not pass the container environment to jobs. Keep only the
    # application settings in a root-only runtime file, never in the crontab
    # or startup output where the NAS password could be exposed.
    python - <<'PY'
import os
import shlex

path = "/run/fn-photo-scan.env"
names = ("FNOS_HOST", "FNOS_USERNAME", "FNOS_PASSWORD", "FNOS_2FA_SECRET_FILE")
flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
fd = os.open(path, flags, 0o600)
os.fchmod(fd, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as stream:
    for name in names:
        if name in os.environ:
            stream.write(f"export {name}={shlex.quote(os.environ[name])}\n")
    stream.flush()
PY
    
    # 创建 crontabs 目录
    mkdir -p /var/spool/cron/crontabs
    
    # 构建 cron 作业 - 同时输出到文件和标准输出
    CRON_JOB="${CRON_SCHEDULE} . /run/fn-photo-scan.env && cd /app && /usr/local/bin/python fnPhotoScan.py 2>&1 | tee -a /var/log/fnPhotoScan.log"
    
    # 写入 crontab
    echo "${CRON_JOB}" | crontab -
    
    echo "📋 当前 cron 作业:"
    crontab -l
    
    # 创建日志文件并设置权限
    touch /var/log/fnPhotoScan.log
    chmod 666 /var/log/fnPhotoScan.log
    
    echo "🔄 启动 cron 服务..."
    echo "📝 日志输出到: /var/log/fnPhotoScan.log"
    
    # 启动一个后台进程来 tail 日志文件到标准输出
    tail -f /var/log/fnPhotoScan.log &
    
    # 正确启动 crond：-f 前台运行，-l 8 调试级别（如果支持）
    # 先尝试带 -l 参数，如果不支持就只用 -f
    if crond -f -l 8 >/dev/null 2>&1; then
        exec crond -f -l 8
    else
        exec crond -f
    fi
else
    echo "⚡ 执行单次任务..."
    exec su -p fnos-user -c "cd /app && python fnPhotoScan.py"
fi
