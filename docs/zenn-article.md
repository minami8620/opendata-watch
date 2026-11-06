---
title: "自治体オープンデータの「更新だけ」を毎朝通知する仕組みを、サーバーなし・無料で作った"
emoji: "🔔"
type: "tech"
topics: ["python", "githubactions", "opendata", "ckan", "自動化"]
published: false
---

## はじめに

入札・調達情報、保育所の空き状況、避難所一覧——自治体のオープンデータは少しずつ更新されますが、
「いつ何が変わったか」を知るには、結局サイトを開いて目で確認するしかありません。

そこで、東京都オープンデータカタログを毎朝チェックし、**前回から新しく追加・差し替えられたデータだけ**を
Slack / Discord と Markdown レポートに届ける小さなツールを作りました。
サーバーは使わず、GitHub Actions だけで無料で動きます。

リポジトリ：https://github.com/minami8620/opendata-watch

## 全体像

```
watches.json ──▶ CKAN package_search（監視対象ごとに1日1回）
                         │
state/state.json ◀── 前回のスナップショットと比較
                         │
                         ├─▶ reports/YYYY-MM-DD.md
                         ├─▶ GitHub Actions のジョブサマリー
                         └─▶ Slack / Discord
```

東京都のカタログは CKAN というオープンソースのデータカタログで動いており、
`/api/3/action/package_search` で検索結果を JSON で取得できます。

## 工夫した点

### 1. 「何をもって変更とするか」を決める

CKAN のデータセットには `metadata_modified`（最終更新日時）がありますが、
これは説明文の誤字修正のような、データそのものが変わらない更新でも変わります。
これをそのまま通知すると、受け取る側にはノイズになります。

そこで、**ファイル（リソース）の追加・差し替えがあったときだけ**を変更として扱いました。

```python
def compare(previous, datasets):
    changes = []
    for d in datasets:
        before = previous.get(d.id)
        if before is None:
            changes.append(Change("new", d, new_resources=list(d.resources)))
            continue
        if before["modified"] == d.modified:
            continue
        old = before.get("resources", {})
        added = [r for r in d.resources if r.id not in old]
        replaced = [r for r in d.resources if r.id in old and old[r.id] != r.last_modified]
        if added or replaced:
            changes.append(Change("updated", d, added, replaced))
    return changes
```

### 2. 初回は「ベースライン」だけ記録する

最初の実行で既存の50件を全部「新規」と通知すると、最初の通知で使う気がなくなります。
初回は状態を保存するだけにして、2回目以降の差分から通知するようにしました。

### 3. 検索範囲から外れたデータも状態に残す

検索は「更新日時の新しい順に50件」なので、古いデータは結果から外れます。
状態ファイルを毎回上書きすると、そのデータが再び結果に戻ってきたときに「新規」と誤判定してしまいます。
そこで、状態は上書きではなくマージにしています。

### 4. 日本語検索は `title:` を付けたほうが正確だった

最初は `入札 OR 調達 OR 契約` のような検索式にしていましたが、
「地域防災計画 火山編」のような関係ないデータがヒットしました。
`title:入札 OR title:調達` のようにタイトルに絞ると、意図どおりの結果になりました
（`契約` は「テレビ契約数」がヒットするので外しました）。

### 5. 相手のサーバーに配慮する

公開APIとはいえ、自治体のサーバーです。監視対象ごとに1日1回・1リクエストだけにし、
User-Agent にツール名とリポジトリURLを入れ、リトライも1回に抑えています。

## GitHub Actions で毎朝動かす

```yaml
on:
  schedule:
    - cron: "0 23 * * *" # 08:00 JST
```

実行後に `state/` と `reports/` に差分があればコミットします。
状態をリポジトリに置くので、データベースもサーバーも不要です。
通知先の Webhook URL はリポジトリの Secrets に登録します。

## テスト

ネットワークには接続せず、CKAN の応答を模したデータで次の挙動を確認しています。

- 新規データは全ファイルつきで通知される
- 説明文だけの更新は通知されない
- ファイルの追加・差し替えは通知される
- 初回はベースラインのみで、2回目に追加されたデータだけがレポートに載る

## おわりに

「毎日サイトを見に行く」作業は、差分の定義さえ決めれば小さなコードで置き換えられます。
同じ仕組みは、新着物件、ECサイトの在庫、官公庁のお知らせなど、いろいろな「見に行く作業」に応用できます。
