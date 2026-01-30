# FNOS PhotoScan 自动化工具

📖 **项目简介**  
一个用于 FNOS 系统的照片文件夹自动化扫描工具，支持 Docker 容器化部署和定时任务调度，实现全自动化的照片扫描和管理。
用于飞牛相册挂载远程目录时候，无法自动监听新照片的补充。

✨ **核心功能**

- ✅ Docker 容器化部署 - 一键部署，环境隔离
- ✅ Cron 定时任务调度 - 灵活配置执行频率
- ✅ 自动登录认证 - 安全可靠的系统登录
- ✅ 批量文件夹扫描 - 自动扫描所有照片文件夹
- ✅ 任务清理 - 自动清理已完成的任务
- ✅ 实时日志输出 - 完整的执行过程监控

## 🚀 快速开始

### 前置要求
- Docker 或 Podman
- Python 3.9+
- 可访问的 FNOS 系统

### 1. 构建 Docker 镜像


# 克隆项目（如果从远程仓库）
    git clone <repository-url>
    cd fnPhotosAutoScan

# 构建镜像
    docker build -t fnos-photoscan .

### 2. 运行单次任务（测试）

    docker run --rm \
        -e FNOS_HOST="your-server:port" \
        -e FNOS_USERNAME="your-username" \
        -e FNOS_PASSWORD="your-password" \
        god1ong/fn-photo-scan:latest

### 3. 运行定时任务（生产环境）

    docker run -d \
        -e FNOS_HOST="your-server:port" \
        -e FNOS_USERNAME="your-username" \
        -e FNOS_PASSWORD="your-password" \
        -e CRON_SCHEDULE="0 */2 * * *" \
        --name fnos-photo-scan \
        --restart unless-stopped \
        god1ong/fn-photo-scan:latest



  ### 4. 监控任务执行

    # 查看实时日志
    docker logs -f fnos-scan

    # 查看容器状态
    docker ps | grep fnos-scan

    # 停止服务
    docker stop fnos-scan

    # 重启服务
    docker restart fnos-scan

## ⚙️ 配置选项

### 环境变量

| 变量名          | 必填 | 默认值 | 说明                              |
|-----------------|------|--------|-----------------------------------|
| `FNOS_HOST`     | ✓    | -      | FNOS 服务器地址，格式：ip:port 或 hostname:port |
| `FNOS_USERNAME` | ✓    | -      | FNOS 系统登录用户名               |
| `FNOS_PASSWORD` | ✓    | -      | FNOS 系统登录密码                 |
| `CRON_SCHEDULE` |      | -      | Cron 表达式，未设置时执行单次任务  |

### 常用 Cron 表达式示例

| 表达式           | 说明                  |
|------------------|-----------------------|
| `*/5 * * * *`    | 每 5 分钟执行一次     |
| `0 */2 * * *`    | 每 2 小时执行一次     |
| `0 * * * *`      | 每小时的第 0 分钟执行 |
| `30 3 * * *`     | 每天凌晨 3:30 执行    |
| `0 2 * * 0`      | 每周日凌晨 2:00 执行  |
| `0 0 1 * *`      | 每月 1 日的 0:00 执行 |


## 🛠️ 开发指南

### 本地开发环境

    # 1. 创建虚拟环境
    python -m venv .venv
    
    # 2. 激活虚拟环境
    # Linux/Mac:
    source .venv/bin/activate
    # Windows:
    # .venv\Scripts\activate
    
    # 3. 安装依赖
    pip install -r requirements.txt
    
    # 4. 设置环境变量
    
        export FNOS_HOST="your-server:port"
        export FNOS_USERNAME="your-username"
        export FNOS_PASSWORD="your-password"
    
    # 5. 运行脚本
    python fnPhotoScan.py

## 🔧 故障排除

### 常见问题

**容器启动后立即退出**
- 检查环境变量是否正确设置
- 查看 Docker 日志：`docker logs <container-id>`

**Cron 任务未执行**
- 确认容器内时间是否正确：`docker exec <container> date`
- 检查 cron 配置：`docker exec <container> crontab -l`

**连接 FNOS 失败**
- 验证网络连通性：`docker exec <container> ping <fnos-host>`
- 检查 FNOS 服务状态和端口

**认证失败**
- 确认用户名密码正确
- 检查用户权限
    
### 调试模式
    
    # 进入容器交互模式
    docker exec -it fnos-scan /bin/sh
    
    # 查看环境变量
    env | grep FNOS
    
    # 手动测试脚本
    cd /app && python fnPhotoScan.py
    
    # 查看 cron 日志
    tail -f /var/log/cron/fnPhotoScan.log

## 📄 许可证与版权

**版权信息**  
作者: godlong  
邮箱: godlong.cn@gmail.com  
日期: 2026年1月29日

**使用说明**  
本项目仅供学习和参考使用，请遵守相关法律法规和服务条款。



## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目：

    1. Fork 本仓库
    2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
    3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
    4. 推送到分支 (`git push origin feature/AmazingFeature`)
    5. 开启 Pull Request



## 📞 支持与反馈

如有问题或建议，请通过以下方式联系：

- 📧 邮箱：godlong.cn@gmail.com
- 🐛 提交 Issue

**提示**：在生产环境中使用前，请务必充分测试，确保脚本行为符合预期。