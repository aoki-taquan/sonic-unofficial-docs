---
title: Srv6Orch — APP_DB SRV6 テーブル
description: "Srv6Orch が消費する APP_DB テーブル（SRV6_SID_LIST_TABLE / SRV6_MY_SID_TABLE / PIC_CONTEXT_TABLE）のフィールド・デフォルト・動作詳解。"
area: reference
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/srv6orch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/srv6orch.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: master
related:
  config_db:
    - SRV6_MY_SIDS
    - SRV6_MY_LOCATORS
    - VRF
  yang:
    - sonic-srv6
hard: 0
---

# Srv6Orch — APP_DB SRV6 テーブル

## 概要

`Srv6Orch`（`orchagent/srv6orch.cpp`）は SRv6 のデータプレーン制御を担う Orchestration Agent であり、
以下の 3 つの APP_DB テーブルを購読して SAI 呼び出しを実行する[^1]。

| テーブル名 (APP_DB) | 役割 |
|--------------------|------|
| `SRV6_SID_LIST_TABLE` | SRv6 セグメントリスト（SID リスト）の管理 |
| `SRV6_MY_SID_TABLE` | ローカル SRv6 SID エントリ（My SID）の管理 |
| `PIC_CONTEXT_TABLE` | SRv6 VPN PIC コンテキスト（prefix aggregation ID）の管理 |

なお、CONFIG_DB 側の `SRV6_MY_SIDS` / `SRV6_MY_LOCATORS` は bgpcfgd の `SRv6Mgr` が管理し、
APP_DB 経由または FRR 経由で Srv6Orch へ伝達される。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB1[("CONFIG_DB<br/>SRV6_MY_SIDS")]
  CDB2[("CONFIG_DB<br/>SRV6_MY_LOCATORS")]
  BGP["bgpcfgd<br/>(SRv6Mgr)"]
  FRR["FRR (zebra/bgpd)"]
  APP1[("APP_DB<br/>SRV6_SID_LIST_TABLE")]
  APP2[("APP_DB<br/>SRV6_MY_SID_TABLE")]
  APP3[("APP_DB<br/>PIC_CONTEXT_TABLE")]
  ORCH["Srv6Orch"]
  SAI["SAI / ASIC"]
  CDB1 --> BGP --> FRR
  CDB2 --> BGP
  FRR --> APP1
  FRR --> APP2
  APP1 --> ORCH
  APP2 --> ORCH
  APP3 --> ORCH
  ORCH --> SAI
```

!!! note "凡例"
    APP_DB テーブルへの書き込みは主に `fpmsyncd` 経由の FRR から行われる。
    `PIC_CONTEXT_TABLE` は ECMP 経路制御コンポーネントが直接書き込む。
<!-- /cdb-mermaid -->

<!-- pubsub -->
## 通信メカニズム（Phase G 解析）

> 根拠: `routesync.cpp` 155-164, 1389, 1424, 1562, 1667, 3389, 3441 / `orchdaemon.cpp` 312-324 / `srv6orch.cpp` 98-140, 2352-2386 / `srv6orch.h` 238-242 / `managers_srv6.py` 14-133 の全行精読。
> evidence: `meta/_intermediate/cdb-flow/srv6-pubsub.md`

### 全体データフロー

SRv6 の設定は CONFIG_DB から SAI まで以下の **非同期パイプライン** を通じて伝達される。
Redis の `ProducerStateTable` / `ConsumerStateTable` は APP_DB 区間のみで使用され、
他の区間は vtysh CLI または FPM TCP ソケットで繋がれる。

```
CONFIG_DB (SRV6_MY_SIDS / SRV6_MY_LOCATORS)
  ↓ Redis keyspace notification (dbId=4)
bgpcfgd — SRv6Mgr (managers_srv6.py)
  ↓ vtysh cfg_mgr.push_list() (TCP, 非 Redis)
FRR zebra / bgpd
  ↓ FPM TCP (port 2620, netlink エンコード, 非 Redis)
fpmsyncd — RouteSync (routesync.cpp)
  ↓ ProducerStateTable + RedisPipeline → APP_DB
    SRV6_SID_LIST_TABLE / SRV6_MY_SID_TABLE / PIC_CONTEXT_TABLE
  ↓ ConsumerStateTable (TableConnector)
Srv6Orch (srv6orch.cpp)
  ↓ SAI C++ API
ASIC
```

### CONFIG_DB → bgpcfgd (SRv6Mgr)

`bgpcfgd` の `SRv6Mgr` は `Manager` 基底クラスを継承し、
`directory.subscribe()` が内部で CONFIG_DB (dbId=4) の Redis **keyspace notification**
(`PSUBSCRIBE __keyspace@4__:SRV6_MY_SIDS|*` 等) を購読する。

| CONFIG_DB テーブル | コールバック | 処理内容 |
|-------------------|-------------|---------|
| `SRV6_MY_LOCATORS` | `locators_set_handler()` | ロケータ情報をキャッシュし `cfg_mgr.push_list(["segment-routing","srv6","locators",...])` |
| `SRV6_MY_SIDS` | `sids_set_handler()` | ロケータ依存解決後に `cfg_mgr.push_list(["segment-routing","srv6","static-sids",...])` |

- `SRV6_MY_SIDS` エントリは参照するロケータ名 (`SRV6_MY_LOCATORS`) が未到達の場合、
  `directory.subscribe()` でロケータ到着を待ちペンディングする（`managers_srv6.py:62-68`）。
- `cfg_mgr.push_list()` は vtysh TCP ソケット経由で FRR bgpd へコマンドを送信する。
  Redis channel は介在しない。

### fpmsyncd → APP_DB (ProducerStateTable)

`RouteSync` クラス (`routesync.cpp`) が FPM インタフェース（TCP port 2620）経由で
FRR zebra からのネットリンクメッセージを受信し、APP_DB に `ProducerStateTable` で書き込む。

```cpp
// routesync.cpp:163-164, 159
m_srv6MySidTable(pipeline, APP_SRV6_MY_SID_TABLE_NAME, true),  // "SRV6_MY_SID_TABLE"
m_srv6SidListTable(pipeline, APP_SRV6_SID_LIST_TABLE_NAME, true), // "SRV6_SID_LIST_TABLE"
m_pic_context_groupTable(pipeline, APP_PIC_CONTEXT_TABLE_NAME, true), // "PIC_CONTEXT_TABLE"
```

| APP_DB テーブル | 書き込み操作 | routesync.cpp 行 |
|----------------|------------|-----------------|
| `SRV6_SID_LIST_TABLE` | `m_srv6SidListTable.set()` / `.del()` | 1424 / 1389 |
| `SRV6_MY_SID_TABLE` | `m_srv6MySidTable.set()` / `.del()` | 1667 / 1562 |
| `PIC_CONTEXT_TABLE` | `m_pic_context_groupTable.set()` / `.del()` | 3441 / 3389 |

- `RedisPipeline` でバッチ書き込み。フラッシュ間隔は `gFlushTimeout` で制御。
- Route テーブルと異なり SRv6 テーブルは ZMQ バイパスなし（pipeline 直接書き込み）。

### APP_DB → Srv6Orch (ConsumerStateTable)

`orchdaemon.cpp:312-324` で `TableConnector` を 4 テーブル分設定し、
`Orch(tables)` コンストラクタへ渡すことで `ConsumerStateTable` + `Executor` が自動生成される。

| テーブル | DB | channel (Redis key pattern) |
|---------|----|-----------------------------|
| `SRV6_SID_LIST_TABLE` | APP_DB (dbId=0) | `_QUEUEEVENTS` keyspace 通知 |
| `SRV6_MY_SID_TABLE` | APP_DB (dbId=0) | 同上 |
| `PIC_CONTEXT_TABLE` | APP_DB (dbId=0) | 同上 |
| `SRV6_MY_SIDS` | CONFIG_DB (dbId=4) | 同上 |

`Srv6Orch::doTask(Consumer &consumer)` (`srv6orch.cpp:2352`) がテーブル名で分岐し、
各 `doTaskXxx()` ハンドラへディスパッチする。

```cpp
// srv6orch.cpp:2362-2386
if      (table_name == APP_SRV6_SID_LIST_TABLE_NAME)  doTaskSidTable(t);
else if (table_name == APP_SRV6_MY_SID_TABLE_NAME)    doTaskMySidTable(t);
else if (table_name == APP_PIC_CONTEXT_TABLE_NAME)     doTaskPicContextTable(t);
else if (table_name == CFG_SRV6_MY_SID_TABLE_NAME)    doTaskCfgMySidTable(t);
```

`SelectableTimer` ベースの `doTask()` (`srv6orch.cpp:286`) も存在し、
`PIC_CONTEXT_TABLE` の参照カウント待ちリトライキューを定期処理する。

### ProducerStateTable メンバ（書き込み専用）

`srv6orch.h:238-240` の以下メンバは SAI 処理結果を APP_DB へ書き戻す目的で宣言されている。
ConsumerStateTable としての購読とは別チャネルであり、二重登録ではない。

| メンバ | 書き込み先 |
|--------|-----------|
| `m_sidTable` | `SRV6_SID_LIST_TABLE` |
| `m_mysidTable` | `SRV6_MY_SID_TABLE` |
| `m_piccontextTable` | `PIC_CONTEXT_TABLE` |

### NotificationProducer / SubscriberStateTable 非使用確認

- `SRV6_MY_SIDS` / `SRV6_MY_LOCATORS` に対して orchagent が `SubscriberStateTable` を直接使う箇所はなし。
- `NotificationProducer` で SRv6 関連の通知を発行する箇所はソース全体になし。
- STATE_DB への書き戻しは Srv6Orch 自体が行わず、SAI/ASIC 層で完結する。
<!-- /pubsub -->

---

## SRV6_SID_LIST_TABLE

### key 構造

```text
SRV6_SID_LIST_TABLE|<seg_name>
```

- `<seg_name>`: セグメントリストの識別名（任意の文字列）

### フィールド一覧

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `path` | string (カンマ区切り IPv6 アドレスリスト) | **なし（実質必須）** | SRv6 SID リスト。カンマ区切り複数 IPv6 アドレス。省略時は空リストで SAI 呼び出しをスキップ |
| `type` | enum | `encaps.red` | SID リストタイプ。有効値: `insert` / `insert.red` / `encaps` / `encaps.red` |

<!-- defaults -->
### コード由来のデフォルト（Phase A 解析）

> 根拠: `srv6orch.cpp` 行 73-79, 1079-1089, 1151-1162 の全行精読。
> evidence: `meta/_intermediate/cdb-flow/srv6-orch-defaults.md`

| フィールド | YANG default | コード fallback | 実効デフォルト |
|-----------|-------------|----------------|--------------|
| `path` | N/A (APP_DB) | 省略時 count=0 → スキップ | **省略不可**（SAI 呼び出し不発） |
| `type` | N/A | `SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED` (`srv6orch.cpp:1083`) | `"encaps.red"` |

**`type` の fallback 挙動**:
`srv6orch.cpp:1080-1088` で `sidlist_type_map.find(sidlist_type) == sidlist_type_map.end()` の場合
（未指定または不正値を含む）、`SWSS_LOG_INFO("Use default sidlist type: ENCAPS_RED")` を出力し
`SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED` を使用する。これはハードコードされた唯一の code-level default。
<!-- /defaults -->

---

## SRV6_MY_SID_TABLE

### key 構造

```text
SRV6_MY_SID_TABLE|<block_len>:<node_len>:<func_len>:<args_len>:<sid_ipv6_addr>
```

- `<block_len>`: ロケータブロック長（ビット）
- `<node_len>`: ロケータノード長（ビット）
- `<func_len>`: ファンクション長（ビット）
- `<args_len>`: アーギュメント長（ビット）
- `<sid_ipv6_addr>`: SID を表す IPv6 アドレス（例: `fc00:0:1:1::`）

キー例: `32:16:16:0:fc00:0:1:1::`

### フィールド一覧

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `action` | enum | **なし（必須）** | SRv6 エンドポイント動作（下表参照）。省略または不正値はエラー |
| `vrf` | string | `""` (action 依存) | デカプセル VRF 名。`"default"` で global VRF。VRF 不要な action では無視 |
| `adj` | string (カンマ区切り) | `""` (action 依存) | L3 Adjacency（nexthop アドレス）。nexthop 不要な action では無視 |

#### action 有効値と VRF/nexthop 要否

| `action` 値 | SAI 動作 | VRF 必要 | Nexthop (adj) 必要 |
|-------------|---------|---------|------------------|
| `end` | PSP/USD endpoint | いいえ | いいえ |
| `end.x` | L3 cross-connect | いいえ | **はい** |
| `end.t` | Table lookup | **はい** | いいえ |
| `end.dx4` | IPv4 decap + cross-connect | いいえ | **はい** |
| `end.dx6` | IPv6 decap + cross-connect | いいえ | **はい** |
| `end.dt4` | IPv4 decap + VRF lookup | **はい** | いいえ |
| `end.dt6` | IPv6 decap + VRF lookup | **はい** | いいえ |
| `end.dt46` | IPv4/6 decap + VRF lookup | **はい** | いいえ |
| `end.b6.encaps` | B6 encaps | いいえ | **はい** |
| `end.b6.encaps.red` | B6 encaps reduced | いいえ | **はい** |
| `end.b6.insert` | B6 insert | いいえ | **はい** |
| `end.b6.insert.red` | B6 insert reduced | いいえ | **はい** |
| `un` | Micro-SID uN | いいえ | いいえ |
| `ua` | Micro-SID uA | いいえ | **はい** |
| `udx4` / `udx6` | uDX (Micro-SID) | いいえ | **はい** |
| `udt4` / `udt6` / `udt46` | uDT (Micro-SID) | **はい** | いいえ |

<!-- defaults -->
### コード由来のデフォルト（Phase A 解析）

> 根拠: `srv6orch.cpp` 行 41-71, 1384-1430, 2204-2248 の全行精読。
> evidence: `meta/_intermediate/cdb-flow/srv6-orch-defaults.md`

| フィールド | YANG default | コード fallback | 実効デフォルト |
|-----------|-------------|----------------|--------------|
| `action` | N/A (APP_DB) | 省略・不正値 → エラー return | **省略不可** |
| `vrf` | N/A | `""` → action 不要時は無視。必要 action で空 → VRF 解決失敗 | action 依存（`"default"` を推奨） |
| `adj` | N/A | `""` → action 不要時は無視。必要 action で空 → pending 状態 | action 依存 |

**`end_flavor` の自動設定**:
`end` / `end.x` / `end.t` は `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_PSP_AND_USD`、
`un` は `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_NONE`、
`ua` は `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_PSP_AND_USD` と
`end_flavor_map` (`srv6orch.cpp:64-71`) で固定される。
その他の action は `end_flavor` を `FLAVOR_NONE` 相当で扱う。

**`adj` のペンディング機構**:
nexthop が未解決時、`m_pendingSRv6MySIDEntries` に保留し (`srv6orch.cpp:1532-1542`)、
NeighOrch から neighbor 追加通知を受けた際に自動で再インストールを試みる。

**`un` / `udt46` の IPinIP トンネル自動生成**:
`mySidTunnelRequired()` (`srv6orch.cpp:1417-1429`) により、`un` / `udt46` で
`decap_dscp_mode` が CONFIG_DB (`SRV6_MY_SIDS`) に設定されている場合のみ
IPinIP トンネル (`SAI_TUNNEL_TYPE_IPINIP`) を自動生成する。
DSCP mode 未設定時はトンネルを生成しない (`boost::none` 判定)。
<!-- /defaults -->

---

## PIC_CONTEXT_TABLE

### key 構造

```text
PIC_CONTEXT_TABLE|<context_id>
```

- `<context_id>`: PIC コンテキスト識別子（任意の文字列）

### フィールド一覧

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `nexthop` | string (カンマ区切り IPv6 アドレスリスト) | `""` (空) | SRv6 VPN の対向エンドポイント IP アドレスリスト |
| `vpn_sid` | string (カンマ区切り IPv6 アドレスリスト) | `""` (空) | 各エンドポイントに対応する VPN SID リスト |

<!-- defaults -->
### コード由来のデフォルト（Phase A 解析）

> 根拠: `srv6orch.cpp` 行 2272-2343 の全行精読。
> evidence: `meta/_intermediate/cdb-flow/srv6-orch-defaults.md`

| フィールド | YANG default | コード fallback | 実効デフォルト |
|-----------|-------------|----------------|--------------|
| `nexthop` | N/A (APP_DB) | 省略時は空ベクタ | 空（整合性エラーなし） |
| `vpn_sid` | N/A | 省略時は空ベクタ | 空（整合性エラーなし） |

**整合性チェック**:
`pci.nexthops.size() != pci.sids.size()` の場合 (`srv6orch.cpp:2298-2303`)、
`SWSS_LOG_ERROR` を出力して `task_failed` を返す。
エントリ数が一致しない `nexthop` / `vpn_sid` の組み合わせは受け付けない。

**参照カウント管理**:
`PIC_CONTEXT_TABLE` エントリは `routeorch` から `increasePicContextIdRefCount()` / `decreasePicContextIdRefCount()`
で参照カウントが管理される。ref_count > 0 の間は DEL 操作をリトライキューに保留する。

**`prefix_agg_id` の自動採番**:
VPN ごとに内部識別子 `prefix_agg_id` を `getAggId()` で採番 (`srv6orch.cpp:1715-1741`)。
初期値 1 から単調増加し、使用中の ID をスキップ。uint32_t オーバーフロー時は 1 に折り返す。
<!-- /defaults -->

---

## Overlay RIF と IPinIP トンネルのデフォルト

MySID の `un` / `udt46` で IPinIP トンネルを使用する際、内部で自動生成される SAI オブジェクトに
以下のハードコード値が使用される（`srv6orch.cpp:486-548`）:

| 属性 | 値 | 根拠 |
|------|----|------|
| Overlay RIF MTU | `9100` (`OVERLAY_RIF_DEFAULT_MTU`) | `srv6orch.cpp:20` |
| Tunnel type | `SAI_TUNNEL_TYPE_IPINIP` | `srv6orch.cpp:515` |
| Peer mode | `SAI_TUNNEL_PEER_MODE_P2MP` | `srv6orch.cpp:527` |
| Decap TTL mode | `SAI_TUNNEL_TTL_MODE_PIPE_MODEL` | `srv6orch.cpp:535` |
| Decap DSCP mode | CONFIG_DB の `decap_dscp_mode` 値 | `srv6orch.cpp:530-532` |

---

## 設定例

### SRV6_SID_LIST_TABLE エントリ（via fpmsyncd）

```json
{
    "SRV6_SID_LIST_TABLE": {
        "seg1": {
            "path": "fc00:0:1::/48,fc00:0:2::/48",
            "type": "encaps.red"
        }
    }
}
```

### SRV6_MY_SID_TABLE エントリ（via fpmsyncd）

```json
{
    "SRV6_MY_SID_TABLE": {
        "32:16:16:0:fc00:0:1:1::": {
            "action": "udt46",
            "vrf": "Vrf_Customer1"
        },
        "32:16:16:0:fc00:0:1:2::": {
            "action": "un"
        }
    }
}
```

---

## 依存関係

- **SRV6_MY_SID_TABLE** の `vrf` フィールドに custom VRF を指定する場合は、
  VRF テーブルが先に存在している必要がある（`m_vrfOrch->isVRFexists()` チェック）。
- **SRV6_MY_SID_TABLE** の `adj` フィールドは NeighOrch が解決する。
  Neighbor 未解決時はエントリをペンディングし、neighbor ADD 通知で自動再試行。
- **SRV6_SID_LIST_TABLE** エントリは `SRV6_MY_SID_TABLE` の nexthop 作成時に参照される
  (`srv6_segment_id` の解決）。

## 関連テーブル

- `SRV6_MY_SIDS` (CONFIG_DB) — SRv6 SID の設定源
- `SRV6_MY_LOCATORS` (CONFIG_DB) — SRv6 ロケータ設定
- `VRF` (CONFIG_DB) — VRF 定義

[^1]: `sonic-swss/orchagent/srv6orch.cpp` (revision 4305596156d70e9797e8a881b3d19b46de0bce0d) より。
