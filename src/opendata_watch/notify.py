"""Turn changes into a Markdown report and, optionally, a Slack / Discord message."""

from __future__ import annotations

import json
import os
from datetime import date

import requests

from .diff import Change

MAX_ITEMS_IN_CHAT = 10


def format_markdown(watch_changes: dict[str, list[Change]], today: date) -> str:
    lines = [f"# オープンデータ更新レポート {today.isoformat()}", ""]
    total = sum(len(c) for c in watch_changes.values())
    if total == 0:
        lines.append("前回から変更はありませんでした。")
        return "\n".join(lines) + "\n"
    for name, changes in watch_changes.items():
        if not changes:
            continue
        lines += [f"## {name}（{len(changes)}件）", ""]
        for c in changes:
            label = "🆕 新規" if c.kind == "new" else "🔄 更新"
            d = c.dataset
            lines.append(f"- {label} [{d.title}]({d.page_url}) — {d.organization}")
            files = c.new_resources + c.updated_resources
            for r in files[:5]:
                fmt = f" ({r.format})" if r.format else ""
                lines.append(f"  - [{r.name or 'ファイル'}]({r.url}){fmt}")
            if len(files) > 5:
                lines.append(f"  - ほか {len(files) - 5} ファイル")
        lines.append("")
    return "\n".join(lines)


def format_chat(watch_changes: dict[str, list[Change]]) -> str | None:
    items = [(n, c) for n, cs in watch_changes.items() for c in cs]
    if not items:
        return None
    lines = [f"オープンデータに {len(items)} 件の新着・更新があります"]
    for name, c in items[:MAX_ITEMS_IN_CHAT]:
        label = "新規" if c.kind == "new" else "更新"
        lines.append(f"・[{name}] {label}: {c.dataset.title} {c.dataset.page_url}")
    if len(items) > MAX_ITEMS_IN_CHAT:
        lines.append(f"…ほか {len(items) - MAX_ITEMS_IN_CHAT} 件（レポートを参照）")
    return "\n".join(lines)


def send_webhooks(text: str, session: requests.Session | None = None) -> list[str]:
    """Post ``text`` to every configured webhook; return the names of the services used."""
    session = session or requests.Session()
    sent = []
    targets = {
        "slack": (os.environ.get("SLACK_WEBHOOK_URL"), {"text": text}),
        "discord": (os.environ.get("DISCORD_WEBHOOK_URL"), {"content": text[:1900]}),
    }
    for name, (url, payload) in targets.items():
        if not url:
            continue
        response = session.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        sent.append(name)
    return sent
