from .encryption import aes_decrypt
from watchdog.events import FileSystemEventHandler
from .exceptions import BadRequestError


async def HandlerDefault(client, data):
    if "errno" in data:
        error_code = data["errno"]
        raise BadRequestError(error_code, data)
    # 测试抛出错误， 程序会不会停止 如果except Exception就不会，不except Exception就会停止


async def HandlerGetRSAPub(client, data):
    client.pub = data.get('pub', None)
    client.si = data.get('si', None)


async def HandlerLogin(client, data):
    # 以下是登录返回
    client.backId = data.get('backId', None)
    client.token = data.get('token', None)
    client.secret = data.get('secret', None)
    client.uid = data.get('uid', None)
    client.admin = data.get('admin', None)
    client.sign_key = aes_decrypt(client.secret, client.key, client.iv)


async def HandlerUserInfo(client, data):
    # 以下是用户详细回调函数
    pass


async def HandlerGetSI(client, data):
    client.si = data.get('si', None)


async def HandlerAuthToken(client, data):
    pass


async def HandlerFileList(client, data):
    print(data)


class AsyncFileEventHandler(FileSystemEventHandler):
    def __init__(self, queue, loop):
        self.queue = queue
        self.loop = loop

    def on_modified(self, event):
        if not event.is_directory:
            self.loop.call_soon_threadsafe(
                self.queue.put_nowait, ('modified', event.src_path)
            )

    def on_created(self, event):
        if not event.is_directory:
            self.loop.call_soon_threadsafe(
                self.queue.put_nowait, ('created', event.src_path)
            )

    def on_deleted(self, event):
        if not event.is_directory:
            self.loop.call_soon_threadsafe(
                self.queue.put_nowait, ('deleted', event.src_path)
            )
