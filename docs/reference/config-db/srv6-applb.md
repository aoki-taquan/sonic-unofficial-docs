---
title: "APPL_DB SRV6テーブル (SRV6_MY_SID_TABLE / SRV6_SID_LIST_TABLE)"
description: "fpmsyncd が FRR から書き込む APPL_DB の SRV6_MY_SID_TABLE・SRV6_SID_LIST_TABLE スキーマ詳解。Srv6Orch が消費してSAIへ転送する。"
area: reference
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: fpmsyncd/routesync.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/srv6orch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: main
related:
  config_db:
    - SRV6_MY_SIDS
    - SRV6_MY_LOCATORS
    - VRF
  appl_db:
    - SRV6_MY_SID_TABLE
    - SRV6_SID_LIST_TABLE
hard: 0
---

# APPL_DB SRV6 テーブル

## 概要

SONiC の SRv6 制御面は 3 層構造をとる。

1. **CONFIG_DB** (`SRV6_MY_SIDS` / `SRV6_MY_LOCATORS`) — ユーザー設定の起点
2. **APPL_DB** (`SRV6_MY_SID_TABLE` / `SRV6_SID_LIST_TABLE`) — FRR → SAI のパイプライン中継点
3. **ASIC_DB** — SAI が書き込むハードウェア状態

本ページは **APPL_DB 側の 2 テーブル**を解説する。
これらは `fpmsyncd` が FRR の netlink メッセージを受け取って書き込み、
`Srv6Orch`（`sonic-swss/orchagent/srv6orch.cpp`）が消費して SAI オブジェクトを作成する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  FRR["FRR (zebra/bgpd)"]
  FPM["fpmsyncd\n(routesync.cpp)"]
  APSID[("APPL_DB\nSRV6_MY_SID_TABLE")]
  APLIST[("APPL_DB\nSRV6_SID_LIST_TABLE")]
  ORCH["Srv6Orch"]
  SAI["SAI / ASIC\nMY_SID_ENTRY\nSRV6_SIDLIST"]
  FRR --> FPM --> APSID --> ORCH --> SAI
  FPM --> APLIST --> ORCH
```

!!! note "凡例"
    APPL_DB は FRR と ASIC の橋渡しテーブルであり、直接ユーザー設定するテーブルではない。
<!-- /cdb-mermaid -->

---

## SRV6_MY_SID_TABLE

### key 構造

```
SRV6_MY_SID_TABLE|<block_len>:<node_len>:<func_len>:<arg_len>:<sid_ipv6>
```

例: `SRV6_MY_SID_TABLE|32:16:16:0:fc00:0:1:64::`[^1]

key 内の各長さフィールドはロケータのビット長を示し、`Srv6Orch` がパースして
`sai_my_sid_entry_t` に詰める（`srv6orch.cpp:1453-1456`）。

### フィールド一覧

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `action` | string | SRv6 エンドポイント動作（下表参照）。**必須** |
| `vrf` | string | デカプセル後の VRF 名。行動によって必要・不要が変わる |
| `adj` | string | nexthop 隣接 IPv4/IPv6 アドレス。行動によって必要・不要が変わる |

<!-- defaults -->
### コード由来のデフォルト（Phase A 解析）

| フィールド | 実効デフォルト | コード根拠 |
|-----------|--------------|-----------|
| `action` | **省略不可** | 空文字列だと `sidEntryEndpointBehavior` が false を返し、orch がエントリ拒否（`srv6orch.cpp:1473-1477`） |
| `vrf` | **行動依存**（下記参照） | `mySidVrfRequired(end_behavior)` が真の行動（`end.dt*`/`udt*`）では省略不可。偽の行動では省略可。VRF 名 `"default"` は `gVirtualRouterId` に解決（`srv6orch.cpp:1484-1486`） |
| `adj` | **行動依存**（下記参照） | `mySidNextHopRequired(end_behavior)` が真の行動（`end.x`/`ua` 等）では省略不可。偽の行動では省略可（`srv6orch.cpp:1511-1547`） |

**NB-ZMQ 有効時の差異**:
`fpmsyncd` が NB-ZMQ モード（`nbZmqEnabled=true`）の場合、
`action`/`vrf`/`adj` を常に全フィールド push する（値が空文字列でも）。
これは ZMQ 側の冪等更新要件によるもの（`routesync.cpp:1169-1172`）。
通常モード（ZMQ 無効）では空文字列フィールドは省略される（`routesync.cpp:1174-1182`）。

**`vrf` フィールドの行動別要否**:

| 行動 | `vrf` 必須 | 備考 |
|------|-----------|------|
| `end`, `un`, `ua` | 不要 | SAI VRF 属性を設定しない |
| `end.x`, `end.dx4`, `end.dx6`, `udx4`, `udx6` | 不要 | nexthop (adj) を使用 |
| `end.dt4`, `end.dt6`, `end.dt46`, `udt4`, `udt6`, `udt46` | **必須** | VRF 未指定だとエラー |

**`adj` フィールドの行動別要否**:

| 行動 | `adj` 必須 | 備考 |
|------|-----------|------|
| `end`, `un`, `end.dt*`, `udt*` | 不要 | nexthop 不使用 |
| `end.x`, `end.dx4`, `end.dx6`, `ua`, `udx4`, `udx6` | **必須** | 隣接未解決の場合 pending エントリへ移動 |
<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

> 根拠: `srv6orch.cpp` `createUpdateMysidEntry()` L1511-1543、`updateNeighbor()` L1212-1341、`doTaskSidTable()` L1146-1186 全行精読。
> evidence: `meta/_intermediate/cdb-flow/srv6-applb-ordering.md`

APPL_DB `SRV6_MY_SID_TABLE` と `SRV6_SID_LIST_TABLE` はそれぞれ独立した Consumer (`m_mysidTable` / `m_sidTable`) で処理されるが、`adj` フィールドを持つ MySID エントリには隣接 (Neighbor) 解決の順序依存がある。

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `adj` 依存行動の MySID — Neighbor 先行推奨 | **先行推奨**（逆順は pending 自動解決） | `updateNeighbor()` ADD 通知で自動再処理 |
| 2 | Neighbor DEL 時、対応 MySID が SAI から自動削除 → pending 再登録 | **自動**（意図しない削除に注意） | MySID DEL → Neighbor DEL の順序を推奨 |
| 3 | `SRV6_SID_LIST_TABLE` vs `SRV6_MY_SID_TABLE` | 順序依存なし | — |

### adj 依存 MySID のペンディング挙動 (依存 #1)

`mySidNextHopRequired(end_behavior)` が true の行動 (`end.x`, `ua`, `udx4`, `udx6` 等) では
`adj` で指定した IP アドレスを `m_neighOrch->hasNextHop()` で解決する (`srv6orch.cpp:1524`)。
Neighbor が未確立の場合はエントリを `m_pendingSRv6MySIDEntries[nexthop]` に追加して処理を保留する (`srv6orch.cpp:1533-1534`)。
Neighbor ADD 通知が `updateNeighbor()` に届くと、対応する pending エントリが自動再処理されて SAI に登録される (`srv6orch.cpp:1224-1259`)。

### Neighbor DEL 時の自動ロールバック (依存 #2)

`updateNeighbor()` の DEL パス (`srv6orch.cpp:1266-1341`) は隣接 DELETE 通知を受け取ると、その adj を参照する全 MySID エントリを SAI から削除し、`m_pendingSRv6MySIDEntries` に再登録する。Neighbor が再確立された際に自動再 install される。意図しない MySID 削除を防ぐには MySID DEL → Neighbor DEL の順序を推奨する。

<!-- /ordering -->

### サポート action 値

`end_behavior_map`（`srv6orch.cpp:41-62`）に定義:

| action 文字列 | SAI 動作 |
|--------------|---------|
| `end` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_E` |
| `end.x` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_X` |
| `end.t` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_T` |
| `end.dx6` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DX6` |
| `end.dx4` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DX4` |
| `end.dt4` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DT4` |
| `end.dt6` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DT6` |
| `end.dt46` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DT46` |
| `un` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UN` |
| `ua` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UA` |
| `udx4` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDX4` |
| `udx6` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDX6` |
| `udt4` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDT4` |
| `udt6` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDT6` |
| `udt46` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDT46` |
| `end.b6.encaps` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_B6_ENCAPS` |
| `end.b6.encaps.red` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_B6_ENCAPS_RED` |
| `end.b6.insert` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_B6_INSERT` |
| `end.b6.insert.red` | `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_B6_INSERT_RED` |

`fpmsyncd` の `mySidAction2Str()`（`routesync.cpp:300-338`）は
FRR netlink action 値を上記文字列に変換してから APPL_DB へ書き込む。

---

## SRV6_SID_LIST_TABLE

### key 構造

```
SRV6_SID_LIST_TABLE|<sid_name>
```

`<sid_name>` は通常 VPN SID の IPv6 アドレス文字列として fpmsyncd が設定する
（`routesync.cpp:1408`）。

### フィールド一覧

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `path` | string (カンマ区切り IPv6 リスト) | SID リスト（セグメントリスト）。**必須** |
| `type` | enum | sidlist タイプ。省略可（デフォルト `encaps.red`） |

<!-- defaults -->
### コード由来のデフォルト（Phase A 解析）

| フィールド | 実効デフォルト | コード根拠 |
|-----------|--------------|-----------|
| `path` | **省略不可（実質）** | 省略または空文字列だと `segment_list.count=0` となり、orch が `segment list count is zero, skip` と記録して SAI 作成をスキップする（サイレント。`srv6orch.cpp:1052-1055`） |
| `type` | `encaps.red` | `sidlist_type_map` にキーが存在しない場合（フィールド未設定を含む）、`SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED` を使用（`srv6orch.cpp:1080-1083` の `SWSS_LOG_INFO("Use default sidlist type: ENCAPS_RED")`） |

**fpmsyncd は `type` フィールドを書かない**:
`Srv6SidListTableFieldValueTupleWrapper::fieldValueTupleVector()` は
`path` のみを設定し、`type` フィールドは push しない（`routesync.cpp:1189-1203`）。
FRR 経由で登録されるすべての SID リストは実質 `type=encaps.red` 相当になる。

テストや手動設定で `type` を明示指定した場合は以下の値が有効:
`insert`, `insert.red`, `encaps`, `encaps.red`（`srv6orch.cpp:73-79`）。
<!-- /defaults -->

---

## 設定例

### SRV6_MY_SID_TABLE エントリ（`end.dt46` 行動）

```json
{
    "SRV6_MY_SID_TABLE": {
        "32:16:16:0:fc00:0:1:64::": {
            "action": "end.dt46",
            "vrf": "VrfDt46"
        }
    }
}
```

### SRV6_SID_LIST_TABLE エントリ

```json
{
    "SRV6_SID_LIST_TABLE": {
        "fc00:0:2:1::": {
            "path": "fc00:0:2:1::"
        }
    }
}
```

`type` フィールドを省略すると Orch が `encaps.red` として処理する。

---

## 関連テーブル

- `SRV6_MY_SIDS` (CONFIG_DB) — ユーザー設定。bgpcfgd / fpmsyncd 経由で本テーブルへ反映
- `SRV6_MY_LOCATORS` (CONFIG_DB) — ロケータ定義
- `VRF` (CONFIG_DB) — `vrf` フィールドで参照する VRF エントリ

[^1]: `sonic-swss/tests/test_srv6.py:837` より実例。
