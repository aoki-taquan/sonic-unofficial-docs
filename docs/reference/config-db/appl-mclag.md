---
title: APPL_DB MCLAG/ICCP 関連テーブル
description: "APPL_DB MCLAG/ICCP 関連テーブル — mclagsyncd が iccpd からの IPC メッセージを受けて APPL_DB に書き込む MCLAG_FDB_TABLE・ISOLATION_GROUP_TABLE・LAG_TABLE・PORT_TABLE・INTF_TABLE の各フィールドとコード由来デフォルト。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15

sources:
  - repo: sonic-net/sonic-swss
    path: mclagsyncd/mclaglink.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: mclagsyncd/mclaglink.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: mclagsyncd/mclag.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
  - repo: sonic-net/sonic-buildimage
    path: src/iccpd/include/scheduler.h
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/iccpd/src/iccp_csm.c
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MCLAG_DOMAIN
    - MCLAG_INTERFACE
    - MCLAG_UNIQUE_IP
  cli:
    - show mclag brief
    - show mclag interface
---

# APPL_DB MCLAG/ICCP 関連テーブル

## 概要

MC-[LAG](../../reference/glossary.md#term-lag) (Multi-Chassis Link Aggregation) の実行時状態は `mclagsyncd` が管理する[^link]。`mclagsyncd` は `iccpd`（ICCP デーモン）から Unix ソケット経由で IPC メッセージを受信し、`ProducerStateTable` 経由で [APPL_DB](../../reference/glossary.md#term-appl_db) に書き込む。

書き込まれるテーブルは 5 種類[^schema]:

| APPL_DB テーブル | 目的 |
|----------------|------|
| `MCLAG_FDB_TABLE` | ピア同期 MAC アドレスエントリ |
| `ISOLATION_GROUP_TABLE` | ポート分離グループ（対応プラットフォームのみ） |
| `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` | ポート分離 ACL（非対応プラットフォームのフォールバック） |
| `LAG_TABLE` | PortChannel の MAC 学習モード・トラフィック分散制御 |
| `PORT_TABLE` | 物理ポートの MAC 学習モード制御 |
| `INTF_TABLE` | インタフェースの MAC アドレス上書き |

STATE_DB への書き込み（`MCLAG_TABLE`・`MCLAG_LOCAL_INTF_TABLE`・`MCLAG_REMOTE_INTF_TABLE`）は `mclagsyncd` が直接行うが、本ページでは APPL_DB を対象とする。

---

## MCLAG_FDB_TABLE

### key 構造

```text
MCLAG_FDB_TABLE|Vlan<vid>:<mac>
```

例: `MCLAG_FDB_TABLE|Vlan100:00:01:02:03:04:05`

### フィールド

| フィールド | 型 | 説明 |
|-----------|----|----|
| `port`    | string | MAC エントリが所属するインタフェース名（PortChannel 名など） |
| `type`    | string | エントリ種別。`"static"` / `"dynamic"` / `"dynamic_local"` |

`type` の値は `iccpd` が IPC で送る `MCLAG_FDB_TYPE` 列挙値に基づく[^link]:

| 列挙値 | 値 | `type` 文字列 |
|--------|-----|-------------|
| `MCLAG_FDB_TYPE_STATIC` | 1 | `"static"` |
| `MCLAG_FDB_TYPE_DYNAMIC` | 2 | `"dynamic"` |
| `MCLAG_FDB_TYPE_DYNAMIC_LOCAL` | 3 | `"dynamic_local"` |

`dynamic_local` は aging が有効なローカルエントリとして ASIC に書き込む際に使用する。

---

## ISOLATION_GROUP_TABLE

ポート分離（ピアリンク経由ループ防止）に使用する。プラットフォームが `broadcom`・`barefoot`・`centec`・`clounix`・`marvell-prestera`・`marvell-teralynx` のいずれかの場合に書き込まれる[^link]。

### key 構造

```text
ISOLATION_GROUP_TABLE|MCLAG_ISO_GRP
```

キーは `"MCLAG_ISO_GRP"` 固定（1 エントリのみ）。

### フィールド

| フィールド    | 型 | 値 |
|--------------|----|----|
| `DESCRIPTION` | string | `"Isolation group for MCLAG"`（ハードコード） |
| `TYPE`        | string | `"bridge-port"`（ハードコード） |
| `PORTS`       | string | 分離元ポート名（MCLAG インタフェース） |
| `MEMBERS`     | string | 分離先PortChannel 名（カンマ区切り）。全リモートが down のとき空文字列 |

`MEMBERS` は `Ethernet` で始まるポートが除外された PortChannel 名のみが設定される[^link]。ICCP セッションが down で全リモートインタフェースが down の場合は `MEMBERS` を空にしてエントリを保持し、ICCP セッション自体が切断 (`is_iccp_up == false`) の場合はエントリを DEL する。

---

## ACL フォールバック（非対応プラットフォーム）

上記プラットフォーム以外では isolation group の代わりに ACL を使用する[^link]:

### ACL_TABLE_TABLE

| キー | フィールド | 値 |
|------|-----------|---|
| `mclag` | `policy_desc` | `"Mclag egress port isolate acl"` |
| | `type` | `"L3"` |
| | `ports` | 分離元ポート名 |

### ACL_RULE_TABLE

| キー | フィールド | 値 |
|------|-----------|---|
| `mclag:mclag` | `IP_TYPE` | `"ANY"` |
| | `OUT_PORTS` | 分離先 Ethernet ポート名（PortChannel 除外後） |
| | `PACKET_ACTION` | `"DROP"` |

分離先ポートが空（`op_len == 0`）の場合は `ACL_TABLE_TABLE` の `mclag` エントリを DEL する。

---

## LAG_TABLE

### MAC 学習モード

`setPortMacLearnMode()` がポートが PortChannel の場合に LAG_TABLE へ書き込む[^link]:

| フィールド    | 型 | 値 |
|--------------|----|----|
| `learn_mode` | string | `"hardware"` または `"disable"` |

`MCLAG_SUB_OPTION_TYPE_MAC_LEARN_ENABLE` → `"hardware"`、`MCLAG_SUB_OPTION_TYPE_MAC_LEARN_DISABLE` → `"disable"`。

### トラフィック分散制御

`mclagsyncdSetTrafficDisable()` が PortChannel のトラフィック分散を制御する[^link]:

| フィールド        | 型 | 値 |
|-----------------|----|----|
| `traffic_disable` | string | `"true"` または `"false"` |

`MCLAG_MSG_TYPE_SET_TRAFFIC_DIST_DISABLE` → `"true"`（分散無効化）、`ENABLE` → `"false"`。

---

## PORT_TABLE

物理ポートの MAC 学習モード。PortChannel でないポートに `setPortMacLearnMode()` が書き込む[^link]:

| フィールド    | 型 | 値 |
|--------------|----|----|
| `learn_mode` | string | `"hardware"` または `"disable"` |

---

## INTF_TABLE

`setIntfMac()` がインタフェースの MAC アドレスを書き込む[^link]:

| フィールド  | 型 | 説明 |
|------------|----|----|
| `mac_addr` | string | ICCP が決定したシステム MAC アドレス |

ICCP のロール（active / standby）確定後に iccpd が `MCLAG_MSG_TYPE_SET_INTF_MAC` メッセージで通知する。

---

## 書き込み主体・消費者

| 書き込み元 | テーブル | 消費者 |
|-----------|---------|-------|
| `mclagsyncd` | `MCLAG_FDB_TABLE` | `fdborch` (orchagent) |
| `mclagsyncd` | `ISOLATION_GROUP_TABLE` | `isolationGroupOrch` |
| `mclagsyncd` | `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` | `aclOrch` |
| `mclagsyncd` | `LAG_TABLE` | `lagOrch` |
| `mclagsyncd` | `PORT_TABLE` | `portOrch` |
| `mclagsyncd` | `INTF_TABLE` | `intfOrch` |

<!-- defaults -->
## フィールドの暗黙デフォルト (Phase A)

以下はコード精読により判明した APPL_DB MCLAG 関連フィールドのコード由来デフォルト[^link][^schema]。

### MCLAG_FDB_TABLE — フィールドのデフォルトなし

`setFdbEntry()` L465–521 は `port` と `type` の 2 フィールドを必ず明示的に書き込む。省略ロジックは存在しない。

| フィールド | 省略ルール | iccpd 送信側デフォルト |
|-----------|-----------|---------------------|
| `port`    | 省略なし（常に SET） | なし（必須フィールド） |
| `type`    | 省略なし（常に SET） | `"dynamic"` (最頻値) |

### ISOLATION_GROUP_TABLE — DESCRIPTION・TYPE は固定値

```cpp
// mclaglink.cpp L235, L236, L272, L273
fvts.emplace_back("DESCRIPTION", "Isolation group for MCLAG");
fvts.emplace_back("TYPE", "bridge-port");
```

| フィールド    | コード由来デフォルト | 変更可否 |
|--------------|-------------------|---------|
| `DESCRIPTION` | `"Isolation group for MCLAG"` | 不可（ハードコード） |
| `TYPE`        | `"bridge-port"` | 不可（ハードコード） |
| `MEMBERS`     | `""` (空文字列) — リモート全断時 | ICCP up 時は実値 |

### LAG_TABLE.learn_mode — ENABLE/DISABLE の 2 値のみ

```cpp
// mclaglink.cpp L393, L397
if (op_hdr->op_type == MCLAG_SUB_OPTION_TYPE_MAC_LEARN_ENABLE)
    learn_mode = "hardware";
else if (op_hdr->op_type == MCLAG_SUB_OPTION_TYPE_MAC_LEARN_DISABLE)
    learn_mode = "disable";
```

MCLAG は起動時にリモート側PortChannel の MAC 学習を `"disable"` にし、ICCP セッション確立後は `"hardware"` に戻す。中間状態は存在せず、値は必ず `"hardware"` か `"disable"` のいずれか。

### LAG_TABLE.traffic_disable — ICCP ロール確定前は書き込みなし

```cpp
// mclaglink.cpp L1308, L1310
if (msg_type == MCLAG_MSG_TYPE_SET_TRAFFIC_DIST_DISABLE)
    traffic_dist_disable = "true";
else
    traffic_dist_disable = "false";
```

iccpd からのメッセージがある場合のみ書き込まれる。フィールド不在時の orchagent 側デフォルトは `"false"`（分散有効）。

### CONFIG_DB keepalive_interval / session_timeout のデフォルト（iccpd 内）

`MCLAG_DOMAIN` テーブルの `keepalive_interval` / `session_timeout` が省略（空文字列）の場合、mclagsyncd は値 `-1` として iccpd へ送信し、iccpd 内でデフォルト値にフォールバックする[^sched][^csm]:

| CONFIG_DB フィールド | 省略時の iccpd 内部デフォルト | 定数 |
|--------------------|--------------------------|------|
| `keepalive_interval` | `1` 秒 | `CONNECT_INTERVAL_SEC` (`scheduler.h:40`) |
| `session_timeout`    | `15` 秒 | `HEARTBEAT_TIMEOUT_SEC` (`scheduler.h:42`) |

```cpp
// iccp_csm.c L125-L126
csm->keepalive_time  = CONNECT_INTERVAL_SEC;   // = 1
csm->session_timeout = HEARTBEAT_TIMEOUT_SEC;  // = 15
```

フォールバックは `mlacp_link_handler.c` L3108, L3120, L3137, L3142 で `-1` を検出した際にも同値がセットされる。

<!-- /defaults -->

<!-- pubsub -->
## Redis 通知メカニズム (Phase G)

### 書き込み側 mclagsyncd の通信構造

`mclagsyncd` は APPL_DB に対しては書き込み専用で、上流イベントを 3 系統から受け取る:

1. **iccpd → mclagsyncd**: Unix ドメインソケット経由の IPC (MCLAG_DEFAULT_PORT = 2626、`mclag.h:56`)
2. **CONFIG_DB → mclagsyncd**: `SubscriberStateTable` で keyspace notification を購読
3. **STATE_DB → mclagsyncd**: `SubscriberStateTable` で keyspace notification を購読

APPL_DB への書き込みは 7 種類すべて `ProducerStateTable` 経由 (`mclaglink.cpp:1810-1816`)[^link]。書き込みごとに各テーブルの `<TABLE>_CHANNEL@0` チャネルへ PUBLISH される。

### 購読方式: SubscriberStateTable + keyspace PSUBSCRIBE

`mclagsyncd` は CONFIG_DB / STATE_DB の以下のテーブルを `SubscriberStateTable` で購読する。`SubscriberStateTable` は内部で Redis keyspace notification を PSUBSCRIBE する[^link]:

| 購読元 | DB | テーブル | PSUBSCRIBE パターン |
|--------|----|---------|-------------------|
| CONFIG_DB | 4 | `MCLAG` (MCLAG_DOMAIN) | `__keyspace@4__:MCLAG\|*` |
| CONFIG_DB | 4 | `MCLAG_INTERFACE` | `__keyspace@4__:MCLAG_INTERFACE\|*` |
| CONFIG_DB | 4 | `MCLAG_UNIQUE_IP` | `__keyspace@4__:MCLAG_UNIQUE_IP\|*` |
| STATE_DB | 6 | `FDB_TABLE` | `__keyspace@6__:FDB_TABLE\|*` |
| STATE_DB | 6 | `VLAN_MEMBER_TABLE` | `__keyspace@6__:VLAN_MEMBER_TABLE\|*` |

実装位置: `mclagsyncd.cpp:41` (MCLAG_DOMAIN)、`mclaglink.cpp:912-921` (STATE_FDB / STATE_VLAN_MEMBER / MCLAG_INTF / MCLAG_UNIQUE_IP)。

### 主ループ — 永続 blocking select、明示 retry interval なし

`mclagsyncd.cpp:66-110` の主ループはタイムアウト無しの `s.select(&temps)` で永続ブロックする[^link]:

```cpp
while (true) {
    Selectable *temps;
    s.select(&temps);                       // タイムアウト指定なし = UINT_MAX
    if      (temps == mclag.getStateFdbTable())        mclag.processStateFdb(...);
    else if (temps == &mclag_cfg_tbl)                  mclag.processMclagDomainCfg(entries);
    else if (temps == mclag.getMclagIntfCfgTable())    mclag.mclagsyncdSendMclagIfaceCfg(entries);
    else if (temps == mclag.getMclagUniqueCfgTable())  mclag.mclagsyncdSendMclagUniqueIpCfg(entries);
    else if (temps == mclag.getStateVlanMemberTable()) mclag.processStateVlanMember(...);
    else                                                pipeline.flush();
}
```

リトライは IPC 切断時のみで、外側 `while(1)` が `MclagConnectionClosedException` を捕捉し即時 `accept()` を再呼び出しする。**明示的な retry interval / sleep は存在しない**。

### 消費側 orchagent の select タイムアウト

書き込まれた APPL_DB エントリは orchagent が ConsumerStateTable で消費する (`SELECT_TIMEOUT = 1000` ms、`orchdaemon.cpp:23,959`)[^orch]:

| APPL_DB テーブル | 消費 Orch | バインド箇所 |
|----------------|----------|------------|
| `MCLAG_FDB_TABLE` | `FdbOrch` (`fdborch_pri`) | `orchdaemon.cpp:229`、`fdborch.cpp:724` |
| `ISOLATION_GROUP_TABLE` | `IsolationGroupOrch` | `orchdaemon.cpp:542`、`isolationgrouporch.cpp:68` |
| `LAG_TABLE` / `PORT_TABLE` | `PortsOrch` | （汎用 APPL_DB 経路に相乗り） |
| `INTF_TABLE` | `IntfsOrch` | （汎用 APPL_DB 経路に相乗り） |
| `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` | `AclOrch` | （汎用 APPL_DB 経路に相乗り） |

### iccpd 側タイマー（参考）

iccpd 自身は subscribe ではなく自前のスケジューラで動作する。CONFIG_DB の `keepalive_interval` / `session_timeout` が空のときのみ iccpd 内で `CONNECT_INTERVAL_SEC = 1` 秒・`HEARTBEAT_TIMEOUT_SEC = 15` 秒 にフォールバックする[^sched][^csm]（詳細は上記「フィールドの暗黙デフォルト」節を参照）。

> 中間調査詳細: `meta/_intermediate/cdb-flow/appl-mclag-pubsub.md`
<!-- /pubsub -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

APPL_DB MCLAG/ICCP 関連テーブル群 (`MCLAG_FDB_TABLE` / `ISOLATION_GROUP_TABLE` /
`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `LAG_TABLE` / `PORT_TABLE` / `INTF_TABLE`) の
書込主体である `mclagsyncd` は、本 APPL_DB 書込に **副次して** [STATE_DB](../../reference/glossary.md#term-state_db)
側にも MCLAG 状態テーブルを書き込む。COUNTERS_DB は読取のみで書込は無い[^link]。

| 副次 DB | 書込有無 | 対象テーブル / 根拠 |
|---|---|---|
| STATE_DB | あり | `STATE_MCLAG_TABLE` (`mclaglink.cpp:1357,1412,1460,1503,1733`) / `STATE_MCLAG_LOCAL_INTF_TABLE` (L1520,1533) / `STATE_MCLAG_REMOTE_INTF_TABLE` (L1584,1633) |
| COUNTERS_DB | なし (読取のみ) | `p_counters_db->hgetall("COUNTERS_PORT_NAME_MAP")` (`mclaglink.cpp:66`) — OID 解決用、書込呼出 0 件 |
| ASIC_DB (直接) | なし | `mclagsyncd` から SAI 呼出無し。APPL_DB 経由で `fdborch` / `isolationGroupOrch` が間接書込 |
| FLEX_COUNTER_DB / LOGLEVEL_DB | なし | `mclagsyncd` 全体で参照 0 件 |
| `iccpd` から直接 | なし | iccpd は `mclagsyncd` への IPC メッセージのみで Redis 直書きコード無し (STATE_DB 参照はコメントのみ) |

### STATE_DB 書込の対応表

| 書込関数 | STATE_DB テーブル | 操作 | 用途 |
|---|---|---|---|
| `mclagsyncdSetIccpState()` | `STATE_MCLAG_TABLE` | `set(<mlag_id>, oper_status)` | ICCP セッション up/down |
| `mclagsyncdSetIccpRole()` | `STATE_MCLAG_TABLE` | `set(<mlag_id>, role, system_mac)` | active / standby ロール |
| `mclagsyncdSetSystemId()` | `STATE_MCLAG_TABLE` | `set(<mlag_id>, system_mac)` | システム MAC 通知 |
| `mclagsyncdDelIccpInfo()` | `STATE_MCLAG_TABLE` | `del(<mlag_id>)` | ICCP 情報削除 |
| `setLocalIfPortIsolate()` | `STATE_MCLAG_LOCAL_INTF_TABLE` | `set(<if>, port_isolate_peer_link)` | ローカル IF のピアリンク分離状態 |
| `deleteLocalIfPortIsolate()` | `STATE_MCLAG_LOCAL_INTF_TABLE` | `del(<if>)` | ローカル IF エントリ削除 |
| `mclagsyncdSetRemoteIfState()` | `STATE_MCLAG_REMOTE_INTF_TABLE` | `set("<id>\|<if>", oper_status)` | リモート IF oper 状態 |
| `mclagsyncdDelRemoteIfInfo()` | `STATE_MCLAG_REMOTE_INTF_TABLE` | `del("<id>\|<if>")` | リモート IF エントリ削除 |

これら STATE_DB エントリは `show mclag brief` / `show mclag interface` などの CLI が
直接読みに行く参照源となる。

詳細スキャン手順と grep 結果は `meta/_intermediate/cdb-flow/appl-mclag-side.md` を参照。
<!-- /side-effects -->

## 引用元

[^link]: mclagsyncd 実装: `sonic-swss/mclagsyncd/mclaglink.cpp`, `mclaglink.h`, `mclag.h`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/mclagsyncd/mclaglink.cpp>
[^schema]: テーブル名定数: `sonic-swss-common/common/schema.h`. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h>
[^sched]: keepalive/timeout 定数: `sonic-buildimage/src/iccpd/include/scheduler.h`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/iccpd/include/scheduler.h>
[^csm]: iccpd CSM 初期化: `sonic-buildimage/src/iccpd/src/iccp_csm.c`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/iccpd/src/iccp_csm.c>
[^orch]: orchagent 消費側: `sonic-swss/orchagent/orchdaemon.cpp` (`SELECT_TIMEOUT = 1000` ms), `fdborch.cpp`, `isolationgrouporch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/orchdaemon.cpp>
