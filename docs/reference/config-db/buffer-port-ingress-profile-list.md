---
title: BUFFER_PORT_INGRESS_PROFILE_LIST テーブル
description: "BUFFER_PORT_INGRESS_PROFILE_LIST テーブル — ingress 方向の BUFFER_PG (priority-group ごとのバッファ) と並ぶ別系統で、こちらはポート全体としての ingress プロファイル群の集約。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-buffer-port-ingress-profile-list.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BUFFER_PORT_INGRESS_PROFILE_LIST
    - BUFFER_PROFILE
    - BUFFER_POOL
    - PORT
  cli:
    - config buffer
  yang:
    - sonic-buffer-port-ingress-profile-list
hard: 0
---

# BUFFER_PORT_INGRESS_PROFILE_LIST テーブル

## 概要

**ポートに紐づけるイングレスバッファプロファイル群** を定義する [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル[^1]。[SAI](../../reference/glossary.md#term-sai) における `SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST` 相当で、`BUFFER_PROFILE` テーブルで定義した複数プロファイルを、ポート単位で **順序を保ったリスト** として束ねる。

ingress 方向の `BUFFER_PG` (priority-group ごとのバッファ) と並ぶ別系統で、こちらはポート全体としての ingress プロファイル群の集約。動的バッファモデル (`buffer_model = dynamic`) ではあまり使われず、静的バッファ設定で利用されることが多い。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>BUFFER_PORT_INGRESS_PROFILE_LIST")]
  DM["buffermgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_DB")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_port_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
BUFFER_PORT_INGRESS_PROFILE_LIST|<port>
```

- `<port>`: `PORT.name` への leafref (例: `Ethernet0`)

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `port` (key) | leafref → `PORT.name` | 対象ポート |
| `profile_list` | leaf-list of leafref → `BUFFER_PROFILE.name` (ordered-by user) | ポートにバインドする ingress バッファプロファイル名の順序付きリスト |

`profile_list` は **`ordered-by user`** で設定順を保持する。[CONFIG_DB](../../reference/glossary.md#term-config_db) では `","` 区切りの文字列として保存される慣習。

## 制約

- `port` は `PORT_LIST.name` への leafref で、対象ポートが存在しないと validation エラー。
- 各 `profile_list` 要素も `BUFFER_PROFILE_LIST.name` への leafref。

<!-- defaults -->
## 暗黙デフォルト・コード由来の挙動

YANG に `default` 節は存在しない。以下はすべてコード実装から検出した暗黙挙動。

| フィールド / 条件 | 暗黙挙動 | 種別 | evidence |
|-----------------|---------|------|---------|
| `profile_list` 不在 | APPL_DB に書かない（エントリなし） | dead field なし | `buffermgr.cpp:doBufferTableTask` |
| 参照 `BUFFER_PROFILE` が未ロード | `task_need_retry` でキューに残す（silent retry） | silent fallback | `buffermgrdyn.cpp:3282-3285` |
| `m_bufferPoolReady == false` | APPL_DB 書き込みを保留 (`m_bufferObjectsPending=true`) | 暗黙 pending | `buffermgrdyn.cpp:3408-3414` |
| admin-down ポート | ユーザー設定 `profile_list` を **zero profile list に silent 置換** して APPL_DB へ書き込む | silent substitution | `buffermgrdyn.cpp:3418-3438` |
| zero profile が存在しないプール | WARN ログのみ、当該プールをスキップ（部分置換） | partial silent drop | `buffermgrdyn.cpp:1185-1188` |
| egress 方向プロファイルを `profile_list` に設定 (dynamic) | `task_failed`、エントリ消去 | 方向不一致エラー | `buffermgrdyn.cpp:3289-3296` |
| `packet_discard_action=trim` プロファイルを `profile_list` に設定 | orchagent が `task_failed` を返す（ingress trim 禁止） | ハードコード禁止 | `bufferorch.cpp:1725-1731` |
| bulk SAI 部分失敗 | `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` で続行、失敗ポートは `task_need_retry` 再投入 | partial failure | `bufferorch.cpp:1823-1844` |
| プロファイルリスト変更なし | SAI 呼び出しをスキップ（idempotent） | silent skip | `bufferorch.cpp:1695-1699` |
| キー内ポート名空文字 | `task_invalid_entry`、エントリ消去 | silent drop | `buffermgrdyn.cpp:3509-3513` |
| カンマ区切りポートリスト | 各ポートに展開して順次処理。途中 retry で残りをスキップ | 暗黙展開 + partial retry | `buffermgrdyn.cpp:3527-3548` |
| `buffer_profile_list` 以外のフィールド (dynamic) | SWSS_LOG_ERROR + `continue`（フィールド無視） | silent field drop | `buffermgrdyn.cpp:3402-3405` |
| static buffer model (`buffermgr.cpp`) | 方向チェック・trim チェックなし、そのまま APPL_DB へ転送 | static/dynamic 乖離 | `buffermgr.cpp:doBufferTableTask` |
| DEL 操作 (dynamic) | コード実行はされる（erase + del）が「Mellanox では非サポート」コメントあり | コメントと実装の乖離 | `buffermgrdyn.cpp:3441-3446` |

> **YANG vs 実装 discrepancy**: YANG の `leaf-list profile_list` に `default`・方向制約・trim 禁止の記述はない。これらは純粋に実装（buffermgrdyn.cpp / bufferorch.cpp）による制約。
<!-- /defaults -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **プロファイル参照未解決 → retry**: `profile_list` に参照する `BUFFER_PROFILE` が未存在の場合、`orchagent` は `task_need_retry` を返しエントリを保留する。<!-- evidence: bufferorch.cpp L1679-1686 processIngressBufferProfileList -->
- **リスト変更なし → SAI 呼び出しスキップ**: プロファイルリストが既存キャッシュと同一の場合は SAI を呼ばずにスキップする。<!-- evidence: bufferorch.cpp L1692-1696 -->
- **trimming-eligible プロファイル禁止 → task_failed**: `packet_discard_action = trim` のプロファイルは ingress profile list に設定不可。SAI 仕様上 ingress 側でのパケットトリミングは禁止されており `task_failed` となる。<!-- evidence: bufferorch.cpp L1717-1731 -->
- **ポート未存在 → task_invalid_entry**: 指定ポート名が PortsOrch のポートマップに存在しない場合 `task_invalid_entry` を返す。<!-- evidence: bufferorch.cpp L1760-1764 -->

<!-- value-behavior -->
## 値依存挙動マトリクス

このテーブルに enum フィールドはない。ただし参照する `BUFFER_PROFILE.packet_discard_action` の値によって挙動が変わる。

| 参照プロファイルの `packet_discard_action` | 挙動 |
|------------------------------------------|------|
| `drop`（既定） | `profile_list` に含めて ingress profile list として設定可能。`BufferOrch` が SAI `SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST` を更新する。 |
| `trim` | `BufferOrch` が `isTrimmingEligible=true` を検出し `task_failed` を返す（`bufferorch.cpp:1725-1731`）。ingress profile list への trim プロファイルの適用は SAI 仕様上 **禁止**。 |

また、`buffer_model=dynamic` では `buffermgrd` が profile list を自動生成するため、ユーザによる手動設定は通常不要。
<!-- /value-behavior -->

## 購読者

- `buffermgrd` (`docker-swss`): [CONFIG_DB](../../reference/glossary.md#term-config_db) → [APPL_DB](../../reference/glossary.md#term-appl_db) の `BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE`
- `orchagent` (BufferOrch): [APPL_DB](../../reference/glossary.md#term-appl_db) → [SAI](../../reference/glossary.md#term-sai) の port ingress buffer profile list 設定

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `BUFFER_PROFILE`, `BUFFER_POOL`, `BUFFER_PG`, `PORT`, `BUFFER_PORT_EGRESS_PROFILE_LIST`
- 関連 CLI: `config buffer profile` ([sonic-utilities](../../reference/glossary.md#term-sonic-utilities))
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-buffer-port-ingress-profile-list`, `sonic-buffer-profile`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): `sonic-buffer-port-ingress-profile-list`
- CLI: [`config buffer`](../cli/config-buffer.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-buffer-port-ingress-profile-list.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-buffer-port-ingress-profile-list.yang>

## 関連ページ
- [CONFIG_DB: BUFFER_PROFILE](buffer-profile.md)
- [CONFIG_DB: BUFFER_POOL](buffer-pool.md)
- [CONFIG_DB: BUFFER_PG](buffer-pg.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `BUFFER_PORT_INGRESS_PROFILE_LIST|<port>` (例 `BUFFER_PORT_INGRESS_PROFILE_LIST|Ethernet0`)。
- `profile_list`: `","` 区切り (例 `"ingress_lossless_profile,ingress_lossy_profile"`)。
- static-buffer モードでの利用が中心。dynamic-buffer モードでは通常不要。

### よくある誤設定

- `BUFFER_PROFILE` に存在しないプロファイル名を入れて leafref 検証エラー。
- dynamic-buffer モードで設定したが反映されず混乱する (dynamic では buffermgrd が自動生成)。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'BUFFER_PORT_INGRESS_PROFILE_LIST|Ethernet0'
sonic-db-cli APPL_DB hgetall 'BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE:Ethernet0'
show buffer pool
```
<!-- /ops-hint -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`buffermgrd` → `BufferOrch` (APPL_DB 経由) が CONFIG_DB の `BUFFER_PORT_INGRESS_PROFILE_LIST` テーブルを購読する。

`BUFFER_PORT_INGRESS_PROFILE_LIST` の key は `<port>` (例: `Ethernet0`)。

### 段階 2 — CFG→APPL 翻訳

`APP_BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE` に書き込み

### 段階 3 — APPL→SAI

`sai_buffer_api` / `sai_port_api` — ポートの ingress バッファプロファイルリストをバインド

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `buffermgrd` が検知後 APPL_DB に書き込み。`BufferOrch` が SAI port attribute を更新。

**副作用**: 対象ポートの ingress バッファ割り当てが変更される。PFC や lossless traffic に影響する可能性がある。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `BUFFER_PORT_INGRESS_PROFILE_LIST`

### CLI
- `config interface buffer ingress-profile-list set <port> <profile>`
  - ソース: `sonic-utilities/config/main.py (buffer グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `buffers_config.j2` から生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- Dynamic buffer model: `buffermgrd` がポートごとに書き込み
<!-- /entry-points -->


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 値による他フィールド自動派生

| 条件 | 派生先 | evidence |
|---|---|---|
| Dynamic buffer model: `buffermgrd` がポートの ingress プロファイルリストを自動生成 | `BUFFER_PORT_INGRESS_PROFILE_LIST` にエントリを書き込む | `sonic-swss/cfgmgr/buffermgrdyn.cpp:447,3567` |

### Phase 7: 条件付き module/manager 登録

| 条件 | 登録 module | evidence |
|---|---|---|
| 常時（条件なし） | `BufferMgrDynamic` が `BUFFER_PORT_INGRESS_PROFILE_LIST` を `handleBufferPortIngressProfileListTable` に登録 | `sonic-swss/cfgmgr/buffermgrdyn.cpp:447` |

### grep カバレッジ

- buffermgrdyn.cpp L447: BUFFER_PORT_INGRESS_PROFILE_LIST ハンドラ登録（条件なし）
<!-- /derivation -->
<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Manager / Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `BufferMgrDynamic` | `handleBufferObjectTables()` | キー形式が不正（ポート名空） | `task_invalid_entry` 返却 | `sonic-swss/cfgmgr/buffermgrdyn.cpp:3514` |
| `BufferMgrDynamic` | `handleBufferObjectTables()` | カンマ区切りポートリスト | ポートごとにシングルポートハンドラを繰り返し呼び出し | `sonic-swss/cfgmgr/buffermgrdyn.cpp:3536-3547` |

> **スキャン証跡**: `handleBufferPortIngressProfileListTable` は `handleBufferObjectTables(tuple, CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME, false)` に委譲。egress 版と同一パス。2 件分岐抽出。
<!-- /handler-branching -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`BUFFER_PORT_INGRESS_PROFILE_LIST` エントリが CONFIG_DB に書かれたとき、`buffermgrd` および `BufferOrch` が以下のテーブルを**暗黙的に leafref 参照**する。YANG スキーマ上は leafref として定義されているが、実装上はコード内 lookup / resolve で処理される。

| 参照元フィールド / 状態 | 参照先テーブル | 参照先キー形式 | 解決主体 | 未解決時の挙動 |
|---|---|---|---|---|
| `profile_list` 各要素 | `BUFFER_PROFILE` | `BUFFER_PROFILE\|<name>` | `buffermgrd` の `m_bufferProfileLookup` | `task_need_retry`（silent retry）— `buffermgrdyn.cpp:3280-3285` |
| `profile_list` 各要素 | APPL_DB `BUFFER_PROFILE_TABLE` | `BUFFER_PROFILE_TABLE:<name>` | `BufferOrch` の `resolveFieldRefArray` | `task_need_retry` — `bufferorch.cpp:1683-1688` |
| SET 処理時の pool 準備チェック | `BUFFER_POOL` (ingress 系全プール) | `BUFFER_POOL\|<pool>` | `buffermgrd` の `m_bufferPoolReady` フラグ | APPL_DB 書き込みを pending（`m_bufferObjectsPending=true`）、BUFFER_POOL 完了後自動再処理 — `buffermgrdyn.cpp:3408-3414` |
| キー `<port>` (ポート名) | `PORT` | `PORT\|<port>` | `BufferOrch` の PortsOrch ポートマップ | `task_invalid_entry`（エントリ消去）— `bufferorch.cpp:1762-1765` |
| キー `<port>` (ポート名) | `PORT` | `PORT\|<port>` | `buffermgrd` の `m_portInfoLookup` | admin-down 判定に使用。空文字なら `task_invalid_entry` — `buffermgrdyn.cpp:3509-3513` |

### 特記事項

- `profile_list` の各プロファイルは `direction=ingress` でなければならない。egress プロファイルを混入すると `task_failed`（`buffermgrdyn.cpp:3289-3296`）。
- `packet_discard_action=trim` のプロファイルは `BufferOrch` が ingress profile list への適用を拒否（`bufferorch.cpp:1725-1731`）。
- admin-down ポートでは `m_portInfoLookup[port].state == PORT_ADMIN_DOWN` を検出し、通常 profile_list の代わりに zero profile list を APPL_DB に書き込む（`buffermgrdyn.cpp:3418-3438`）。
- 詳細スキャン記録: `meta/_intermediate/cdb-flow/buffer-port-ingress-profile-list-cross-refs.md`
<!-- /cross-refs -->
<!-- glossary-links-injected: 021ae16e7b9c -->
