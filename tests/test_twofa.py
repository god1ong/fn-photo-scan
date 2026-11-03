import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import importlib.util

module_path = Path(__file__).resolve().parents[1] / "sdk" / "twofa.py"
spec = importlib.util.spec_from_file_location("fnos_twofa", module_path)
twofa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(twofa)

TwoFactorError = twofa.TwoFactorError
build_twofa_payload = twofa.build_twofa_payload
generate_totp = twofa.generate_totp
get_twofa_code = twofa.get_twofa_code
is_twofa_challenge = twofa.is_twofa_challenge
read_totp_secret = twofa.read_totp_secret

RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


class TwoFactorTests(unittest.TestCase):
    def test_totp_matches_rfc_6238_sha1_vectors(self):
        vectors = {
            59: "287082",
            1111111109: "081804",
            1111111111: "050471",
            1234567890: "005924",
            2000000000: "279037",
            20000000000: "353130",
        }
        for timestamp, expected in vectors.items():
            with self.subTest(timestamp=timestamp):
                self.assertEqual(generate_totp(RFC_SECRET, timestamp), expected)

    def test_rejects_malformed_totp_secret(self):
        with self.assertRaises(TwoFactorError):
            generate_totp("not-valid!")

    def test_identifies_bound_and_unbound_challenges(self):
        bound = {
            "result": "succ",
            "isBindTwofaSecret": True,
            "isTrustedDevice": False,
            "accessToken": "challenge-token",
        }
        unbound = {
            "result": "succ",
            "isTwofaEnforced": True,
            "isBindTwofaSecret": False,
            "accessToken": "challenge-token",
        }
        self.assertEqual(is_twofa_challenge(bound), "code")
        self.assertEqual(is_twofa_challenge(unbound), "setup")

    def test_does_not_treat_trusted_or_completed_login_as_challenge(self):
        trusted = {
            "result": "succ",
            "isBindTwofaSecret": True,
            "isTrustedDevice": True,
            "accessToken": "challenge-token",
        }
        complete = {"result": "succ", "token": "session", "secret": "encrypted"}
        self.assertIsNone(is_twofa_challenge(trusted))
        self.assertIsNone(is_twofa_challenge(complete))

    def test_builds_login_verify_payload_without_trusting_device(self):
        pending = {
            "accessToken": "challenge-token",
            "stay": True,
            "deviceName": "PhotoScan",
            "deviceType": "Browser",
        }
        payload = build_twofa_payload("123456", pending, "session-id")
        self.assertEqual(payload["code"], "123456")
        self.assertIs(payload["isTrustedDevice"], False)
        self.assertEqual(payload["accessToken"], "challenge-token")
        self.assertEqual(payload["stay"], 1)
        self.assertEqual(payload["deviceName"], "PhotoScan")
        self.assertEqual(payload["deviceType"], "Browser")
        self.assertEqual(payload["si"], "session-id")
        self.assertTrue(payload["did"])

    def test_rejects_invalid_code_and_missing_challenge(self):
        with self.assertRaises(TwoFactorError):
            build_twofa_payload("12345", {"accessToken": "challenge-token"}, "si")
        with self.assertRaises(TwoFactorError):
            build_twofa_payload("123456", None, "si")

    def test_reads_totp_secret_from_regular_file(self):
        with tempfile.TemporaryDirectory() as directory:
            secret_file = Path(directory) / "totp"
            secret_file.write_text(RFC_SECRET + "\n", encoding="ascii")
            self.assertEqual(read_totp_secret(str(secret_file)), RFC_SECRET)

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires O_NOFOLLOW")
    def test_rejects_symlink_secret_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            link = Path(directory) / "secret"
            target.write_text(RFC_SECRET, encoding="ascii")
            link.symlink_to(target)
            with self.assertRaises(TwoFactorError):
                read_totp_secret(str(link))

    def test_noninteractive_challenge_requires_secret_file(self):
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaisesRegex(TwoFactorError, "FNOS_2FA_SECRET_FILE"):
                get_twofa_code()

    def test_interactive_challenge_prompts_without_echo_helper(self):
        with patch("sys.stdin.isatty", return_value=True), patch(
            "getpass.getpass", return_value="123456"
        ) as prompt:
            self.assertEqual(get_twofa_code(), "123456")
        prompt.assert_called_once()


if __name__ == "__main__":
    unittest.main()
