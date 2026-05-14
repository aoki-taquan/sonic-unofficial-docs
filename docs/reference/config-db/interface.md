---
title: INTERFACE テーブル
description: "INTERFACE テーブル — 物理 Ethernet ポート (PORT) を L3 IF として扱う設定を保持する。VRF / VNET binding、IP アサイン、NAT zone、MPLS、IPv6 link-local モード、MAC を持つ。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-interface.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - INTERFACE
    - PORT
    - VRF
  cli:
    - config interface
  yang:
    - sonic-interface
---

# INTERFACE テーブル

## 概要

物理 Ethernet ポート (`PORT`) を L3 IF として扱う設定を保持する。[VRF](../../reference/glossary.md#term-vrf) / [VNET](../../reference/glossary.md#term-vnet) binding、IP アサイン、[NAT](../../reference/glossary.md#term-nat) zone、[MPLS](../../reference/glossary.md#term-mpls)、IPv6 link-local モード、MAC を持つ[^1]。VLAN_MEMBER に登録された port は L2 として扱われるため `INTERFACE` には登録できない（VLAN_MEMBER 側の `must` で除外される）。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>INTERFACE")]
  DM["intfmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_INTF_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_router_intf_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
INTERFACE|<name>                       # 属性ロウ
INTERFACE|<name>|<ip_prefix>           # IP プレフィクス
```

`<name>` は `PORT.name` への leafref。

## 属性ロウのフィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | leafref `PORT.name` | ✅ | - | 物理ポート名 |
| `vrf_name` | leafref `VRF.name` | - | - | バインドする [VRF](../../reference/glossary.md#term-vrf) |
| `vnet_name` | leafref `VNET.name` | - | - | バインドする [VNET](../../reference/glossary.md#term-vnet) |
| `nat_zone` | uint8 (0..3) | - | `0` | [NAT](../../reference/glossary.md#term-nat) zone |
| `mpls` | enum `enable`/`disable` | - | - | [MPLS](../../reference/glossary.md#term-mpls) routing |
| `ipv6_use_link_local_only` | `mode-status` | - | `disable` | IPv6 link-local のみ |
| `mac_addr` | mac-address | - | - | 管理者指定 MAC |
| `loopback_action` | `loopback_action` | - | - | ingress→same-IF routing 動作 |

## IP プレフィクスロウ

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `name` (key) | leafref `PORT.name` | ✅ | ポート名 (`INTERFACE_LIST` に存在することが `must` で要求) |
| `ip-prefix` (key) | union (v4/v6 prefix) | ✅ | IP/プレフィクス |
| `scope` | enum `global`/`local` | - | アドレススコープ |
| `family` | `ip-family` (`IPv4`/`IPv6`) | - | アドレスファミリ。`ip-prefix` の `:` / `.` と整合する `must` |

## 購読者

- `intfmgrd`: [VRF](../../reference/glossary.md#term-vrf) / MAC / [MPLS](../../reference/glossary.md#term-mpls) / IPv6 LL を Linux に反映
- `orchagent` `IntfsOrch`: [SAI](../../reference/glossary.md#term-sai) ルータインタフェースを生成
- `natmgrd`: `nat_zone` を利用

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `PORT`、`VRF`、`VNET`、`VLAN_MEMBER`（排他）
- 関連 CLI: `config interface ip add/remove`、`config interface vrf bind/unbind`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-interface`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-interface`](../yang/sonic-interface.md)
- CLI: [`config interface`](../cli/config-interface.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-interface.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-interface.yang>

## 関連ページ
- [HLD: VRF サポート](../../routing/sonic-vrf-support-design-spec-draft.md)
- [CLI: config interface](../cli/config-interface.md)
- [CONFIG_DB: PORT](port.md)
- [YANG: sonic-interface](../yang/sonic-interface.md)

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: L2 / VLAN / LAG / MC-LAG](../../topics/06-l2-vlan-lag/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `INTERFACE|EthernetN` (L3 enable 行) と `INTERFACE|EthernetN|<ip/prefix>` (IP 行)。
- `vrf_name`: `Vrfdefault` か `Vrf<name>`。

### よくある誤設定

- [VLAN](../../reference/glossary.md#term-vlan) メンバになっているポートを `INTERFACE` で L3 化すると [orchagent](../../reference/glossary.md#term-orchagent) が拒否する。VLAN_MEMBER から外してから。
- IPv6 link-local だけ欲しい場合でも L3 enable 行が必要。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'INTERFACE|Ethernet0*'
show ip interfaces
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `mpls`

| 値 | 挙動 |
|----|------|
| `enable` | `ip link set mpls on` → Linux MPLS ルーティングを有効化 |
| `disable`（または空） | MPLS 無効化 |
| その他 | `SWSS_LOG_ERROR("MPLS state is invalid")` → 設定適用されない |

### `ipv6_use_link_local_only`

| 値 | 挙動 |
|----|------|
| `enable` | IPv6 link-local only モード有効化。`m_ipv6LinkLocalModeList` に追加 |
| `disable`（デフォルト） | link-local only モード解除。グローバルアドレス割り当て可能 |

### `admin_status`

| 値 | 挙動 |
|----|------|
| `up` | インタフェース UP |
| `down` | インタフェース DOWN |
| その他 | `SWSS_LOG_WARN` → `up` にデフォルト（intfmgr.cpp L867） |

### `loopback_action`

| 値 | 挙動 |
|----|------|
| `drop` | `SAI_PACKET_ACTION_DROP`：ingress → 同 IF 宛パケットを破棄 |
| `forward` | `SAI_PACKET_ACTION_FORWARD`：通常転送 |
| 未設定 | SAI プラットフォームデフォルト動作 |

### `scope`（IP プレフィクスロウ）

| 値 | 挙動 |
|----|------|
| `global` | グローバルスコープアドレス（intfmgrd が APP_DB に `scope=global` を書く） |
| `local` | ローカルスコープアドレス |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-swss/cfgmgr/intfmgr.cpp -->

| 条件 | 挙動 |
|------|------|
| IPv6 有効化失敗 | `SWSS_LOG_ERROR("Failed to enable IPv6 on interface %s")` → 処理継続・再試行あり |
| `admin_status` に `up`/`down` 以外の値 | `SWSS_LOG_WARN` → `up` にデフォルト（intfmgr.cpp L867） |
| `mpls` に `enable`/`disable` 以外の値 | `SWSS_LOG_ERROR("MPLS state is invalid")` → MPLS 設定適用されない |
| 別 VRF への直接変更 | `SWSS_LOG_ERROR("%s can not change to %s directly, skipping")` → VRF 除去 → 再設定の 2 ステップが必要 |
| interface / VRF が未 ready | `SWSS_LOG_DEBUG("Interface is not ready, skipping %s")` → Consumer キューに残り再試行 |
| `grat_arp` / `proxy_arp` に不正値 | `SWSS_LOG_ERROR("GARP state is invalid")` / `"Proxy ARP state is invalid"` → 設定適用されない |
| サブインターフェース名が不正 | `SWSS_LOG_ERROR("Invalid subnitf: %s")` → エントリスキップ |
| MTU 設定コマンド失敗 | `SWSS_LOG_WARN("Setting mtu to %s netdev failed")` → warn のみ、旧 MTU のまま継続 |

<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`intfmgrd` → `IntfsOrch` (APPL_DB 経由) が CONFIG_DB の `INTERFACE` テーブルを購読する。

`INTERFACE` の key は `<intf_name>|<ip_prefix>` または `<intf_name>` (intf 属性のみ)。physical port の L3 設定。

### 段階 2 — CFG→APPL 翻訳

`APP_INTF_TABLE` に書き込み (IP address 付き router interface)

### 段階 3 — APPL→SAI

`sai_router_intf_api` — router interface を作成/更新 + `sai_neighbor_api` で ネイバー設定

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `intfmgrd` が検知後 `APP_INTF_TABLE` に書き込み。`IntfsOrch` が APPL_DB を購読して SAI router interface を作成/更新。IP address 追加は即時反映。

**副作用**: IP address 追加は ARP/NDP 送信を開始。IP address 削除は関連する ARP エントリと neighbor を削除。MTU 変更は PMTUD に影響。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `INTERFACE`

### CLI
- `config interface ip add/remove <port> <ip/prefix>`
- `config interface vrf bind/unbind <port> <vrf>`
  - ソース: `sonic-utilities/config/main.py (interface グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- sonic-mgmt-common OpenConfig interfaces 経由 (xfmr_intf.go)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `sonic-cfggen -m` で minigraph から L3 インタフェース IP を生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
<!-- /entry-points -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

### Producer/Consumer ペア

CONFIG_DB から SAI までの全通信は Redis の **keyspace notification** と **ProducerStateTable/ConsumerStateTable** パターンで構成される。

#### CONFIG_DB → intfmgrd

`intfmgrd` は起動時に以下のテーブルを `SubscriberStateTable` で購読する。

| テーブル | 用途 |
|---------|------|
| `INTERFACE` | 物理 L3 IF 属性・IP プレフィクス |
| `VLAN_INTERFACE` | VLAN L3 IF |
| `LAG_INTERFACE` | PortChannel L3 IF |
| `LOOPBACK_INTERFACE` | Loopback IF |
| `VLAN_SUB_INTERFACE` | サブインタフェース |
| `VOQ_INBAND_INTERFACE` | VOQ inband IF |

`SubscriberStateTable` は Redis の **keyspace notification** を用いる。

```
PSUBSCRIBE __keyspace@{db_id}__:INTERFACE|*
```

イベント (`hset` / `hdel` / `del`) 受信 → `readData()` がバッファに蓄積 → `pops()` でキーを取り出し `TABLE.get(key)` で現在値取得 → `Consumer::doTask()` 呼び出し。

また、PORT / LAG の状態変化を検知するために STATE_DB の `STATE_PORT_TABLE` と `STATE_LAG_TABLE` も別途 `SubscriberStateTable` で購読する（親ポートの admin_status・MTU 変化をサブインタフェースに伝播）。

#### intfmgrd → APPL_DB

処理完了後、`ProducerStateTable m_appIntfTableProducer` で `APP_INTF_TABLE` に書き込む。

| 項目 | 値 |
|------|----|
| Publish チャンネル | `APP_INTF_TABLE_CHANNEL@0` |
| Key SET | `APP_INTF_TABLE_KEY_SET` |
| Del SET | `APP_INTF_TABLE_DEL_SET` |
| 一時 hash | `_APP_INTF_TABLE:<key>` |

Lua スクリプト (`EVALSHA`) が `SADD KEY_SET` + `HSET _<table>:<key>` + `PUBLISH APP_INTF_TABLE_CHANNEL@0 G` をアトミックに実行する。

#### APPL_DB → orchagent (IntfsOrch)

`orchdaemon` が `IntfsOrch(m_applDb, APP_INTF_TABLE_NAME, ...)` を生成し、`ConsumerStateTable` が `APP_INTF_TABLE_CHANNEL@0` を購読する。

```
WATCH APP_INTF_TABLE_KEY_SET
SUBSCRIBE APP_INTF_TABLE_CHANNEL@0
```

チャンネル通知で `Select::select()` が wake-up → `consumer_state_table_pops.lua` (`SPOP KEY_SET` + `HGETALL _<table>:<key>`) で一括取得 → `IntfsOrch::doTask()` → `sai_router_intf_api`。

### STATE_DB への書き込み (hset / TTL)

`intfmgrd` は以下のタイミングで STATE_DB (`STATE_INTERFACE_TABLE`) に書き込む。TTL は使用しない。

| タイミング | 操作 |
|-----------|------|
| L3 IF 属性設定完了 | `m_stateIntfTable.hset(alias, "vrf", vrf_name)` |
| IP アドレス追加完了 | `m_stateIntfTable.hset("<alias>\|<prefix>", "state", "ok")` |
| IP アドレス削除 | `m_stateIntfTable.del("<alias>\|<prefix>")` |
| L3 IF 削除 | `m_stateIntfTable.del(alias)` |

`isIntfCreated(alias)` は `m_stateIntfTable.get(alias, ...)` で STATE_DB エントリの有無を確認し、IP アドレス設定の前提条件チェックに用いる。

### select() ループと retry

`intfmgrd` の main ループはタイムアウト 1000 ms で `Select::select()` を呼ぶ。

```
SELECT_TIMEOUT = 1000 ms
if (TIMEOUT) { intfmgr.doTask(); }   // 未処理タスクを全 consumer で再試行
```

`doIntfGeneralTask` / `doIntfAddrTask` が `false` を返した場合（IF/VRF が not ready）、エントリは `m_toSync` に残留し次のループで再試行される。

### cross-namespace 通信 (VOQ / Chassis)

VOQ システム (`isChassisDbInUse()` が真) では `CHASSIS_APP_DB` の `SYSTEM_INTERFACE_TABLE` も `SubscriberStateTable` で購読し、リモートシステムポートの IF 情報を受信する。通常の単体スイッチでは使用されない。

### 通信フロー全体図

```
CONFIG_DB[INTERFACE|*]
  │  keyspace notification (psubscribe __keyspace@N__:INTERFACE|*)
  ▼
intfmgrd::doIntfGeneralTask / doIntfAddrTask
  │  ProducerStateTable::set/del
  │  EVALSHA → SADD KEY_SET + HSET _APP_INTF_TABLE:key
  │            + PUBLISH APP_INTF_TABLE_CHANNEL@0 G
  ▼
APPL_DB[APP_INTF_TABLE|*]
  │  ConsumerStateTable (subscribe APP_INTF_TABLE_CHANNEL@0)
  │  consumer_state_table_pops.lua → SPOP + HGETALL
  ▼
orchagent::IntfsOrch::doTask
  ▼
sai_router_intf_api (SAI)

STATE_DB[STATE_INTERFACE_TABLE]
  ← intfmgrd hset(vrf) / hset(state=ok)  ← TTL なし

STATE_DB[STATE_PORT_TABLE / STATE_LAG_TABLE]
  → SubscriberStateTable → intfmgrd::doPortTableTask
    (admin_status / MTU 変化をサブインタフェースへ伝播)
```

<!-- /pubsub -->
<!-- glossary-links-injected: 8c01908c2492 -->
