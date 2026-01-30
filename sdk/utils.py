import time
import random
import os
from .exceptions import BadRequestError


def _get_reqid():
    index = 1

    def func(backId='0000000000000000'):
        nonlocal index
        t = format(int(time.time()), 'x').zfill(8)
        e = format(index, 'x').zfill(4)
        index += 1
        return f"{t}{backId}{e}"

    return func


get_reqid = _get_reqid()


# 生成随机字符串
def generate_random_string(t):
    chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return ''.join(random.choice(chars) for _ in range(t))


def check_response(response: dict):
    """检查响应，如果包含错误代码则抛出异常"""
    if "errno" in response:
        error_code = response["errno"]
        raise BadRequestError(error_code)


def get_mtime(path) -> int:
    # 也可以用Path(file_path).stat().st_mtime
    mod_time = int(os.path.getmtime(path))
    return mod_time


def list_files(path: str, recursive: bool = False):
    for root, dirs, files in os.walk(path):
        if recursive is not True and path != root:
            break
        for file in files:
            file_path = os.path.join(root, file)
            mtime = get_mtime(file_path)
            yield file, file_path, mtime