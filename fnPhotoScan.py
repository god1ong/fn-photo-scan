#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FNOS 文件夹扫描工具
版本: 1.3 (Docker + Cron版)
功能: 自动登录、扫描所有照片文件夹、清理已完成任务
"""
import logging
import os
import asyncio
import time
import random
import hashlib
import requests
import json
import datetime
from sdk import FnOsClient

# ===== 配置常量（从环境变量读取）=====
VERSION = "1.3"

# 从 FNOS_HOST 环境变量构建 URL
FNOS_HOST = os.getenv("FNOS_HOST")
if not FNOS_HOST:
    raise ValueError("❌ 必须设置 FNOS_HOST 环境变量 (格式: ip:port)")

BASE_URL = f"http://{FNOS_HOST}"
WEBSOCKET_URL = f"ws://{FNOS_HOST}/websocket?type=main"

# 账号凭证
USERNAME = os.getenv("FNOS_USERNAME")
PASSWORD = os.getenv("FNOS_PASSWORD")

if not USERNAME or not PASSWORD:
    raise ValueError("❌ 必须设置 FNOS_USERNAME 和 FNOS_PASSWORD 环境变量")

# API 路径
FOLDER_LIST_PATH = "/p/api/v1/photo/folder/list"
FOLDER_SCAN_PATH = "/p/api/v1/photo/folder/scan"
CLEAR_DONE_TASKS_PATH = "/p/api/v1/task-panel/clear-done"

# 签名配置（从 JS 分析得出）
SIGN_SECRET = "NDzZTVxnRKP8Z0jXg1VAMonaG8akvh"
SIGN_SALT = "EAECCF25-80A6-4666-A7C2-A76904A74AB6"


def md5(s: str) -> str:
    """计算字符串的 MD5 哈希值"""
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def gen_authx(path: str, payload: str = "") -> str:
    """
    生成 authx 签名参数
    
    Args:
        path: 请求路径（带 /p 前缀）
        payload: 请求负载（GET 为空字符串，POST 为 JSON 字符串）
    
    Returns:
        authx 签名字符串
    """
    nonce = str(random.randint(100000, 999999)).zfill(6)
    timestamp = str(int(time.time() * 1000))
    payload_hash = md5(payload)

    raw = "_".join([
        SIGN_SECRET,
        path,
        nonce,
        timestamp,
        payload_hash,
        SIGN_SALT
    ])
    
    sign = md5(raw)
    return f"nonce={nonce}&timestamp={timestamp}&sign={sign}"


def make_request(method: str, path: str, token: str, data: dict = None) -> dict:
    """
    统一的 HTTP 请求函数
    
    Args:
        method: HTTP 方法 ('GET' 或 'POST')
        path: API 路径
        token: 访问令牌
        data: POST 请求的数据（可选）
    
    Returns:
        API 响应数据字典
    """
    # 准备 payload 和 body
    if method.upper() == 'POST' and data:
        body = json.dumps(data)
        payload_for_sign = body
    else:
        body = None
        payload_for_sign = ""
    
    # 生成签名
    authx = gen_authx(path, payload_for_sign)
    
    # 设置 headers
    headers = {
        "Accept": "application/json, text/plain, */*" if method.upper() == 'POST' else "application/json",
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE_URL}/p/setting?key=folderManager",
        "accesstoken": token,
        "authx": authx,
        "cache-control": "no-cache",
        "pragma": "no-cache"
    }
    
    if method.upper() == 'POST':
        headers["content-type"] = "application/json"
    
    # 设置 cookies
    cookies = {
        "language": "zh-CN",
        "fnos-token": token,
    }
    
    # 发送请求
    url = BASE_URL + path
    if method.upper() == 'POST':
        response = requests.post(url, headers=headers, cookies=cookies, data=body, verify=False)
    else:
        response = requests.get(url, headers=headers, cookies=cookies, verify=False)
    
    # 处理响应
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"HTTP {response.status_code}: {response.text}")


async def clear_done_tasks(token: str) -> bool:
    """
    清理已完成的任务
    
    Args:
        token: 访问令牌
    
    Returns:
        是否成功
    """
    print("🧹 正在清理已完成的任务...")
    try:
        response = make_request('POST', CLEAR_DONE_TASKS_PATH, token)
        if response.get("code") == 0:
            print("✅ 已完成任务清理成功")
            return True
        else:
            print(f"⚠️  清理任务失败: {response.get('msg', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"⚠️  清理任务时发生异常: {e}")
        return False


async def main():
    """主函数 - 执行单次扫描任务"""
    print(f"🚀 FNOS 文件夹扫描工具 v{VERSION} (Docker + Cron版)")
    print(f"👨‍💻 作者: godlong (godlong.cn@gmail.com)")
    print(f"📅 发布: 2026/01/29")
    print("=" * 60)
    print(f"📡 目标地址: {BASE_URL}")
    print(f"👤 用户名: {USERNAME}")
    print(f"🕐 时间: {datetime.datetime.now().strftime('%m-%d %H:%M')}")
    print("=" * 60)
    
    # 1️⃣ 登录获取 token
    print("🔑 正在登录...")
    client = FnOsClient(ping_interval=60, logger=logging.getLogger("null"))
    await client.connect(WEBSOCKET_URL)
    login_res = await client.login(USERNAME, PASSWORD)
    token = login_res["token"]
    print(f"✅ 登录成功")
    
    try:
        # 2️⃣ 获取文件夹列表
        print("\n📁 正在获取文件夹列表...")
        folder_response = make_request('GET', FOLDER_LIST_PATH, token)
        
        if folder_response.get("code") != 0:
            raise Exception(f"获取文件夹列表失败: {folder_response.get('msg', 'Unknown error')}")
        
        folders = folder_response["data"]["list"]
        folder_ids = [folder["folderId"] for folder in folders]
        print(f"✅ 获取到 {len(folders)} 个文件夹: {folder_ids}")
        
        # 3️⃣ 扫描所有文件夹
        print("\n🔄 开始扫描所有文件夹...")
        success_count = 0
        
        for folder_id in folder_ids:
            print(f"   📂 扫描文件夹 {folder_id}...")
            scan_response = make_request('POST', FOLDER_SCAN_PATH, token, {"folder_id": folder_id})
            
            if scan_response.get("code") == 0:
                print(f"   ✅ 文件夹 {folder_id} 扫描成功")
                success_count += 1
            else:
                print(f"   ❌ 文件夹 {folder_id} 扫描失败: {scan_response.get('msg', 'Unknown error')}")
            
            # 添加小延迟避免请求过快
            time.sleep(0.1)
        
        print(f"\n📊 扫描完成！成功: {success_count}/{len(folder_ids)}")
        
        # 4️⃣ 清理已完成的任务
        print("\n" + "=" * 60)
        await clear_done_tasks(token)
        
        print("=" * 60)
        print("🎉 本次任务执行完毕！")
        
    except Exception as e:
        print(f"\n❌ 执行过程中出错: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())