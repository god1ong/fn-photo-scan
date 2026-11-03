"""Helpers for the FNOS login-time TOTP challenge."""
import base64
import binascii
import hashlib
import hmac
import os
import re
import stat
import struct
import time
import uuid


class TwoFactorError(ValueError):
    """Raised when a two-factor challenge cannot be completed safely."""


def is_twofa_challenge(response):
    """Return the kind of FNOS login challenge, if any."""
    if not isinstance(response, dict) or response.get("result") != "succ":
        return None
    if response.get("token") or response.get("secret"):
        return None
    if not response.get("accessToken"):
        return None
    if (response.get("isBindTwofaSecret") is True
            and response.get("isTrustedDevice") is not True):
        return "code"
    if (response.get("isTwofaEnforced") is True
            and response.get("isBindTwofaSecret") is False):
        return "setup"
    return None


def build_twofa_payload(code, pending, session_id):
    """Build the encrypted request body fields expected by fnOS loginVerify."""
    if not isinstance(code, str) or re.fullmatch(r"\d{6}", code) is None:
        raise TwoFactorError("FNOS verification code must contain exactly 6 digits.")
    if not isinstance(pending, dict) or not pending.get("accessToken"):
        raise TwoFactorError("There is no pending FNOS two-factor challenge.")
    return {
        "code": code,
        "isTrustedDevice": False,
        "accessToken": pending["accessToken"],
        "stay": int(bool(pending.get("stay", False))),
        "deviceName": pending.get("deviceName", "FNOS PhotoScan"),
        "deviceType": pending.get("deviceType", "Browser"),
        "did": uuid.uuid4().hex,
        "si": session_id,
    }


def generate_totp(secret, at=None):
    """Generate a six-digit RFC 6238 TOTP using HMAC-SHA1 and a 30s step."""
    if not isinstance(secret, str):
        raise TwoFactorError("The TOTP secret is invalid.")
    normalized = re.sub(r"\s+", "", secret).upper()
    if not normalized:
        raise TwoFactorError("The TOTP secret is empty.")
    try:
        key = base64.b32decode(normalized + "=" * (-len(normalized) % 8), casefold=True)
    except (binascii.Error, ValueError):
        raise TwoFactorError("The TOTP secret is not valid Base32.") from None
    timestamp = time.time() if at is None else at
    if not isinstance(timestamp, (int, float)) or timestamp < 0:
        raise TwoFactorError("The TOTP timestamp is invalid.")
    counter = int(timestamp) // 30
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{binary % 1_000_000:06d}"


def read_totp_secret(path):
    """Read a TOTP seed from a regular, non-symlink file without logging it."""
    flags = (os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
             | getattr(os, "O_NONBLOCK", 0))
    try:
        fd = os.open(path, flags)
    except OSError:
        raise TwoFactorError("Could not open FNOS_2FA_SECRET_FILE.") from None
    with os.fdopen(fd, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise TwoFactorError("FNOS_2FA_SECRET_FILE must be a regular file.")
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise TwoFactorError("FNOS_2FA_SECRET_FILE is too large.")
    try:
        secret = raw.decode("ascii").strip()
    except UnicodeDecodeError:
        raise TwoFactorError("FNOS_2FA_SECRET_FILE must contain an ASCII Base32 secret.") from None
    # Validate before returning so a bad secret fails before any scan request.
    generate_totp(secret)
    return secret


def get_twofa_code(secret_file=None):
    """Use a protected TOTP seed file, or prompt for one OTP on a TTY."""
    if secret_file:
        return generate_totp(read_totp_secret(secret_file))
    import getpass
    import sys

    if not sys.stdin.isatty():
        raise TwoFactorError(
            "FNOS requires a second factor. Set FNOS_2FA_SECRET_FILE for unattended runs, "
            "or run this command with an interactive terminal to enter an OTP."
        )
    code = getpass.getpass("Enter the 6-digit FNOS verification code: ")
    if re.fullmatch(r"\d{6}", code) is None:
        raise TwoFactorError("FNOS verification code must contain exactly 6 digits.")
    return code
