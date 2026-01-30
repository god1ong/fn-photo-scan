import asyncio
import websockets
import json
import os
import logging
import signal
from typing import Optional, List

from .exceptions import WebSocketConnectionError
from .handlers import *
from .utils import *
from .encryption import login_encrypt, get_signature_req


class BaseClient:
    def __init__(self, url, ping_interval=10, log_level=logging.DEBUG):
        self.url = url
        self.websocket = None
        self.handlers = {}
        self.pending_requests = {}
        self.req_mapping = {}
        self.ping_interval = ping_interval

        self._listen_task = None
        self._ping_task = None

        # 下面数据自动初始化
        self.sign_key = None
        self.key = generate_random_string(32)
        self.iv = os.urandom(16)

        # 网站数据, 不用赋值，自动赋值
        self.si = None
        self.pub = None
        # 以下登录返回
        self.backId = '0000000000000000'
        self.token = None
        self.secret = None
        self.uid = None
        self.admin = None

        # 设置日志
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # 确保日志被正确传播
        self.logger.propagate = True

    @property
    async def connected(self):
        """检查连接是否活跃"""
        if self.websocket is None or self.websocket.closed:
            return False
        try:
            # 快速发送 Ping 测试
            await asyncio.wait_for(self.websocket.ping(), timeout=2)
            return True
        except (websockets.ConnectionClosed, asyncio.TimeoutError):
            return False

    async def connect(self):
        # 添加默认响应处理， 为了方便维护，其他的不在sdk中
        self.add_handler('util.crypto.getRSAPub', HandlerGetRSAPub)
        self.add_handler('user.login', HandlerLogin)
        try:
            self.websocket = await websockets.connect(self.url)
            # 创建监听任务
            self._listen_task = asyncio.create_task(self._listen())
            # 创建心跳任务
            self._ping_task = asyncio.create_task(self._ping_loop())

            # 初始化 获取RSAPub等
            await self._init()
            # await asyncio.gather(*[self._listen_task, self._ping_task])
        except websockets.WebSocketException as e:
            raise WebSocketConnectionError(f"Failed to connect: {str(e)}")

    async def _listen(self):
        while True:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)

                self.logger.debug(f"Received: {message}")
                if 'reqid' in data:
                    reqid = data['reqid']
                    # 返回响应
                    if reqid in self.pending_requests:
                        handler = self.pending_requests.pop(reqid)
                        handler(data)
                    # 检查错误放在这里，放在前面request一直卡
                    check_response(data)
                    # 处理响应
                    if reqid in self.req_mapping:
                        req_type = self.req_mapping.pop(reqid)
                        handler = self.handlers[req_type]
                        await handler(self, data)
                else:
                    pass
                    # 处理没有reqid的消息
                    # self.logger.info(f"Received message without reqid: {data}")
            except asyncio.CancelledError:
                break
            except websockets.ConnectionClosed:
                self.logger.debug(f"Websocket connection closed")
                break
            except Exception as e:
                self.logger.exception(e)
        self.logger.debug(f"_listen end...")

    async def _ping_loop(self):
        while True:
            try:
                await asyncio.sleep(self.ping_interval)
                await self.send_ping()
            except asyncio.CancelledError:
                break
            except websockets.ConnectionClosedError:
                await self.connect()
                # if not await self.connected:  self.logger.error(f"Error in ping loop: {str(e)}")
                break
            except Exception as e:
                self.logger.exception(e)
        self.logger.debug(f"_ping_loop end...")

    async def _init(self):
        await self.request(req='util.crypto.getRSAPub')

    async def send_ping(self):
        try:
            await self.websocket.send(json.dumps({"req": "ping"}))
            self.logger.debug("Sent ping to server")
        except Exception as e:
            self.logger.error(f"Failed to send ping: {str(e)}")
            raise

    async def send_request(self, req, **kwargs):
        reqid = get_reqid(self.backId)
        data = {'req': req, 'reqid': reqid, **kwargs}
        if req == 'user.login':
            # 加密
            data = json.dumps(data, separators=(',', ':'))
            data = login_encrypt(data, self.pub, self.key, self.iv)

        # 签名
        message = get_signature_req(data, self.sign_key)

        await self.websocket.send(message)
        self.req_mapping[reqid] = req
        self.logger.debug(f"Sent: {req} {message}")
        return reqid

    def add_handler(self, req, handler):
        self.handlers[req] = handler

    async def request(self, req, **kwargs):
        reqid = await self.send_request(req, **kwargs)
        future = asyncio.Future()
        self.pending_requests[reqid] = lambda data: future.set_result(data)
        return await future

    async def close(self, timeout: float = 5.0):
        """关闭连接并取消所有任务"""
        tasks = []
        if self._ping_task:
            self._ping_task.cancel()
            tasks.append(self._ping_task)
        if self._listen_task:
            self._listen_task.cancel()
            tasks.append(self._listen_task)
        self.logger.info("Connection closed.")

    def run_polling(
        self,
        *,
        stop_signals: Optional[List[int]] = None,
        close_timeout: float = 5.0,
    ):
        """
        同步方法：启动事件循环并运行 WebSocket 监听，直到收到停止信号。
        用法：
            client = BaseClient(url)
            client.run_polling()  # 阻塞直到 Ctrl+C
        """
        if stop_signals is None:
            stop_signals = [signal.SIGINT, signal.SIGTERM]  # 默认监听 Ctrl+C 和 kill

        # 定义异步主逻辑
        async def _async_main():
            await self.connect()
            stop_event = asyncio.Event()
            # 注册信号处理器
            loop = asyncio.get_running_loop()
            for sig in stop_signals:
                loop.add_signal_handler(sig, stop_event.set)

            self.logger.info("Client started. Press Ctrl+C to stop...")
            await stop_event.wait()  # 阻塞直到收到信号
            await self.close(timeout=close_timeout)

        # 启动事件循环
        try:
            asyncio.run(_async_main())
        except KeyboardInterrupt:
            self.logger.info("User interrupted, shutting down...")
        finally:
            self.logger.info("Client stopped.")
