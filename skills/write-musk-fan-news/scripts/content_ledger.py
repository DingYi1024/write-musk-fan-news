#!/usr/bin/env python3
"""Check and maintain the publishing ledger used for 30-day topic deduplication."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path


FIELDS = (
    "publish_date",
    "platform",
    "pool",
    "topic",
    "subject",
    "event",
    "conclusion",
    "source_url",
    "status",
    "notes",
)
DEFAULT_LEDGER = Path(__file__).resolve().parent.parent / "assets" / "publishing-ledger.csv"


def normalize(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.casefold())


def similarity(left: str, right: str) -> float:
    a, b = normalize(left), normalize(right)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError(f"台账字段不匹配，应为：{','.join(FIELDS)}")
        return list(reader)


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def find_duplicates(
    rows: list[dict[str, str]],
    *,
    as_of: date,
    days: int,
    topic: str,
    subject: str,
    event: str,
    conclusion: str,
    threshold: float,
) -> list[dict[str, object]]:
    since = as_of - timedelta(days=days)
    matches: list[dict[str, object]] = []
    for row in rows:
        try:
            published = parse_date(row["publish_date"])
        except (ValueError, KeyError):
            continue
        if published < since or published > as_of:
            continue
        scores = {
            "topic": similarity(topic, row.get("topic", "")),
            "subject": similarity(subject, row.get("subject", "")),
            "event": similarity(event, row.get("event", "")),
            "conclusion": similarity(conclusion, row.get("conclusion", "")),
        }
        matched_fields = [
            field for field in ("topic", "event", "conclusion") if scores[field] >= threshold
        ]
        if len(matched_fields) >= 2:
            matches.append({"row": row, "scores": scores, "matched_fields": matched_fields})
    return matches


def ensure_ledger(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=FIELDS).writeheader()


def command_check(args: argparse.Namespace) -> int:
    rows = read_rows(args.ledger)
    matches = find_duplicates(
        rows,
        as_of=parse_date(args.date),
        days=args.days,
        topic=args.topic,
        subject=args.subject,
        event=args.event,
        conclusion=args.conclusion,
        threshold=args.threshold,
    )
    result = {"duplicate": bool(matches), "window_days": args.days, "matches": matches}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if matches else 0


def command_add(args: argparse.Namespace) -> int:
    ensure_ledger(args.ledger)
    row = {field: getattr(args, field) for field in FIELDS}
    parse_date(row["publish_date"])
    with args.ledger.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=FIELDS).writerow(row)
    print(json.dumps({"added": True, "row": row}, ensure_ascii=False, indent=2))
    return 0


def command_list(args: argparse.Namespace) -> int:
    rows = read_rows(args.ledger)
    print(json.dumps(rows[-args.limit :], ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check")
    check.add_argument("--date", default=date.today().isoformat())
    check.add_argument("--days", type=int, default=30)
    check.add_argument("--threshold", type=float, default=0.82)
    check.add_argument("--topic", default="")
    check.add_argument("--subject", default="")
    check.add_argument("--event", default="")
    check.add_argument("--conclusion", default="")
    check.set_defaults(func=command_check)

    add = subparsers.add_parser("add")
    for field in FIELDS:
        required = field in {"publish_date", "topic", "subject", "event", "conclusion"}
        add.add_argument(f"--{field.replace('_', '-')}", dest=field, default="", required=required)
    add.set_defaults(func=command_add)

    listing = subparsers.add_parser("list")
    listing.add_argument("--limit", type=int, default=20)
    listing.set_defaults(func=command_list)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
