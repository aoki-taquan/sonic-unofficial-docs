---
title: PORT テーブル
description: "PORT テーブル — 物理スイッチポートの設定を保持するテーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-port.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - PORT
    - VLAN_MEMBER
    - PORTCHANNEL_MEMBER
    - INTERFACE
  cli:
    - config interface
  yang:
    - sonic-port
---

# PORT テーブル

## 概要

物理スイッチポートの設定を保持するテーブル。ポート名（`Ethernet0` など）をキーに、speed、lanes、MTU、admin status、FEC、auto-negotiation、breakout subport、MACsec プロファイル、TPID、mux cable 情報、400G ZR トランシーバ向けの tx-power / laser_freq などを記載する[^1]。

`portmgrd` / `orchagent` の `PortsOrch` が PORT テーブルを購読し、[SAI](../../reference/glossary.md#term-sai) 経由で hardware に設定を反映する。`speed` と `lanes` は通常 `port_config.ini` 由来の初期値で、運用中に CLI で変更可能。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>PORT")]
  DM["portmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_PORT_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_port_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
PORT|<name>
```

`<name>` は `Ethernet<N>` 形式の物理ポート名。

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | string (1..128) | ✅ | - | 物理ポート名（例: `Ethernet0`） |
| `core_id` | string (1..16) | - | - | ポートが属する ASIC コア |
| `core_port_id` | string (1..16) | - | - | ASIC コア上のポート ID |
| `num_voq` | string (1..16) | - | - | このポートでサポートする VoQ 数 |
| `alias` | string (1..128) | - | - | ベンダ固有のポート別名／フロントパネル表記 |
| `lanes` | string (1..128) | ✅ (chassis 例外あり) | - | ハードウェアレーン数（chassis では条件付き） |
| `mode` | `switchport_mode` (`routed`/`access`/`trunk`) | - | `routed` | スイッチポートモード |
| `description` | string (0..255) | - | - | ユーザ定義説明 |
| `speed` | uint32 (1..1600000) | ✅ | - | ポート速度 [Mbps] |
| `dhcp_rate_limit` | uint32 | - | `300` | DHCP DOS 緩和レート |
| `link_training` | string `on`/`off` | - | - | リンクトレーニング |
| `autoneg` | string `on`/`off` | - | - | オートネゴシエーション |
| `adv_speeds` | leaf-list uint32 \| `all` | - | - | 広告する速度。`all` は単独でのみ |
| `interface_type` | `interface_type` | - | - | ポートインタフェースタイプ |
| `adv_interface_types` | leaf-list `interface_type` \| `all` | - | - | 広告するインタフェースタイプ |
| `mtu` | uint16 (68..9216) | - | - | MTU [byte] |
| `subport` | uint8 (0..8) | - | - | breakout で生成された論理サブポート番号 |
| `index` | uint16 | - | - | フロントパネルポートインデックス |
| `asic_port_name` | string | - | - | ASIC 内部のポート名（例: `Eth0-ASIC1`） |
| `role` | string `Ext`/`Int`/`Inb`/`Rec`/`Dpc` | - | `Ext` | 多 ASIC / [SmartSwitch](../../reference/glossary.md#term-smartswitch) のロール |
| `admin_status` | `admin_status` (`up`/`down`) | - | `down` | 管理状態 |
| `fec` | string `rs`/`fc`/`none`/`auto` | - | - | 前方誤り訂正モード |
| `dom_polling` | `admin_mode` (`enabled`/`disabled`) | - | - | DOM (Digital Optical Monitoring) ポーリング |
| `pfc_asym` | string `on`/`off` | - | - | 非対称 [PFC](../../reference/glossary.md#term-pfc) |
| `tpid` | `tpid_type` (0x8100 / 0x9100 / 0x9200 / 0x88a8) | - | - | TPID。HW 対応時のみ |
| `mux_cable` | boolean | - | - | dual-ToR mux cable 接続フラグ |
| `macsec` | leafref `MACSEC_PROFILE.name` | - | - | 適用する MACsec プロファイル |
| `tx_power` | decimal64 | - | - | 400G ZR 向け目標出力 [dBm] |
| `laser_freq` | int32 | - | - | 400G ZR 向け目標レーザ周波数 [GHz] |
| `fast_linkup` | boolean | - | `false` | fast link-up |

## 制約

- `lanes` は通常 `mandatory true` だが、`switch_type` が `voq` / `chassis-packet` / `fabric` または `hwsku` が `msft_*_asic_vs` の場合は除外（`when` 条件）[^1]
- `adv_speeds` / `adv_interface_types` は `all` を指定する場合 1 要素のみ（`must`）

## 購読者

- `orchagent` の `PortsOrch`: PORT 全フィールドを購読し、[SAI](../../reference/glossary.md#term-sai) で `SAI_PORT_ATTR_*` に反映
- `portmgrd`: ポート status と admin_status をモニタ
- `xcvrd`: トランシーバ関連 (`tx_power`、`laser_freq`、`dom_polling`) をモニタ
- `linkmgrd`: `mux_cable = true` のポートを mux 制御対象として扱う
- `macsecmgrd`: `macsec` 参照をもとに MACsec セッション確立

## 関連 CONFIG_DB テーブル / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `VLAN_MEMBER`（PORT を leafref 参照）、`PORTCHANNEL_MEMBER`（PORT を leafref）、`INTERFACE`（L3 用 PORT 上の IP）、`MACSEC_PROFILE`、`BUFFER_PG` / `BUFFER_QUEUE`
- 関連 CLI: [`config interface`](../cli/config-interface.md)（speed / mtu / admin / fec / autoneg を変更）
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-port`、`sonic-types`（`switchport_mode`、`admin_status`、`interface_type`、`tpid_type`）

<!-- value-behavior -->
## 値依存挙動マトリクス

### PORT.admin_status

| 値 | PortsOrch / portmgrd 挙動 |
|----|--------------------------|
| `up` | SAI SAI_PORT_ATTR_ADMIN_STATE=true、Linux netdev も up |
| `down` (デフォルト) | SAI SAI_PORT_ATTR_ADMIN_STATE=false、netdev down |

### PORT.fec

| 値 | SAI 属性 | 挙動 |
|----|---------|------|
| `rs` | SAI_PORT_FEC_MODE_RS | Reed-Solomon FEC (100G+ 向け) |
| `fc` | SAI_PORT_FEC_MODE_FC | FireCode FEC (25G 向け) |
| `none` | SAI_PORT_FEC_MODE_NONE | FEC 無効 |
| `auto` | SAI_PORT_FEC_MODE_AUTO | 対向とネゴシエーションで決定 |
| 不正 | - | `Failed to set FEC mode` SWSS_LOG_ERROR |

### PORT.autoneg / link_training

| 値 | 挙動 |
|----|------|
| `on` | オートネゴ / リンクトレーニングを有効化 |
| `off` | 無効化 |
| `on` (非サポート HW) | `autoneg is not supported (cap=%d)` SWSS_LOG_ERROR |

### PORT.mode (switchport_mode)

| 値 | 挙動 |
|----|------|
| `routed` (デフォルト) | L3 ルーテッドポートとして扱う |
| `access` | L2 access ポート (single VLAN) |
| `trunk` | L2 trunk ポート (複数 VLAN) |

### PORT.role (multi-ASIC / SmartSwitch)

| 値 | 意味 |
|----|------|
| `Ext` (デフォルト) | 外部向けポート |
| `Int` | 内部 ASIC 間接続 |
| `Inb` | inband 管理ポート |
| `Rec` | recirculation ポート |
| `Dpc` | DPC (Data Plane CPU) ポート |

### PORT.tpid

| 値 | SAI 属性 | 備考 |
|----|---------|------|
| `0x8100` | 標準 802.1Q | デフォルト TPID |
| `0x9100` / `0x9200` | Q-in-Q / VLAN Stacking | HW 対応が必要 |
| `0x88a8` / `0x88A8` | 802.1ad (Provider Bridging) | HW 対応が必要 |

*speed は uint32 (1..1600000 Mbps)、mtu は uint16 (68..9216 byte)。adv_speeds/adv_interface_types で all と他値の混在は must 制約で reject。*

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: meta/_intermediate/cdb-flow/port.md -->

### YANG スキーマ検証
- `lanes` は mandatory (chassis 以外)、length 1..128。
- `speed` は mandatory、range 1..1600000 (Kbps)。
- `mtu` range: 68..9216。`fec` pattern: `rs|fc|none|auto`。`autoneg` / `pfc_asym` pattern: `on|off`。
- `adv_speeds`: `all` と他値の混在は `must` 制約で reject。`adv_interface_types` も同様。

### consumer (portsorch / portmgr) 例外動作
- 非サポート speed: SAI supported speed リストと照合; 不一致は SWSS_LOG_ERROR + 処理中断。
- MTU 設定失敗: `Failed to set MTU %u to port pid` → SWSS_LOG_ERROR。
- FEC モード不正: `Failed to set FEC mode` → SWSS_LOG_ERROR。
- AutoNeg 設定失敗: `Failed to set AutoNeg %u to port %s` → SWSS_LOG_ERROR。
- `autoneg` 非サポート: `autoneg is not supported (cap=%d)` → SWSS_LOG_ERROR。
- portmgr MTU netdev 設定失敗: `Setting mtu to alias:%s netdev failed` → SWSS_LOG_WARN + `return false`。
- portmgr admin_status netdev 設定失敗: `Setting admin_status to alias:%s netdev failed` → SWSS_LOG_WARN + `return false`。

<!-- /cdb-exceptions -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-port`](../yang/sonic-port.md)
- CLI: [`config interface`](../cli/config-interface.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-port.yang` (sha `9ea932ec`). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-port.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Platform / Port / Optics / PHY](../../topics/14-platform-port-optics/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- `Ethernet0` 等の `EthernetN` 形式キー。`N` は [port_config.ini](../../reference/glossary.md#term-port-config-ini) 由来の lane base。
- `speed`: 10000 / 25000 / 40000 / 100000 / 400000 (Mbps)。
- `mtu`: 9100（jumbo を有効にする一般運用値）。
- `admin_status`: `up`（運用ポート）。
- `fec`: `rs` (100G+) / `fc` (25G) / `none`。
- `autoneg`: `on`/`off`（25G/100G の対向と合わせる）。

### よくある誤設定

- `speed` を `lanes` 数と不整合な値にすると [SAI](../../reference/glossary.md#term-sai) が `SAI_STATUS_INVALID_PARAMETER` を返してポートが down のまま。
- 対向と `fec` が不一致だと PHY は up しても link 不安定。両端を同じ FEC モードに揃える。
- `mtu` を [VLAN](../../reference/glossary.md#term-vlan)/[PortChannel](../../reference/glossary.md#term-portchannel) メンバ間で揃えないと L2 で巨大フレームがドロップされる。
- Breakout 中の親ポートに `admin_status: up` を残すと subport と二重設定で [orchagent](../../reference/glossary.md#term-orchagent) エラー。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'PORT|Ethernet0'
show interfaces status
show interfaces transceiver eeprom Ethernet0
```
<!-- /ops-hint -->


<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / PortsOrch** (`sonic-swss/orchagent/portsorch.cpp`): `PORT` テーブルを `SubscriberStateTable` で購読。
- **portmgrd** (`sonic-swss/cfgmgr/portmgr.cpp`): `PORT` テーブルを購読して Linux netdev を設定。
- **xcvrd** (`sonic-platform-daemons`): トランシーバ関連フィールドを購読。

### 段階 2: CFG → APPL 翻訳

- portmgrd が `PORT` → `APP_PORT_TABLE` に admin_status / mtu / speed 等を書き込む。
- PortsOrch は CONFIG_DB と APP_DB 両方から PORT 情報を統合して処理。

### 段階 3: APPL → SAI

- PortsOrch が `sai_port_api->set_port_attribute()` で speed/FEC/autoneg/MTU/admin_status を SAI に反映。
- syncd が SAI 呼び出しをシリアライズして ASIC ドライバに転送。

### 段階 4: タイミング + 副作用

- admin_status 変更: SAI 反映後に Linux netdev も portmgrd が更新 (二重管理)。数百 ms 以内。
- speed/FEC 変更: リンクフラップが発生する。対向装置との調整が必要。
- 副作用: breakout 操作は他サブポートへの影響大。VLAN/LAG に所属している場合は先に削除が必要。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

PORT テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config interface ...` — `config/main.py` が PORT テーブルを更新 (speed/mtu/fec/autoneg など); `config/switchport.py` が `set_entry('PORT', port, data)` を呼ぶ (sonic-utilities/config/switchport.py:69)

### minigraph / sonic-cfggen

**minigraph.py** が `results['PORT']` にポート一覧 (alias / speed / lanes / description) を投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py:2515)

### REST / gNMI

REST/gNMI 書き込み経路なし (PORT はプラットフォーム初期化で確定)

### db_migrator

**db_migrator.py** が PORT テーブルのマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py:224)

### ビルド時デフォルト (build-time default)

各プラットフォームの `port_config.ini` が `sonic-cfggen` によって PORT テーブルに変換されビルド時デフォルトとなる

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- glossary-links-injected: 16a5b728a75a -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

| 派生先フィールド | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| `PORT` エントリ全体 | minigraph.py が XML `Interfaces` / port_config.ini を解析したとき | `alias`、`lanes`、`speed`、`admin_status` 等 | `sonic-buildimage/src/sonic-config-engine/minigraph.py` |
| `admin_status` | minigraph.py デフォルト | `"up"` (明示的に down 指定がない限り) | `minigraph.py` PORT 生成ロジック |
| `mux_cable` | 対応 MUX_CABLE エントリが存在する場合 | `"true"` | `minigraph.py:2621-2622` |
| init_cfg.json.j2 | 全 PORT エントリのデフォルト | `"admin_status": "up"` など最小限の属性 | `sonic-buildimage/files/build_templates/init_cfg.json.j2:29` |

### Phase 7: 条件付き登録

| 条件 | 影響 | ソース |
|---|---|---|
| `PortsOrch` は常時登録かつ最優先 (orchList 先頭) | `PORT` テーブル購読は無条件。全ポート初期化後に other orch が起動 | `orchdaemon.cpp:232,500` |

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| init_cfg.json.j2 PORT デフォルト | 1 | `init_cfg.json.j2:29` |
| PortsOrch 登録 (先頭) | 2 | `orchdaemon.cpp:232,500` |
| minigraph.py mux_cable 派生 | 2 | `minigraph.py:2621-2622` |

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

`PortsOrch` の PORT 処理分岐 (主要分岐のみ):

| Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `PortsOrch` | `doTask()` | SET 操作かつポートが未作成 | SAI `create_port()` でポートを作成 | `sonic-swss/orchagent/portsorch.cpp` |
| `PortsOrch` | `doTask()` | `admin_status == "up"` | SAI `set_port_attribute(SAI_PORT_ATTR_ADMIN_STATE, true)` | `portsorch.cpp` |
| `PortsOrch` | `doTask()` | `fec` フィールドあり | SAI `SAI_PORT_ATTR_FEC_MODE` を設定。`auto` の場合は `SAI_PORT_FEC_MODE_AUTO` | `portsorch.cpp` |
| `PortsOrch` | `doTask()` | `autoneg == "on"` かつ `speed` 指定あり | `SAI_PORT_ATTR_AUTO_NEG_MODE` + advertised speed 設定 | `portsorch.cpp` |
| `PortsOrch` | `doTask()` | `mux_cable == "true"` | ポートの MUX cable フラグを設定し MuxOrch に通知 | `portsorch.cpp` |
| `PortsOrch` | `doTask()` | SET でポートが `allPortsReady()` を完成させた場合 | `allPortsReady` = true、他 orch の doTask() をアンブロック | `portsorch.cpp:allPortsReady()` |

> **スキャン証跡**: `portsorch.cpp` PORT 処理ロジックおよび `init_cfg.json.j2:29`、`minigraph.py:2621-2622` を確認、6 件分岐抽出 — 誤読なし。

<!-- /handler-branching -->

<!-- cross-refs -->
## 暗黙参照マップ (Phase C)

> leafref として YANG スキーマで強制される参照に加え、orchagent コード上の `m_port_ref_count` 機構・macsecmgrd 直接購読・runtime orch ゲートとして PORT が関与する暗黙参照を網羅する。
> 詳細証跡: `meta/_intermediate/cdb-flow/port-cross-refs.md`

### PORT.name を leafref で参照するテーブル (27+)

PORT エントリが存在しない状態でこれらのテーブルに書き込むと YANG バリデーション失敗になる。

| カテゴリ | テーブル群 |
|---|---|
| L2 | `VLAN_MEMBER`, `PORTCHANNEL_MEMBER`, `MCLAG_INTF` |
| L3 | `INTERFACE`, `BGP_NEIGHBOR`, `BGP_PEER_RANGE`, `NEIGH`, `ROUTE_MAP`, `FINE_GRAINED_ECMP` |
| バッファ | `BUFFER_PG`, `BUFFER_QUEUE`, `BUFFER_PORT_INGRESS_PROFILE_LIST`, `BUFFER_PORT_EGRESS_PROFILE_LIST` |
| QoS | `PORT_QOS_MAP`, `QUEUE`, `PFCWD`, `STORM_CONTROL`, `CABLE_LENGTH` |
| セキュリティ | `MACSEC_PROFILE`(PORT.macsec の leafref), `ACL_TABLE`(port bind) |
| 可視化・管理 | `MIRROR_SESSION`(dst_port), `SFLOW_SESSION`, `LLDP_PORT_TABLE`, `HIGH_FREQUENCY_TELEMETRY` |
| 隣接・デバイス | `DEVICE_NEIGHBOR`, `MUX_CABLE` |
| AAA | `RADIUS_SERVER`, `TACACS_SERVER`, `NTP_SERVER` |
| その他 | `PBH_RULE`, `DHCPV4_RELAY`, `DHCP_SERVER_IPV4` |

### orchagent ref_count を保持するコンポーネント

`m_port_ref_count` が 0 でないと PORT DEL は拒否される (`portsorch.cpp:5649`)。

| コンポーネント | 契機 | ソース |
|---|---|---|
| `intfsorch` | `INTERFACE` SET 時 | `intfsorch.cpp:498` |
| `bufferorch` | `BUFFER_PG` SET 時 | `bufferorch.cpp:1175` |
| `bufferorch` | `BUFFER_QUEUE` SET 時 | `bufferorch.cpp:1546` |
| `portsorch` (sub-intf) | sub-interface 作成時 | `portsorch.cpp:2071` |
| `portsorch` (bridge port) | VLAN_MEMBER 追加時 | `portsorch.cpp:2943` |
| `portsorch` (LAG member) | PORTCHANNEL_MEMBER 追加時 | `portsorch.cpp:8205` |
| P4 Router Interface Mgr | P4 RIF 作成時 | `p4orch/router_interface_manager.cpp:354` |
| P4 ACL Rule Mgr | port bind 時 | `p4orch/acl_rule_manager.cpp:2077` |
| P4 L3 Admit Mgr | L3 admit 設定時 | `p4orch/l3_admit_manager.cpp:283` |
| P4 Mirror Session Mgr | ミラーセッション設定時 | `p4orch/mirror_session_manager.cpp:387` |
| P4 L3 Multicast Mgr | マルチキャストレプリカ設定時 | `p4orch/l3_multicast_manager.cpp:1844` |

### macsecmgrd の直接購読 (非 orch パターン)

`macsecmgrd` は `CFG_PORT_TABLE_NAME` (`PORT`) を直接 SET/DEL で購読する。PORT エントリの `macsec` フィールドを読み取り `MACSEC_PROFILE` を参照して `wpa_supplicant` を起動する。`MACSEC_PROFILE` エントリが存在しない場合は silent early return (`macsecmgr.cpp:296-299,480,543-557`)。

### runtime ゲート参照

| 参照 | 方向 | 機構 | 備考 |
|---|---|---|---|
| `BUFFER_PG` / `BUFFER_QUEUE` | → PORT | `gBufferOrch->isPortReady()` で PORT ready 待機 | BUFFER 処理が完了するまで PORT HW 反映を保留 |
| `MUX_CABLE` | ← / → PORT | linkmgrd が `PORT.mux_cable=true` を検知し MuxOrch へ通知 | minigraph.py が MUX_CABLE 存在時に自動派生 |
| `STATE_PORT_TABLE` | PORT → STATE_DB | portsorch が oper_status / speed / flap_count を書き込む | warm reboot 復元時の引き継ぎ元 |
| `PORT_SERDES` | PORT → | PORT DEL 時に自動連動削除 | `portsorch.cpp:1526` |
| 他テーブル全体 | PORT → | `allPortsReady()` が true になるまで VLAN/INTERFACE/LAG/ACL orch の doTask() を保留 | 最後の PORT が初期化完了するとゲート解除 |

<!-- /cross-refs -->
