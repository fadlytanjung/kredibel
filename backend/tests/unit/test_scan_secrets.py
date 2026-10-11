"""Tests for tools/checks/scan_secrets.py."""

import tempfile
from pathlib import Path

from tools.checks.scan_secrets import scan_path_for_secrets


def test_clean_files_pass_secret_scan():
    """Files without secrets pass."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        clean_file = tmp_path / "app.py"
        clean_file.write_text('APP_NAME = "kredibel"\nAPI_VERSION = "v1"\n')

        findings = scan_path_for_secrets(tmp_path)
        assert len(findings) == 0


def test_private_key_detected():
    """Private key patterns fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        secret_file = tmp_path / "key.pem"
        header = "-----" + "BEGIN RSA PRIVATE KEY" + "-----"
        secret_file.write_text(f"{header}\nMIIEowIBAAKCAQEA0\n")

        findings = scan_path_for_secrets(tmp_path)
        assert len(findings) >= 1
        assert "private key" in findings[0].lower()


def test_service_account_json_detected():
    """Google service account JSON content fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        secret_file = tmp_path / "creds.json"
        sa_type = "service_" + "account"
        secret_file.write_text(f'{{"type": "{sa_type}", "private_key_id": "12345"}}\n')

        findings = scan_path_for_secrets(tmp_path)
        assert len(findings) >= 1
