#!/usr/bin/env python3
"""Fail CI when committed files contain likely production secrets.

The scanner intentionally favors high-confidence findings. It catches common
provider keys and suspicious secret assignments while allowing explicit
placeholder/test values that appear in docs and fixtures.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SKIP_DIRS = {
    ".asterion",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".svelte-kit",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "playwright-report",
    "target",
    "test-results",
}

SKIP_SUFFIXES = {
    ".db",
    ".gif",
    ".icns",
    ".ico",
    ".jpg",
    ".jpeg",
    ".lockb",
    ".pdf",
    ".png",
    ".pyc",
    ".sqlite",
    ".webp",
}

PLACEHOLDER_MARKERS = {
    "***",
    "...",
    "<",
    ">",
    "changeme",
    "change-me",
    "change_me",
    "dummy",
    "example",
    "fake",
    "fixture",
    "mock",
    "placeholder",
    "sample",
    "test",
    "unused",
    "your_",
    "xxxx",
    "\u2022\u2022",
}

HIGH_CONFIDENCE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("stripe-live-key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}\b")),
)

KEYWORD_ASSIGNMENT = re.compile(
    r"""
    \b
    (?P<name>
      api[_-]?key |
      auth[_-]?token |
      client[_-]?secret |
      db[_-]?password |
      passphrase |
      password |
      private[_-]?key |
      secret(?:[_-]?key)? |
      token
    )
    \b
    \s*[:=]\s*
    (?P<quote>["']?)
    (?P<value>[A-Za-z0-9_./+=:@-]{16,})
    (?P=quote)
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int
    column: int
    preview: str


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {char: value.count(char) for char in set(value)}
    return -sum((count / len(value)) * math.log2(count / len(value)) for count in counts.values())


def looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def mask(value: str) -> str:
    compact = value.strip()
    if len(compact) <= 10:
        return "*" * len(compact)
    return f"{compact[:4]}...{compact[-4:]}"


def should_scan(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    if any(part in SKIP_DIRS for part in relative.parts):
        return False
    if path.suffix.lower() in SKIP_SUFFIXES:
        return False
    return path.is_file()


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if should_scan(path, root):
            yield path


def scan_text(text: str, display_path: str) -> list[Finding]:
    findings: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in HIGH_CONFIDENCE_PATTERNS:
            for match in pattern.finditer(line):
                value = match.group(0)
                if looks_like_placeholder(value):
                    continue
                findings.append(
                    Finding(rule, display_path, line_no, match.start() + 1, mask(value))
                )

        for match in KEYWORD_ASSIGNMENT.finditer(line):
            value = match.group("value")
            if not match.group("quote") and "." in value:
                continue
            if looks_like_placeholder(value):
                continue
            if len(value) < 24 and shannon_entropy(value) < 3.8:
                continue
            findings.append(
                Finding(
                    f"keyword-assignment:{match.group('name').lower()}",
                    display_path,
                    line_no,
                    match.start("value") + 1,
                    mask(value),
                )
            )
    return findings


def scan_path(root: Path) -> list[Finding]:
    root = root.resolve()
    findings: list[Finding] = []
    for path in iter_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
        except OSError:
            continue
        display_path = str(path.relative_to(root)).replace("\\", "/")
        findings.extend(scan_text(text, display_path))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository files for likely secrets.")
    parser.add_argument("path", nargs="?", default=".", help="Repository or subdirectory to scan.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    findings = scan_path(Path(args.path))
    if args.json:
        print(json.dumps([asdict(finding) for finding in findings], indent=2))
    elif findings:
        print("Potential secrets found:")
        for finding in findings:
            print(
                f"- {finding.path}:{finding.line}:{finding.column} "
                f"{finding.rule} {finding.preview}"
            )
    else:
        print("No likely production secrets found.")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
