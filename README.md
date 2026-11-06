# opendata-watch

東京都オープンデータカタログ（CKAN）を毎日チェックし、**前回から新しく追加・差し替えられたデータだけ**を
Markdownレポートと Slack / Discord に通知するツールです。

> Watches the Tokyo Open Data catalog once a day and notifies only datasets whose files were
> added or replaced since the last run. State lives in a JSON file committed by GitHub Actions,
> so it runs for free with no server.

## なぜ作ったか

入札・調達情報、保育所の空き状況、避難所一覧などは自治体のサイトで少しずつ更新されます。
「毎朝サイトを開いて目で確認する」作業を、差分だけが届く仕組みに置き換えるためのツールです。

## 仕組み

```
watches.json ──▶ CKAN package_search（監視対象ごとに1日1回だけリクエスト）
                         │
state/state.json ◀── 前回のスナップショットと比較（diff.py）
                         │
                         ├─▶ reports/YYYY-MM-DD.md（変更がある日だけ作成）
                         ├─▶ GitHub Actions のジョブサマリー
                         └─▶ Slack / Discord（Webhook を設定した場合のみ）
```

- **ファイルの追加・差し替えだけを通知**：説明文の修正など、データが変わらないメタデータ更新は通知しません。
- **初回はベースラインのみ記録**：最初の実行で既存データを大量に「新規」として通知しません。
- **検索範囲から外れたデータも状態に残す**：再び検索結果に出てきたときに「新規」と誤判定しません。
- **相手サーバーへの配慮**：監視対象ごとに1日1回・1リクエスト、タイムアウトとリトライは1回だけ。

## 使い方

```bash
pip install -e .
opendata-watch run              # watches.json の内容でチェック
opendata-watch run --dry-run    # 状態を保存せず、通知も送らずに確認だけ
```

監視対象は `watches.json` で設定します（`query` は CKAN の検索式、`organization` で組織を絞り込み可能）。

```json
{ "watches": [ { "name": "入札・調達", "query": "入札 OR 調達 OR 契約" } ] }
```

通知先は環境変数で指定します（どちらも任意）。

| 変数 | 内容 |
|---|---|
| `SLACK_WEBHOOK_URL` | Slack の Incoming Webhook URL |
| `DISCORD_WEBHOOK_URL` | Discord の Webhook URL |

## GitHub Actions での自動実行

`.github/workflows/watch.yml` が毎日 08:00（JST）に実行し、`state/` と `reports/` をコミットします。
Webhook を使う場合はリポジトリの Secrets に上記の変数を登録してください。

## 開発

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
```

テストはネットワークに接続せず、CKAN の応答を模したデータで差分判定・レポート生成・CLI の流れを検証します。

## ライセンス

MIT
