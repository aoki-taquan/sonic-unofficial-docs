---
title: ROUTE_MAP_SET テーブル
description: "ROUTE_MAP_SET テーブル — route-map 名の YANG レジストリ。frrcfgd / bgpcfgd は非購読。ROUTE_MAP テーブルの call_route_map leafref 整合性のために存在する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-route-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - ROUTE_MAP
    - BGP_NEIGHBOR_AF
    - BGP_PEER_GROUP_AF
    - BGP_GLOBALS_AF
  cli: []
  yang:
    - sonic-route-map
---

# ROUTE_MAP_SET テーブル

## 概要

route-map 名を登録する YANG レジストリテーブル[^1]。`sonic-route-map.yang` の `ROUTE_MAP_SET` コンテナで定義されており、`ROUTE_MAP.call_route_map` や `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` 等の route-map 参照 leafref の整合性検証に使われる。

**frrcfgd・[bgpcfgd](../../reference/glossary.md#term-bgpcfgd)・[orchagent](../../reference/glossary.md#term-orchagent) のいずれも本テーブルを購読しない**。[FRR](../../reference/glossary.md#term-frr) への反映は行われず、純粋に [YANG](../../reference/glossary.md#term-yang) データモデル上の名前空間として機能する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>ROUTE_MAP")]
  DM["bgpcfgd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
ROUTE_MAP_SET|<name>
```

`<name>` は route-map の名称文字列。同名のエントリを `ROUTE_MAP|<name>|<seq>` で参照する。

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `name` | string (key) | route-map 名。フィールドは key のみで、他のデータフィールドは存在しない |

## 購読者

なし。`frrcfgd`・`bgpcfgd`・[orchagent](../../reference/glossary.md#term-orchagent) のいずれも ROUTE_MAP_SET テーブルを購読しない（`frrcfgd.py` の `table_handler_list` および `tbl_to_key_map` に含まれないことを全行確認済み）。

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): [`ROUTE_MAP`](./route-map.md)（`call_route_map` leafref）、`BGP_NEIGHBOR_AF`、`BGP_PEER_GROUP_AF`、`BGP_GLOBALS_AF`（route-map 参照 leafref）
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-route-map`
- 関連 CLI: なし（`config load` / `sonic-db-cli` による直接投入）

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 |
|------|------|
| ROUTE_MAP_SET への書き込み | frrcfgd はイベントを受信しない。[FRR](../../reference/glossary.md#term-frr) 反映なし |
| ROUTE_MAP_SET が未作成で ROUTE_MAP を設定 | sonic-db-cli 直接書き込みは YANG 検証をバイパス。[FRR](../../reference/glossary.md#term-frr) への反映は ROUTE_MAP テーブルのみで決まる |
| YANG strict mode ([gNMI](../../reference/glossary.md#term-gnmi)/NETCONF) でのみ | ROUTE_MAP.call_route_map が存在しない名前を参照するとリジェクトされる |

<!-- evidence: sonic-route-map.yang:125-134; frrcfgd.py:2293-2338 table_handler_list -->
<!-- /cdb-exceptions -->

<!-- defaults -->
## 暗黙デフォルト・コード由来の落とし穴

YANG に定義されているフィールドは `name`（key）のみ。データフィールドが存在しないため、デフォルト値の概念は該当しない。

| フィールド | YANG default | コード実効デフォルト | パターン | 根拠 |
|-----------|-------------|-------------------|---------|------|
| `name` | なし（key、必須） | なし（必須キー） | — | `sonic-route-map.yang:129`; frrcfgd 非購読 |

### frrcfgd 非購読による落とし穴

`ROUTE_MAP_SET` を書き込むだけでは FRR に route-map は作成されない。route-map の実体は `ROUTE_MAP|<name>|<seq>` テーブルへの書き込みによって frrcfgd が `vtysh route-map` コマンドで作成する。

**ROUTE_MAP_SET は YANG leafref 整合性のための名前登録のみ**を担う。ROUTE_MAP エントリを作成する前後いずれかのタイミングで ROUTE_MAP_SET エントリを作成するかは、sonic-db-cli 直接投入では YANG 検証がバイパスされるため任意。

### db_migrator 非対応

`db_migrator.py` に ROUTE_MAP_SET の参照なし（grep 確認済み）。バージョン移行での自動補完なし。
<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`ROUTE_MAP_SET` テーブルは frrcfgd・[bgpcfgd](../../reference/glossary.md#term-bgpcfgd)・[orchagent](../../reference/glossary.md#term-orchagent) のいずれも購読しないため、
**FRR への反映という観点での書込み順序制約は存在しない**。

ただし [gNMI](../../reference/glossary.md#term-gnmi) / NETCONF 等の YANG 検証が有効なパスでは、以下のテーブルのフィールドが
`ROUTE_MAP_SET_LIST/name` を leafref で参照しているため、**参照元エントリを書く前に
`ROUTE_MAP_SET|<name>` エントリが存在しなければ leafref 検証失敗**となる。

| 参照元テーブル | 参照フィールド | 根拠 |
|---------------|---------------|------|
| `ROUTE_MAP` | `call_route_map` | `sonic-route-map.yang:269-273` |
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | `default_rmap` | `sonic-bgp-common.yang:354-358` |
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | `route_map_in` | `sonic-bgp-common.yang:385-392` |
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | `route_map_out` | `sonic-bgp-common.yang:394-401` |
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | `unsuppress_map_name` | `sonic-bgp-common.yang:408-413` |
| `BGP_GLOBALS_AF` | 各 route-map フィールド | `sonic-bgp-global.yang:373,380,502,532` |
| `ROUTE_REDISTRIBUTE` | `route_map` | `sonic-route-common.yang:60-66` |

`sonic-db-cli` 直接投入は YANG 検証をバイパスするため、この順序制約は実質適用されない。
DEL 時も同様で、`sonic-db-cli` であれば参照中の `ROUTE_MAP_SET` エントリを先に削除することは可能だが、
[gNMI](../../reference/glossary.md#term-gnmi)/NETCONF では参照元の解除が先行必須となる。

> **スキャン証跡**: `sonic-route-map.yang:125-134,269-273`、`sonic-bgp-common.yang:354-413`、`sonic-bgp-global.yang:373,380,502,532`、`sonic-route-common.yang:60-66`。詳細は `meta/_intermediate/cdb-flow/route-map-set-ordering.md` を参照。
<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

YANG leafref スキャン (`sonic-route-map.yang`, `sonic-bgp-common.yang`, `sonic-bgp-global.yang`, `sonic-route-common.yang`) および frrcfgd 実装確認による参照関係。詳細は `meta/_intermediate/cdb-flow/route-map-set-cross-refs.md` を参照。

`ROUTE_MAP_SET` テーブル自身は他テーブルを leafref で参照するフィールドを持たない（`name` key のみの名前レジストリ）。以下はすべて **被参照**（他テーブルから ROUTE_MAP_SET.name を参照する逆参照）。

| 参照元テーブル | 参照フィールド | YANG 根拠 | 備考 |
|--------------|--------------|----------|------|
| [`ROUTE_MAP`](./route-map.md) | `call_route_map` | `sonic-route-map.yang:269-273` | frrcfgd が FRR に `call <name>` を発行。call 先未定義時は FRR がポリシー素通り |
| [`BGP_NEIGHBOR_AF`](./bgp-neighbor-af.md) | `route_map_in`, `route_map_out`, `default_rmap`, `unsuppress_map_name` | `sonic-bgp-common.yang:354-413` | frrcfgd が `neighbor {} route-map {} in/out` に変換 |
| [`BGP_PEER_GROUP_AF`](./bgp-peer-group-af.md) | `route_map_in`, `route_map_out`, `default_rmap`, `unsuppress_map_name` | `sonic-bgp-common.yang:354-413` | BGP_NEIGHBOR_AF と同一 YANG grouping を共有 |
| `BGP_GLOBALS_AF` | `import_vrf_route_map`, `route_download_filter` | `sonic-bgp-global.yang:371-382` | frrcfgd が `vrf import` / `table-map` コマンドに変換 |
| `BGP_GLOBALS_AF_AGGREGATE_ADDR` | `policy` | `sonic-bgp-global.yang:500-505` | [BGP](../../reference/glossary.md#term-bgp) aggregate-address に route-map を適用 |
| `BGP_GLOBALS_AF_NETWORK` | `policy` | `sonic-bgp-global.yang:530-534` | [BGP](../../reference/glossary.md#term-bgp) network コマンドに route-map を適用 |
| `ROUTE_REDISTRIBUTE` | `route_map` (leaf-list) | `sonic-route-common.yang:60-66` | redistribute コマンドへの route-map 付与 |

!!! note "frrcfgd の実行時チェックなし"
    これらの参照は YANG レベルの leafref 整合性検証のみ機能する。frrcfgd は ROUTE_MAP_SET エントリの存在を実行時にチェックせず、name 文字列を FRR コマンドにそのまま渡す（`sonic-route-map.yang:269-273`; `frrcfgd.py:1942`）。`sonic-db-cli` 直接投入では YANG 検証もバイパスされるため、参照整合性は実質ユーザー責任となる。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動・エラーパス (Phase D)

> **調査根拠**: `sonic-route-map.yang:125-134,269-273`; `frrcfgd.py` 全文 grep (2026-05-18)
> 詳細証跡: `meta/_intermediate/cdb-flow/route-map-set-failure.md`

ROUTE_MAP_SET テーブルには **購読デーモンが存在しない**。frrcfgd・[bgpcfgd](../../reference/glossary.md#term-bgpcfgd)・orchagent のいずれも本テーブルを購読しないため、「デーモンが書き込みを処理してエラーを返す」形式の失敗パスは存在しない。

### SET / DEL 失敗マトリクス

| 操作 | 条件 | 動作 | 備考 |
|------|------|------|------|
| ROUTE_MAP_SET エントリ SET | gNMI / NETCONF 経由かつ ROUTE_MAP.call_route_map から参照中の name と重複 | YANG leafref 整合性違反として拒否 | sonic-db-cli 直接書き込みではバイパス |
| ROUTE_MAP_SET エントリ DEL | gNMI / NETCONF 経由かつ ROUTE_MAP.call_route_map が参照中 | YANG leafref 参照先削除として拒否 | sonic-db-cli では拒否されず [Redis](../../reference/glossary.md#term-redis) から削除される |
| ROUTE_MAP_SET エントリ SET | sonic-db-cli 直接書き込み | 常に成功（YANG 検証なし） | 購読デーモンがないため副作用なし |
| 存在しない ROUTE_MAP_SET を参照する ROUTE_MAP の FRR 反映 | frrcfgd が call_route_map 値をそのまま [vtysh](../../reference/glossary.md#term-vtysh) に渡す | FRR が `% Unknown command` 等で拒否 → `LOG_ERR` + `continue` | frrcfgd の実行時チェックなし (`frrcfgd.py:1942`) |

### ステータス書き戻しなし

ROUTE_MAP_SET への SET/DEL の成否は [CONFIG_DB](../../reference/glossary.md#term-config_db) に書き戻されない。YANG 検証エラーは gNMI/NETCONF のレスポンスで返されるのみ。

<!-- evidence: sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-map.yang:125-134 (ROUTE_MAP_SET_LIST 定義、must 句なし) -->
<!-- evidence: sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-map.yang:269-273 (call_route_map leafref) -->
<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

> **調査根拠**: `sonic-route-map.yang:125-134`; `frrcfgd.py` 全文 grep (ROUTE_MAP_SET 出現なし); `db_migrator.py` 全文 grep (2026-05-18)
> 詳細証跡: `meta/_intermediate/cdb-flow/route-map-set-constants.md`

ROUTE_MAP_SET テーブルは frrcfgd・bgpcfgd・orchagent のいずれも購読しないため、**ランタイムのハードコード定数は存在しない**。実装コードがこのテーブルを処理しないことを `frrcfgd.py` 全文 grep（`ROUTE_MAP_SET` 出現なし）および `db_migrator.py` grep で確認した。

### YANG 定義上の制約（定数相当）

| 制約 | 値 / 内容 | ソース |
|------|----------|--------|
| `name` 型 | `string`（長さ制約なし、YANG デフォルト） | `sonic-route-map.yang:129` |
| フィールド数 | key (`name`) のみ。データフィールドなし | `sonic-route-map.yang:126-133` |

YANG の `string` 型にはデフォルトの長さ上限はなく、`sonic-route-map.yang` に `length` 制約も定義されていない。`sonic-db-cli` 直接投入では YANG 検証もバイパスされるため、name 文字列長の実質的な上限は [Redis](../../reference/glossary.md#term-redis) のキー長制限（512 MB）のみとなる。

<!-- evidence: sonic-route-map.yang:125-134; frrcfgd.py table_handler_list L2293-2338 (ROUTE_MAP_SET 出現なし) -->
<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

> **調査根拠**: `frrcfgd.py` 全文 grep (`ROUTE_MAP_SET` 出現なし); `bgpcfgd` ソース全文 grep (2026-05-19)
> 詳細証跡: `meta/_intermediate/cdb-flow/route-map-set-side-effects.md`

`ROUTE_MAP_SET` テーブルへの SET / DEL に伴う**副次 DB 書込は存在しない**。frrcfgd・bgpcfgd・orchagent のいずれも本テーブルを購読しないため、[APPL_DB](../../reference/glossary.md#term-appl_db) / [STATE_DB](../../reference/glossary.md#term-state_db) / [ASIC_DB](../../reference/glossary.md#term-asic_db) / [COUNTERS_DB](../../reference/glossary.md#term-counters_db) への書込は構造的に発生しない。

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| [APPL_DB](../../reference/glossary.md#term-appl_db) | なし | frrcfgd / bgpcfgd が ROUTE_MAP_SET を購読しないため AppDB への転送は発生しない |
| [STATE_DB](../../reference/glossary.md#term-state_db) | なし | ROUTE_MAP_SET の処理コードが存在せず、status 書き戻しも存在しない |
| [ASIC_DB](../../reference/glossary.md#term-asic_db) | なし | orchagent が ROUTE_MAP_SET を購読しないため [SAI](../../reference/glossary.md#term-sai) 経路を経由しない |
| [COUNTERS_DB](../../reference/glossary.md#term-counters_db) | なし | routing エントリのためのカウンタテーブルは存在しない |
| [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) | なし | カウンタ設定対象外 |
| [LOGLEVEL_DB](../../reference/glossary.md#term-loglevel_db) | なし | ROUTE_MAP_SET 処理コードが存在しないため |

### gNMI / NETCONF パスの副作用

gNMI / NETCONF 経由で YANG 検証が有効な場合、leafref 整合性エラーは `google.rpc.Status` として RPC レスポンスに返される。これは DB 書込ではなく RPC 応答レベルの副作用であり、[CONFIG_DB](../../reference/glossary.md#term-config_db) および他 DB への書込は発生しない。

<!-- evidence: frrcfgd.py table_handler_list L2293-2338 (ROUTE_MAP_SET 出現なし); bgpcfgd/ grep (出現なし); orchagent/ grep (出現なし) -->
<!-- /side-effects -->

<!-- pubsub -->
## CONFIG_DB 購読メカニズム (Phase G)

> **調査根拠**: `frrcfgd.py` 全文 grep (`ROUTE_MAP_SET` 出現なし); `bgpcfgd/` 全文 grep (出現なし); `orchagent/` 全文 grep (出現なし) (2026-05-19)
> 詳細証跡: `meta/_intermediate/cdb-flow/route-map-set-pubsub.md`

`ROUTE_MAP_SET` テーブルを **購読するデーモンは存在しない**。

| 購読候補 | 購読有無 | 根拠 |
|---------|---------|------|
| `frrcfgd` (`ExtConfigDBConnector`) | **なし** | `table_handler_list` (L2293-2338) に `ROUTE_MAP_SET` 出現なし。`ROUTE_MAP` のみ登録 |
| `bgpcfgd` (`RouteMapMgr` 等) | **なし** | `bgpcfgd/` 全文 grep で `ROUTE_MAP_SET` 出現なし |
| `orchagent` (各 Orch クラス) | **なし** | `orchagent/` 全文 grep で `ROUTE_MAP_SET` 出現なし |
| `syncd` | **なし** | [SAI](../../reference/glossary.md#term-sai) 経路を経由しない。route-map は FRR 側で完結 |

### 購読なしの設計理由

`ROUTE_MAP_SET` は YANG leafref 整合性検証のための**名前レジストリ**として設計されており、FRR や [SAI](../../reference/glossary.md#term-sai) への直接的な設定投入は意図されていない。実際の route-map 設定投入は `ROUTE_MAP|<name>|<seq>` テーブルへの書き込みによって `frrcfgd` が処理する。

### Redis keyspace イベントの扱い

CONFIG_DB への `ROUTE_MAP_SET` SET/DEL 操作は [Redis](../../reference/glossary.md#term-redis) keyspace 通知
(`__keyspace@4__:ROUTE_MAP_SET|*`) を発行するが、**どのデーモンも購読していない**ためイベントは消費されない。

```text
CONFIG_DB hset 'ROUTE_MAP_SET|ALLOW' ''
  ↓ Redis keyspace PUBLISH "__keyspace@4__:ROUTE_MAP_SET|ALLOW" "hset"
  ↓ (購読者なし → イベント消費されず)
```

`frrcfgd` が使用する `ExtConfigDBConnector` は `psubscribe __keyspace@4__:*` で全イベントを受信するが、`sub_msg_handler` がキー名を `table_handler_list` に照合し、登録のない `ROUTE_MAP_SET` はスキップされる (`frrcfgd.py:1527`）。

<!-- evidence: frrcfgd.py:2293-2338 table_handler_list (ROUTE_MAP_SET 出現なし); frrcfgd.py:1527 sub_msg_handler キーマッチング -->
<!-- /pubsub -->

<!-- platform -->
## プラットフォーム差分 (Phase H)

> 調査証跡: `meta/_intermediate/cdb-flow/route-map-set-platform.md`

### プラットフォーム非依存の設計

`ROUTE_MAP_SET` は YANG leafref 整合性検証のための**純粋な名前レジストリ**であり、SAI API・[ASIC](../../reference/glossary.md#term-asic) Capability・プラットフォーム固有ビルドテンプレートのいずれにも依存しない。

| 観点 | 状況 |
|------|------|
| j2 テンプレートによるビルド時注入 | **なし**（`qos_config.j2` 等の全 j2 を grep しても `ROUTE_MAP_SET` 出現なし） |
| SAI 呼び出し | **なし**（`orchagent/` 全体 grep で出現なし。FRR 側で完結） |
| [ASIC](../../reference/glossary.md#term-asic) Capability チェック | **なし** |
| platform_config.json / device profile 注入 | **なし** |
| multi-[ASIC](../../reference/glossary.md#term-asic) / [VOQ](../../reference/glossary.md#term-voq) chassis 分岐 | **なし** |

### 結論

どのプラットフォームでも `ROUTE_MAP_SET` の動作は同一である。ビルド時の自動生成も行われず、エントリの投入は `sonic-db-cli CONFIG_DB hset 'ROUTE_MAP_SET|<name>' ''` による手動操作、または YANG-aware 設定ツール (`config load` 等) 経由のみとなる。

<!-- /platform -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-route-map`](../yang/sonic-route-map.md)
- 関連テーブル: [`ROUTE_MAP`](./route-map.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-route-map.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-route-map.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `ROUTE_MAP_SET|<name>` (例: `ROUTE_MAP_SET|ALLOW`)。
- フィールドは key のみ。値なし。

### よくある誤設定

- ROUTE_MAP_SET エントリだけを作成し ROUTE_MAP エントリを作成しない場合、FRR に route-map は生成されない。実体は `ROUTE_MAP|<name>|<seq>` テーブルにある。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'ROUTE_MAP_SET|*'
sonic-db-cli CONFIG_DB keys 'ROUTE_MAP|*'
vtysh -c 'show route-map'
```
<!-- /ops-hint -->

<!-- glossary-links-injected: b86bd80f1174 -->
