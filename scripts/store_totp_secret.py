#!/usr/bin/env python3
"""Store an FNOS TOTP seed in a Git-ignored, owner-only file."""
import base64
import binascii
import getpass
import os
from pathlib import Path
import stat
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    directory = root / "secrets"
    path = directory / "fnos_2fa_secret"

    if directory.is_symlink():
        raise SystemExit("Refusing a symlink secrets directory.")
    directory.mkdir(mode=0o700, exist_ok=True)
    directory_stat = directory.stat()
    if not stat.S_ISDIR(directory_stat.st_mode) or directory_stat.st_uid != os.getuid():
        raise SystemExit("The secrets directory must be owned by the current user.")
    os.chmod(directory, 0o700)
    if path.exists() or path.is_symlink():
        raise SystemExit("TOTP secret file already exists; remove it explicitly before replacing.")
    if not sys.stdin.isatty():
        raise SystemExit("Run this utility in a local interactive terminal.")

    seed = getpass.getpass("FNOS authenticator Base32 secret (hidden): ").strip().upper()
    confirmation = getpass.getpass("Confirm secret (hidden): ").strip().upper()
    if not seed or seed != confirmation:
        raise SystemExit("Secret is empty or does not match; no file written.")
    try:
        base64.b32decode(seed + "=" * (-len(seed) % 8), casefold=True)
    except (binascii.Error, ValueError):
        raise SystemExit("Secret is not valid Base32; no file written.") from None

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(seed + "\n")
            stream.flush()
            os.fchmod(stream.fileno(), 0o600)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    print("TOTP secret stored in secrets/fnos_2fa_secret with mode 0600.")


if __name__ == "__main__":
    main()
