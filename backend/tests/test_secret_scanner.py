from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCANNER_PATH = ROOT / "scripts" / "scan_secrets.py"
spec = importlib.util.spec_from_file_location("scan_secrets", SCANNER_PATH)
assert spec and spec.loader
scan_secrets = importlib.util.module_from_spec(spec)
sys.modules["scan_secrets"] = scan_secrets
spec.loader.exec_module(scan_secrets)


def test_scanner_flags_high_confidence_provider_key() -> None:
    findings = scan_secrets.scan_text(
        'OPENAI_API_KEY="sk-proj-' + "A" * 48 + '"',
        "sample.env",
    )
    assert findings
    assert findings[0].rule == "openai-key"


def test_scanner_ignores_explicit_placeholder_secret() -> None:
    findings = scan_secrets.scan_text(
        'SEARXNG_SECRET_KEY="asterion_searxng_secret_key_change_me_in_production"',
        "scripts/searxng_settings.yml",
    )
    assert findings == []


def test_scanner_flags_entropy_keyword_assignment() -> None:
    findings = scan_secrets.scan_text(
        "client_secret = " + '"qX7vL9pR2sT5uW8yZ1aB4cD6eF9gH2jK"',
        "config.py",
    )
    assert findings
    assert findings[0].rule == "keyword-assignment:client_secret"


def test_scanner_ignores_code_expressions() -> None:
    findings = scan_secrets.scan_text(
        "private_key = ed25519.Ed25519PrivateKey.generate()",
        "tests/test_security.py",
    )
    assert findings == []


def test_repository_has_no_likely_production_secrets() -> None:
    findings = scan_secrets.scan_path(ROOT)
    assert findings == []
