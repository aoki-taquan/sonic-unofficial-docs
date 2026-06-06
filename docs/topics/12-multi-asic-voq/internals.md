---
title: 内部実装
description: Multi-ASIC / VOQ chassis の内部実装。namespace 分割した per-ASIC Redis / orchagent
  / syncd と、chassis 全体を束ねる CHASSIS_APP_DB / database-chassis container の二重構造、SYSTEM_PORT_TABLE
  / SYSTEM_NEIGH_TABLE による状態同期、FabricPortsOrch の auto-isolation を解説する。
area: topics
verification: code-verified
last_verified: 2026-06-04
sources:
- repo: sonic-net/sonic-swss
  path: orchagent/main.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: orchagent/portsorch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: orchagent/neighorch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: orchagent/fabricportsorch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: orchagent/chassisorch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss-common
  path: common/schema.h
  ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
- repo: sonic-net/sonic-utilities
  path: show/fabric.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-utilities
  path: config/chassis_modules.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  cli:
  - show fabric
  - show fabric reachability
  - show fabric isolation
  - show chassis-modules
  - config chassis_modules shutdown
  - config chassis_modules startup
  config_db:
  - SYSTEM_PORT
  - CHASSIS_MODULE
  - FABRIC_MONITOR
  - FABRIC_PORT
  - VOQ_INBAND_INTERFACE
  yang:
  - sonic-system-port
  - sonic-chassis-module
  - sonic-fabric-monitor
  - sonic-fabric-port
  - sonic-voq-inband-interface
  - sonic-bgp-voq-chassis-neighbor
---

# 内部実装

[Multi-ASIC](../../reference/glossary.md#term-multi-asic) / [VOQ](../../reference/glossary.md#term-voq) chassis の内部実装は「namespace で分けられた [Redis](../../reference/glossary.md#term-redis) / [orchagent](../../reference/glossary.md#term-orchagent) / [syncd](../../reference/glossary.md#term-syncd) インスタンス」と「chassis 全体を束ねる chassis_db / database-chassis container」の二重構造で動きます。論理スイッチ単位の Redis インスタンスと、シャーシ全体で共有する Redis インスタンスを混同しないことが重要です。

## データフロー

```mermaid
flowchart TB
  subgraph ns0[asic0 namespace]
    SWSS0[swss0]
    SYNCD0[syncd0]
    REDIS0[(redis<br/>asic0)]
  end
  subgraph ns1[asic1 namespace]
    SWSS1[swss1]
    SYNCD1[syncd1]
    REDIS1[(redis<br/>asic1)]
  end
  subgraph host[host namespace]
    SUPER[swss-common / chassis_db / database-chassis]
    BGP[bgpd<br/>per-asic FRR instance]
    GLOBAL[(CHASSIS_APP_DB<br/>+ CHASSIS_STATE_DB)]
  end
  SWSS0 <--> REDIS0
  SWSS1 <--> REDIS1
  SWSS0 <-->|system port / inband| GLOBAL
  SWSS1 <-->|system port / inband| GLOBAL
  SUPER --> GLOBAL
  BGP --> SWSS0
  BGP --> SWSS1
```

## 主要 daemon / コンポーネントの責務

| コンポーネント | 主実体 | 責務 |
| --- | --- | --- |
| `database-chassis` container | chassis-wide `redis-server` | `CHASSIS_APP_DB` と `CHASSIS_STATE_DB` をホスト |
| per-asic `database` container | namespace 内 `redis-server` | `APPL_DB` / `ASIC_DB` / `CONFIG_DB` / `STATE_DB` / `COUNTERS_DB` |
| `orchagent` per-asic | `SwitchOrch` で `SAI_SWITCH_ATTR_TYPE = VOQ` を指定 | system port、fabric port、inband interface を作成 |
| `FabricPortsOrch` (`orchagent/fabricportsorch.cpp`) | fabric link 監視 | fabric 側 link の up/down と link mon |
| `VoqOrch` / `SystemPortOrch` | `SystemNeighOrch`、`SystemLagOrch` 等 | system port を chassis 全体で広報、neighbor / [LAG](../../reference/glossary.md#term-lag) を chassis 規模で同期 |
| `chassisd` / `chassis_db` | chassis init scripts | 全 [ASIC](../../reference/glossary.md#term-asic) の system port を `CHASSIS_APP_DB:SYSTEM_PORT_TABLE` に登録 |
| `bgpcfgd` per-asic | per-namespace [FRR](../../reference/glossary.md#term-frr) | 各 ASIC が独自の [BGP](../../reference/glossary.md#term-bgp) プロセスを持つ |

## SAI 属性使用一覧

VOQ chassis 固有:

| object | 属性 |
| --- | --- |
| `SAI_OBJECT_TYPE_SWITCH` | `SAI_SWITCH_ATTR_TYPE = SAI_SWITCH_TYPE_VOQ`、`SAI_SWITCH_ATTR_SWITCH_ID`、`SAI_SWITCH_ATTR_MAX_SYSTEM_CORES`、`SAI_SWITCH_ATTR_SYSTEM_PORT_CONFIG_LIST`[^orch-main] |
| `SAI_OBJECT_TYPE_SYSTEM_PORT` | `SAI_SYSTEM_PORT_ATTR_CONFIG_INFO`、`SAI_SYSTEM_PORT_ATTR_ADMIN_STATE`、`SAI_SYSTEM_PORT_ATTR_QOS_TC_TO_QUEUE_MAP` |
| `SAI_OBJECT_TYPE_FABRIC_PORT` | `SAI_PORT_ATTR_TYPE = FABRIC`、`SAI_PORT_ATTR_FABRIC_ATTACHED`、`SAI_PORT_ATTR_FABRIC_REACHABILITY` |
| `SAI_OBJECT_TYPE_NEIGHBOR_ENTRY` (system) | system port を nexthop とする encap 情報を含む |

Multi-ASIC（pizza-box の packet mode 含む）では `SAI_SWITCH_ATTR_TYPE = SAI_SWITCH_TYPE_NPU` のままで、ASIC ごとに独立した [SAI](../../reference/glossary.md#term-sai) switch object を作る点が VOQ と違います。

## Redis テーブル参照関係

```yaml
Per-ASIC namespace:
  APPL_DB / CONFIG_DB / ASIC_DB / STATE_DB / COUNTERS_DB
Chassis global:
  CHASSIS_APP_DB:
    SYSTEM_PORT_TABLE
    SYSTEM_NEIGH_TABLE
    SYSTEM_LAG_TABLE
    SYSTEM_LAG_MEMBER_TABLE
  CHASSIS_STATE_DB:
    LINECARD_TABLE
    FABRIC_ASIC_TABLE
    HOSTNAME_ASIC_MAP
```

各 ASIC orchagent は自身の `APPL_DB:NEIGH_TABLE` から学習した neighbor を `CHASSIS_APP_DB:SYSTEM_NEIGH_TABLE` に複製し、他 ASIC の orchagent はそれを subscribe して自身の system port nexthop に変換します[^neighorch].

## ZMQ / Redis pub/sub

- chassis 内通信は **Redis pub/sub のみ**で、inband (cpu) や fabric 専用回線を経由した IP 接続上で chassis_db redis サーバに接続します。
- ZMQ は VOQ chassis では使われていません（一部の [SONiC](../../reference/glossary.md#term-sonic) chassis variant では検討された経緯はあるが master では Redis のみ）。
- `database-chassis` の redis は `0.0.0.0` で listen し、IPSec / TLS を使わない平文通信が前提。シャーシ内通信路（midplane）が信頼境界です。

## 既知の実装上の制約

- chassis_db への接続切断は ASIC 間の neighbor / system port 情報の同期を止め、データプレーンの forwarding は維持しつつ control plane は段階的に古い状態を信用する設計です。長時間の切断は警告のみで自動 reboot にはなりません。
- VOQ chassis では、各 ASIC の `CONFIG_DB` を**共通設定として一括反映**する仕組みが limited で、運用者は per-asic の [config_db.json](../../reference/glossary.md#term-config_db.json) + chassis 全体 minigraph の二段管理になります。
- Multi-ASIC pizza-box（VOQ ではなく packet mode の multi-[NPU](../../reference/glossary.md#term-npu)）は LAG / [VLAN](../../reference/glossary.md#term-vlan) が ASIC を跨げないため、サブインタフェース化や PE-CE モデルで運用されます。
- BGP は per-asic で独立した FRR process が走り、internal BGP（iBGP）で ASIC 間を結ぶ構成が一般的。external BGP の view を一つにする abstraction は SONiC master にはありません。
- `show` 系 CLI は `--namespace` を取らない場合に host namespace から各 namespace に exec する構造で、多 ASIC では出力が長くなり、collect 時にエラーが部分的に出ても全体が成功扱いになる落とし穴があります。

## chassis_db / system port の同期

`chassis_db` は線カード (LC) / supervisor (SUP) 間で system-wide な状態を共有する Redis インスタンスで、各 ASIC namespace の `CONFIG_DB` / `APPL_DB` とは別に SUP 上に置かれます。同期対象は次の通りです。

| テーブル | 役割 |
| --- | --- |
| `SYSTEM_PORT_TABLE` | chassis 全体での system port ID 割当（VOQ 設計上の必須） |
| `SYSTEM_NEIGH_TABLE` | 全 LC 共有の neighbor entry |
| `SYSTEM_LAG_TABLE` | chassis 跨ぎ LAG（VOQ chassis only） |
| `SYSTEM_LAG_MEMBER_TABLE` | chassis 跨ぎ LAG のメンバー port 情報[^lagorch-chassis] |

`SystemPortOrch` / `SystemNeighOrch` が chassis_db を subscribe して、自 ASIC の `SAI_OBJECT_TYPE_SYSTEM_PORT` を作成 / 更新します。chassis_db 自体は SUP 上の Redis で、LC 側からは TCP で接続します（接続切断時は前述の段階的劣化）。

## fabric link 監視と `FabricPortsOrch`

VOQ chassis では fabric port が線カード間の中継を担い、`FabricPortsOrch` がその状態を監視します。

| 状態 | 検出 | 反映先 |
| --- | --- | --- |
| `FABRIC_ATTACHED` | SAI port attribute から fabric 接続済みか | `STATE_DB:FABRIC_PORT_TABLE` |
| `FABRIC_REACHABILITY` | 各 fabric switch への到達性 | `CHASSIS_STATE_DB:FABRIC_ASIC_TABLE` |
| `isolated` | port が isolation domain にあるか | counter / `show fabric` |

fabric link の flap は `SAI_PORT_ATTR_FABRIC_ATTACHED` の poll で取得され、`isolationPollsCfg`（既定値 `ISOLATION_POLLS_CFG`）連続で error が観測されると auto-isolation 判定が走ります[^fabric-iso]. chassis 全体の health を `chassisd` が `CHASSIS_STATE_DB:LINECARD_TABLE` で集約します。CLI からは `show fabric reachability` / `show fabric isolation` で状態を確認できます[^show-fabric].

## per-ASIC FRR と internal BGP の構成

VOQ chassis では各 ASIC namespace で独立した FRR が動き、ASIC 間は internal BGP（多くは iBGP over loopback over inband）でつなぐ構成が標準です。

| 観点 | 説明 |
| --- | --- |
| AS 番号 | 同一（iBGP） |
| nexthop | inband interface 経由の loopback |
| advertise | 外部 BGP の view は per-asic、abstraction なし |
| convergence | ASIC 間で routes が異なる時間帯が存在しうる |

`minigraph.xml` の `<BGPSessions>` セクションで internal session が定義され、`bgpcfgd` per-namespace が反映します。abstraction が必要な運用では Route Reflector を SUP 上に立てる構成が `BGP setup for VOQ chassis` [HLD](../../reference/glossary.md#term-hld) に書かれています。

## 関連ページ

- [VOQ SONiC](../../platform/voq-sonic.md)
- [Single ASIC VOQ fixed system](../../platform/single-asic-voq-fixed-system-sonic.md)
- [SONiC on multi-ASIC platforms](../../platform/1-sonic-on-multi-asic-platforms.md)
- [DB design for multi-ASIC scenarios](../../platform/db-design-for-multi-asic-scenarios.md)
- [Multi-ASIC warm reboot](../../system/multi-asic-warm-reboot.md)
- [Aggregate VOQ counters in SONiC](../../internals/aggregate-voq-counters-in-sonic.md)
- [BGP setup for VOQ chassis](../../routing/bgp-setup-for-voq-chassis.md)

[^orch-main]: `gMySwitchType == "voq"` のとき `SAI_SWITCH_ATTR_TYPE = SAI_SWITCH_TYPE_VOQ` / `SAI_SWITCH_ATTR_SWITCH_ID` / `SAI_SWITCH_ATTR_MAX_SYSTEM_CORES` / `SAI_SWITCH_ATTR_SYSTEM_PORT_CONFIG_LIST` を switch create 時に渡す。sonic-net/[sonic-swss](../../reference/glossary.md#term-sonic-swss) `orchagent/main.cpp` L688-720 (ref `4305596156d7`).
[^neighorch]: VOQ switch では `CHASSIS_APP_SYSTEM_NEIGH_TABLE_NAME` を `chassisAppDb` 上に open し、リモート neighbor の同期に用いる。sonic-net/sonic-swss `orchagent/neighorch.cpp` L54-61, L887 (ref `4305596156d7`).
[^fabric-iso]: `isolationPollsCfg` のデフォルトは `ISOLATION_POLLS_CFG`、`CONFIG_DB:FABRIC_MONITOR` から override 可能。`consecutivePollsWithErrors >= isolationPollsCfg` で auto-isolation 状態に遷移する。sonic-net/sonic-swss `orchagent/fabricportsorch.cpp` L436-475, L787-906 (ref `4305596156d7`).
[^show-fabric]: `show fabric reachability` は `fabricstat -r`、`show fabric isolation` は `fabricstat -i` を実行する click group。sonic-net/[sonic-utilities](../../reference/glossary.md#term-sonic-utilities) `show/fabric.py` L33-50 (ref `39732bceb8bd`).
[^lagorch-chassis]: VOQ chassis では [PortChannel](../../reference/glossary.md#term-portchannel) の add / member 変更時に `SYSTEM_LAG_TABLE` / `SYSTEM_LAG_MEMBER_TABLE` を `CHASSIS_APP_DB` 上で更新する。sonic-net/sonic-swss `orchagent/portsorch.cpp` L8037, L8114 (ref `4305596156d7`).

<!-- glossary-links-injected: 889740d66e5f -->
