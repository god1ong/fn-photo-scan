import base64
import json
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Util.Padding import pad, unpad
import json
import random
import hmac, hashlib


# 生成 32 字节的随机字符串
def generate_random_string(t):
    chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return ''.join(random.choice(chars) for _ in range(t))


# RSA 加密
def rsa_encrypt(public_key_str, plaintext):
    key = RSA.import_key(public_key_str)

    # 注释和不注释都能过，就很奇怪
    # MAX_ENCRYPT_BLOCK = 117
    # ciphertext = b''
    # for i in range(0, len(plaintext), MAX_ENCRYPT_BLOCK):
    #     chunk = plaintext[i:i + MAX_ENCRYPT_BLOCK]
    #     cipher = PKCS1_v1_5.new(key)
    #     encrypted_chunk = cipher.encrypt(chunk)
    #     ciphertext += encrypted_chunk

    cipher = PKCS1_v1_5.new(key)
    ciphertext = cipher.encrypt(plaintext.encode())
    ciphertext = base64.b64encode(ciphertext).decode()
    return ciphertext


# AES 加密
def aes_encrypt(data, key, iv):
    cipher = AES.new(key.encode(), AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    return base64.b64encode(ciphertext).decode('utf-8')


# AES 解密
def aes_decrypt(ciphertext, key, iv):
    cipher = AES.new(key.encode(), AES.MODE_CBC, iv)
    ciphertext = ciphertext.encode()
    decrypted = unpad(cipher.decrypt(base64.b64decode(ciphertext)), AES.block_size)
    return base64.b64encode(decrypted).decode('utf-8')


def login_encrypt(data, public_key_str, key, iv):
    # RSA 加密
    rsa_encrypted = rsa_encrypt(public_key_str, key)

    # AES 加密
    # data = json.dumps(t, separators=(',', ':'))
    aes_encrypted = aes_encrypt(data, key, iv)

    # 返回加密数据
    return {
        'req': 'encrypted',
        'iv': base64.b64encode(iv).decode('utf-8'),  # 正常
        'rsa': rsa_encrypted,
        'aes': aes_encrypted  # 正常
    }


# kw 是 base64 编码的密钥字符串
def get_signature(data: str, key: str) -> str:
    key_bytes = base64.b64decode(key)
    hmac_obj = hmac.new(key_bytes, data.encode('utf-8'), hashlib.sha256)
    signature = base64.b64encode(hmac_obj.digest()).decode('utf-8')
    return signature


def get_signature_req(data, key: str):
    # 不需要签名的req
    sign_req = [
        'encrypted',
        'util.getSI',
        'util.crypto.getRSAPub',
    ]
    req = data['req']
    json_str = json.dumps(data, separators=(',', ':'))  # 确保没有空格，等同于 JS 的 JSON.stringify
    if req not in sign_req and key:
        return get_signature(json_str, key) + json_str
    return json_str


if __name__ == '__main__':
    # 例子：
    public_key_str = '''-----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzWICqab2gcSuRzhguXqH
    KOzS0irokLS9pvT488UIv1581RcfuqUKV/CpvBvbzrLEM1kQtbSAXjOSAYrmOW+V
    N9Nwb8XhJSZHuPdAmqDzm9hu+06QDkIE9TLkNnIZcQKW6gG9Pbo5vID7BWYjzJVU
    7rP+lX5lUrCbpgsXxs5UjEb+4E5St1RaKFCOMiapy40wXgMh4rVyfbfkT752RSsj
    vnNWyYEHuFDJZ7Z2JHJZBhZnIRXOt0k4bTzpqxBbq/2llZ2Z60pm+Ad/h+xpLjvU
    lITh9ddocFpYddYO7MIGQ6dDO4KBObPkqvOJuZ+9sKw1PE6pm4C/ArR1lVHh4L3j
    8wIDAQAB
    -----END PUBLIC KEY-----'''

    t = {
        "reqid": "67f858df00000000000000000003",
        "user": "admin",
        "password": "password",
        "deviceType": "Browser",
        "deviceName": "Windows-Google Chrome",
        "stay": False,
        "req": "user.login",
        "si": "72057615512764607"
    }
    # t = '{"reqid":"67f852e900000000000000000003","user":"1","password":"1","deviceType":"Browser","deviceName":"Windows-Google Chrome","stay":false,"req":"user.login","si":"72057615512764624"}'
    t = json.dumps(t, separators=(',', ':'))
    result = get_signature_req(t, public_key_str)
    print(json.dumps(result, separators=(',', ':')))

    # 67f83da400000000000000000006
    # 67f8586300000000000000000001

    # aes正常，能解密浏览器解密的，能解密自己的
    # text = '7Lbabt9m8G7t/kW/gfJ+yynFQjABKxRGPADIdGibdzu0+q1maTERQHap+A0K3DUPA9++DVpdGH7BaERDyWYXm4k3lmTqCiCZnnlzN2m0QOI7sEZgNn4DfEcw3MPrWKygZvJGwlN/3XlLGaK15zNkZYLQZnPjUBBkbjun4UhwBvGFZ5QYgtv65Dkgcis/GT4f66nUhcAA4Yb4eHgI6WulTeOVbEKseQXx+D7m3pwwa4Y6/zPZpqqZQV2Go5D4xTzH'
    # key = '394b646e3439656a58304a663647477057446c6a614a794f38366e6d7453474f' # hex
    # iv = '7d5613e01ae1f48fcae06ab5bcf9fae9'
    # key = bytes.fromhex(key)
    # iv = bytes.fromhex(iv)
    #
    # print(aes_decrypt(text, key, iv))
