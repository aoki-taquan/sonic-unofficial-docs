---
title: VLAN テーブル
description: "VLAN テーブル — IEEE 802.1Q VLAN を CONFIG_DB で定義するテーブル。VLAN 名 (Vlan100 形式) をキーに、VLAN ID、DHCP リレーサーバ、MTU、admin status、MAC、エイリアスを保持する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-vlan.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - VLAN
    - VLAN_MEMBER
    - VLAN_INTERFACE
  cli:
    - config vlan
  yang:
    - sonic-vlan
---

# VLAN テーブル

## 概要

IEEE 802.1Q [VLAN](../../reference/glossary.md#term-vlan) を [CONFIG_DB](../../reference/glossary.md#term-config_db) で定義するテーブル。[VLAN](../../reference/glossary.md#term-vlan) 名 (`Vlan100` 形式) をキーに、[VLAN](../../reference/glossary.md#term-vlan) ID、DHCP リレーサーバ、MTU、admin status、MAC、エイリアスを保持する[^1]。`VLAN_MEMBER` と組合わせてポート割当てを、`VLAN_INTERFACE` と組合わせて L3 IF を構成する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>VLAN")]
  DM["vlanmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_VLAN_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_vlan_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
VLAN|<name>
```

`<name>` は `Vlan<id>` (id 範囲 2..4094)。

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | string `Vlan<2..4094>` | ✅ | - | VLAN 名 |
| `vlanid` | uint16 (2..4094) | - | - | VLAN ID。`name` 末尾と一致しなければならない (`must`) |
| `alias` | string | - | - | ユーザ別名 |
| `description` | string (1..255) | - | - | 説明 |
| `dhcp_servers` | leaf-list ip-address | - | - | DHCPv4 リレー先 |
| `dhcpv6_servers` | leaf-list ipv6-address | - | - | DHCPv6 リレー先 |
| `mtu` | uint16 (1..9216) | - | - | MTU |
| `admin_status` | `admin_status` | - | - | 管理状態 |
| `mac` | mac-address | - | - | VLAN 上の MAC |

## 制約

- `vlanid` は `name` の数値部分と一致しなければならない (`substring-after(../name, 'Vlan') = current()`)

## 購読者

- `vlanmgrd`: VLAN 作成・MTU・admin_status をモニタし Linux bridge に反映
- `orchagent` の `VlanMgr` / `VRouterOrch`: [SAI](../../reference/glossary.md#term-sai) bridge / VLAN を構成
- `dhcprelayd` (`sonic-dhcp-relay`): `dhcp_servers` / `dhcpv6_servers` を読み出して relay agent を構成

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `VLAN_MEMBER`、`VLAN_INTERFACE`、`DHCP_RELAY`
- 関連 CLI: `config vlan` (add / del / member / dhcp_relay)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-vlan`

<!-- constants -->
## ハードコード定数

| 定数 | 値 | 定義箇所 | 備考 |
|------|-----|----------|------|
| `DEFAULT_MTU_STR` | `"9100"` | vlanmgr.cpp:19 | MTU 省略時に APP_DB へ注入するデフォルト値（バイト）。Bridge 初期化にも適用 |
| `DEFAULT_VLAN_ID` | `"1"` | vlanmgr.cpp:18 | Bridge 初期化時に削除する IEEE 802.1Q デフォルト VLAN（`bridge vlan del vid 1`）|
| `DOT1Q_BRIDGE_NAME` | `"Bridge"` | vlanmgr.cpp:15 | Linux dot1q ブリッジデバイス名（固定文字列）|
| `VLAN_PREFIX` | `"Vlan"` | vlanmgr.cpp:16 | VLAN インタフェース名プレフィクス。キー長チェックに `4` バイトとして使用 |
| `LAG_PREFIX` | `"PortChannel"` | vlanmgr.cpp:17 | LAG インタフェース名プレフィクス。`VLAN_MEMBER` 追加時のレースコンディション判定（PortChannel vs Ethernet の挙動分岐）に使用 |
| `VLAN_HLEN` | `4` | vlanmgr.cpp:20 | IEEE 802.1Q ヘッダ長（バイト）— 定義のみ・ファイル内未参照（dead define）|
| `MAX_VALID_VLAN_ID` | `4094` | portsorch.cpp:82 | サブインタフェース VLAN ID 上限。YANG `range 2..4094` と一致 |
| `DEFAULT_SYSTEM_PORT_MTU` | `9100` | portsorch.cpp:79 | portsorch 側の MTU 初期値。vlanmgr.cpp の `DEFAULT_MTU_STR` とは独立定義 |
| UUC/BC flooding デフォルト | `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL` | portsorch.cpp:7409-7410 | `create_vlan()` 時の初期 flooding 制御型。プラットフォーム SAI で上書き可能 |
| YANG `vlanid` range | `2..4094` | sonic-vlan.yang:225 | YANG バリデーション範囲。`pattern` も同範囲を正規表現で表現 |
| YANG `mtu` range | `1..9216` | sonic-vlan.yang:257 | MTU 許容範囲。`DEFAULT_MTU_STR=9100` はこの範囲内 |
| YANG `description` length | `1..255` | sonic-vlan.yang:239 | 説明フィールド最大文字数 |
| YANG `nat_zone` range | `0..3` (default `0`) | sonic-vlan.yang:105 | VLAN_INTERFACE の NAT ゾーン番号範囲 |
| `arp_evict_nocarrier` 設定値 | `0` | vlanmgr.cpp:139 | VLAN IF 作成後に `/proc/sys/net/ipv4/conf/Vlan<N>/arp_evict_nocarrier` へ書き込む値 |

<!-- /constants -->

<!-- defaults -->
## コード由来の暗黙デフォルト

| フィールド | YANG default | コード実装デフォルト | 出典 |
|-----------|-------------|---------------------|------|
| `admin_status` | なし | `"up"` — フィールド省略時に `fvVector` へ自動補完 (vlanmgr.cpp:424) | vlanmgrd |
| `mtu` | なし | `9100` (`DEFAULT_MTU_STR`) — 省略時に APP_DB へ注入 (vlanmgr.cpp:19,357,428) | vlanmgrd |
| `mac` | なし | `gMacAddress`（スイッチ MAC）— 省略時に APP_DB へ注入 (vlanmgr.cpp:358) | vlanmgrd |
| `vlanid` | なし | コードで未使用（YANG バリデーション専用 dead field） | - |
| `alias` | なし | コードで未使用（dead field） | - |
| `description` | なし | コードで未使用（dead field） | - |
| `dhcp_servers` | なし（leaf-list）| vlanmgrd は無視。dhcprelayd が CONFIG_DB を直接購読 | dhcprelayd |
| `dhcpv6_servers` | なし（leaf-list）| vlanmgrd は無視。dhcprelayd が CONFIG_DB を直接購読 | dhcprelayd |

### 注記

- **`mtu` の silent drop**: `mtu` は APP_DB に書かれるが、ホスト側 netdev (`ip link set Vlan<N> mtu`) への適用は TODO 状態 (vlanmgr.cpp:401-406)。明示指定しても netdev MTU は変わらない。
- **`mac` の書き込み順依存**: `gMacAddress` が未初期化（スイッチ MAC 未確定）の間、vlanmgrd は全 VLAN タスクを保留する (vlanmgr.cpp:318-321)。
- **`dhcp_servers` の経路乖離**: vlanmgrd→APP_DB 経路を通らず、dhcprelayd が CONFIG_DB `VLAN` テーブルを直接購読する。vlanmgrd の処理順序に非依存。
- **SAI デフォルト**: orchagent は `SAI_VLAN_ATTR_VLAN_ID` のみ指定して `sai_vlan_api->create_vlan()` を呼ぶ (portsorch.cpp:7392)。flooding control 等はプラットフォーム SAI デフォルトに委ねられる。
<!-- /defaults -->

<!-- value-behavior -->
## 値依存挙動マトリクス

| フィールド | 値 | 実挙動 |
|-----------|-----|--------|
| `admin_status` | `up` | `ip link set Vlan<id> up` (vlanmgr.cpp:168-170) |
| `admin_status` | `down` | `ip link set Vlan<id> down` |
| `admin_status` | 省略 | `"up"` が自動補完される (vlanmgr.cpp:424) |
| `mtu` | 省略 | `DEFAULT_MTU_STR`（通常 `9100`）が使用される (vlanmgr.cpp:96) |
| `mtu` | 明示指定 | 受け取るが netdev MTU は変更しない。`SWSS_LOG_DEBUG("Host VLAN mtu setting to be supported.")` のみ出力（TODO 状態）|
| `mac` | 省略 | `gMacAddress`（スイッチ MAC）が自動補完 |
| `mac` | 明示指定 | 指定 MAC が VLAN インタフェース MAC として設定される |
| `dhcp_servers` | leaf-list | `dhcprelayd` がリストを読み DHCPv4 relay を構成 |
| `dhcp_servers` | 単一文字列誤入力 | `dhcprelayd` が relay を起動しない（leaf-list 形式で入力必須）|
| `vlanid` | `name` 末尾と不一致 | YANG `must` 違反で reject |

<!-- /value-behavior -->

## 例外条件・特殊挙動 <!-- cdb-exceptions -->

<!-- evidence: sonic-swss/cfgmgr/vlanmgr.cpp; sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang -->

- **キー形式検証**: `Vlan<2..4094>` パターン。`Vlan` プレフィクスがない、または数値部が不正な場合 `vlanmgrd` はエントリを破棄する (`SWSS_LOG_ERROR("Invalid key format")`)[^exc1]。
- **`vlanid` 整合性 (YANG)**: `must "substring-after(../name, 'Vlan') = current()"` — `name` 末尾と `vlanid` フィールドが不一致の場合 YANG バリデーションが reject する[^exc2]。
- **MTU 無視**: `mtu` フィールドはホスト VLAN netdev への適用が TODO 扱いで、`vlanmgrd` は受け取っても `SWSS_LOG_DEBUG("Host VLAN mtu setting to be supported.")` のみ出力し実際には変更しない[^exc1]。
- **warm-restart 重複スキップ**: [STATE_DB](../../reference/glossary.md#term-state_db) に既存かつ `m_vlans` に登録済みの場合、再作成をスキップして replay エントリを削除する（"already created" デバッグログ）[^exc1]。
- **デフォルト補完**: `mtu` 省略時は `DEFAULT_MTU_STR`（通常 `9100`）、`mac` 省略時はスイッチ MAC が自動補完される[^exc1]。

[^exc1]: `sonic-swss/cfgmgr/vlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vlanmgr.cpp>
[^exc2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vlan.yang>

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-vlan`](../yang/sonic-vlan.md)
- CLI: [`config vlan`](../cli/config-vlan.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang` (sha `9ea932ec`). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-vlan.yang>

## 関連ページ
- [HLD: Switchport モードと VLAN CLI 拡張](../../switching/switch-port-modes-and-vlan-cli-enhancement.md)
- [CLI: config vlan](../cli/config-vlan.md)
- [CLI: show vlan](../cli/show-vlan.md)
- [YANG: sonic-vlan](../yang/sonic-vlan.md)

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: L2 / VLAN / LAG / MC-LAG](../../topics/06-l2-vlan-lag/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- `Vlan100` 等の `Vlan<2..4094>` 形式キー。`vlanid` は名前末尾と一致。
- `mtu`: 9100（ホスト側 jumbo 用途）。
- `admin_status`: `up`。
- `dhcp_servers`: `["10.0.0.1", "10.0.0.2"]` 等の relay 先。

### よくある誤設定

- `vlanid` を `name` 末尾と異なる値で投入すると YANG `must` 違反で reject される。
- `VLAN_MEMBER` を作る前に `VLAN_INTERFACE` を作ると L3 IF が isolated VLAN にぶら下がる。
- `dhcp_servers` をリストで無く単一文字列で入れると dhcprelayd が relay を起動しない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'VLAN|Vlan100'
sonic-db-cli CONFIG_DB keys 'VLAN_MEMBER|Vlan100|*'
show vlan brief
```
<!-- /ops-hint -->


<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / VlanOrch**: `VLAN` テーブルを `SubscriberStateTable` で購読。
- **vlanmgrd** (`sonic-swss/cfgmgr/vlanmgr.cpp`): `VLAN` テーブルを購読して Linux VLAN ブリッジを管理。

### 段階 2: CFG → APPL 翻訳

- vlanmgrd が `VLAN` エントリを APP_DB `VLAN_TABLE` に書き込み、`ip link add Vlan<N> type bridge vlan_filtering 1` でカーネルブリッジを作成。

### 段階 3: APPL → SAI

- VlanOrch が APP_DB `VLAN_TABLE` を読み `sai_vlan_api->create_vlan()` でハードウェア VLAN を作成。

### 段階 4: タイミング + 副作用

- カーネルブリッジ作成 (vlanmgrd) と SAI VLAN 作成 (VlanOrch) はほぼ同時。数十 ms 以内。
- 副作用: admin_status=down でもカーネルブリッジは作成される (`ip link set Vlan<N> down` が別途発行)。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

VLAN テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config vlan add/del ...` — `config/vlan.py` が `set_entry('VLAN', vlan_name, {'vlanid': str(vid)})` を呼ぶ (sonic-utilities/config/vlan.py:141)

### minigraph / sonic-cfggen

**minigraph.py** が VLAN を生成し投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が VLAN のマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py:931)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- glossary-links-injected: 6981be1a469d -->