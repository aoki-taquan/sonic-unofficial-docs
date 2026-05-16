---
title: SYSLOG_SERVER テーブル
description: "SYSLOG_SERVER テーブル — リモート syslog 送信先を保持する。hostcfgd の SyslogHandler がこのテーブルを購読し、/etc/rsyslog.d/-remote.conf を生成して rsyslogd を再ロードする。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-syslog.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - SYSLOG_SERVER
    - SYSLOG_CONFIG
    - VRF
    - MGMT_VRF_CONFIG
  cli:
    - config syslog
  yang:
    - sonic-syslog
---

# SYSLOG_SERVER テーブル

## 概要

リモート syslog 送信先を保持する[^1]。`hostcfgd` の `SyslogHandler` がこのテーブルを購読し、`/etc/rsyslog.d/<n>-remote.conf` を生成して `rsyslogd` を再ロードする。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>SYSLOG_SERVER")]
  DM["hostcfgd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
SYSLOG_SERVER|<server_address>
```

`<server_address>` は `inet:host`（IP アドレスまたはホスト名）。

## フィールド一覧

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `server_address` (key) | `inet:host` | ✅ | サーバアドレス |
| `source` | ip-address | - | 送信元 IP。`server_address` と同 family である `must` |
| `port` | port-number | - | UDP/TCP ポート |
| `vrf` | leafref `VRF.name` または enum (`default`/`mgmt`) | - | 経路 [VRF](../../reference/glossary.md#term-vrf)。`mgmt` 指定時は `MGMT_VRF_CONFIG.mgmtVrfEnabled = true` 必須 (`must`) |
| `filter` | enum `include`/`exclude` | - | フィルタタイプ |
| `filter_regex` | string (`[^\n\r]+`) | - | フィルタ正規表現 |
| `protocol` | enum `tcp`/`udp` | - | 転送プロトコル |
| `severity` | enum `none`/`debug`/`info`/`notice`/`warn`/`error`/`crit` | - | 最低重大度 |

## 関連サブテーブル

- `SYSLOG_CONFIG|GLOBAL`: 全体 syslog 設定（rate limit、format、severity）
    - `format` (welf/standard, default standard)、`welf_firewall_name` (`format != standard` 必須)
- `SYSLOG_CONFIG_FEATURE|<service>` (key: leafref `FEATURE.name`): サービス単位 rate-limit

## 購読者

- `hostcfgd` `SyslogHandler`: rsyslog 設定生成

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `VRF`、`MGMT_VRF_CONFIG`、`FEATURE`、`SYSLOG_CONFIG`
- 関連 CLI: `config syslog add/del`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-syslog`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-syslog`](../yang/sonic-syslog.md)
- CLI: [`config syslog`](../cli/config-syslog.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-syslog.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-syslog.yang>

## 関連ページ
- [HLD: Syslog Source IP](../../system/sonic-syslog-source-ip.md)
- [CLI: config syslog](../cli/config-syslog.md)
- [YANG: sonic-syslog](../yang/sonic-syslog.md)

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Telemetry / SNMP / Observability](../../topics/09-telemetry-snmp/index.md)

<!-- /topics-back-ref -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `vrf`: `default` / `mgmt` / VRF 名 (leafref)

### `filter` (syslog-filter-type): `include` / `exclude`

### `protocol` (rsyslog-protocol): `tcp` / `udp`

### `severity` (rsyslog-severity): `none` / `debug` / `info` / `notice` / `warn` / `error` / `crit`

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `vrf` | `mgmt` | 管理 [VRF](../../reference/glossary.md#term-vrf) 経由。`MGMT_VRF_CONFIG.mgmtVrfEnabled != true` なら YANG must 違反で拒否 |
| `vrf` | `default` | デフォルト [VRF](../../reference/glossary.md#term-vrf) 経由で転送 |
| `filter` | `include` | `filter_regex` にマッチするメッセージのみ転送 |
| `filter` | `exclude` | `filter_regex` にマッチするメッセージを除外して転送 |
| `source` | `server_address` と異なる IP family | YANG must 制約違反で書き込み拒否 |
| `protocol` | `tcp` | rsyslog が TCP で転送。接続失敗時はキュー蓄積 |
| `protocol` | `udp` | rsyslog が UDP で転送。パケットロスあり |
| `severity` | `none` | フィルタなし（全 severity を転送） |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-host-services/scripts/hostcfgd@c5bbbe8b07b96f078fa4b761316627404b01bd04 L2417-2415 -->

- **SYSLOG_CONFIG と合算で再評価**: `rsyslog_server_handler()` はエントリの追加/削除/変更のいずれでも `SYSLOG_CONFIG` と `SYSLOG_SERVER` 両テーブルを再取得し `rsyslog-config` サービスを再起動する。サーバー 1 台の変更でも全設定が再生成される点に注意。
- **全エントリ削除時の挙動**: `SYSLOG_SERVER` エントリが 0 件になるとリモート転送設定が空のテンプレートが生成される。ローカルログは継続されるが rsyslog のリモート転送は停止する。
- **rsyslog 再起動失敗時は設定不反映**: `systemctl restart rsyslog-config` が失敗すると `"RSyslogCfg: Failed to restart rsyslog service"` を LOG_ERR してキャッシュを更新せずに return する（次回テーブル変更時に再試行）。
- **IP バリデーションは YANG 層**: key（サーバー IP / ホスト名）の構文チェックは `sonic-syslog.yang` の `inet:ip-address` / `inet:host` 型制約で行われ、`hostcfgd` 層での追加チェックはない。

<!-- /cdb-exceptions -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `SYSLOG_SERVER|<ip>`。
- `source`: `Loopback0` 等。
- `vrf`: `default` / `mgmt`。
- `port`: 514。

### よくある誤設定

- `vrf: mgmt` で `source` を data-plane IP にすると syslog が出ない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'SYSLOG_SERVER|*'
show syslog
```
<!-- /ops-hint -->


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

hostcfgd が `protocol` フィールド値から rsyslog forwarding 形式を自動決定する。`udp` → `@<host>:<port>` 形式、`tcp` → `@@<host>:<port>` 形式。`port` フィールド未設定の場合はデフォルト UDP/514 を補完する。`vrf==mgmt` の場合は VRF バインド設定を自動付与する。

### Phase 7: 条件付き登録 (add_manager 条件)

hostcfgd は常時起動し `SYSLOG_SERVER` テーブルを無条件購読する。`DEVICE_METADATA.hostname` が必要（hostname ベースのフィルタ設定）。

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `hostcfgd` | `protocol==udp` | rsyslog `@<host>:<port>` 形式 | `hostcfgd.py` |
| `hostcfgd` | `protocol==tcp` | rsyslog `@@<host>:<port>` 形式 | `hostcfgd.py` |
| `hostcfgd` | `vrf==mgmt` | VRF バインド設定を追加 | `hostcfgd.py` |
| `hostcfgd` | `vrf==default` または未設定 | デフォルト VRF で転送 | `hostcfgd.py` |
| `hostcfgd` | `source_interface` フィールドあり | rsyslog source IP 設定 | `hostcfgd.py` |
| `hostcfgd` | サーバー削除 | 対応 rsyslog 設定を削除して reload | `hostcfgd.py` |

> **スキャン証跡**: `SYSLOG_SERVER` はリモート syslog 転送先の設定。`protocol` フィールドと `vrf` フィールドの組み合わせが主要分岐。ポートデフォルト値の補完が Phase 6 相当。

<!-- /handler-branching -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **hostcfgd**: `SYSLOG_SERVER` テーブルを `ConfigDBConnector` で購読。

### 段階 2: CFG → APPL 翻訳

- hostcfgd の `syslogHandler` がリモート syslog サーバ宛の転送設定を `/etc/rsyslog.d/` に書き込み rsyslog 再起動。

### 段階 3: APPL → SAI

- SAI 経由なし。rsyslog が UDP/TCP 514 番でリモートサーバへ転送。

### 段階 4: タイミング + 副作用

- rsyslog 再起動まで数秒。VRF を使用する場合は rsyslog の VRF バインド設定が必要。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

SYSLOG_SERVER テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config syslog add/del ...` — `config/main.py` または `config/syslog.py` が `set_entry('SYSLOG_SERVER', ...)` を呼ぶ (sonic-utilities/config/main.py, config/syslog.py)

### minigraph / sonic-cfggen

**minigraph.py** が `<SyslogServer>` タグから SYSLOG_SERVER エントリを生成 (sonic-buildimage/src/sonic-config-engine/minigraph.py)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での SYSLOG_SERVER マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

### CONFIG_DB 購読 API

`hostcfgd` は `swsscommon.ConfigDBConnector` の `subscribe()` で `SYSLOG_SERVER` テーブルを購読する。`ConsumerStateTable`（channel ベース）は使用しない。

```python
# sonic-host-services/scripts/hostcfgd L2499-2503
# Handle SYSLOG_CONFIG and SYSLOG_SERVER changes
self.config_db.subscribe(swsscommon.CFG_SYSLOG_CONFIG_TABLE_NAME,
                         make_callback(self.rsyslog_config_handler))
self.config_db.subscribe(swsscommon.CFG_SYSLOG_SERVER_TABLE_NAME,
                         make_callback(self.rsyslog_server_handler))
```

- `ConfigDBConnector.listen()` が内部で Redis **keyspace 通知** (`__keyspace@4__:SYSLOG_SERVER|*` への PSUBSCRIBE) を購読する。
- `SYSLOG_SERVER` と `SYSLOG_CONFIG` を独立して登録するが、両ハンドラとも同じ `rsyslog_handler()` を呼び、**両テーブルを一括再取得**してキャッシュ比較後に `systemctl restart rsyslog-config` を発行する。

### ハンドラ呼び出しフロー

```
SYSLOG_SERVER|<ip> 変更 (hset/del)
  → keyspace 通知 (__keyspace@4__:SYSLOG_SERVER|<ip>)
  → rsyslog_server_handler(key, op, data)          # hostcfgd L2417-2419
  → rsyslog_handler()                              # hostcfgd L2410-2415
      → get_table(SYSLOG_CONFIG) + get_table(SYSLOG_SERVER)
      → RSyslogCfg.update_rsyslog_config()         # L1715-1743
          → キャッシュ差分あり → systemctl restart rsyslog-config
```

### rsyslog SIGHUP / restart 経路

`rsyslog-config.service` の `ExecStart=/usr/bin/rsyslog-config.sh` が実際の設定反映を行う。

```bash
# sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh L58-73
sonic-cfggen -d -t rsyslog.conf.j2 ... > "$TMPFILE"

if [ ! -f /etc/rsyslog.conf ] || ! cmp -s "$TMPFILE" /etc/rsyslog.conf; then
    cp "$TMPFILE" /etc/rsyslog.conf
    systemctl restart rsyslog      # 設定変更あり → rsyslogd 完全再起動
else
    systemctl kill -s HUP rsyslog  # 設定変更なし → SIGHUP のみ（ログファイル再オープン）
fi
```

| 状況 | 操作 | 意味 |
|------|------|------|
| `/etc/rsyslog.conf` 変化あり | `systemctl restart rsyslog` | rsyslogd プロセス完全再起動（設定全再読込） |
| `/etc/rsyslog.conf` 変化なし | `systemctl kill -s HUP rsyslog` | SIGHUP でログファイル再オープン（ログローテーション対応）のみ |

!!! note "SIGHUP の役割"
    SIGHUP は「設定変更なし時」のログローテーション対応専用。通常の設定反映は `systemctl restart rsyslog` が担う。`hostcfgd` 自身は SIGHUP を受信しても無視する（L111-112）。

### keyspace 通知パターン

| Redis keyspace 通知 | hostcfgd ハンドラ |
|---------------------|------------------|
| `__keyspace@4__:SYSLOG_SERVER\|192.168.1.1` `hset` | `rsyslog_server_handler("192.168.1.1", SET, {...})` |
| `__keyspace@4__:SYSLOG_SERVER\|192.168.1.1` `del` | `rsyslog_server_handler("192.168.1.1", DEL, {})` |
| `__keyspace@4__:SYSLOG_CONFIG\|GLOBAL` `hset` | `rsyslog_config_handler("GLOBAL", SET, {...})` |

- APPL_DB / STATE_DB への中継なし。SAI 経路なし。
- 経路: CONFIG_DB → hostcfgd (keyspace 通知) → rsyslog-config.service → rsyslogd restart/SIGHUP

<!-- /pubsub -->

<!-- glossary-links-injected: 639b97382f4c -->
