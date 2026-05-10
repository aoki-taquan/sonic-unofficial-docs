---
title: MCLAG Enhancements（dynamic config / unique IP / isolation group / static MAC）
area: switching
verification: hld-only
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/mclag/MCLAG_Enhancements_HLD.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - MCLAG_DOMAIN
    - MCLAG_INTERFACE
    - MCLAG_UNIQUE_IP
  cli:
    - config mclag
    - show mclag
  yang: []
---

!!! info "裏取りステータス: HLD-only"
    HLD は Rev 0.1。`MclagSyncd` の現行 master 実装、`STATE_MCLAG_*` テーブル、`ISOLATION_GROUP_TABLE`、`APP_MCLAG_FDB_TABLE` の SWSS / FdbOrch コードパス、`config mclag` Click CLI / SONiC CLI の sonic-utilities 取り込みは未確認。

# MCLAG Enhancements（dynamic config / unique IP / isolation group / static MAC）

> 大きな HLD（42 KB）。本ページは architecturally distinctive な要素に絞る。詳細は HLD `doc/mclag/MCLAG_Enhancements_HLD.md` を参照。

## 概要

MCLAG（Multi-Chassis Link Aggregation）は 2 台のスイッチが **互いに peer** となり、下流ホストから見ると 1 個の LAG（ICCP 同期）として振る舞う冗長構成。本 HLD はそれを以下の側面で拡張する[^1]:

1. **dynamic configuration of MCLAG**（再起動なしで domain / mclag_interface を CONFIG_DB から触れる）
2. **keep-alive / session timeout の動的設定**
3. **static MAC** の MCLAG ピア間同期
4. **ICCP 学習 MAC の aging disable**
5. **MAC sync 最適化** によるパフォーマンス改善
6. **isolation group** で peer 経由の重複転送を抑止
7. **unique IP** で MCLAG VLAN interface 上の L3 プロトコル（OSPF 等）対応

## 動作仕様

### CONFIG_DB の主要テーブル

```
MCLAG_DOMAIN|<domain_id>
  source_ip      = <my IP>
  peer_ip        = <peer IP>
  peer_link      = <portchannel or interface name>
  keepalive_interval = <sec>
  session_timeout    = <sec>

MCLAG_INTERFACE|<domain_id>|<intf>     # MCLAG メンバになる LAG
  if_type = "PortChannel"

MCLAG_UNIQUE_IP|<vlan_intf>
  unique_ip = "enable"                  # この VLAN intf を unique IP モードで動かす
```

### ISOLATION group / APPL_DB

```
ISOLATION_GROUP_TABLE:<group_id>
  members = "<port>,..."
  description = "..."

APP_LAG_TABLE:<lag>          # 既存 + MCLAG 状態
APP_MCLAG_FDB_TABLE:<vlan>:<mac>
  port = "<port>"
  type = "static" | "dynamic"
  mclag = "remote" | "local"
```

### STATE_DB

```
STATE_MCLAG_TABLE|<domain>
  oper_status = "up" | "down"
  peer_link_status = ...

STATE_MCLAG_REMOTE_INTF_TABLE|<intf>
STATE_MCLAG_REMOTE_FDB_TABLE|<vlan>:<mac>
```

### 全体構造

```mermaid
flowchart LR
  subgraph S0[Switch 0 (Active)]
    CFG0[CONFIG_DB MCLAG_*]
    ICC0[iccpd]
    MS0[MclagSyncd]
    APP0[APPL_DB APP_MCLAG_FDB_TABLE]
    OR0[FdbOrch / PortsOrch / IsolGroupOrch]
    SAI0[ASIC]
  end
  subgraph S1[Switch 1]
    CFG1[CONFIG_DB MCLAG_*]
    ICC1[iccpd]
    MS1[MclagSyncd]
    APP1[APPL_DB APP_MCLAG_FDB_TABLE]
    OR1[FdbOrch / PortsOrch / IsolGroupOrch]
    SAI1[ASIC]
  end
  CFG0 --> ICC0
  ICC0 <-->|ICCP messages over peer-link| ICC1
  ICC0 --> MS0
  MS0 --> APP0
  APP0 --> OR0
  OR0 --> SAI0
  CFG1 --> ICC1
  ICC1 --> MS1
  MS1 --> APP1
  APP1 --> OR1
  OR1 --> SAI1
```

要点[^1]:

- **`iccpd`**（FRR 由来 / SONiC 内 daemon）が ICCP メッセージで peer と同期
- **`MclagSyncd`** が ICCP からの MAC / interface state を APPL_DB に橋渡し
- 旧版で MclagSyncd 内に持っていた **FDB table はリファクタで撤廃**（APPL_DB の `APP_MCLAG_FDB_TABLE` に集約）[^1]

### Static MAC

旧来は dynamic MAC のみ ICCP 同期されていた。本拡張で **static MAC** も同期対象に。FdbOrch が CONFIG_DB の static MAC を受けたら ICCP 経由で peer にも reflect[^1]。

### Unique IP for MCLAG VLAN interface

通常 MCLAG では 2 台の VLAN interface に同じ仮想 IP を持たせる構成が一般的だが、その上で OSPF 等の L3 プロトコルを動かすと隣接形成に問題が出る。**unique IP** モードはこの interface に **個別の IP** を割り当てて L3 隣接を可能にする[^1]:

```
MCLAG_UNIQUE_IP|Vlan100
  unique_ip = "enable"
```

### Isolation Group

MCLAG 構成では peer-link 経由で MAC 学習が双方向に伝播するため、**peer-link の port を MCLAG メンバ port group から isolate** して ループ / 重複転送 を防ぐ[^1]:

```
ISOLATION_GROUP_TABLE:<id>
  members = "PortChannel0001,PortChannel0002,..."   # MCLAG メンバ
  exclude = "<peer-link>"
```

SAI 側では `SAI_OBJECT_TYPE_ISOLATION_GROUP` 系で実装される（HLD で詳述）[^1]。

### Aging disable for ICCP-learned MAC

remote (peer 由来) で学習した MAC は **local の aging timer で消されてはいけない**[^1]。FdbOrch / kernel への hint で aging を無効化する。

### Performance: MAC sync 最適化

MAC bulk 同期、差分のみ転送等の最適化[^1]。多数 VLAN で MCLAG を構成する場合の収束時間短縮が狙い。

<!-- evidence:
source: sonic-net/SONiC/doc/mclag/MCLAG_Enhancements_HLD.md#L19-L29 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  Dynamic configuration of MCLAG / mclag_interface
  Keep-alive timer configuration / Session timeout configuration
  Static MAC support / Aging disable for ICCP learned MAC addresses
  Performance improvements / Isolation group support / Unique IP enhancements
reasoning: 9 つの拡張項目の根拠。
-->

## 設定

### 関連する CONFIG_DB

| Table | Key | フィールド |
|-------|-----|------------|
| `MCLAG_DOMAIN` | `<domain_id>` | `source_ip`, `peer_ip`, `peer_link`, `keepalive_interval`, `session_timeout` |
| `MCLAG_INTERFACE` | `<domain_id>\|<intf>` | `if_type` |
| `MCLAG_UNIQUE_IP` | `<vlan_intf>` | `unique_ip` |

### 関連する CLI

`config mclag domain ...`、`config mclag member add ...`、`show mclag brief / detail`（具体名は実装側で確認）。

### 設定例

```bash
config mclag add 1 10.0.0.1 10.0.0.2 PortChannel999
config mclag member add 1 PortChannel0001
config mclag unique-ip add Vlan100

show mclag brief
show mclag intf-list
```

## 制限事項

- HLD は Rev 0.1 で日付欄空欄
- ICCP は **2 台ピアまで**（3-way 以上は未対応）
- isolation group は SAI 対応必要。未対応 ASIC では peer-link 経由のループ抑止は別手法に依存
- unique IP モードでは active/active 両方が L3 で見える。ルーティング設計（OSPF cost / BGP)) を peer 間で揃える必要
- 大量の static MAC sync は ICCP メッセージ量を増やすので scalability 影響あり

## 干渉する機能

- **iccpd**: ICCP 自体は別文書。Keep-alive / session timeout はここの動作と直結
- **FdbOrch / PortsOrch**: MAC 学習・aging の SONiC 側統合
- **VRRP / OSPF / BGP**: unique IP 経由で L3 隣接を組む際に整合
- **VXLAN / EVPN MH**: 別の冗長機構。MCLAG と直接の併用は稀
- **L3 PortChannel / sub-interface**: MCLAG-LAG 上の L3 の挙動

## トラブルシューティング

```bash
show mclag brief
redis-cli -n 6 HGETALL "STATE_MCLAG_TABLE|1"

# remote MAC が来ているか
redis-cli -n 6 KEYS "STATE_MCLAG_REMOTE_FDB_TABLE|*" | head

# MCLAG_FDB
redis-cli -n 0 KEYS "APP_MCLAG_FDB_TABLE:*" | head

# Isolation group
redis-cli -n 0 HGETALL "ISOLATION_GROUP_TABLE:1"
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/mclag/MCLAG_Enhancements_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
