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
    require("你肯定不敢相信" in skill_text,
            "SKILL.md must define the signature opening phrase")

    required_files = [
        SKILL_DIR / "agents" / "openai.yaml",
        SKILL_DIR / "references" / "style-system.md",
        SKILL_DIR / "references" / "source-narration-system.md",
        SKILL_DIR / "references" / "reaction-story-system.md",
        SKILL_DIR / "references" / "musk-public-behavior-anchors.md",
        SKILL_DIR / "references" / "book-of-elon-sourcebook.md",
        SKILL_DIR / "references" / "evergreen-content-engine.md",
        SKILL_DIR / "references" / "musk-life-relationships-sourcebook.md",
        SKILL_DIR / "references" / "rewrite-protocol.md",
        SKILL_DIR / "references" / "platform-adapters.md",
        SKILL_DIR / "references" / "musk-wisdom-system.md",
    ]
    for path in required_files:
        require(path.is_file(), f"Missing required file: {path.relative_to(ROOT)}")

    style_text = (SKILL_DIR / "references" / "style-system.md").read_text(encoding="utf-8")
    require("## 品牌声纹" in style_text and "你肯定不敢相信" in style_text,
            "Style system must define the signature hook system")
    require("## 马斯克中心度" in style_text and "70/30叙事预算" in style_text,
            "Style system must keep Musk at the narrative center")
    require("合格的12句骨架" in style_text and "仍判定失败并重写" in style_text,
            "Style system must include a concrete reaction-story regression pattern")
    require("不得连续超过两句" in skill_text and "## 主角锁定" in skill_text,
            "SKILL.md must prevent third-party facts from taking over the narrative")
    require("M—E—M回环" in skill_text and "E类产品事实最多两句" in skill_text,
            "SKILL.md must define the reaction-story center audit")
    require("不要直接自由起稿" in skill_text and "判定句子类型时使用删除测试" in skill_text,
            "SKILL.md must define the fixed reaction-story scaffold")

    narration = (SKILL_DIR / "references" / "source-narration-system.md").read_text(encoding="utf-8")
    for heading in ("## 核心原则", "## 四级来源路由", "## 前台口播规则", "## 原创与合规边界"):
        require(heading in narration, f"Source narration system is missing section: {heading}")
    require("单一媒体独家" in narration and "后台来源卡" in narration,
            "Source narration system must protect attribution and internal sourcing")

    behavior_anchors = (SKILL_DIR / "references" / "musk-public-behavior-anchors.md").read_text(encoding="utf-8")
    require(len(re.findall(r"^### A\d{2}\b", behavior_anchors, re.MULTILINE)) >= 5,
            "Public behavior anchors must contain at least 5 evidence cards")
    require("## 发布前检查" in behavior_anchors and "不可升级" in behavior_anchors,
            "Public behavior anchors must define evidence limits")

    reaction_system = (SKILL_DIR / "references" / "reaction-story-system.md").read_text(encoding="utf-8")
    for heading in ("## 触发条件", "## 唯一允许的句位", "## 成稿闸门", "## Kimi回归闸门"):
        require(heading in reaction_system, f"Reaction story system is missing section: {heading}")
    require("2.8万亿" in reaction_system and "成稿禁止出现" in reaction_system,
            "Reaction story system must protect the Kimi regression case")

    sourcebook = (SKILL_DIR / "references" / "book-of-elon-sourcebook.md").read_text(encoding="utf-8")
    require(len(re.findall(r"^### S\d{2}\b", sourcebook, re.MULTILINE)) >= 18,
            "Sourcebook must contain at least 18 story anchors")
    require(len(re.findall(r"^\| M\d{2}\b", sourcebook, re.MULTILINE)) >= 20,
            "Sourcebook must contain at least 20 methods")
    require(len(re.findall(r"^\| Q\d{2}\b", sourcebook, re.MULTILINE)) >= 13,
            "Sourcebook must contain at least 13 short quotations")
    for heading in ("## 来源等级", "## 创业时间线", "## 马斯克书单选题"):
        require(heading in sourcebook, f"Sourcebook is missing section: {heading}")

    evergreen = (SKILL_DIR / "references" / "musk-life-relationships-sourcebook.md").read_text(encoding="utf-8")
    require(len(re.findall(r"^### E\d{2}\b", evergreen, re.MULTILINE)) >= 30,
            "Evergreen sourcebook must contain at least 30 fact cards")
    for heading in ("## 来源等级", "## 快速检索路由", "## 公共来源入口", "## 发布前记录模板"):
        require(heading in evergreen, f"Evergreen sourcebook is missing section: {heading}")

    engine = (SKILL_DIR / "references" / "evergreen-content-engine.md").read_text(encoding="utf-8")
    for heading in ("## 八个常青栏目", "## 自动选题流程", "## 隐私与敏感内容边界", "## 时效分级"):
        require(heading in engine, f"Evergreen engine is missing section: {heading}")

    print(f"Repository is valid: {SKILL_NAME} v{version}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
