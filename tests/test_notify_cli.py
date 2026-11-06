import json
from datetime import date

from test_diff import ds

from opendata_watch import catalog, cli, notify
from opendata_watch.diff import compare


def test_markdown_lists_changes_and_links():
    md = notify.format_markdown({"入札・調達": compare({}, [ds()])}, date(2026, 11, 6))
    assert "## 入札・調達（1件）" in md
    assert "[調達情報](https://catalog.example.jp/dataset/d1)" in md
    assert "[契約一覧](https://x/r1.csv) (CSV)" in md


def test_markdown_when_nothing_changed():
    md = notify.format_markdown({"a": []}, date(2026, 11, 6))
    assert "変更はありませんでした" in md


def test_chat_is_none_without_changes_and_truncated_when_long():
    assert notify.format_chat({"a": []}) is None
    many = compare({}, [ds(name=f"d{i}") for i in range(15)])
    text = notify.format_chat({"a": many})
    assert text.startswith("オープンデータに 15 件")
    assert "ほか 5 件" in text


class FakeSession:
    def __init__(self):
        self.posts = []

    def post(self, url, data, headers, timeout):
        self.posts.append((url, json.loads(data)))

        class R:
            def raise_for_status(self):
                pass

        return R()


def test_webhooks_only_for_configured_services(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/hook")
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    s = FakeSession()
    assert notify.send_webhooks("hi", s) == ["discord"]
    assert s.posts == [("https://discord.example/hook", {"content": "hi"})]


def test_cli_first_run_is_baseline_then_reports_changes(tmp_path, monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    config = tmp_path / "watches.json"
    config.write_text(json.dumps({"watches": [{"name": "調達", "query": "調達"}]}), "utf-8")
    state = tmp_path / "state.json"
    reports = tmp_path / "reports"
    catalog_now = [ds(name="d1")]
    monkeypatch.setattr(catalog, "search", lambda session, w, api: catalog_now)
    argv = ["run", "--config", str(config), "--state", str(state), "--reports", str(reports)]

    cli.main(argv)
    assert "d1" in json.loads(state.read_text("utf-8"))["調達"]
    assert not reports.exists()  # baseline run reports nothing

    catalog_now = [ds(name="d1"), ds(name="d2", title="入札結果")]
    cli.main(argv)
    report = next(reports.glob("*.md")).read_text("utf-8")
    assert "入札結果" in report and "調達情報" not in report
