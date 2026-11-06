"""Command line entry point: ``opendata-watch run``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from . import catalog, diff, notify


def load_watches(path: Path) -> list[catalog.Watch]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [catalog.Watch(**w) for w in raw["watches"]]


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    watches = load_watches(args.config)
    state = load_state(args.state)
    session = catalog.make_session()
    results: dict[str, list[diff.Change]] = {}
    for w in watches:
        datasets = catalog.search(session, w, api=args.api)
        previous = state.get(w.name)
        if previous is None:
            # First run for this watch: record a baseline instead of flooding with "new" items.
            results[w.name] = []
            print(f"[{w.name}] 初回のためベースラインを記録しました（{len(datasets)}件）")
        else:
            results[w.name] = diff.compare(previous, datasets)
            print(f"[{w.name}] 変更 {len(results[w.name])} 件")
        state[w.name] = diff.merge(previous or {}, datasets)

    today = date.today()
    report = notify.format_markdown(results, today)
    if any(results.values()):
        args.reports.mkdir(parents=True, exist_ok=True)
        (args.reports / f"{today.isoformat()}.md").write_text(report, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(report)

    chat = notify.format_chat(results)
    if chat and not args.dry_run:
        sent = notify.send_webhooks(chat, session)
        if sent:
            print("通知を送信しました: " + ", ".join(sent))
    if not args.dry_run:
        save_state(args.state, state)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opendata-watch")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run", help="check every watch once and report changes")
    p.add_argument("--config", type=Path, default=Path("watches.json"))
    p.add_argument("--state", type=Path, default=Path("state/state.json"))
    p.add_argument("--reports", type=Path, default=Path("reports"))
    p.add_argument("--api", default=catalog.DEFAULT_API)
    p.add_argument("--dry-run", action="store_true", help="do not save state or send webhooks")
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
