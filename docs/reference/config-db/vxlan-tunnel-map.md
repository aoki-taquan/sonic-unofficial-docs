---
title: VXLAN_TUNNEL_MAP テーブル
description: "VXLAN_TUNNEL_MAP テーブル — VXLAN tunnel に対し、ローカル VLAN と VNI (VXLAN Network Identifier) のマッピングを与える。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-vxlan.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - VXLAN_TUNNEL_MAP
    - VXLAN_TUNNEL
    - VLAN
  cli:
    - config vxlan
  yang:
    - sonic-vxlan
---

# VXLAN_TUNNEL_MAP テーブル

## 概要

[VXLAN](../../reference/glossary.md#term-vxlan) tunnel に対し、ローカル [VLAN](../../reference/glossary.md#term-vlan) と VNI ([VXLAN](../../reference/glossary.md#term-vxlan) Network Identifier) のマッピングを与える[^1]。`orchagent` の `VxlanTunnelMapOrch` がこのテーブルを購読し、[SAI](../../reference/glossary.md#term-sai) tunnel-map (`SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VNI` / `SAI_TUNNEL_MAP_TYPE_VNI_TO_VLAN_ID`) のエントリを生成する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>VXLAN_TUNNEL_MAP")]
  DM["vxlanmgrd"]
  CDB --> DM
  APPDB[("APPL_DB<br/>APP_VXLAN_TUNNEL_MAP_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_tunnel_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
VXLAN_TUNNEL_MAP|<tunnel_name>|<map_name>
```

`<tunnel_name>` は `VXLAN_TUNNEL.name` への leafref、`<map_name>` はユーザ任意。

## フィールド一覧

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `name` (key) | leafref `VXLAN_TUNNEL.name` | ✅ | 親トンネル |
| `mapname` (key) | string | ✅ | マッピング名（任意ラベル） |
| `vlan` | string `Vlan<id>` (パターン) | ✅ | 対応 [VLAN](../../reference/glossary.md#term-vlan) |
| `vni` | `vnid_type` (uint32 0..2^24-1) | ✅ | VNI |

備考: `vlan` 本来は `VLAN.name` への leafref が望ましいが、libyang の back-link 問題により暫定的に文字列パターン化されている (`sonic-vxlan.yang` のコメント参照)。

## 購読者

- `orchagent` `VxlanTunnelMapOrch`: [SAI](../../reference/glossary.md#term-sai) tunnel-map エントリ生成
- [EVPN](../../reference/glossary.md#term-evpn) フローでは `VxlanMgr` がここから [VLAN](../../reference/glossary.md#term-vlan)-VNI を引き、type-2/3 経路と紐付ける

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `VXLAN_TUNNEL`、`VLAN`、`VLAN_INTERFACE`、`VNET`
- 関連 CLI: [`config vxlan`](../cli/config-vxlan.md) (`map add` / `map del`)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-vxlan`

<!-- value-behavior -->
## 値依存挙動マトリクス

| フィールド | 値 | 実挙動 |
|-----------|-----|--------|
| `vlan` | `Vlan<id>` 形式 | YANG pattern で検証。[SAI](../../reference/glossary.md#term-sai) tunnel-map に `SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VNI` / `_TO_VLAN_ID` エントリを生成 |
| `vlan` | `Vlan` プレフィクスなし | YANG pattern 違反で reject |
| `vlan` | 既にマップ済みの VLAN | `vxlanmgr` が `"Vlan %s already mapped. Map Create failed"` でエラーして破棄 (vxlanmgr.cpp) |
| `vni` | 有効な VNI | VLAN と VNI を紐付け。[EVPN](../../reference/glossary.md#term-evpn) type-2/3 経路と紐付く |
| `vni` | 既にマップ済みの VNI | `vxlanmgr` が重複エラーで破棄 |
| `vni` | `0` | 予約済み値。使用不可（`vnid_type` 型は 1 以上が実質有効）|

<!-- /value-behavior -->

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

<!-- evidence: meta/_intermediate/cdb-flow/vxlan-tunnel-map-defaults.md -->

| 挙動 | 実装動作 | コードロケーション |
|------|---------|------------------|
| mapping type | 常に `VNI_TO_VLAN_ID` (decap) + `VLAN_ID_TO_VNI` (encap) のペアを自動生成。[CONFIG_DB](../../reference/glossary.md#term-config_db) に型指定フィールドなし | `vxlanorch.cpp:759-760` |
| [VRF](../../reference/glossary.md#term-vrf) マッパー初期化 | VLAN MAP 追加時にトンネルが inactive ならば [VRF](../../reference/glossary.md#term-vrf) マッパー (`VIRTUAL_ROUTER_ID_TO_VNI` / `VNI_TO_VIRTUAL_ROUTER_ID`) も同時に先行生成 (over-provision) | `vxlanorch.cpp:2065-2072` |
| `vni` >= 16777215 | `SWSS_LOG_ERROR` + `return true` で永続破棄 (リトライなし)。YANG `vnid_type` 型との二重チェック | `vxlanorch.cpp:2037-2040` |
| L3VNI の場合 | `VRFOrch::isL3VniVlan()` が真の場合 SAI entry を生成せず `SAI_NULL_OBJECT_ID` を記録 (暗黙 no-op) | `vxlanorch.cpp:2101-2113` |
| VLAN 未存在 | `PortsOrch::getVlanByVlanId()` が失敗 → `return false` でリトライ待ち | `vxlanorch.cpp:2031-2035` |
| tunnel 未存在 | `TunnelOrch::isTunnelExists()` が失敗 → `return false` でリトライ待ち | `vxlanorch.cpp:2047-2051` |
| del_tnl_hw_pending | 親トンネルの HW 削除保留中は MAP 追加もブロック → `return false` でリトライ待ち | `vxlanorch.cpp:2053-2058` |

### 書込み順依存

- `VXLAN_TUNNEL` が未作成の状態で `VXLAN_TUNNEL_MAP` を書くとトンネル存在チェックで `false` 返却 → リトライ。トンネル登録後に自動再処理される。
- `VLAN` が未作成の状態で MAP を書くと VLAN チェックで `false` 返却 → 同様にリトライ。

### 既知 YANG-実装 discrepancy

- L3VNI 判定は `VRFOrch` の内部状態 (`isL3VniVlan()`) に依存。YANG / [CONFIG_DB](../../reference/glossary.md#term-config_db) に L3VNI を明示するフィールドはなく、同じ `vni` 値でも [VRF](../../reference/glossary.md#term-vrf) 登録状態により SAI entry が生成されるかどうかが変わる — **外部から観測不可能な silent 挙動差**。

<!-- /defaults -->

<!-- ordering -->
## 書込み順序依存 (Phase B)

<!-- evidence: meta/_intermediate/cdb-flow/vxlan-tunnel-map-ordering.md; sonic-swss/orchagent/vxlanorch.cpp -->

### 作成順序

| 順序 | テーブル | 理由 |
|------|---------|------|
| 1 | `VLAN\|<id>` | `VxlanTunnelMapOrch::addOperation()` が `gPortsOrch->getVlanByVlanId()` で VLAN の存在を確認。未作成なら `return false`（リトライ待ち）(vxlanorch.cpp:2030) |
| 2 | `VXLAN_TUNNEL\|<tunnel-name>` | `isTunnelExists()` チェック。TUNNEL 未登録なら `return false`（リトライ待ち）(vxlanorch.cpp:2047) |
| 3 | `VXLAN_TUNNEL_MAP\|<tunnel>\|<map>` | 初回エントリ受信時に `createTunnelHw()` が呼ばれ SAI トンネルオブジェクト（mapper → tunnel → tunnel-term）が一括生成される (vxlanorch.cpp:2063)。VXLAN_TUNNEL 単体では SAI HW は作成されない点に注意 |

複数の MAP エントリは VLAN・TUNNEL が揃っていれば順不同で書込み可能。

### SAI HW 作成の内部順序（参考）

`createTunnelHw()` 内部では以下の順で SAI オブジェクトを生成する:

1. `createMapperHw()` — `sai_tunnel_api->create_tunnel_map()`（encap/decap マッパー）
2. `create_tunnel()` — `sai_tunnel_api->create_tunnel()`（マッパー OID リストを参照）
3. `create_tunnel_termination()` — `sai_tunnel_api->create_tunnel_term_table_entry()`

### 削除順序（逆順）

```
VXLAN_EVPN_NVO 削除 → VXLAN_TUNNEL_MAP 全削除 → VXLAN_TUNNEL 削除 → VLAN 削除
```

`del_tnl_hw_pending` フラグが true の間は MAP 追加もブロックされる (vxlanorch.cpp:2057)。削除途中での再追加は避けること。

<!-- /ordering -->

<!-- failure -->
## 失敗・リトライ挙動 (Phase D)

<!-- evidence: meta/_intermediate/cdb-flow/vxlan-tunnel-map-failure.md; sonic-swss/orchagent/vxlanorch.cpp -->

### addOperation() 失敗分類

#### 永続破棄（return true）― リトライなし

| 条件 | ログメッセージ | コードロケーション |
|------|-------------|------------------|
| マップキーが既にキャッシュに存在 | `"Vxlan tunnel map '%s' already exist"` (SWSS_LOG_ERROR) | `vxlanorch.cpp:2025-2027` |
| `vni` >= 16777215 (`MAX_VNI_ID`) | `"Vxlan tunnel map vni id is too big: %d"` (SWSS_LOG_ERROR) | `vxlanorch.cpp:2037-2040` |

#### リトライ待ち（return false）― 依存オブジェクト未解決

| 条件 | ログメッセージ | コードロケーション |
|------|-------------|------------------|
| VLAN が PortsOrch に未登録 | `"Vxlan tunnel map vlan id doesn't exist: %d"` (SWSS_LOG_WARN) | `vxlanorch.cpp:2030-2033` |
| 親 VXLAN_TUNNEL が未存在 | `"Vxlan tunnel '%s' doesn't exist"` (SWSS_LOG_WARN) | `vxlanorch.cpp:2047-2050` |
| `del_tnl_hw_pending` フラグが立っている | `"Tunnel Mapper deletion is pending"` (SWSS_LOG_WARN) | `vxlanorch.cpp:2057-2060` |
| `createTunnelHw()` が失敗（SAI 内部エラー） | — | `vxlanorch.cpp:2069-2074` |

#### SAI 呼び出し失敗（runtime_error catch → return false）

| 操作 | SAI API | ログメッセージ | コードロケーション |
|------|---------|-------------|------------------|
| トンネルマップオブジェクト作成失敗 | `create_tunnel_map()` | `"Can't create tunnel map object"` (SWSS_LOG_ERROR)、`SAI_NULL_OBJECT_ID` 返却 | `vxlanorch.cpp:147-154` |
| トンネルマップエントリ作成失敗 | `create_tunnel_map_entry()` | `"Can't create a tunnel map entry object"` (SWSS_LOG_ERROR)、`SAI_NULL_OBJECT_ID` 返却 | `vxlanorch.cpp:215-221` |
| エントリ作成で例外送出 | — | `"Error adding tunnel map entry. Tunnel: %s. Entry: %s. Error: %s"` (SWSS_LOG_WARN)、`return false` | `vxlanorch.cpp:2113-2117` |
| SAI トンネルオブジェクト作成失敗 | `create_tunnel()` | `"Can't create a tunnel object"` (SWSS_LOG_ERROR)、`return false` | `vxlanorch.cpp:403-409` |
| SAI tunnel-term 作成失敗 | `create_tunnel_term_table_entry()` | `"Can't create a tunnel term table object"` (SWSS_LOG_ERROR)、`return false` | `vxlanorch.cpp:488-494` |

### delOperation() 失敗分類

#### 永続破棄（return true）― 警告のみ・処理継続

| 条件 | ログメッセージ | コードロケーション |
|------|-------------|------------------|
| 削除対象マップキーが存在しない | `"Vxlan tunnel map '%s' doesn't exist"` (SWSS_LOG_WARN) | `vxlanorch.cpp:2138-2141` |
| 削除時に VLAN が消えていた | `"Delete VLAN-VNI map.vlan id doesn't exist: %d"` (SWSS_LOG_ERROR) | `vxlanorch.cpp:2145-2148` |
| ブリッジポート取得失敗（マップ数ゼロ時） | `"Get port failed for source vtep %s"` (SWSS_LOG_ERROR) | `vxlanorch.cpp:2196-2197` |
| ブリッジポート削除失敗 | `"Remove Bridge port failed for source vtep = %s fdbcount = %d"` (SWSS_LOG_ERROR) | `vxlanorch.cpp:2202-2204` |

#### SAI 呼び出し失敗（runtime_error catch → return false）

| 操作 | SAI API | ログメッセージ | コードロケーション |
|------|---------|-------------|------------------|
| SAI マップエントリ削除失敗 | `remove_tunnel_map_entry()` | `"Can't delete a tunnel map entry object"` (SWSS_LOG_ERROR) | `vxlanorch.cpp:237-242` |
| 削除で例外送出 | — | `"Error removing tunnel map %s: %s"` (SWSS_LOG_ERROR)、`return false` | `vxlanorch.cpp:2158-2161` |

### del_tnl_hw_pending による連鎖ブロック

最後の MAP エントリ削除時（`vlan_vrf_vni_count == 0`）に DIP トンネルが残存している場合、
`del_tnl_hw_pending = true` が設定され（`vxlanorch.cpp:2215`）、以降の MAP 追加は
`"Tunnel Mapper deletion is pending"` で return false となる。
DIP トンネルが解放されて `del_tnl_hw_pending` が `false` に戻るまで MAP 追加は全てブロックされる。

### SAI 失敗後の状態不整合（既知リスク）

`create_tunnel_map_entry()` が `SAI_NULL_OBJECT_ID` を返した場合、`vxlan_tunnel_map_table_` には
`map_entry_id = SAI_NULL_OBJECT_ID` のままエントリが記録される（`vxlanorch.cpp:2108`）。
これは L3VNI の意図的 no-op と同じコードパスであるため、ログ上は正常に見えるが
HW にマッピング実体が存在しない状態となる。後続の `delOperation()` では
`remove_tunnel_map_entry(SAI_NULL_OBJECT_ID)` 呼び出し時に
`if (obj_id != SAI_NULL_OBJECT_ID)` ガードでスキップされるため SAI エラーにはならない
（`vxlanorch.cpp:232-235`）。ただしパケット転送には影響する。

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

<!-- evidence: meta/_intermediate/cdb-flow/vxlan-tunnel-map-constants.md; sonic-swss/orchagent/vxlanorch.h; sonic-swss/orchagent/vxlanorch.cpp -->

### vxlanorch.h — 数値マクロ

| 定数 | 値 | 用途 | コードロケーション |
|-----|-----|------|-----------------|
| `MAX_VNI_ID` | `16777215` (= 2^24 − 1) | VNI 上限チェック。`vni_id >= MAX_VNI_ID` の場合 `SWSS_LOG_ERROR` + 永続破棄 (return true)。注: `>=` なので VNI=16777215 も reject。実質有効範囲は 1–16777214 | `vxlanorch.h:48`, `vxlanorch.cpp:2037` |
| `MIN_VLAN_ID` | `1` | `vlan` 文字列の数字部分を `to_uint<sai_vlan_id_t>()` で変換する際の下限クランプ | `vxlanorch.h:45` |
| `MAX_VLAN_ID` | `4095` | 同上、上限クランプ。範囲外は例外 → SWSS_LOG_WARN + return false | `vxlanorch.h:46` |
| `DEFAULT_TUNNEL_ENCAP_TTL` | `255` | `create_tunnel()` の `encap_ttl` 引数省略時に適用される TTL 初期値 | `vxlanorch.h:49` |
| `TUNNEL_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` ms | トンネル統計 flex counter ポーリング間隔 (10 秒) | `vxlanorch.h:40` |

### vxlanorch.h — 文字列マクロ（ポート名プレフィクス）

| 定数 | 値 | 用途 | コードロケーション |
|-----|-----|------|-----------------|
| `TUNNEL_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"TUNNEL_STAT_COUNTER"` | flex_counter_manager へ渡すグループ名 | `vxlanorch.h:39` |
| `LOCAL_TUNNEL_PORT_PREFIX` | `"Port_SRC_VTEP_"` | 自ノード [VTEP](../../reference/glossary.md#term-vtep) 発トンネルポート名のプレフィクス | `vxlanorch.h:41` |
| `EVPN_TUNNEL_PORT_PREFIX` | `"Port_EVPN_"` | [EVPN](../../reference/glossary.md#term-evpn) remote [VTEP](../../reference/glossary.md#term-vtep) トンネルポート名のプレフィクス | `vxlanorch.h:42` |
| `EVPN_TUNNEL_NAME_PREFIX` | `"EVPN_"` | EVPN 動的 DIP トンネル名のプレフィクス | `vxlanorch.h:43` |

### MAP_T 列挙 → SAI マッピングテーブル

`vxlanTunnelMap` / `vxlanTunnelMapKeyVal` テーブル (`vxlanorch.cpp:37-70`) より全 6 エントリを抽出。`VXLAN_TUNNEL_MAP` SET 時は `VNI_TO_VLAN_ID` と `VLAN_ID_TO_VNI` のペアが常に生成される。

| MAP_T 値 | SAI マップ種別 | SAI エントリ key attr | SAI エントリ value attr |
|---------|-------------|---------------------|-----------------------|
| `VNI_TO_VLAN_ID` | `SAI_TUNNEL_MAP_TYPE_VNI_TO_VLAN_ID` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VNI_ID_KEY` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VLAN_ID_VALUE` |
| `VLAN_ID_TO_VNI` | `SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VNI` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VLAN_ID_KEY` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VNI_ID_VALUE` |
| `VRID_TO_VNI` | `SAI_TUNNEL_MAP_TYPE_VIRTUAL_ROUTER_ID_TO_VNI` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VIRTUAL_ROUTER_ID_KEY` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VNI_ID_VALUE` |
| `VNI_TO_VRID` | `SAI_TUNNEL_MAP_TYPE_VNI_TO_VIRTUAL_ROUTER_ID` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VNI_ID_KEY` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VIRTUAL_ROUTER_ID_VALUE` |
| `BRIDGE_TO_VNI` | `SAI_TUNNEL_MAP_TYPE_BRIDGE_IF_TO_VNI` | `SAI_TUNNEL_MAP_ENTRY_ATTR_BRIDGE_ID_KEY` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VNI_ID_VALUE` |
| `VNI_TO_BRIDGE` | `SAI_TUNNEL_MAP_TYPE_VNI_TO_BRIDGE_IF` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VNI_ID_KEY` | `SAI_TUNNEL_MAP_ENTRY_ATTR_BRIDGE_ID_VALUE` |

### tunnel_map_use_t — マッパー共有モード

`VXLAN_TUNNEL_MAP` の初回 SET 時に `createTunnelHw()` へ渡されるモードは常に `TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP`。このモードでは encap 用 (`VLAN_ID_TO_VNI`) と decap 用 (`VNI_TO_VLAN_ID`) のマッパーが独立した SAI オブジェクトとして生成される。

| 列挙値 | 使用箇所 |
|--------|---------|
| `TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP` | CLI / NVO [VTEP](../../reference/glossary.md#term-vtep) 用（**VXLAN_TUNNEL_MAP 追加時**） (`vxlanorch.cpp:2070`) |
| `TUNNEL_MAP_USE_COMMON_ENCAP_DECAP` | EVPN remote DIP トンネル生成時 (`vxlanorch.cpp:1169`) |
| `TUNNEL_MAP_USE_COMMON_DECAP_DEDICATED_ENCAP` | 混在モード（内部利用） |
| `TUNNEL_MAP_USE_DECAP_ONLY` | decap 専用（内部利用） |

<!-- /constants -->

<!-- side-effects -->
## 副作用・連動更新 (Phase F)

<!-- evidence: meta/_intermediate/cdb-flow/vxlan-tunnel-map-side.md; sonic-swss/cfgmgr/vxlanmgr.cpp; sonic-swss/orchagent/vxlanorch.cpp -->

`VXLAN_TUNNEL_MAP` への SET / DEL は CONFIG_DB 外の複数のコンポーネントに副作用を及ぼす。

### SET 時

| 副作用 | 対象 | 詳細 | evidence |
|--------|------|------|---------|
| カーネル [VXLAN](../../reference/glossary.md#term-vxlan) net device 作成 | Linux kernel | `<tunnel>-<vlan_id>` デバイスを `ip link add ... type vxlan` で作成し、`Bridge` に参加させて UP | `vxlanmgr.cpp:1003-1051` |
| `STATE_NEIGH_SUPPRESS_VLAN_TABLE` 書込み | [STATE_DB](../../reference/glossary.md#term-state_db) | `Vlan<id>` key に `netdev=<tunnel>-<vlan_id>` を書込み。[vlanmgrd](../../reference/glossary.md#term-vlanmgrd) が [ARP](../../reference/glossary.md#term-arp)/ND Suppression フラグ更新のためにこのエントリを参照する | `vxlanmgr.cpp:613-618` |
| APP_DB エントリ書込み | APP_DB | `APP_VXLAN_TUNNEL_MAP_TABLE` にエントリを転記し、[orchagent](../../reference/glossary.md#term-orchagent) が SAI 操作を実行するトリガとなる | `vxlanmgr.cpp:592` |
| SAI トンネルオブジェクト一括生成（初回のみ） | SAI / HW | 初回 MAP エントリ受信時に `createTunnelHw()` が呼ばれ、encap/decap マッパー・SAI トンネル・トンネル終端エントリが一括生成される。**2 枚目以降の MAP エントリ追加では SAI トンネル再作成は発生しない** | `vxlanorch.cpp:2063-2087` |
| [orchagent](../../reference/glossary.md#term-orchagent) 内部マップ更新 | orchagent memory | `vxlan_vni_vlan_map_table_[vni] = vlan_id` が更新され、EVPN 動的 DIP トンネル処理時に参照される | `vxlanorch.cpp:2120`, `vxlanorch.h:354-357` |

### DEL 時

| 副作用 | 対象 | 詳細 | evidence |
|--------|------|------|---------|
| カーネル VXLAN net device 削除 | Linux kernel | `ip link set dev <tunnel>-<vlan_id> down` → `ip link del dev <tunnel>-<vlan_id>` を実行 | `vxlanmgr.cpp:655-656`, `vxlanmgr.cpp:1065-1069` |
| `STATE_NEIGH_SUPPRESS_VLAN_TABLE` 削除 | [STATE_DB](../../reference/glossary.md#term-state_db) | `Vlan<id>` エントリを削除し、[ARP](../../reference/glossary.md#term-arp)/ND suppression 設定が解除される | `vxlanmgr.cpp:668` |
| 最終エントリ削除時: SAI トンネルオブジェクト削除 | SAI / HW | `vlan_vrf_vni_count == 0` で `deleteTunnelHw()` が呼ばれ SAI マッパー・トンネル・終端が削除される。DIP トンネルが残存する場合は `del_tnl_hw_pending = true` で遅延削除される | `vxlanorch.cpp:2180-2226` |
| EVPN MAC/IP ルート連動削除 | [FDB](../../reference/glossary.md#term-fdb) / ルートテーブル | VXLAN MAP 削除に伴い、対応する EVPN type-2/3 経路と紐付いた MAC/IP エントリが自動削除される | `vxlanorch.cpp` (EVPN ルート管理経路) |

<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

<!-- evidence: meta/_intermediate/cdb-flow/vxlan-tunnel-map-pubsub.md; sonic-swss/cfgmgr/vxlanmgrd.cpp; sonic-swss/cfgmgr/vxlanmgr.cpp; sonic-swss/orchagent/vxlanorch.cpp -->

`VXLAN_TUNNEL_MAP` テーブルは **[vxlanmgrd](../../reference/glossary.md#term-vxlanmgrd) → [APPL_DB](../../reference/glossary.md#term-appl_db) → orchagent** の 2 段階パイプラインで処理される。

### 購読チャンネル一覧

| 購読者 | DB | テーブル名 | API 種別 | ハンドラ |
|--------|-----|----------|---------|---------|
| `vxlanmgrd` (VxlanMgr) | CONFIG_DB (dbId=4) | `VXLAN_TUNNEL_MAP` | [ConsumerStateTable](../../reference/glossary.md#term-consumerstatetable) (Orch 継承) | `doVxlanTunnelMapCreateTask` / `doVxlanTunnelMapDeleteTask` |
| orchagent (VxlanTunnelMapOrch) | [APPL_DB](../../reference/glossary.md#term-appl_db) (dbId=0) | `APP_VXLAN_TUNNEL_MAP_TABLE` | [ConsumerStateTable](../../reference/glossary.md#term-consumerstatetable) (Orch2 継承) | `VxlanTunnelMapOrch::addOperation` / `delOperation` |

### 第 1 段: CONFIG_DB → vxlanmgrd

`vxlanmgrd.cpp:46-51` で `CFG_VXLAN_TUNNEL_MAP_TABLE_NAME` を含むテーブルリストを `VxlanMgr` に渡す。メインループ (`vxlanmgrd.cpp:88-116`) は `s.select(&sel, SELECT_TIMEOUT=1000ms)` でイベントを待機し、検出時に `VxlanMgr::doTask(Consumer&)` を呼び出す。

`doTask` でのルーティング (`vxlanmgr.cpp:235-238`):

```cpp
else if (table_name == CFG_VXLAN_TUNNEL_MAP_TABLE_NAME) {
    task_result = doVxlanTunnelMapCreateTask(t);   // SET_COMMAND
    // or
    task_result = doVxlanTunnelMapDeleteTask(t);   // DEL_COMMAND
}
```

### 第 2 段: APPL_DB ProducerStateTable → orchagent

`doVxlanTunnelMapCreateTask` が成功すると `addAppDBTunnelMapTable()` (`vxlanmgr.cpp:943`) で `m_appVxlanTunnelMapTable.set(...)` を呼び出し、`APP_VXLAN_TUNNEL_MAP_TABLE` に転記する。orchagent の `VxlanTunnelMapOrch` はこのテーブルを [ConsumerStateTable](../../reference/glossary.md#term-consumerstatetable) で購読し (`orchdaemon.cpp:352`)、`addOperation()` でハードウェアへの SAI 呼び出しを実行する。

### STATE_DB への副次書き込み

| 操作 | テーブル | キー | フィールド | コードロケーション |
|------|---------|------|----------|-----------------|
| SET 成功時 | `STATE_NEIGH_SUPPRESS_VLAN_TABLE` | `Vlan<id>` | `netdev=<tunnel>-<vlan_id>` | `vxlanmgr.cpp:618` |
| DEL 時 | `STATE_NEIGH_SUPPRESS_VLAN_TABLE` | `Vlan<id>` | (削除) | `vxlanmgr.cpp:668` |

[vlanmgrd](../../reference/glossary.md#term-vlanmgrd) がこの [STATE_DB](../../reference/glossary.md#term-state_db) エントリを参照して [ARP](../../reference/glossary.md#term-arp)/ND Suppression フラグを更新する。

### イベントフロー全体

```
CONFIG_DB HSET "VXLAN_TUNNEL_MAP|tunnel1|map1" vlan Vlan100 vni 1000
  ↓ Redis keyspace notification → vxlanmgrd ConsumerStateTable バッファ
s.select(1000ms) で検出 → VxlanMgr::doTask() → doVxlanTunnelMapCreateTask()
  ↓ createVxlanNetdevice(): ip link add ... type vxlan + bridge join
  ↓ m_stateNeighSuppressVlanTable.set("Vlan100", {netdev=tunnel1-100})
  ↓ m_appVxlanTunnelMapTable.set("tunnel1:map1", fvs)  ← APPL_DB 書込
APPL_DB 書込 → Redis Lists → orchagent VxlanTunnelMapOrch ConsumerStateTable
  ↓ addOperation(): VLAN / VXLAN_TUNNEL 存在確認
  ↓ createTunnelHw() (初回のみ: encap/decap mapper → tunnel → tunnel-term を一括 SAI 生成)
  ↓ sai_tunnel_api->create_tunnel_map_entry() で VNI↔VLAN マッピングを HW 登録
```

<!-- /pubsub -->

<!-- platform -->
## プラットフォーム差 (Phase H)

<!-- evidence: meta/_intermediate/cdb-flow/vxlan-tunnel-map-platform.md; sonic-swss/orchagent/vxlanorch.cpp -->

`VXLAN_TUNNEL_MAP` の SAI オブジェクト生成・削除パスは、`VxlanTunnelOrch` 初期化時に実行される SAI ケーパビリティクエリによって P2P / P2MP モードが決定され、[ASIC](../../reference/glossary.md#term-asic) 種別によって挙動が分岐する。

### SAI ケーパビリティクエリによるモード決定 (vxlanorch.cpp:1256-1274)

`VxlanTunnelOrch` コンストラクタ起動時に `sai_query_attribute_enum_values_capability()` で [ASIC](../../reference/glossary.md#term-asic) がサポートするトンネルピアモードを問い合わせる:

| 結果 | `is_dip_tunnel_supported` | 動作モード |
|------|--------------------------|-----------|
| SAI クエリ失敗（未対応ドライバ等） | `true`（fallback） | P2P モード（DIP トンネルあり） |
| `SAI_TUNNEL_PEER_MODE_P2P` が列挙に含まれる | `true` | P2P モード（DIP トンネルあり） |
| `SAI_TUNNEL_PEER_MODE_P2P` が列挙にない（P2MP のみ） | `false` | P2MP モード（DIP トンネルなし） |

CONFIG_DB の `VXLAN_TUNNEL_MAP` スキーマにこの差異を制御するフィールドはなく、**[ASIC](../../reference/glossary.md#term-asic) の SAI 実装次第で自動選択される**。

### MAP addOperation() でのプラットフォーム分岐

初回 MAP エントリ追加（SIP トンネルが未 active）時に分岐する (vxlanorch.cpp:2075-2086):

| ASIC モード | 動作 |
|------------|------|
| **P2MP** (`!isDipTunnelsSupported()`) | `addOperation()` 内で SIP トンネルポートとブリッジポートを即時生成。`gPortsOrch->addTunnel()` + `addBridgePort()` を呼ぶ |
| **P2P** (`isDipTunnelsSupported()`) | ブリッジポート生成をスキップ。EVPN `addTunnelUser()` が後から DIP トンネルごとにブリッジポートを生成する |

### MAP delOperation() でのプラットフォーム分岐

最後の MAP エントリ削除時（`vlan_vrf_vni_count == 0`）の SIP トンネル HW 削除 (vxlanorch.cpp:2191-2226):

| ASIC モード | 動作 |
|------------|------|
| **P2MP** (`!isDipTunnelsSupported()`) | リモート参照なし (`!isTunnelReferenced()`) を確認して即時にブリッジポート・トンネルポートを削除後、`deleteTunnelHw()` を実行 |
| **P2P** (`isDipTunnelsSupported()`) | DIP トンネルが残存している場合は `del_tnl_hw_pending = true` を設定して遅延削除。ログ: `"Postponing the SIP Tunnel HW deletion DIP Tunnel count = %d"` |

### SmartSwitch / DPU 差異

`vxlanorch.cpp` に [SmartSwitch](../../reference/glossary.md#term-smartswitch) [DPU](../../reference/glossary.md#term-dpu) 固有の分岐コードは存在しない。[DPU](../../reference/glossary.md#term-dpu) 側の VXLAN トンネル処理は別のオーバーレイスタックが担当する可能性があるが、現在の orchagent 実装では [NPU](../../reference/glossary.md#term-npu) 通常モードのみが対象。

### まとめ

| 差異ポイント | P2P（DIP サポートあり） | P2MP（DIP サポートなし） |
|---|---|---|
| SAI クエリ失敗時 | fallback で P2P | — |
| MAP 初回追加時ブリッジポート | スキップ（EVPN が後で管理） | addOperation() で即時生成 |
| MAP 最終削除時ブリッジポート | 遅延（DIP カウント 0 待ち） | 参照なければ即時削除 |
| `del_tnl_hw_pending` 設定 | DIP トンネル残存時 | リモート参照残存時 |
| [SmartSwitch](../../reference/glossary.md#term-smartswitch) [DPU](../../reference/glossary.md#term-dpu) | コード分岐なし | 同左 |

<!-- /platform -->

## 例外条件・特殊挙動 <!-- cdb-exceptions -->

<!-- evidence: sonic-swss/cfgmgr/vxlanmgr.cpp; sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vxlan.yang -->

- **`vlan` 必須 (YANG)**: `mandatory true`、`pattern 'Vlan([0-9]{1,3}|...)'` — パターン違反は YANG で reject される[^exc2]。
- **`vni` 必須 (YANG)**: `mandatory true`[^exc2]。
- **VLAN leafref 無効化 (既知制限)**: libyang の back-link 問題のため VLAN の `leafref` はコメントアウトされ、文字列パターンのみで検証される（`sonic-vlan.yang` との整合性チェックなし）[^exc2]。
- **VLAN 重複マッピング禁止**: 同じ `vlan` が既にマップされている場合 `SWSS_LOG_ERROR("Vlan %s already mapped. Map Create failed")` を記録して破棄[^exc1]。
- **VNI 重複マッピング禁止**: 同じ `vni` が既にマップされている場合も同様に破棄[^exc1]。
- **マップキー重複**: キャッシュに同名マップが存在する場合 `SWSS_LOG_ERROR("Map already present")` で破棄[^exc1]。
- **参照トンネル未 active**: `VXLAN_TUNNEL` が active でない場合リトライ待ち[^exc1]。

[^exc1]: `sonic-swss/cfgmgr/vxlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vxlanmgr.cpp>
[^exc2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vxlan.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vxlan.yang>

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-vxlan`](../yang/sonic-vxlan.md)
- CLI: [`config vxlan`](../cli/config-vxlan.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-vxlan.yang` 内 `VXLAN_TUNNEL_MAP`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-vxlan.yang#L66>

## 関連ページ
- [HLD: VXLAN / VNet 全体設計](../../overlay/vxlan-sonic.md)
- [CLI: config vxlan](../cli/config-vxlan.md)
- [CONFIG_DB: VXLAN_TUNNEL](vxlan-tunnel.md)
- [YANG: sonic-vxlan](../yang/sonic-vxlan.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `VXLAN_TUNNEL_MAP|<tunnel>|<map-name>` (例 `tunnel1|map_1000_Vlan100`)。
- `vni`: L2 VNI (例 1000)。
- `vlan`: `Vlan100`。

### よくある誤設定

- VLAN 未作成のまま VNI map を入れると [orchagent](../../reference/glossary.md#term-orchagent) が pending、トンネルが半開状態。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'VXLAN_TUNNEL_MAP|*'
show vxlan vlanvnimap
```
<!-- /ops-hint -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / VxlanOrch**: `VXLAN_TUNNEL_MAP` テーブルを `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- VxlanOrch が VNI ↔ VLAN マッピングを解析。APP_DB への書き込みなし。

### 段階 3: APPL → SAI

- VxlanOrch が `sai_tunnel_api->create_tunnel_map_entry()` で VNI ↔ VLAN のマッピングエントリをハードウェアに設定。

### 段階 4: タイミング + 副作用

- VXLAN_TUNNEL と VLAN テーブルが処理済みであることが前提。
- 副作用: VNI マッピング削除時は対応する EVPN MAC/IP ルートも連動して削除。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

VXLAN_TUNNEL_MAP テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config vxlan map add/del ...` / `config vxlan map_range add/del ...` — `config/vxlan.py` が `set_entry('VXLAN_TUNNEL_MAP', mapname, fvs)` を呼ぶ ([sonic-utilities](../../reference/glossary.md#term-sonic-utilities)/config/vxlan.py:206, 248, 315, 359)

### minigraph / sonic-cfggen

minigraph.py に VXLAN_TUNNEL_MAP 生成なし

### REST / gNMI

REST/[gNMI](../../reference/glossary.md#term-gnmi) 書き込み経路なし

### db_migrator

**db_migrator.py** が VXLAN_TUNNEL_MAP のマイグレーション処理を実装 ([sonic-utilities](../../reference/glossary.md#term-sonic-utilities)/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- cross-refs -->
## 暗黙参照 (Phase C / vxlanorch.cpp)

<!-- evidence: sonic-swss/orchagent/vxlanorch.cpp -->

以下の参照は `VXLAN_TUNNEL_MAP` テーブルが間接的に依存するが、CONFIG_DB スキーマや YANG には明示されていない。

### VXLAN_TUNNEL (VxlanTunnelOrch)

- **参照箇所**: `vxlanorch.cpp:2047-2058`
- `VxlanTunnelMapOrch::addOperation()` が `tunnel_orch->isTunnelExists(tunnel_name)` で親トンネルを確認し、`tunnel_orch->getVxlanTunnel(tunnel_name)` でポインタを取得する。
- 未登録時は `SWSS_LOG_WARN("Vxlan tunnel '%s' doesn't exist")` を記録して `return false` (リトライ待ち)。
- `del_tnl_hw_pending` フラグが立っている場合も `SWSS_LOG_WARN("Tunnel Mapper deletion is pending")` を記録して `return false` でブロック (`vxlanorch.cpp:2053-2058`)。
- **MAP エントリ数がゼロになると TUNNEL HW 削除がトリガされる**: `vlan_vrf_vni_count == 0` になった時点で `deleteTunnelHw()` が呼ばれ、DIP トンネルが残存している場合は `del_tnl_hw_pending = true` が設定される (`vxlanorch.cpp:2193-2226`)。

### VLAN (PortsOrch)

- **参照箇所**: `vxlanorch.cpp:2030-2034, 2145-2148`
- `gPortsOrch->getVlanByVlanId(vlan_id, tempPort)` で VLAN オブジェクトを取得する。
- VLAN が `PortsOrch` に未登録の場合 `SWSS_LOG_WARN("Vxlan tunnel map vlan id doesn't exist: %d", vlan_id)` を記録して `return false` (リトライ待ち)。
- 削除時に VLAN が消えていた場合は `SWSS_LOG_ERROR("Delete VLAN-VNI map.vlan id doesn't exist: %d")` を記録して `return true` (永続破棄、警告のみ)。

### VRF (VRFOrch) — L3VNI 判定

- **参照箇所**: `vxlanorch.cpp:2095-2113`
- `VRFOrch* vrf_orch = gDirectory.get<VRFOrch*>()` → `vrf_orch->isL3VniVlan(vni_id)` でこの VNI が L3VNI として登録済みかを確認する。
- `isL3VniVlan()` が `true` の場合、SAI `create_tunnel_map_entry()` を呼ばず `SAI_NULL_OBJECT_ID` を記録する (暗黙 no-op)。
- CONFIG_DB に L3VNI を明示するフィールドはなく VRFOrch 内部状態に依存する **silent 挙動差**。同じ `vni` 値でも VRF 登録状態により SAI エントリが生成されるかどうかが変わる。

### PortsOrch — トンネルポート / ブリッジポート管理

- **参照箇所**: `vxlanorch.cpp:2082-2084`
- `VXLAN_TUNNEL_MAP` の最初のエントリ追加がトンネルポートの HW 作成トリガになる（トンネルが非 active かつ DIP トンネル不使用の場合に `gPortsOrch->addTunnel()` / `addBridgePort()` を呼ぶ）。
- 逆に最後のエントリ削除時 (`vlan_vrf_vni_count == 0`) にトンネルポートの HW 削除が走る。

### 依存解決順序

```
VLAN (PortsOrch) ──┐
VRF  (VRFOrch)  ───┼──→ VXLAN_TUNNEL ──→ VXLAN_TUNNEL_MAP
```

削除は逆順: `VXLAN_EVPN_NVO` → `VXLAN_TUNNEL_MAP` → `VXLAN_TUNNEL`  
(`VLAN` は `VXLAN_TUNNEL_MAP` 全削除後に削除可)

<!-- /cross-refs -->

<!-- glossary-links-injected: ef52452d313c -->
