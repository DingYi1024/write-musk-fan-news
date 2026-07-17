#!/usr/bin/env python3
"""Validate the publishable repository structure without third-party packages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "write-musk-fan-news"
SKILL_DIR = ROOT / "skills" / SKILL_NAME


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", version)), "VERSION must use semantic versioning")

    source_pdfs = [path.relative_to(ROOT) for path in ROOT.rglob("*.pdf")]
    require(not source_pdfs, f"Do not commit source PDFs: {source_pdfs}")

    manifest_path = ROOT / ".claude-plugin" / "marketplace.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["metadata"]["version"] == version, "Marketplace metadata version differs from VERSION")
    require(len(manifest["plugins"]) == 1, "Expected exactly one plugin")

    plugin = manifest["plugins"][0]
    require(plugin["name"] == SKILL_NAME, "Plugin name differs from skill name")
    require(plugin["version"] == version, "Plugin version differs from VERSION")
    require(plugin["skills"] == [f"./skills/{SKILL_NAME}"], "Plugin skill path is incorrect")

    skill_path = SKILL_DIR / "SKILL.md"
    skill_text = skill_path.read_text(encoding="utf-8")
    require(skill_text.startswith("---\n"), "SKILL.md must start with YAML frontmatter")
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", skill_text, re.DOTALL)
    require(frontmatter_match is not None, "SKILL.md frontmatter is malformed")
    frontmatter = frontmatter_match.group(1)
    require(re.search(rf"^name:\s*{re.escape(SKILL_NAME)}\s*$", frontmatter, re.MULTILINE) is not None,
            "SKILL.md name is incorrect")
    require(re.search(r"^description:\s*\S+", frontmatter, re.MULTILINE) is not None,
            "SKILL.md description is missing")

    required_files = [
        SKILL_DIR / "agents" / "openai.yaml",
        SKILL_DIR / "references" / "style-system.md",
        SKILL_DIR / "references" / "rewrite-protocol.md",
        SKILL_DIR / "references" / "platform-adapters.md",
        SKILL_DIR / "references" / "musk-wisdom-system.md",
    ]
    for path in required_files:
        require(path.is_file(), f"Missing required file: {path.relative_to(ROOT)}")

    print(f"Repository is valid: {SKILL_NAME} v{version}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
