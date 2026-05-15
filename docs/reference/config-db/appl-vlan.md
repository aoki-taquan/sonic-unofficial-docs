---
title: APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE テーブル
description: "APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE テーブル — vlanmgrd が CONFIG_DB VLAN/VLAN_MEMBER を変換して書き込む中間テーブル。orchagent (portsorch) が購読して SAI VLAN/VLAN_MEMBER を生成する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: cfgmgr/vlanmgr.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.cpp
    ref: master
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: master
related:
  config_db:
    - VLAN
    - VLAN_MEMBER
  cli:
    - config vlan
    - show vlan
---

# APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE テーブル

## 概要

`VLAN_TABLE` および `VLAN_MEMBER_TABLE` は [APPL_DB](../../reference/glossary.md#term-appl_db) 上に存在する中間テーブル。`vlanmgrd`（sonic-swss/cfgmgr/vlanmgr.cpp）が [CONFIG_DB](../../reference/glossary.md#term-config_db) の `VLAN` / `VLAN_MEMBER` テーブルを購読し、変換・補完を加えて書き込む。`orchagent` 内の `PortsOrch` がこれらのテーブルを購読し、`sai_vlan_api` を通じてハードウェア VLAN を生成する[^vlanmgr][^portsorch]。

テーブル名の定数は `schema.h` で次のように定義されている[^schema]:

```
APP_VLAN_TABLE_NAME        = "VLAN_TABLE"
APP_VLAN_MEMBER_TABLE_NAME = "VLAN_MEMBER_TABLE"
```

## データフロー

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>VLAN / VLAN_MEMBER")]
  MGR["vlanmgrd<br/>(cfgmgr/vlanmgr.cpp)"]
  ADB[("APPL_DB<br/>VLAN_TABLE<br/>VLAN_MEMBER_TABLE")]
  ORCH["orchagent<br/>PortsOrch"]
  SYNCD["syncd"]
  SAI["SAI<br/>sai_vlan_api"]
  CDB --> MGR --> ADB --> ORCH --> SYNCD --> SAI
```

## key 構造

### VLAN_TABLE

```text
VLAN_TABLE|<vlan_name>
```

`<vlan_name>` は `Vlan<id>` 形式（例: `Vlan100`）。`Vlan` プレフィクスがない場合 vlanmgrd はエントリを破棄する。

### VLAN_MEMBER_TABLE

```text
VLAN_MEMBER_TABLE|<vlan_name>|<port_alias>
```

`<port_alias>` は `Ethernet0` や `PortChannel1` 形式。

## VLAN_TABLE フィールド一覧

| フィールド | 型 | APPL_DB での扱い | 説明 |
|-----------|----|----------------|------|
| `admin_status` | string (`up`/`down`) | 常に存在 | CONFIG_DB 省略時は `"up"` が自動補完される |
| `mtu` | string (数値) | 常に存在 | CONFIG_DB 省略時は `"9100"` が補完される |
| `mac` | string (MAC アドレス) | 常に存在 | CONFIG_DB 省略時はスイッチ MAC (`gMacAddress`) が補完される |
| `host_ifname` | string | 常に存在（省略時は空文字列） | ホストインタフェース名。空文字列の場合 portsorch は `createVlanHostIntf()` をスキップする |

## VLAN_MEMBER_TABLE フィールド一覧

| フィールド | 型 | APPL_DB での扱い | 説明 |
|-----------|----|----------------|------|
| `tagging_mode` | string (`tagged`/`untagged`/`priority_tagged`) | CONFIG_DB のフィールドをそのまま転送 | CONFIG_DB 省略時は vlanmgrd が `"untagged"` で補完。portsorch も同じく `"untagged"` fallback |
| `dynamic` | string (`yes`) | PAC 経路のみ注入 | YANG 定義なし・CONFIG_DB 非存在の隠しフィールド。`doVlanPacVlanMemberTask()` が PAC 制御メンバにのみ挿入する |

<!-- defaults -->
## コード由来の暗黙デフォルト

### VLAN_TABLE

| フィールド | YANG default | コード実装デフォルト | 出典 |
|-----------|-------------|---------------------|------|
| `admin_status` | なし | `"up"` — `fvVector` が空の場合（admin_status 省略時）に自動挿入 | vlanmgr.cpp:421-426 |
| `mtu` | なし | `"9100"` (`DEFAULT_MTU_STR`) — CONFIG_DB 省略時の変数初期化値がそのまま APPL_DB に書かれる | vlanmgr.cpp:19,357,428 |
| `mac` | なし | `gMacAddress`（スイッチ MAC）— CONFIG_DB 省略時の変数初期化値がそのまま APPL_DB に書かれる | vlanmgr.cpp:358,431 |
| `host_ifname` | なし | `""` (空文字列) — CONFIG_DB に `host_ifname` フィールドが存在しない場合は空文字列が書かれる | vlanmgr.cpp:359,434 |

### VLAN_MEMBER_TABLE

| フィールド | YANG default | コード実装デフォルト | 出典 |
|-----------|-------------|---------------------|------|
| `tagging_mode` | なし（YANG では mandatory） | `"untagged"` — vlanmgrd (L648) と portsorch (L5916) が独立に fallback。CONFIG_DB に不在の場合は二重補完が発生する | vlanmgr.cpp:648, portsorch.cpp:5916 |
| `tagging_mode` (`members@` 経路) | - | `"untagged"` ハードコード — CONFIG_DB `VLAN.members@` フィールド経由の minigraph 互換経路では常に `"untagged"` が注入される | vlanmgr.cpp:573 |
| `tagging_mode` (PAC 経路) | - | `"untagged"` ハードコード — PAC 制御による VLAN_MEMBER は `doVlanPacVlanMemberTask()` が `"untagged"` 固定で設定する | vlanmgr.cpp:873 |
| `dynamic` | なし | PAC 経路のみ `"yes"` を注入 — 通常 CLI / minigraph 経路では存在しない隠しフィールド | vlanmgr.cpp:887 |

### 注記

- **`mac` の書き込み順依存**: `gMacAddress` が未初期化（スイッチ MAC 未確定）の間、vlanmgrd は `isVlanMacOk()` チェック (L316-L321) で全 VLAN タスクを保留する。
- **`mtu` の silent drop**: `mtu` は APPL_DB に書かれるが、portsorch は mtu 更新を `setRouterIntfsMtu()` 経由で処理するのみで、ホスト netdev (`ip link set Vlan<N> mtu`) への適用は vlanmgr.cpp:401-406 の TODO コメント通り未実装。
- **`tagging_mode` の二重補完**: vlanmgrd が CONFIG_DB の raw フィールドをそのまま転送するため (vlanmgr.cpp:672)、`tagging_mode` が CONFIG_DB に存在しない場合は APPL_DB にも書かれない。portsorch が受信側で再度 `"untagged"` に fallback する。
- **`priority_tagged` の bridge/SAI 乖離**: `priority_tagged` は vlanmgr.cpp:238 で `bridge vlan add ... pvid untagged`（`untagged` と同一）として処理されるが、portsorch は SAI では `SAI_VLAN_TAGGING_MODE_PRIORITY_TAGGED` と区別する。ホスト転送と ASIC 転送で動作が乖離する。
<!-- /defaults -->

<!-- side-effects -->
## 副次 DB 書込（STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB）

`APPL_DB|VLAN_TABLE` / `APPL_DB|VLAN_MEMBER_TABLE` の SET / DEL 時、vlanmgrd は同一トランザクションで `STATE_DB` 上の対応エントリも更新する。`COUNTERS_DB` および `FLEX_COUNTER_DB` への副次書込みは **存在しない**（SAI VLAN counter は master ブランチ未実装）。

### STATE_DB

`VlanMgr` コンストラクタ (vlanmgr.cpp:24-32) が保持する `m_stateVlanTable` / `m_stateVlanMemberTable` 経由で書込まれる。

| STATE_DB key | 書込み箇所 | フィールド | トリガ |
|--------------|------------|----------|--------|
| `VLAN_TABLE\|Vlan<id>` | vlanmgr.cpp:443 (SET) / 463 (DEL) | `state="ok"` 固定 | `doVlanTask()` SET/DEL 成功時 |
| `VLAN_MEMBER_TABLE\|Vlan<id>\|<port>` | vlanmgr.cpp:677 / 698 | `state="ok"` 固定 | `doVlanMemberTask()` (通常 `VLAN_MEMBER` 経路) |
| `VLAN_MEMBER_TABLE\|Vlan<id>\|<port>` | vlanmgr.cpp:950 / 973 | `state="ok"` 固定 | `addPortToVlan()` / `removePortFromVlan()` (`VLAN.members@` 経由) |
| `VLAN_MEMBER_TABLE\|Vlan<id>\|<port>` | vlanmgr.cpp:894 / 907 | `state="ok"` (+ `dynamic="yes"` が混入する実装) | `doVlanPacVlanMemberTask()` (PAC 経路) |

`state` フィールドは常に `"ok"` 固定で、失敗パスは APPL_DB 自体を書かないため STATE_DB にも痕跡を残さない。これらのエントリは **vlanmgrd 内部の冪等チェック専用** (`isVlanStateOk()` vlanmgr.cpp:521-523, `isVlanMemberStateOk()` vlanmgr.cpp:535-537) で、ホスト netdev (`Vlan<N>` / bridge member) が作成済みかを判定するためにのみ使われる。`orchagent` / `portsorch` はこれらの STATE_DB エントリを購読しない（APPL_DB 側を直接 `ConsumerStateTable` で購読する）。

PAC 経路 (vlanmgr.cpp:894) では state vector ではなく APPL_DB 用 vector を流用しているため、`dynamic="yes"` が STATE_DB エントリにも書き込まれる実装の cleanup 抜けが見える。読み手側 (`isVlanMemberStateOk` は値ではなく key 存在のみを見る) には影響しないが、STATE_DB を dump した際の混入要因。

### COUNTERS_DB

`vlanmgr.cpp` は `COUNTERS_DB` の `DBConnector` を保持しない。`portsorch.cpp` は `m_counter_db` を持つが用途は `COUNTERS_PORT_NAME_MAP` / `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_PG_NAME_MAP` 等 **物理ポート単位** に限定され (portsorch.cpp:758-785)、`addVlan()` / `addVlanMember()` 経路では COUNTERS_DB に何も書込まない。SAI 仕様上 `SAI_VLAN_STAT_*` は存在するが、SONiC master は `COUNTERS_VLAN_NAME_MAP` を実装していない。

### FLEX_COUNTER_DB

`portsorch.cpp` の `FlexCounterManager` インスタンス (portsorch.cpp:727-739: `port_stat_manager` / `queue_stat_manager` / `pg_watermark_manager` ほか) はいずれも物理ポート / queue / priority-group スコープで、VLAN 単位の `FlexCounterManager` は存在しない。`APPL_DB|VLAN_TABLE` SET の連鎖で `FLEX_COUNTER_DB` への書込みは発火しない。

副次書込みの evidence は `meta/_intermediate/cdb-flow/appl-vlan-side.md` を参照。
<!-- /side-effects -->

<!-- platform -->
## プラットフォーム差

APPL_DB `VLAN_TABLE` / `VLAN_MEMBER_TABLE` 自体のスキーマ・暗黙デフォルトはすべてのプラットフォームで同一。`vlanmgrd` (`cfgmgr/vlanmgr.cpp` / `cfgmgr/vlanmgrd.cpp`) に `platform` / `asic_type` / `MLNX_PLATFORM_SUBSTRING` / `is_multi_npu` / `chassis` 参照は一切ない（`grep` で `using namespace std/swss` 以外 0 ヒット）。書き込み経路は ASIC ベンダー非依存[^vlanmgr]。

ただし**購読側の `PortsOrch` には SAI capability 依存の分岐**が存在する[^portsorch]:

| 分岐点 | SAI 問い合わせ | 未対応 ASIC での挙動 |
|-------|---------------|---------------------|
| VLAN flood control 切替 | `sai_query_attribute_enum_values_capability(SAI_OBJECT_TYPE_VLAN, SAI_VLAN_ATTR_{UNKNOWN_UNICAST,BROADCAST}_FLOOD_CONTROL_TYPE)` (portsorch.cpp:900-932) | `uuc_sup_flood_control_type` / `bc_sup_flood_control_type` 空集合。`SAI_VLAN_FLOOD_CONTROL_TYPE_ALL` 固定で `COMBINED` への切替が抑止される (portsorch.cpp:7605-7641, 7781-7849) |
| `end_point_ip` 付き VLAN_MEMBER (EVPN VxLAN flood group) | 同上で `SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED` capability 必須 | `addVlanMember()` が `Flood group with end point ip is not supported` で失敗 (portsorch.cpp:7517-7524) |
| VLAN host interface TX queue | `gSwitchOrch->querySwitchCapability(SAI_OBJECT_TYPE_HOSTIF, SAI_HOSTIF_ATTR_QUEUE)` (portsorch.cpp:933-940) | `m_supportsHostIfTxQueue=false` でホスト IF TX queue 設定が無効化（VLAN テーブル自体には影響しない） |

### MLNX (Nvidia) 限定の port stat plugin

`isMlnxPlatform()` (portsorch.cpp:689-698, 環境変数 `platform` 文字列マッチ) が true の場合のみ `SAI_PORT_STAT_TRIM_PACKETS` を含む custom Lua plugin (`nvdaPortTrimSha`) が port stat collector に追加される (portsorch.cpp:858-865)。VLAN テーブル書き込みには無関係で、counter 系の差分。

### multi-asic / VOQ chassis

`vlanmgrd` および `portsorch` は asic namespace 内のコンテナ (`swss@<asicN>`) で起動し、その namespace の CONFIG_DB / APPL_DB のみを購読・書込みする。`VLAN_TABLE` / `VLAN_MEMBER_TABLE` は asic ごとにローカルで、chassis-wide 統合経路（`CHASSIS_APP_DB`）は VLAN には存在しない（`CHASSIS_APP_DB` 連携は SYSTEM_PORT / SYSTEM_NEIGH 系のみ）。

詳細は `meta/_intermediate/cdb-flow/appl-vlan-platform.md` を参照。
<!-- /platform -->

<!-- cross-refs -->
## 暗黙参照テーブル (cross-refs)

APPL_DB `VLAN_TABLE` / `VLAN_MEMBER_TABLE` は YANG 未定義のため、明示的な leafref は存在しない。
しかしコード上、`vlanmgrd` および `PortsOrch::doVlanMemberTask()` 経路で以下のテーブル / リソースに
暗黙依存する。

### 参照関係マップ

| 参照元 | 参照先テーブル / リソース | 解決経路 | 失敗時挙動 |
|--------|---------------------------|----------|------------|
| `VLAN_MEMBER_TABLE\|Vlan<id>\|EthernetN` | `APPL_DB\|PORT_TABLE` / `STATE_DB\|PORT_TABLE` | `PortsOrch::getPort(alias)` / `VlanMgr::isMemberStateOk` (`vlanmgr.cpp:486-510`, `portsorch.cpp:5898-5912`) | `it++` で無限ポーリング再試行（PortsOrch）／ APPL_DB 書込み保留（vlanmgrd） |
| `VLAN_MEMBER_TABLE\|Vlan<id>\|PortChannelN` | `STATE_DB\|LAG_TABLE` (`m_stateLagTable`) | `VlanMgr::isMemberStateOk` (`vlanmgr.cpp:495`) ＋ `Port::LAG` OID 解決 (`portsorch.cpp:2049, 2627`) | LAG 未確立中は書込保留。bridge コマンド失敗時は LAG 削除レース判定で retry スキップ (`vlanmgr.cpp:260-272`) |
| `VLAN_MEMBER_TABLE` フィールド `end_point_ip` | VxlanTunnelOrch + `vlan.m_vlan_info.l2mc_group_id` | `PortsOrch::addVlanMember` → `addVlanFloodGroups` (`portsorch.cpp:7511-7740`) | SAI capability 不足時 `Flood group with end point ip is not supported` で失敗 |
| `doVlanPacFdbTask` (`VLAN_TABLE` 確立後) | `APPL_DB\|FDB_TABLE` (`m_appFdbTableProducer`) | `vlanmgr.cpp:776-841` (key=`Vlan<id>:<MAC>`) | `m_vlans.count(vlan_name)` 未登録なら FDB 注入保留 (`vlanmgr.cpp:806-811`) |
| `VLAN_MEMBER_TABLE` SET → `STATE_DB\|VLAN_MEMBER_TABLE` 連鎖 | mclagsyncd 購読 (`STATE_VLAN_MEMBER_TABLE_NAME`, `mclaglink.cpp:915`) | `SubscriberStateTable` 経由で MCLAG peer へ伝播。ASIC_DB `SAI_OBJECT_TYPE_VLAN` 経由で BVID→VID 逆引き (`mclaglink.cpp:101-112`) | mclagsyncd は APPL_DB を直接購読しない（間接依存） |

### 順序依存

- `VLAN_TABLE` SET が先行しない VLAN_MEMBER は portsorch 側で `getPort(vlan_alias)` 失敗で保留される (`portsorch.cpp:5900-5905`)。
- `VLAN_TABLE` 確立後でないと `doVlanPacFdbTask` の FDB 注入は `m_vlans.count()` ガードで保留される。
- `end_point_ip` 付き VLAN_MEMBER は L2MC group OID (`vlan.m_vlan_info.l2mc_group_id`) が VLAN 作成時に確立されている必要があり、対応する VxLAN remote VTEP は VxlanTunnelOrch 経由で別途解決される。

### MCLAG との関係

`mclagsyncd` (`mclaglink.cpp`) は APPL_DB `VLAN_TABLE` / `VLAN_MEMBER_TABLE` を **直接購読しない**。
代わりに `STATE_DB|VLAN_MEMBER_TABLE` (vlanmgrd が APPL_DB 書込と同時に書く state="ok" エントリ) を
購読することで MCLAG peer 同期をトリガする。`portsorch.cpp` には `mclag` / `MCLAG` 識別子の
直接参照は存在しない。

詳細な evidence は `meta/_intermediate/cdb-flow/appl-vlan-cross-refs.md` を参照。
<!-- /cross-refs -->

## 書き込み主体

| 書き込み元 | 対象テーブル | 経路 |
|-----------|------------|------|
| `vlanmgrd` (doVlanTask) | `VLAN_TABLE` | CONFIG_DB `VLAN` 購読 → 補完 → APPL_DB |
| `vlanmgrd` (doVlanMemberTask) | `VLAN_MEMBER_TABLE` | CONFIG_DB `VLAN_MEMBER` 購読 → APPL_DB |
| `vlanmgrd` (processUntaggedVlanMembers) | `VLAN_MEMBER_TABLE` | CONFIG_DB `VLAN.members@` 経由の minigraph 互換経路 |
| `vlanmgrd` (doVlanPacVlanMemberTask) | `VLAN_MEMBER_TABLE` | PAC 制御経路（`dynamic="yes"` フィールド付き） |

## 購読者

- `orchagent` / `PortsOrch`: `VLAN_TABLE` および `VLAN_MEMBER_TABLE` を `ConsumerStateTable` で購読。`sai_vlan_api->create_vlan()` および `sai_vlan_api->create_vlan_member()` でハードウェアに反映する (portsorch.cpp:6470-6527)。
- warm-restart 時: `addExistingData(APP_VLAN_TABLE_NAME)` / `addExistingData(APP_VLAN_MEMBER_TABLE_NAME)` で既存エントリを再処理する (portsorch.cpp:4389-4390)。

## 引用元

[^vlanmgr]: `sonic-swss/cfgmgr/vlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vlanmgr.cpp>
[^portsorch]: `sonic-swss/orchagent/portsorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/portsorch.cpp>
[^schema]: `sonic-swss-common/common/schema.h` <https://github.com/sonic-net/sonic-swss-common/blob/master/common/schema.h>

## 関連ページ

- [CONFIG_DB: VLAN](vlan.md)
- [CONFIG_DB: VLAN_MEMBER](vlan-member.md)
- [CLI: config vlan](../cli/config-vlan.md)
- [CLI: show vlan](../cli/show-vlan.md)
