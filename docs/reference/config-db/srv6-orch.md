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

<!-- failure -->
## 失敗挙動・エラーハンドリング

> 根拠: `srv6orch.cpp` 全体の SWSS_LOG_ERROR / task_process_status 精読。
> evidence: `meta/_intermediate/cdb-flow/srv6-failure.md`

### SRV6_SID_LIST_TABLE の失敗ケース

| 条件 | ログ / 挙動 | task_status |
|------|------------|-------------|
| `path` が空（セグメント 0 件） | `SWSS_LOG_ERROR("segment list count is zero, skip")` → SAI 未呼び出しで `return true` | `task_success`（SAI 登録なし） |
| SAI `create_srv6_sidlist` 失敗 | `SWSS_LOG_ERROR("Failed to create srv6 sidlist object, rv %d")` | `task_failed` |
| SAI `set_srv6_sidlist_attribute` 失敗 | `SWSS_LOG_ERROR("Failed to set srv6 sidlist object with new segments, rv %d")` | `task_failed` |
| DEL: 存在しない `seg_name` | `SWSS_LOG_ERROR("segment name %s doesn't exist")` | `task_failed` |
| DEL: nexthop 参照中（refcount > 0） | `SWSS_LOG_NOTICE("referenced by other nexthops: count %zu, not deleting")` | `task_need_retry`（再キュー） |
| DEL: SAI `remove_srv6_sidlist` 失敗 | `SWSS_LOG_ERROR("Failed to delete SRV6 sidlist object for %s")` | `task_failed` |

### SRV6_MY_SID_TABLE の失敗ケース

| 条件 | ログ / 挙動 | 備考 |
|------|------------|------|
| 不正な `action` 値 | `SWSS_LOG_ERROR("Invalid my_sid action %s")` → `return false` | エントリは SAI 未登録 |
| VRF が CONFIG_DB に存在しない（DT 系） | `SWSS_LOG_ERROR("VRF %s doesn't exist in DB")` → `return false` | VRF を先に作成する必要あり |
| VRF が DB に存在するが SAI OID が null | `SWSS_LOG_ERROR("VRF object not created for DT VRF %s")` → `return false` | VRF Orch の初期化待ち |
| ECMP adjacency（`adj` にカンマ区切り複数指定） | `SWSS_LOG_ERROR("ECMP adjacency not yet supported")` → `return false` | 現行実装では単一 adj のみ対応 |
| `adj` が NeighOrch に未解決 | `m_pendingSRv6MySIDEntries` に保留 → `return false` | neighbor ADD で自動再インストール |
| IPinIP トンネル作成失敗（`un`/`udt46`） | `SWSS_LOG_ERROR("Failed to create MySID IPinIP tunnel: %d")` → ロールバック後 `return false` | tunnel term entry 失敗時も `removeMySidIpInIpTunnel()` を呼び部分ロールバック |
| ロケータが CONFIG_DB に存在しない | `SWSS_LOG_ERROR("Failed to get the SRv6 locator %s - not present in the CONFIG_DB")` | IPinIP tunnel DSCP 解決不可 |
| 不正な `decap_dscp_mode` 文字列 | `SWSS_LOG_ERROR("Invalid MySID %s DSCP mode: %s")` → キャッシュ未登録で早期 return | CONFIG_DB `SRV6_MY_SIDS` 側の設定ミス |
| SAI `create_my_sid_entry` 失敗 | `SWSS_LOG_ERROR("Failed to create my_sid entry %s, rv %d")` → `return false` | SAI / プラットフォーム起因エラー |
| SAI カウンタ作成失敗 | `SWSS_LOG_ERROR("Failed to create SAI counter for SRv6 MySID entry")` → `return false` | SID エントリ全体の作成を中断 |
| DEL: エントリが存在しない | `SWSS_LOG_ERROR("My_sid_entry doesn't exist for %s")` → `return false` | 二重削除防止 |

**Neighbor pending 機構の詳細**:

1. `adj` に指定された nexthop が NeighOrch に未解決の場合、エントリを `m_pendingSRv6MySIDEntries` に保留する（`srv6orch.cpp:1532-1542`）。
2. NeighOrch から neighbor ADD 通知が届いた時点で `updateNeighbor()` が `createUpdateMysidEntry()` を再呼び出しする（`srv6orch.cpp:1236-1248`）。
3. 再インストールも失敗した場合はエントリを pending に残したまま `continue`（ループ継続）。
4. neighbor DELETE 通知時は、インストール済み SID を ASIC から削除して pending に戻す（`srv6orch.cpp:1197-1210`）。

### PIC_CONTEXT_TABLE の失敗ケース

| 条件 | ログ / 挙動 | task_status |
|------|------------|-------------|
| SET: 既存エントリへの上書き試行 | `SWSS_LOG_ERROR("update is not allowed for pic context table")` | `task_duplicated`（PIC は不変） |
| `nexthop` と `vpn_sid` の件数不一致 | `SWSS_LOG_ERROR("inconsistent number of endpoints(%zu) and vpn sids(%zu)")` | `task_failed`（再試行なし） |
| VPN 作成失敗（P2P トンネル未確立等） | `SWSS_LOG_ERROR("Failed to create SRv6 VPNs for context id %s")` | `task_need_retry` |
| DEL: `ref_count` > 0（routeorch 参照中） | `addToRetry()` でリトライキューへ保留 | `task_need_retry`（ref 解放後に自動再実行） |
| DEL: VPN 削除失敗 | `SWSS_LOG_ERROR("Failed to delete SRv6 VPNs for context id %s")` | `task_need_retry` |

**`task_process_status` の doTask() マッピング**（`srv6orch.cpp:2352-2394`）:

- `task_need_retry` → イテレータを進めて次のイベントループで再処理（エントリは m_toSync に残留）
- `task_failed` / `task_success` / `task_duplicated` / `task_ignore` → m_toSync から削除（失敗はログのみ）

### SAI エラー伝播パターン

`sai_srv6_api->*` の戻り値（`sai_status_t`）を直接チェックし、`SAI_STATUS_SUCCESS` 以外は
`SWSS_LOG_ERROR` に `rv %d` 形式で SAI ステータスコードを記録して `return false` を返す。
複合オブジェクト（IPinIP トンネル + tunnel term entry）の途中失敗時のロールバックは
`createMySidIpInIpTunnelTermEntry` 失敗時のみ実装されており（`srv6orch.cpp:1564`）、
それ以外のケースでは作成済み SAI オブジェクトの自動クリーンアップは行われない。
<!-- /failure -->

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
