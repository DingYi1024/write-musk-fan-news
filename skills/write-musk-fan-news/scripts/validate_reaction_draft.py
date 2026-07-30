#!/usr/bin/env python3
"""Validate tagged reaction-story drafts before removing M/E labels."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


TAG_RE = re.compile(r"^(M|E|X)(\d+)\s*[|：:]\s*(.+)$")
TITLE_RE = re.compile(r"^TITLE\s*[|：:]\s*(.+)$", re.IGNORECASE)
ABSOLUTE_CLAIMS_RE = re.compile(r"(一贯|从来|总是|永远)")
KIMI_BANNED = (
    "2.8万亿",
    "100万token",
    "100万 Token",
    "45纳米",
    "100MHz",
    "8700",
    "7月27",
    "完整权重",
)


def parse_draft(path: Path) -> tuple[str, list[dict[str, str]], list[str]]:
    title = ""
    sentences: list[dict[str, str]] = []
    syntax_errors: list[str] = []

    for line_no, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        title_match = TITLE_RE.match(line)
        if title_match:
            if title:
                syntax_errors.append(f"第{line_no}行：标题重复")
            title = title_match.group(1).strip()
            continue
        tag_match = TAG_RE.match(line)
        if not tag_match:
            syntax_errors.append(f"第{line_no}行：必须使用 TITLE|、M数字|、E数字| 或 X数字| 标签")
            continue
        kind, number, text = tag_match.groups()
        sentences.append(
            {"tag": f"{kind}{number}", "kind": kind, "text": text.strip(), "line": str(line_no)}
        )
    return title, sentences, syntax_errors


def validate(
    title: str,
    sentences: list[dict[str, str]],
    syntax_errors: list[str],
    *,
    duration: int,
    case: str,
) -> tuple[list[str], list[str], dict[str, int]]:
    errors = list(syntax_errors)
    warnings: list[str] = []
    counts = {
        "M": sum(item["kind"] == "M" for item in sentences),
        "E": sum(item["kind"] == "E" for item in sentences),
        "X": sum(item["kind"] == "X" for item in sentences),
    }

    if not title:
        errors.append("缺少 TITLE")
    elif "马斯克" not in title:
        errors.append("标题必须以马斯克的动作、判断或人物反差为主，标题中应出现“马斯克”")

    if not sentences:
        errors.append("正文为空")
        return errors, warnings, counts

    if sentences[0]["kind"] != "M" or (len(sentences) > 1 and sentences[1]["kind"] != "M"):
        errors.append("第一、第二句必须都是M句")

    first_text = sentences[0]["text"]
    if not first_text.startswith("你肯定不敢相信，"):
        errors.append("M1必须以“你肯定不敢相信，”开头")
    if not 18 <= len(first_text) <= 45:
        errors.append(f"M1长度应为18—45个字符，当前为{len(first_text)}")

    if counts["E"] > 2:
        errors.append(f"E句最多2句，当前为{counts['E']}句")
    if counts["M"] < counts["E"] * 2:
        errors.append(f"M句至少为E句的两倍，当前M={counts['M']}、E={counts['E']}")

    minimum_m = 8 if duration >= 75 else 5
    if counts["M"] < minimum_m:
        errors.append(f"{duration}秒反应型稿至少需要{minimum_m}个M句，当前为{counts['M']}句")

    for previous, current in zip(sentences, sentences[1:]):
        if previous["kind"] == current["kind"] == "E":
            errors.append(f"不得出现E—E相邻：{previous['tag']}、{current['tag']}")

    closing = sentences[-3:] if len(sentences) >= 3 else sentences
    if any(item["kind"] != "M" for item in closing):
        errors.append("结尾三句必须全部回到马斯克，不能出现E或X句")

    all_text = "\n".join(item["text"] for item in sentences)
    if ABSOLUTE_CLAIMS_RE.search(all_text):
        warnings.append("出现“一贯/从来/总是/永远”，发布前必须确认至少有两项马斯克公开行为支持")

    if case == "kimi":
        for term in KIMI_BANNED:
            if term.lower() in all_text.lower():
                errors.append(f"Kimi反应型稿禁止展开“{term}”")
        e_text = "\n".join(item["text"] for item in sentences if item["kind"] == "E")
        if "48小时" not in e_text:
            errors.append("Kimi案例的E1应只保留“48小时完成芯片设计、优化和验证”的结果事实")

    body_chars = sum(len(item["text"]) for item in sentences)
    if duration >= 75 and not 320 <= body_chars <= 650:
        warnings.append(f"90秒稿建议约320—650字符，当前为{body_chars}字符")

    return errors, warnings, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path, help="UTF-8 tagged draft file")
    parser.add_argument("--duration", type=int, default=90, help="target duration in seconds")
    parser.add_argument("--case", choices=("generic", "kimi"), default="generic")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if not args.draft.is_file():
        print(f"ERROR: file not found: {args.draft}", file=sys.stderr)
        return 2

    title, sentences, syntax_errors = parse_draft(args.draft)
    errors, warnings, counts = validate(
        title, sentences, syntax_errors, duration=args.duration, case=args.case
    )
    result = {
        "ok": not errors,
        "title": title,
        "counts": counts,
        "errors": errors,
        "warnings": warnings,
    }

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("PASS" if result["ok"] else "FAIL")
        print(f"M={counts['M']} E={counts['E']} X={counts['X']}")
        for message in errors:
            print(f"ERROR: {message}")
        for message in warnings:
            print(f"WARN: {message}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
