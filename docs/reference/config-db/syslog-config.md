---
title: SYSLOG_CONFIG テーブル
description: "SYSLOG_CONFIG テーブル — ホスト全体の rsyslog グローバル設定を CONFIG_DB に保持するシングルトンテーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-syslog.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - SYSLOG_CONFIG
    - SYSLOG_CONFIG_FEATURE
    - SYSLOG_SERVER
  cli:
    - config syslog
  yang:
    - sonic-syslog
---

# SYSLOG_CONFIG テーブル

## 概要

ホスト全体の rsyslog グローバル設定を [CONFIG_DB](../../reference/glossary.md#term-config_db) に保持するシングルトンテーブル[^1]。`hostcfgd` (`sonic-host-services` 内 `syslog` ハンドラ) が `/etc/rsyslog.conf` および各 docker の rsyslog テンプレに反映する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>SYSLOG_CONFIG")]
  DM["hostcfgd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
SYSLOG_CONFIG|GLOBAL
```

固定キー `GLOBAL` のみのシングルトン container (`SYSLOG_CONFIG.GLOBAL`)。

## フィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `rate_limit_interval` | uint32 (0..2147483647 秒) | なし | rsyslog rate-limit インターバル (`syslog-rate-limit-interval` typedef) |
| `rate_limit_burst` | uint32 (0..2147483647 件) | なし | rate-limit バースト件数 (`syslog-rate-limit-burst` typedef) |
| `format` | enum `welf`/`standard` | `standard` | ログ書式 (`log-format` typedef) |
| `welf_firewall_name` | string | なし | WELF 形式時のファイアウォール名 (`format != 'standard'` の must 制約あり) |
| `severity` | enum `none`/`debug`/`info`/`notice`/`warn`/`error`/`crit` | `notice` | ローカル最低 severity (`rsyslog-severity` typedef) |

## 制約

- `welf_firewall_name` は `must "(../format != 'standard')"` で WELF 形式時にのみ意味を持つ
- container 名 `SYSLOG_CONFIG`、内部 container 名 `GLOBAL` ([YANG](../../reference/glossary.md#term-yang) コメントには `SYSLOG_CONFIG_LIST` と書かれているが、実体は container)[^1]

## 購読者

- `hostcfgd` (`sonic-host-services`): [CONFIG_DB](../../reference/glossary.md#term-config_db) → rsyslog テンプレ展開 → systemd reload
- 各 docker 内の `rsyslogd`: ホスト側 rsyslog にフォワード後、グローバル設定で集約

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): [`SYSLOG_CONFIG_FEATURE`](syslog-config-feature.md), [`SYSLOG_SERVER`](syslog-server.md)
- 関連 CLI: `config syslog rate-limit-host` / `config syslog level`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-syslog`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-syslog`](../yang/sonic-syslog.md)
- CLI: [`config syslog`](../cli/config-syslog.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `src/sonic-yang-models/yang-models/sonic-syslog.yang` (container `SYSLOG_CONFIG` / `GLOBAL`、typedef `log-format`/`rsyslog-severity`). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-syslog.yang>

## 関連ページ
- [CONFIG_DB: SYSLOG_CONFIG_FEATURE](syslog-config-feature.md)
- [CONFIG_DB: SYSLOG_SERVER](syslog-server.md)

<!-- value-behavior -->
## 値依存挙動マトリクス

### `format` (log-format): `welf` / `standard` (default)

### `severity` (rsyslog-severity): `none` / `debug` / `info` / `notice` (default) / `warn` / `error` / `crit`

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `format` | `standard` | 標準 rsyslog フォーマットで書き込み。`welf_firewall_name` は無視 |
| `format` | `welf` | WELF フォーマット出力。`welf_firewall_name` の設定が必須（YANG must 制約） |
| `welf_firewall_name` | 設定あり + `format=standard` | YANG must 制約違反で書き込み拒否 |
| `rate_limit_interval` | `0` | rate-limit 無効化 |
| `rate_limit_burst` | `0` | バースト上限 0 = 全ログドロップ |
| `severity` | `none` | フィルタなし（全 severity を出力） |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-host-services/scripts/hostcfgd@c5bbbe8b07b96f078fa4b761316627404b01bd04 L1715-1743 -->

- **rsyslog 再起動失敗時は設定不反映**: `systemctl restart rsyslog-config` が失敗すると `"RSyslogCfg: Failed to restart rsyslog service"` を LOG_ERR してキャッシュ更新せずに return する。CONFIG_DB の値は書き込まれているが rsyslog には反映されない（次回 [hostcfgd](../../reference/glossary.md#term-hostcfgd) 再起動またはテーブル変更時に再試行される）。
- **変更なしはノーオペレーション**: `SYSLOG_CONFIG` と `SYSLOG_SERVER` をまとめてキャッシュと比較し、変更がなければ `systemctl restart` をスキップする。
- **YANG must 制約**: `welf_firewall_name` は `format != 'standard'` の must 制約を持ち、`format = standard` のまま書き込もうとすると YANG バリデーション層で拒否される（[hostcfgd](../../reference/glossary.md#term-hostcfgd) レベルの追加チェックはなし）。

<!-- /cdb-exceptions -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `SYSLOG_CONFIG|GLOBAL`。
- `format`: `standard`、`welf_facility`: 任意、`rate_limit_interval`/`rate_limit_burst` でドロップ閾値。

### よくある誤設定

- rate_limit_burst が小さすぎて障害発生時に重要 syslog が捨てられる。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'SYSLOG_CONFIG|GLOBAL'
show syslog
```
<!-- /ops-hint -->

<!-- ordering -->
## 書込み順依存 (Phase B)

### SYSLOG_CONFIG と SYSLOG_SERVER のペア書込み

`rsyslog_handler()` は `SYSLOG_CONFIG` と `SYSLOG_SERVER` の**両テーブルを毎回まとめて読み直す**。どちらのテーブルへの変更も `rsyslog-config` サービスの再起動を引き起こす。

| 操作順序 | rsyslog-config 再起動回数 | 備考 |
|----------|--------------------------|------|
| `SYSLOG_SERVER` を先に投入 → `SYSLOG_CONFIG` を書き込む | **1 回** | 推奨パターン |
| `SYSLOG_CONFIG` を先に書き込む → `SYSLOG_SERVER` を後から追加 | **2 回** | 最終状態は同じだが再起動が増える |
| 同一値を再書き込み | **0 回** | キャッシュ比較でスキップ (hostcfgd:1725) |

**推奨書込み順序**:

```
# 1. リモートサーバ設定（先に投入）
SET SYSLOG_SERVER|<ip>  port=514  ...

# 2. グローバル設定（後から書き込む）
SET SYSLOG_CONFIG|GLOBAL  format=standard  rate_limit_interval=300  rate_limit_burst=20000
```

### welf_firewall_name の順序制約

YANG `must "(../format != 'standard')"` 制約により、`welf_firewall_name` は `format = welf` に変更した**後**でなければ書き込めない。

| ステップ | 操作 | 結果 |
|---------|------|------|
| 1 | `SYSLOG_CONFIG|GLOBAL format=welf` | OK |
| 2 | `SYSLOG_CONFIG|GLOBAL welf_firewall_name=<name>` | OK (YANG 制約満足) |
| × | `format=standard` のまま `welf_firewall_name` を書く | YANG バリデーションエラーで拒否 |

<!-- evidence: sonic-host-services/scripts/hostcfgd L2410-2415, L1725-1726; sonic-syslog.yang must "(../format != 'standard')" -->
<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照 — Phase C (cross-table refs)

> **調査根拠**: `hostcfgd` (`RSyslogCfg.update_rsyslog_config`, `rsyslog_handler`)・`rsyslog.conf.j2` 全行精読 (2026-05-18)
> 詳細証跡: `meta/_intermediate/cdb-flow/syslog-config-cross-refs.md`

`SYSLOG_CONFIG` テーブルは実行時に以下のテーブルを暗黙参照する。

| 参照先 | DB | 参照方向 | YANG leafref | 実装上の必須度 | 証拠 |
|---|---|---|---|---|---|
| `SYSLOG_SERVER` | CONFIG_DB | 読み取り (毎回ペア取得 + テンプレート展開) | なし | 任意 (0件でも動作) | `hostcfgd:2410-2415`, `rsyslog.conf.j2:84-125` |
| `DEVICE_METADATA\|localhost.hostname` | CONFIG_DB | 読み取り (welf_firewall_name フォールバック) | なし | 条件付き必須 (format=welf かつ welf_firewall_name 未設定時) | `rsyslog.conf.j2:52` |
| `SYSLOG_CONFIG_FEATURE` | CONFIG_DB | 参照元として rate-limit 提供 (ホスト側のみ) | なし | アーキテクチャ上の独立 | `rsyslog-container.conf.j2` defaults |

### SYSLOG_SERVER — 常にペアで読まれる

`rsyslog_handler()` は `SYSLOG_CONFIG` と `SYSLOG_SERVER` を同時に `get_table()` で取得し (`hostcfgd:2410-2415`)、`RSyslogCfg.update_rsyslog_config(rsyslog_config, rsyslog_servers)` へ渡す。`rsyslog.conf.j2` の `{% for server in SYSLOG_SERVER %}` ループ (L84-125) が全サーバエントリを展開する。`SYSLOG_CONFIG|GLOBAL.format = welf` の場合、テンプレート内でサーバ側の出力テンプレートも `WelfRemoteFormat` に切り替わるため (L99-105)、`SYSLOG_CONFIG.format` 値が `SYSLOG_SERVER` の出力形式を間接的に制御する[^cross-server]。

### DEVICE_METADATA|localhost.hostname — welf_firewall_name フォールバック

`rsyslog.conf.j2` L52: `{% set fw_name = gconf.get('welf_firewall_name', hostname) %}` — `welf_firewall_name` が未設定の場合、`sonic-cfggen -d` が `DEVICE_METADATA|localhost.hostname` から取得した `hostname` 変数がフォールバックとして WELF ログのファイアウォール名になる[^cross-hostname]。`format = welf` 時に `welf_firewall_name` を省略すると、意図しないホスト名がログに含まれる。

### SYSLOG_CONFIG_FEATURE との独立性

`SYSLOG_CONFIG|GLOBAL` の rate-limit 設定はホスト側 rsyslog にのみ反映される。各コンテナの rsyslog は `containercfgd` が `rsyslog-container.conf.j2` を展開し、`SYSLOG_CONFIG_FEATURE` が未設定のコンテナにはテンプレートのハードコードデフォルト (`interval=300`, `burst=20000`) が使われる。`SYSLOG_CONFIG|GLOBAL` の値はコンテナ rsyslog には**直接継承されない**[^cross-feature]。

[^cross-server]: `sonic-host-services/scripts/hostcfgd` L2410-2415 (`rsyslog_handler`), `sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2` L84-125. <https://github.com/sonic-net/sonic-buildimage/blob/master/files/image_config/rsyslog/rsyslog.conf.j2>
[^cross-hostname]: `sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2` L52 (`welf_firewall_name` フォールバック). <https://github.com/sonic-net/sonic-buildimage/blob/master/files/image_config/rsyslog/rsyslog.conf.j2>
[^cross-feature]: `sonic-buildimage/files/image_config/rsyslog/rsyslog-container.conf.j2` (`|default('300')`, `|default('20000')`). <https://github.com/sonic-net/sonic-buildimage/blob/master/files/image_config/rsyslog/rsyslog-container.conf.j2>

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

ソース: `sonic-net/sonic-host-services/scripts/hostcfgd` (`RSyslogCfg` クラス, L1695-1743)
詳細証跡: `meta/_intermediate/cdb-flow/syslog-config-failure.md`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `systemctl reset-failed rsyslog-config rsyslog` が `CalledProcessError` | `update_rsyslog_config()` L1731-1739 | `return` でキャッシュ未更新・rsyslog 設定**未反映** | LOG_ERR ("RSyslogCfg: Failed to restart rsyslog service") | `hostcfgd:1731-1739` |
| `systemctl restart rsyslog-config` が `CalledProcessError` | `update_rsyslog_config()` L1734-1739 | 同上（`raise_exception=True` で例外捕捉 → LOG_ERR + return） | LOG_ERR | `hostcfgd:1734-1739` |
| config/servers 内容が前回と同一（キャッシュ一致） | `update_rsyslog_config()` L1725-1726 | `systemctl restart` をスキップ (ノーオペレーション) | LOG_DEBUG のみ | `hostcfgd:1724-1726` |
| YANG must 制約違反 — `format=standard` のまま `welf_firewall_name` を書き込む | YANG バリデーション層 | CONFIG_DB への書き込みが reject（hostcfgd には到達しない） | YANG バリデーションエラー | `sonic-syslog.yang must "(../format != 'standard')"` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `SYSLOG_CONFIG\|GLOBAL` を DEL → `rsyslog_handler()` が空 dict でテーブル取得 | `update_rsyslog_config()` L1725 | 差分あり判定で `rsyslog-config` を再起動・Jinja2 テンプレートが空設定で rsyslog.conf を再生成 | `hostcfgd:2410-2415`, L1725 |

### 補足

- **restart 失敗時のキャッシュ非更新**: `return` 前にキャッシュを更新しないため、次回テーブル変更時に「差分あり」と判定され再度 restart が試みられる（実質的な自動リトライ）。
- **`rsyslog-config` サービス**: このサービスが Jinja2 テンプレートを展開し `rsyslog.conf` を生成後に `rsyslogd` を再起動する。`reset-failed` を先に行うのは前回の `failed` 状態をクリアするためで、これも失敗すると restart は試みられない。
- **SYSLOG_SERVER 変更による連鎖**: `rsyslog_server_handler()` も同一 `rsyslog_handler()` を呼ぶため、`SYSLOG_SERVER` の追加/削除時に `rsyslog-config` restart が失敗した場合も同様（LOG_ERR + キャッシュ非更新）。

<!-- /failure -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

hostcfgd が `rate_limit_interval==0` の場合に rate limit 無効化設定を自動生成する（特殊値による分岐）。`SYSLOG_CONFIG_FEATURE` が未設定の feature に対してグローバル値のフォールバックが発生する（間接的な Phase 6 派生）。

### Phase 7: 条件付き登録 (add_manager 条件)

hostcfgd は常時起動し `SYSLOG_CONFIG` テーブルを無条件購読する。`SYSLOG_CONFIG|GLOBAL` エントリのみ処理するシングルトン制約あり（YANG で強制）。

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `hostcfgd` | `rate_limit_interval==0` | rate limit 無効化設定を生成 | `hostcfgd.py` |
| `hostcfgd` | `rate_limit_interval>0` | 指定インターバルで rate limit 設定を生成 | `hostcfgd.py` |
| `hostcfgd` | `rate_limit_burst==0` | burst limit 無効化 | `hostcfgd.py` |
| `hostcfgd` | 設定変更 | rsyslog サービスを reload | `hostcfgd.py` |

> **スキャン証跡**: `SYSLOG_CONFIG` はグローバル syslog rate limit 設定。`rate_limit_interval==0` での無効化分岐が主要ポイント。`SYSLOG_CONFIG_FEATURE` への値の伝播が Phase 6 自動派生相当。

<!-- /handler-branching -->

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

YANG default 宣言 (`format=standard` / `severity=notice`) を補完する形で、テンプレート fallback や `containercfgd` のローカル fallback が複層に効く。CONFIG_DB に行が無い／フィールドが欠落した場合の実効値を以下にまとめる。

| フィールド | YANG default | コード由来デフォルト | 発生源 |
|---|---|---|---|
| `rate_limit_interval` | なし | **未指定 (rsyslog ディレクティブ非出力 → `imuxsock` 既定で実効 rate limit 無効)** | `rsyslog.conf.j2` L17, L22 `is not none` ガード |
| `rate_limit_burst` | なし | **未指定 (同上、rsyslog `imuxsock` 既定値)** | `rsyslog.conf.j2` L18, L22 `is not none` ガード |
| `format` | `standard` | **`standard`** (二重防御) | YANG `default standard` + `rsyslog.conf.j2` L51 `gconf.get('format', 'standard')` |
| `welf_firewall_name` | なし | **`{{ hostname }}`** (DEVICE_METADATA 由来) | `rsyslog.conf.j2` L52 `gconf.get('welf_firewall_name', hostname)` |
| `severity` | `notice` | **`notice`** (YANG default) / `*` (テーブル全欠落時の per-server fallback) | YANG `default notice` + `rsyslog.conf.j2` L92 `gconf.get('severity', '*')` |

### `format` の詳細

YANG が `default standard` を宣言しているため、CLI / sonic-cfggen / YANG-aware 書き込み経路では `format` 欠落時に `standard` が自動付与される。`rsyslog.conf.j2` L51 はこの YANG default をバイパスする経路（直接 redis-cli 書き込み、`SYSLOG_CONFIG|GLOBAL` 行欠落）に備えた二重防御で、`gconf.get('format', 'standard')` で `'standard'` を最終フォールバックとする。

### `severity` の詳細

YANG default `notice` は `SYSLOG_CONFIG.GLOBAL.severity` に対するもの。テンプレート L92 では per-server severity の fallback として `gconf.get('severity', '*')` を使うため、`SYSLOG_CONFIG` テーブル自体が CONFIG_DB に存在しない場合は per-server に対して `'*'`（rsyslog の全 severity 構文）が適用される。これは YANG-実装 discrepancy（YANG 通過時は `notice`、未通過時は `*`）として `syslog-server` 側にも影響する。

### `welf_firewall_name` の暗黙ホスト名フォールバック

`format='welf'` で `welf_firewall_name` を未指定にすると、テンプレート L52 がデバイス hostname（`sonic-cfggen` が `DEVICE_METADATA` から注入）を `fw="..."` として埋め込む。YANG の `must "(../format != 'standard')"` 制約は `format='welf'` 時には必須化を強制しないため、welf_firewall_name 欠落 + format=welf という組み合わせは合法だが、実効的にホスト名がそのまま外部 syslog サーバへ送られる。

### `SYSLOG_CONFIG_FEATURE` への local fallback（コンテナ側）

`SYSLOG_CONFIG` (GLOBAL) はコンテナ内 rsyslog では参照されない（`rsyslog-container.conf.j2` は `SYSLOG_CONFIG_FEATURE` のみ参照）。コンテナ側 rate limit のハードコードフォールバックは `interval=300` / `burst=20000`（テンプレート L27 の `default()` フィルタ）。ただし `containercfgd.py` L143-144 が `data.get(..., '0')` で空 dict 経由でも `'0'` を渡すため、ハードコード fallback `300/20000` が発動するのは sonic-cfggen をスタンドアロン呼び出した特殊ケースに限られる。

> **スキャン証跡**: `sonic-syslog.yang` L156-191、`rsyslog.conf.j2` L16-22 / L51-52 / L92、`rsyslog-container.conf.j2` L16-27、`containercfgd.py` L98-160、`hostcfgd` L1695-1743 を精読。詳細は `meta/_intermediate/cdb-flow/syslog-config-defaults.md`。

<!-- /defaults -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **hostcfgd**: `SYSLOG_CONFIG` テーブルを `ConfigDBConnector` で購読。

### 段階 2: CFG → APPL 翻訳

- hostcfgd がグローバル syslog 設定 (リモートサーバ転送等) を rsyslog 設定ファイルに書き込み再起動。

### 段階 3: APPL → SAI

- SAI 経由なし。rsyslog がネットワーク経由でリモート syslog サーバへ転送。

### 段階 4: タイミング + 副作用

- 設定変更後 rsyslog 再起動まで数秒。リモートサーバ到達不能の場合はバッファリングまたはログ欠落。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

SYSLOG_CONFIG テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config syslog rate-limit ...` / `config syslog format ...` — `config/syslog.py` が SYSLOG_CONFIG を書き込む (sonic-utilities/config/syslog.py)

### minigraph / sonic-cfggen

minigraph.py に SYSLOG_CONFIG 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での SYSLOG_CONFIG マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- glossary-links-injected: f29534787f37 -->
