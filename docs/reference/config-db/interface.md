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

<!-- ordering -->
## 書込み順依存 (Phase B)

### 他テーブル先行必須

| 前提テーブル / 状態 | チェック担当 | 条件未満時の挙動 |
|-------------------|------------|----------------|
| `PORT` → STATE_DB `PORT_TABLE` に `state=ok` | `intfmgr.cpp` `isIntfStateOk()` | SET をスキップしてキューに残す (`return false`) |
| `PORTCHANNEL` → STATE_DB `LAG_TABLE` に ready | 同 `isIntfStateOk()` | 同上 |
| `VRF` → STATE_DB `VRF_TABLE` に ready | `doIntfGeneralTask()` L839–843 | `vrf_name` 指定時に追加チェック。未 ready なら skip |
| `VNET` → orchagent が VNET オブジェクトを保持 | `intfsorch.cpp` `isVnetExists()` | `it++; continue` でリトライ |
| portsorch の `allPortsReady()` | `IntfsOrch::doTask()` L665 | 全ポート ready 前は INTERFACE の SAI 処理全体をブロック |

### SET 後 DEL 順序

1. **IP プレフィクスロウ DEL が先**: 属性ロウ (`INTERFACE|EthernetN`) を DEL する前に、  
   IP プレフィクスロウ (`INTERFACE|EthernetN|<ip/pfx>`) を全件 DEL しなければならない。  
   残っている間は `getIntfIpCount()` が非ゼロを返し DEL が `return false` でブロックされ続ける  
   (`intfmgr.cpp` L1060–1063)。

2. **VRF 変更は 2 ステップ必須**: `vrf_name` を別の VRF 名に直接書き換えると  
   `isIntfChangeVrf()` が検出してエラーログを出力しエントリを破棄する。  
   正しい手順: ① `vrf_name` を空にした SET (VRF 除去) → ② 新 VRF 名で SET  
   (`intfmgr.cpp` L846–849)。

### Notification 順

```
CONFIG_DB INTERFACE SET
  → intfmgrd: isIntfStateOk(port) + isIntfStateOk(vrf) 確認
  → APP_DB INTF_TABLE SET (属性ロウ)
  → STATE_DB INTERFACE_TABLE hset(alias, "vrf", ...)
  → IntfsOrch: APP_DB 変化受信 → addRouterIntfs() → SAI create_router_interface
  ※ IP プレフィクスロウは isIntfCreated(alias) (STATE_DB 確認) 成功後に
    APP_DB INTF_TABLE SET でプレフィクスを送出 (intfmgr.cpp L1115)
```

### select() ポーリング

- `intfmgrd` は `SELECT_TIMEOUT=1000ms` 周期でタイムアウトごとに `doTask()` を再試行する。
- 依存関係が未解消の Consumer エントリは `it++` でキューに残り、次サイクルで再試行される。
- warm-reboot 時は `m_pendingReplayIntfList` が全件完了するまで `RECONCILED` 状態に移行しない。

### 起動時 boot order

- 通常起動: `intfmgrd` コンストラクタが `flushLoopbackIntfs()` を実行してカーネルのダミーデバイスをクリア。
- `IntfsOrch::doTask()` は `gPortsOrch->allPortsReady()` が真になるまで全 INTERFACE 処理を遅延する。  
  つまり `portmgrd → portsorch` によるポート初期化が完了しないと、L3 IF の SAI 作成は開始されない。

### warm-reboot 影響

- warm-start 中: `flushLoopbackIntfs()` をスキップし、カーネルの IP 設定を保持したままリプレイする。
- `buildIntfReplayList()` が `INTERFACE` / `LOOPBACK_INTERFACE` / `VLAN_INTERFACE` / `LAG_INTERFACE` の全キーをリストアップし、再処理完了ごとにリストから除去する。
- pending リストが空になった時点で `WarmStart::RECONCILED` に遷移する。
- ポート ready 通知が遅延した場合、エントリは 1000ms 周期でリトライされ続ける。

<!-- /ordering -->

<!-- glossary-links-injected: 8c01908c2492 -->
