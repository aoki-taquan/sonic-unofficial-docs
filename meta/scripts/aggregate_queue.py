#!/usr/bin/env python3
"""Aggregate per-page queue files into meta/verification-queue.json.

per-page ファイル (`meta/queue/*.json`) を読み込み、後方互換用ビューとして
`meta/verification-queue.json` を再生成する。Writer / Verifier は per-page
ファイルに対して編集を行い、このスクリプトで集約ビューを更新する想定。

Usage:
    .venv/bin/python3 meta/scripts/aggregate_queue.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
QUEUE_DIR = REPO_ROOT / "meta" / "queue"
AGG_PATH = REPO_ROOT / "meta" / "verification-queue.json"

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def load_entries() -> list[dict]:
    entries: list[dict] = []
    for path in sorted(QUEUE_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"failed to parse {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise SystemExit(f"{path}: top-level must be an object (one entry per file)")
        entries.append(data)
    return entries


def sort_key(entry: dict):
    priority = PRIORITY_ORDER.get(entry.get("priority", "medium"), 1)
    return (priority, entry.get("page", ""))


def main() -> None:
    entries = load_entries()
    entries.sort(key=sort_key)
    out = {
        "_comment": (
            "このファイルは meta/queue/*.json の集約ビューであり、自動生成される。"
            "編集は per-page ファイル (meta/queue/<area>-<slug>.json) に対して行うこと。"
            "再生成は .venv/bin/python3 meta/scripts/aggregate_queue.py で実行する。"
        ),
        "schema_version": 1,
        "entries": entries,
    }
    AGG_PATH.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {AGG_PATH} ({len(entries)} entries)")


if __name__ == "__main__":
    main()
