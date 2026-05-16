---
title: VLAN_INTERFACE テーブル
description: "VLAN_INTERFACE テーブル — VLAN を L3 IF (SVI) として扱う設定を保持する。VRF / VNET binding、IP アサイン、NAT zone、MPLS、IPv6 link-local、grat ARP / proxy ARP、loopback action、MAC を持つ。"
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
    - VLAN_INTERFACE
    - VLAN
    - VRF
  cli:
    - config interface
  yang:
    - sonic-vlan
---

# VLAN_INTERFACE テーブル

## 概要

[VLAN](../../reference/glossary.md#term-vlan) を L3 IF (SVI) として扱う設定を保持する。[VRF](../../reference/glossary.md#term-vrf) / [VNET](../../reference/glossary.md#term-vnet) binding、IP アサイン、[NAT](../../reference/glossary.md#term-nat) zone、[MPLS](../../reference/glossary.md#term-mpls)、IPv6 link-local、grat [ARP](../../reference/glossary.md#term-arp) / proxy [ARP](../../reference/glossary.md#term-arp)、loopback action、MAC を持つ[^1]。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>VLAN_INTERFACE")]
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
VLAN_INTERFACE|<name>                       # 属性ロウ
VLAN_INTERFACE|<name>|<ip_prefix>           # IP プレフィクス
```

`<name>` は `VLAN.name` への leafref（例: `Vlan100`）。

## 属性ロウのフィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | leafref `VLAN.name` | ✅ | - | [VLAN](../../reference/glossary.md#term-vlan) 名 |
| `vrf_name` | leafref `VRF.name` | - | - | バインドする [VRF](../../reference/glossary.md#term-vrf) |
| `vnet_name` | leafref `VNET.name` | - | - | バインドする [VNET](../../reference/glossary.md#term-vnet) |
| `nat_zone` | uint8 (0..3) | - | `0` | [NAT](../../reference/glossary.md#term-nat) zone |
| `mpls` | enum `enable`/`disable` | - | - | [MPLS](../../reference/glossary.md#term-mpls) routing |
| `grat_arp` | string `enabled`/`disabled` | - | - | gratuitous [ARP](../../reference/glossary.md#term-arp) |
| `proxy_arp` | string `enabled`/`disabled` | - | - | proxy ARP |
| `ipv6_use_link_local_only` | `mode-status` | - | `disable` | IPv6 link-local のみ |
| `mac_addr` | mac-address | - | - | 管理者指定 MAC |
| `loopback_action` | `loopback_action` | - | - | ingress→same-IF routing 動作 |

## IP プレフィクスロウ

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `name` (key) | leafref `VLAN.name` | ✅ | [VLAN](../../reference/glossary.md#term-vlan) 名（`VLAN_INTERFACE_LIST` に存在することを `must` で要求） |
| `ip-prefix` (key) | union (v4/v6 prefix) | ✅ | IP/プレフィクス |
| `scope` | enum `global`/`local` | - | アドレススコープ |
| `family` | `ip-family` | - | family。`ip-prefix` と整合する `must` |
| `secondary` | boolean | - | secondary subnet フラグ |

## 購読者

- `intfmgrd`: [VRF](../../reference/glossary.md#term-vrf) / MAC / [MPLS](../../reference/glossary.md#term-mpls) / IPv6 LL / proxy_arp / grat_arp を Linux に反映
- `orchagent` `IntfsOrch`: [SAI](../../reference/glossary.md#term-sai) ルータインタフェースを生成
- `arpresponder` 等: proxy ARP / grat ARP を扱う

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `VLAN`、`VLAN_MEMBER`、`VRF`、`VNET`
- 関連 CLI: `config interface ip add/remove Vlan<id>`、`config vlan proxy_arp`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-vlan`

<!-- defaults -->
## コード由来の暗黙デフォルト

> 以下はコード精読により導出した暗黙デフォルト・dead field・乖離の一覧。YANG 定義にない挙動を含む[^d1][^d2]。

| フィールド | 省略・空時の実挙動 | 導出元 |
|-----------|-----------------|--------|
| `nat_zone` | YANG `default "0"`。orchagent 変数も `0` 初期化。NAT 非対応プラットフォームでは SAI に送信されず `SWSS_LOG_NOTICE` のみ | YANG L111; intfsorch.cpp:713,984 |
| `mpls` | `empty()` を `"disable"` と等価に扱う (`sysctl input=0`)。sysctl 失敗は省略時 silent。SAI `ADMIN_MPLS_STATE` はデフォルト disabled のため RIF create attrs に含まれない | intfmgr.cpp:178-189; intfsorch.cpp:1276-1284 |
| `proxy_arp` | カーネル/SAI 操作なし。orchagent 内部フラグ `proxy_arp=false` 固定 | intfsorch.cpp:501,845 |
| `grat_arp` | カーネル操作なし | intfmgr.cpp:1038-1051 |
| `ipv6_use_link_local_only` | YANG `default disable`。省略時は `m_ipv6LinkLocalModeList` への追加なし（通常 IPv6 割当） | YANG L138; intfmgr.cpp:913 |
| `mac_addr` | intfmgr が `00:00:00:00:00:00` を APP_DB へ書く。orchagent はゼロ MAC を受け取ると `gMacAddress`（スイッチ全体 MAC）を SAI に適用 | intfmgr.cpp:1019; intfsorch.cpp:1199-1207 |
| `loopback_action` | intfmgr も orchagent も省略時は SAI attrs に含めない。SAI 実装依存デフォルト（多くは `forward`） | intfsorch.cpp:1187-1195,999 |
| `vrf_name` | orchagent が `gVirtualRouterId`（デフォルト VRF）を使用 | intfsorch.cpp:823 |
| `vnet_name` | 省略時は通常 VRF 経路。`vnet_name` と `vrf_name` を同時指定した場合 `vnet_name` が優先される | intfsorch.cpp:933-957 |
| `scope` (IP prefix) | **dead field**: CONFIG_DB 値は読まれず、intfmgr が常に `"global"` を APP_DB へ書く | intfmgr.cpp:1134 |
| `family` (IP prefix) | **dead field**: CONFIG_DB 値は読まれず、intfmgr が ip-prefix の型から自動判定して APP_DB へ書く | intfmgr.cpp:1129 |
| `secondary` (IP prefix) | **dead consumer**: intfmgr・orchagent のどちらもこのフィールドを参照しない | intfmgr.cpp:784-829; intfsorch.cpp:720-814 |

[^d1]: `sonic-swss/cfgmgr/intfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
[^d2]: `sonic-swss/orchagent/intfsorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/intfsorch.cpp>

<!-- /defaults -->

<!-- constants -->
## ハードコード定数

> コード精読（`intfmgr.cpp` / `intfsorch.cpp` / `portsorch.cpp`）から抽出した数値・文字列定数。YANG 定義には現れないが実挙動を決定する[^c1][^c2][^c3]。

| 定数 / マジック値 | 値 | 定義箇所 | 用途 |
|-----------------|-----|---------|------|
| `DEFAULT_MTU_STR` | `9100` | `intfmgr.cpp:29` | VLAN IF の省略時 MTU。`ip link` コマンドに渡す |
| `LOOPBACK_DEFAULT_MTU_STR` | `"65536"` | `intfmgr.cpp:28` | Loopback ダミー IF 専用。VLAN IF には非適用 |
| `grat_arp=enabled` → `arp_accept` | `"2"` | `intfmgr.cpp:582` | `/proc/sys/net/ipv4/conf/<IF>/arp_accept` に書く値（値 `1` とは意味が異なる） |
| `grat_arp=disabled` → `arp_accept` | `"0"` | `intfmgr.cpp:586` | 同ファイルへの無効化値 |
| `accept_untracked_na` (IPv6) | `"2"` / `"0"` | `intfmgr.cpp:608` | IPv6 NA 用カーネルパラメータ。カーネル非対応時はスキップ |
| `proxy_arp=enabled` → `/proxy_arp` | `"1"` | `intfmgr.cpp:624,642` | `/proc/sys/net/ipv4/conf/<IF>/proxy_arp` と `proxy_arp_pvlan` に書く値 |
| `proxy_arp=disabled` → `/proxy_arp` | `"0"` | `intfmgr.cpp:628,642` | 同ファイルへの無効化値 |
| `sysctl mpls input` (enabled) | `1` | `intfmgr.cpp:176` | `net.mpls.conf.<IF>.input=1` で MPLS 有効化 |
| `sysctl mpls input` (disabled) | `0` | `intfmgr.cpp:180` | `net.mpls.conf.<IF>.input=0` で MPLS 無効化 |
| `mac_addr` 省略時 APP_DB 値 | `"00:00:00:00:00:00"` | `intfmgr.cpp:1019` | ゼロ MAC を APP_DB へ書く。orchagent はゼロ MAC 受信時にスイッチ全体 MAC (`gMacAddress`) を SAI に適用 |
| `scope` 固定値 | `"global"` | `intfmgr.cpp:1134` | IP prefix ロウの `scope` は常に `"global"` を APP_DB へ書く（CONFIG_DB 値無視） |
| `family` 自動判定値 | `IPV4_NAME` / `IPV6_NAME` | `intfmgr.cpp:1129` | IP prefix の型 (`isV4()`) から自動判定（CONFIG_DB 値無視） |
| `admin_status` フォールバック | `"up"` | `intfmgr.cpp:863,868` | 省略・不正値時に `"up"` へ強制補完（`SWSS_LOG_WARN` あり） |
| `nat_zone_id` 初期値 | `0` (uint32) | `intfsorch.cpp:713` | `nat_zone` 省略時の orchagent 内部変数。NAT 非対応プラットフォームでは SAI へ送信しない |
| `loopback_action` 変換テーブル | `"drop"` → `SAI_PACKET_ACTION_DROP` | `intfsorch.cpp:1150` | `getSaiLoopbackAction()` による文字列→SAI 定数マッピング |
| `loopback_action` 変換テーブル | `"forward"` → `SAI_PACKET_ACTION_FORWARD` | `intfsorch.cpp:1151` | 同上。省略時は attrs に含めず SAI 実装依存デフォルト（多くは `forward`） |
| `SAI_ROUTER_INTERFACE_ATTR_ADMIN_MPLS_STATE` | 省略（SAI 側デフォルト disabled） | `intfsorch.cpp:1278` | `mpls` 省略 / `disable` 時は RIF create attrs に含めない |
| `VLAN_PREFIX` | `"Vlan"` | `intfmgr.cpp:19` | VLAN インタフェース名判定用プレフィックス。`alias.compare(0, strlen(VLAN_PREFIX), VLAN_PREFIX)` で VLAN IF か否かを識別する |

[^c1]: `sonic-swss/cfgmgr/intfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
[^c2]: `sonic-swss/orchagent/intfsorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/intfsorch.cpp>
[^c3]: `sonic-swss/orchagent/portsorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/portsorch.cpp>

<!-- /constants -->

<!-- value-behavior -->
## 値依存挙動マトリクス

| フィールド | 値 | 実挙動 |
|-----------|-----|--------|
| `mpls` | `enable` | `sysctl -w net.mpls.conf.<IF>.input=1` (intfmgr.cpp) |
| `mpls` | `disable` または空 | `sysctl -w net.mpls.conf.<IF>.input=0` |
| `proxy_arp` | `enabled` | `/proc/sys/net/ipv4/conf/<IF>/proxy_arp` / `proxy_arp_pvlan` に `1` |
| `proxy_arp` | `disabled` | 同ファイルに `0` |
| `proxy_arp` | その他 | `SWSS_LOG_ERROR("Proxy ARP state is invalid")` で処理中断 |
| `grat_arp` | `enabled` | `/proc/sys/net/ipv4/conf/<IF>/arp_accept` に `2`（accept_untracked_na も同値、カーネル対応時のみ） |
| `grat_arp` | `disabled` | 同ファイルに `0` |
| `grat_arp` | その他 | `SWSS_LOG_ERROR("GARP state is invalid")` で処理中断 |
| `ipv6_use_link_local_only` | `enable` | IPv6 link-local アドレスのみ付与。グローバル IPv6 アドレス付与不可 |
| `ipv6_use_link_local_only` | `disable` | 通常の IPv6 アドレス割当（デフォルト） |
| `loopback_action` | `drop` | 同一 IF に ingress/egress するパケットをドロップ |
| `loopback_action` | `forward` | 同一 IF に ingress/egress するパケットを転送 |
| `nat_zone` | `0` | [NAT](../../reference/glossary.md#term-nat) zone なし（デフォルト） |
| `nat_zone` | `1`〜`3` | 該当 NAT zone へのバインド |
| `vrf_name` | 変更 (既存 IF) | `isIntfChangeVrf()` で検出しエラー。削除後再 add が必要 |

<!-- /value-behavior -->

## 例外条件・特殊挙動 <!-- cdb-exceptions -->

<!-- evidence: sonic-swss/cfgmgr/intfmgr.cpp; sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang -->

- **VRF 変更禁止**: `intfmgrd` は既存 IF の VRF 変更を `isIntfChangeVrf()` で検出し `SWSS_LOG_ERROR("%s can not change to %s directly, skipping")` を記録してエントリを破棄する[^exc1]。
- **インタフェース未 ready**: `isIntfStateOk()` が false の場合リトライ待ち（"Interface is not ready, skipping"）[^exc1]。
- **VRF 未 ready**: VRF が [STATE_DB](../../reference/glossary.md#term-state_db) に未登録の場合もリトライ待ち[^exc1]。
- **`proxy_arp` / `grat_arp` / `mpls` 不正値**: 不正値の場合 `SWSS_LOG_ERROR("... state is invalid")` を記録して処理を中断[^exc1]。
- **デフォルト補完**: `admin_status` 省略時は `"up"` が補完される[^exc1]。YANG では `nat_zone` のデフォルト `0`、`ipv6_use_link_local_only` のデフォルト `disable`[^exc2]。

[^exc1]: `sonic-swss/cfgmgr/intfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
[^exc2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vlan.yang>

<!-- ordering -->
## 書込み順依存

> コード精読（`intfmgr.cpp` / `intfsorch.cpp`）から導出した書込み順序制約。順序違反は silent retry になるため注意。

### SET 時の必須前提条件

| 前提テーブル | 確認場所 | 理由 |
|------------|---------|------|
| `VLAN|Vlan<N>` + vlanmgrd STATE_VLAN_TABLE ready | `intfmgr.cpp:653-660` | `isIntfStateOk()` が STATE_VLAN_TABLE を参照。未登録なら retry |
| `VRF|<name>` + vrfmgrd STATE_VRF_TABLE ready | `intfmgr.cpp:839-842` | `vrf_name` 指定時のみ。未登録なら `return false` で retry |
| VNetOrch が `VNET|<name>` 処理済み | `intfsorch.cpp:933-939` | `vnet_name` 指定時のみ。orchagent 側チェック |
| PortsOrch が VLAN ポートオブジェクト生成済み | `intfsorch.cpp:905` | APP_DB → SAI 経路のチェック。CONFIG_DB 書込みとは独立 |

### 属性ロウ → IP プレフィクスロウ の順序

1. `VLAN_INTERFACE|Vlan<N>` を SET → intfmgrd が STATE_INTERFACE_TABLE に `vrf` を書く
2. STATE_INTERFACE_TABLE に alias エントリが存在する状態で `VLAN_INTERFACE|Vlan<N>|<ip_prefix>` を SET

```
CONFIG_DB: VLAN_INTERFACE|Vlan100  → (intfmgrd doIntfGeneralTask) → STATE_INTF_TABLE|Vlan100
CONFIG_DB: VLAN_INTERFACE|Vlan100|10.0.0.1/24  → (intfmgrd doIntfAddrTask, isIntfCreated check OK)
```

逆順で書いた場合は `isIntfCreated()` が false を返して retry キューに積まれる。最終的には収束するが遅れる。

### DEL 時の必須順序

1. `VLAN_INTERFACE|Vlan<N>|<ip_prefix>` をすべて DEL
2. `VLAN_INTERFACE|Vlan<N>` を DEL

属性ロウの DEL 時に `getIntfIpCount(alias) > 0` であれば `return false`（retry）。IP プレフィクスが残ったまま属性ロウを削除しようとしても適用されない（`intfmgr.cpp:1060-1063`）。

### VRF 変更は 2 ステップ必須

既存 VRF から別 VRF への直接変更は `isIntfChangeVrf()` が検出してエラーログを出し SAI には反映しない。

```
手順:
  1. VLAN_INTERFACE|Vlan<N>  vrf_name=""   (unbind)
  2. VLAN_INTERFACE|Vlan<N>  vrf_name=<new-VRF>  (rebind)
```

### warm-reboot 時の挙動

#### `buildIntfReplayList()` に VLAN_INTERFACE が含まれる

warm-start 時、intfmgrd は `buildIntfReplayList()` で `m_cfgVlanIntfTable.getKeys()` の結果を `m_pendingReplayIntfList` に追加する（`intfmgr.cpp:277-278`）。

```cpp
// intfmgr.cpp:277-278
m_cfgVlanIntfTable.getKeys(intfList);
std::copy(intfList.begin(), intfList.end(), std::inserter(m_pendingReplayIntfList, ...));
```

リストが空になった時点で `setWarmReplayDoneState()` を呼び `REPLAYED` → `RECONCILED` と遷移する。reconciliation ロジックはなく、カーネルへの再 replay で完了とみなされる。**VLAN が STATE_DB で ready になってから VLAN_INTERFACE が replay 収束する** 順序は通常時と同じ。

#### `ipv6_use_link_local_only` は in-memory 状態がリセットされる

`m_ipv6LinkLocalModeList` は `std::set`（in-memory）。warm-reboot 後は空に戻るため、CONFIG_DB に `ipv6_use_link_local_only: enable` エントリが残っていても replay が再 SET を処理するまでの間は link-local モードが失われる。replay で CONFIG_DB 内容が再処理されれば収束する（`intfmgr.cpp:913`）。

### 書込み順依存まとめ

| 依存カテゴリ | 必須順序 | ソース |
|------------|---------|-------|
| VLAN → VLAN_INTERFACE | `VLAN` エントリ + vlanmgrd の STATE_VLAN_TABLE ready が先 | `intfmgr.cpp:653-660` |
| VRF → VLAN_INTERFACE | `VRF` エントリ + vrfmgrd の STATE_VRF_TABLE ready が先 | `intfmgr.cpp:839-842` |
| VNET → VLAN_INTERFACE | VNetOrch が VNET 処理済みであること | `intfsorch.cpp:933-939` |
| 属性ロウ → IP prefix | `VLAN_INTERFACE\|Vlan<N>` SET → STATE_INTF 反映後に `VLAN_INTERFACE\|Vlan<N>\|<ip>` SET | `intfmgr.cpp:1115` |
| IP prefix DEL → 属性ロウ DEL | すべての IP prefix を DEL してから属性ロウを DEL | `intfmgr.cpp:1060-1063` |
| VRF 変更 2 ステップ | unbind (`vrf_name=""`) → rebind (`vrf_name=<新VRF>`) | `intfmgr.cpp:846-849` |
| warm-reboot replay | VLAN STATE_DB ready 後に VLAN_INTERFACE replay 収束 | `intfmgr.cpp:277-278, 286-292` |

<!-- /ordering -->

<!-- phase-d:start -->
## 失敗挙動 (Phase D)

> コード精読（`intfmgr.cpp` / `intfsorch.cpp`）から導出した失敗モード一覧。  
> 引用元: [^pd1][^pd2]

### VLAN 未解決による処理保留

| 条件 | 実挙動 | 証拠 |
|------|--------|------|
| `STATE_VLAN_TABLE\|Vlan<N>` が STATE_DB に未登録 | `isIntfStateOk()` が `false` を返し `SWSS_LOG_DEBUG("Interface is not ready, skipping %s")` を記録。エントリは `m_toSync` に残り次回 Select タイムアウト（1000ms）後にリトライ | `intfmgr.cpp:833-836` |
| orchagent 側で VLAN ポートオブジェクト未生成 | `gPortsOrch->getPort(alias, port)` が失敗し `it++; continue` でイテレータを進めてスキップ。`task_need_retry` 相当の暗黙リトライ | `intfsorch.cpp:905,921-925` |
| `vrf_name` 指定かつ `STATE_VRF_TABLE\|<name>` 未登録 | `isIntfStateOk(vrf_name)` が `false` → `SWSS_LOG_DEBUG("VRF is not ready, skipping %s")` → `return false` でリトライ | `intfmgr.cpp:839-842` |
| IP プレフィクス行を属性ロウより先に投入 | `isIntfCreated()` が `false` を返して `SWSS_LOG_DEBUG("Interface is not ready, skipping %s")` → リトライキュー | `intfmgr.cpp:1112-1118` |
| `vnet_name` が VNetOrch で未処理 | `vnet_orch->isVnetExists(vnet_name)` が `false` → `it++; continue` でスキップ | `intfsorch.cpp:936-939` |

**収束保証**: いずれのケースも silent retry であり、前提条件が満たされれば自動収束する。ただし前提が永続的に未解決の場合（例: 存在しない VLAN 名を指定）はエントリが `m_toSync` に残り続けログには現れない（`DEBUG` レベルのため syslog のデフォルト設定では非表示）。

### SAI RIF 作成失敗

| 条件 | 実挙動 | 証拠 |
|------|--------|------|
| `create_router_interface()` が `SAI_STATUS_SUCCESS` 以外を返却 | `SWSS_LOG_ERROR("Failed to create router interface %s, rv:%d")` → `handleSaiCreateStatus()` を呼び出し | `intfsorch.cpp:1297-1301` |
| `handleSaiCreateStatus()` が `task_success` 以外 | `throw runtime_error("Failed to create router interface.")` が発行され orchagent プロセスが例外捕捉可能な上位ハンドラへ伝播 | `intfsorch.cpp:1301-1304` |
| `remove_router_interface()` 失敗 | `SWSS_LOG_ERROR("Failed to remove router interface for port %s, rv:%d")` → `handleSaiRemoveStatus()` | `intfsorch.cpp:1350-1353` |
| RIF に IP アドレスが残っている状態で RIF 削除を試みる | `m_syncdIntfses[port.m_alias].ref_count > 0` を検出し `SWSS_LOG_NOTICE("Router interface %s is still referenced with ref count %d")` → `return false` で削除を中断 | `intfsorch.cpp:1327-1331` |
| MAC set / MTU set / NAT zone set 等の属性更新失敗 | 各 `sai_router_intfs_api->set_router_interface_attribute()` の戻り値を `handleSaiSetStatus()` で処理。`task_need_retry` 相当の場合は呼び出し元がリトライ | `intfsorch.cpp:205-295` |
| IP2me ルート作成失敗（IP prefix 付与時） | `SWSS_LOG_ERROR("Failed to create IP2me route ip:%s, rv:%d")` → `handleSaiCreateStatus()` | `intfsorch.cpp:1398-1401` |

**SAI 例外時の注意**: `runtime_error` は orchagent の例外ハンドラが捕捉し `SWSS_LOG_ERROR` を記録したうえでプロセス継続またはクラッシュ再起動を行う。SAI 実装（ASIC SDK）の返す具体的なエラーコードは `rv` フィールドに整数で記録される。

### intfmgr 側のカーネル操作失敗

| 操作 | 失敗時の挙動 |
|------|------------|
| `sysctl mpls input` 設定失敗 | `SWSS_LOG_ERROR("Command '%s' failed with rc %d")` → `return false` で処理中断、エントリはリトライ待ち (`intfmgr.cpp:191`) |
| `ip addr add` 等の IP 操作失敗（IPv6 有効化含む） | `SWSS_LOG_ERROR` または `SWSS_LOG_NOTICE` → `return false` (`intfmgr.cpp:119-130`) |
| `proxy_arp` / `grat_arp` 無効値 | `SWSS_LOG_ERROR("... state is invalid")` → `return false` で処理中断 (`intfmgr.cpp:590,632`) |
| `admin_status` 設定失敗 | `SWSS_LOG_WARN` → `return false` (`intfmgr.cpp:501-503`) |

[^pd1]: `sonic-swss/cfgmgr/intfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
[^pd2]: `sonic-swss/orchagent/intfsorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/intfsorch.cpp>

<!-- phase-d:end -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-vlan`](../yang/sonic-vlan.md)
- CLI: [`config interface`](../cli/config-interface.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-vlan.yang` 内 `VLAN_INTERFACE`。<https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-vlan.yang#L71>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: L2 / VLAN / LAG / MC-LAG](../../topics/06-l2-vlan-lag/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `VLAN_INTERFACE|Vlan100` (L3 enable 行) と `VLAN_INTERFACE|Vlan100|10.0.0.1/24` (IP 行) の 2 段。
- `vrf_name`: `Vrfdefault` または `Vrf<name>`。

### よくある誤設定

- L3 enable 行を作らずに IP 行だけ投入すると IntfMgr が IP を作らない。
- `vrf_name` を後から変更しても既存 IP は古い VRF に残る。一旦 del してから再 add。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'VLAN_INTERFACE|*'
show ip interfaces
```
<!-- /ops-hint -->


<!-- pubsub -->
## 通信メカニズム (Redis Pub/Sub)

VLAN_INTERFACE テーブルは **2 系統の異なる購読方式** で伝搬する。

### CONFIG_DB → intfmgrd (SubscriberStateTable / keyspace notification)

`intfmgrd` は起動時に `Orch(cfgDb, tableNames)` を経由して `CFG_VLAN_INTF_TABLE_NAME`（`"VLAN_INTERFACE"`）を登録する。`Orch::addConsumer()` は CONFIG_DB (db_id=4) を検出すると `SubscriberStateTable` を選択し、以下の `PSUBSCRIBE` を発行する[^ps1][^ps2]。

```
PSUBSCRIBE __keyspace@4__:VLAN_INTERFACE|*
```

- CONFIG_DB の `notify-keyspace-events = "KEA"` が有効なため、CLI / minigraph 等が `HSET VLAN_INTERFACE|Vlan100 …` を書き込むと Redis が自動で `PUBLISH __keyspace@4__:VLAN_INTERFACE|Vlan100 hset` を発行する
- `SubscriberStateTable::pops()` がイベントチャンネルからキーを取り出し、`HGETALL VLAN_INTERFACE|Vlan100` で現在値を取得して `KeyOpFieldsValuesTuple` に変換する
- `op = "hset"` → `SET_COMMAND`、`op = "del"` → `DEL_COMMAND`

### intfmgrd → APPL_DB (ProducerStateTable / channel PUBLISH)

`IntfMgr` は `ProducerStateTable m_appIntfTableProducer(appDb, APP_INTF_TABLE_NAME)` を保持する[^ps1]。書き込み時は Lua スクリプトをアトミック実行する：

```
EVALSHA <luaSet>
  SADD INTF_TABLE_KEY_SET "Vlan100"
  HSET _INTF_TABLE|Vlan100 field1 val1 …
  PUBLISH INTF_TABLE_CHANNEL@0 "G"
```

PUBLISH ペイロードは固定文字列 `"G"`。

### APPL_DB → orchagent (ConsumerStateTable / channel SUBSCRIBE)

`orchagent` の `IntfsOrch` は APPL_DB (db_id=0) に対して `ConsumerStateTable` を使用し `INTF_TABLE_CHANNEL@0` を `SUBSCRIBE` する[^ps2][^ps3]。`consumer_state_table_pops.lua` が `SPOP INTF_TABLE_KEY_SET` → `HGETALL _INTF_TABLE|key` → 本体ハッシュへコピーをアトミック実行する。

### STATE_DB への書き戻し

`intfmgrd` は処理完了後に STATE_DB `STATE_INTERFACE_TABLE` へ TTL なしで書き込む：

| タイミング | 操作 |
|-----------|------|
| L3 IF 設定完了 | `hset(alias, "vrf", vrf_name)` |
| IP アドレス追加完了 | `hset(alias+"\|"+pfx, "state", "ok")` |
| IP / IF 削除 | `del(...)` |

**hSetWithTTL は使用されない。**

### 特性まとめ

| 特性 | 内容 |
|------|------|
| CONFIG_DB → intfmgrd | Redis PSUBSCRIBE (keyspace notification) |
| keyspace pattern | `__keyspace@4__:VLAN_INTERFACE\|*` |
| intfmgrd → APPL_DB | Redis PUBLISH/SUBSCRIBE (channel ベース) |
| Publish チャンネル | `INTF_TABLE_CHANNEL@0`、ペイロード固定 `"G"` |
| APPL_DB → orchagent | ConsumerStateTable + `SUBSCRIBE` |
| NotificationConsumer | **不使用** |
| TTL / keyevent expire | **不使用** |
| Select タイムアウト | 1000ms → `intfmgr.doTask()` で未処理タスクを再試行 |
| warm-restart | `buildIntfReplayList()` で起動時に既存 STATE_DB をスキャン |
| chassis (VOQ) | `SubscriberStateTable(chassisAppDb, CHASSIS_APP_SYSTEM_INTERFACE_TABLE_NAME)` で追加購読 |

[^ps1]: `sonic-swss/cfgmgr/intfmgr.cpp` / `intfmgr.h` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
[^ps2]: `sonic-swss/orchagent/orch.cpp` L1186-1195 (`Orch::addConsumer`) <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/orch.cpp>
[^ps3]: `sonic-swss/orchagent/orchdaemon.cpp` L296 / `intfsorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/orchdaemon.cpp>

<!-- /pubsub -->

<!-- phase-g:start -->
## SAI RIF 生成経路の詳細 (Phase G)

> ソース: `sonic-swss/orchagent/intfsorch.cpp` (L1180–1318)[^pg1]

### CONFIG_DB Subscribe — intfmgrd 登録経路

`IntfMgr` コンストラクタは `Orch(cfgDb, tableNames)` を呼び出す (`intfmgr.cpp:32`)。`tableNames` には `CFG_VLAN_INTF_TABLE_NAME`（= `"VLAN_INTERFACE"`）が含まれる。`Orch::addConsumer()` は cfgDb の db_id=4 を検出して **`SubscriberStateTable`** を生成し、Redis に対して以下の PSUBSCRIBE を発行する：

```
PSUBSCRIBE __keyspace@4__:VLAN_INTERFACE|*
```

| 項目 | 値 |
|------|-----|
| 購読クラス | `SubscriberStateTable` |
| keyspace db_id | 4 (CONFIG_DB) |
| keyspace パターン | `__keyspace@4__:VLAN_INTERFACE\|*` |
| pop 実装 | `SubscriberStateTable::pops()` — keyspace イベント受信後 `HGETALL` で最新値取得 |
| Select timeout | 1000 ms → `IntfMgr::doTask()` で `m_toSync` 未処理タスクをリトライ |

### orchagent — IntfsOrch の ConsumerStateTable

`IntfsOrch` は APP_DB (db_id=0) の `APP_INTF_TABLE_NAME`（`"INTF_TABLE"`）を `ConsumerStateTable` で購読する。`INTF_TABLE_CHANNEL@0` を `SUBSCRIBE` し、Lua スクリプト `consumer_state_table_pops.lua` で `SPOP` + `HGETALL` をアトミック実行する。

### SAI RIF 生成属性（VLAN IF 専用）

`IntfsOrch::addRouterIntfs()` (intfsorch.cpp:1180–1319) が VLAN ポートに対して `create_router_interface()` を呼ぶ際に設定する SAI 属性：

| SAI 属性 | 値（VLAN IF の場合） | 証拠 |
|---------|---------------------|------|
| `SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID` | `vrf_id`（省略時 `gVirtualRouterId`） | intfsorch.cpp:1183 |
| `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` | `port.m_mac` または `gMacAddress`（ゼロ MAC 時） | intfsorch.cpp:1196–1208 |
| `SAI_ROUTER_INTERFACE_ATTR_TYPE` | `SAI_ROUTER_INTERFACE_TYPE_VLAN` | intfsorch.cpp:1219–1221 |
| `SAI_ROUTER_INTERFACE_ATTR_VLAN_ID` | `port.m_vlan_info.vlan_oid` | intfsorch.cpp:1246–1248 |
| `SAI_ROUTER_INTERFACE_ATTR_MTU` | `port.m_mtu`（省略時 9100） | intfsorch.cpp:1272–1274 |
| `SAI_ROUTER_INTERFACE_ATTR_ADMIN_MPLS_STATE` | `true`（`mpls=enable` 時のみ。省略時は attrs に含めない） | intfsorch.cpp:1276–1285 |
| `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` | `port.m_nat_zone_id`（`gIsNatSupported` 時のみ） | intfsorch.cpp:1287–1294 |

PHY/LAG と異なり `SAI_ROUTER_INTERFACE_ATTR_PORT_ID` は使用せず、`SAI_ROUTER_INTERFACE_ATTR_VLAN_ID` に VLAN OID を直接設定する点が VLAN SVI の特徴。

### CONFIG_DB → SAI 完全経路サマリ

```
CLI / minigraph
  → HSET CONFIG_DB VLAN_INTERFACE|Vlan100 ...
  → Redis keyspace 通知 (PSUBSCRIBE __keyspace@4__:VLAN_INTERFACE|*)
  → IntfMgr::doTask() [intfmgr.cpp:1173]
      isIntfStateOk() / isIntfChangeVrf() チェック
  → ProducerStateTable EVALSHA
      SADD INTF_TABLE_KEY_SET "Vlan100"
      HSET _INTF_TABLE|Vlan100 ...
      PUBLISH INTF_TABLE_CHANNEL@0 "G"
  → IntfsOrch::doTask() [intfsorch.cpp:884]
      gPortsOrch->getPort() で VLAN OID 取得
      addRouterIntfs() [intfsorch.cpp:1180]
  → sai_router_intfs_api->create_router_interface(
        TYPE=SAI_ROUTER_INTERFACE_TYPE_VLAN,
        VLAN_ID=vlan_oid, MTU=9100, ...)
  → COUNTER_DB COUNTERS_RIF_NAME_MAP に alias → rif_id を登録
```

[^pg1]: `sonic-swss/orchagent/intfsorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/intfsorch.cpp>

<!-- phase-g:end -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / IntfsOrch**: `VLAN_INTERFACE` テーブルを `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- IntfsOrch が VLAN L3 インタフェースの IP プレフィックスを APP_DB `INTF_TABLE` に書き込む。

### 段階 3: APPL → SAI

- IntfsOrch が `sai_router_interface_api->create_router_interface()` で VLAN に対する SAI RIF を作成。
- IP プレフィックスに対して `sai_route_api` でコネクテッドルートを作成。

### 段階 4: タイミング + 副作用

- VLAN テーブルが先に処理されている必要あり。未解決の場合は `task_need_retry`。
- 副作用: IP 削除時は関連 ARP エントリ・ルートが自動削除される。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

VLAN_INTERFACE テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config interface ip add/remove <Vlan...> ...` — `config/main.py` が `set_entry('VLAN_INTERFACE', ...)` を呼ぶ (sonic-utilities/config/main.py)

### minigraph / sonic-cfggen

**minigraph.py** が VLAN_INTERFACE に IP アドレスを投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での VLAN_INTERFACE マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

> **調査根拠**: `intfmgr.cpp`、`sonic-vlan.yang`、`dhcp4relay.cpp`、`config_interface.cpp`、`dhcp_cfggen.py`、`natconfig`、`neighbor_advertiser`、`filter_fdb_entries.py`、`xfmr_intf.go` 全行精読 (2026-05-15)  
> 詳細証跡: `meta/_intermediate/cdb-flow/vlan-interface-cross-refs.md`

`VLAN_INTERFACE` は YANG leafref で `VLAN`・`VRF`・`VNET` を公式参照するほか、
実行時に以下のテーブルを**暗黙的に参照または被参照**する。

### 参照先 (VLAN_INTERFACE → 他テーブル)

| 参照先テーブル | YANG leafref | 参照フィールド | 実装上の必須度 | 証拠 |
|---|---|---|---|---|
| `VLAN\|<name>` | ✅ あり | `name` (key) | 必須 — 未処理なら `task_need_retry` | `intfmgr.cpp`; `sonic-vlan.yang` |
| `VRF\|<name>` | ✅ あり | `vrf_name` | 条件付き — STATE_DB 未登録ならリトライ | `intfmgr.cpp`; `sonic-vlan.yang` |
| `VNET\|<name>` | ✅ あり | `vnet_name` | 条件付き | `sonic-vlan.yang`; `orchagent` |

#### VLAN — task_need_retry による依存

`IntfsOrch` は VLAN_INTERFACE を処理する前に対応 VLAN テーブルが orchagent で完了済みである必要がある。
VLAN が未解決の場合は `task_need_retry` を返し保留する (`orchagent/intfsorch.cpp`)。

#### VRF — STATE_DB 経由の存在確認

`vrf_name` が設定された場合、`intfmgrd` は STATE_DB `VRF_TABLE|<name>` の存在を確認してから処理する。
VRF が未登録のままだと `m_toSync` に積まれ VRF 登録後にリトライされる (`intfmgr.cpp`)。

### 被参照 (他テーブル → VLAN_INTERFACE)

| 参照元コンポーネント | 参照方法 | YANG leafref | 実装上の意味 | 証拠 |
|---|---|---|---|---|
| `DHCP_SERVER_IPV4` (dhcpservd) | `get_config_db_table('VLAN_INTERFACE')` 全量読み取り | なし | サブネット・GW を VLAN_INTERFACE から取得。IP がないと kea-dhcp4 設定生成不可 | `dhcp_cfggen.py:69` |
| `DHCP_RELAY` (dhcp4relay) | `VLAN_INTERFACE\|<vlan>` から `vrf_name` 読み取り | なし | VRF 対応ソケット生成に使用。VLAN_INTERFACE.vrf_name がリレー VRF を決定 | `dhcp4relay.cpp:885` |
| `DHCP_RELAY` (dhcp6relay) | `VLAN_INTERFACE\|<vlan>\|*` パターン検索 | なし | IPv6 プレフィックスが未登録なら `LOG_WARNING` でスキップ | `config_interface.cpp:130,135` |
| NAT (`natconfig`) | VLAN_INTERFACE の `nat_zone` フィールドを走査 | なし | `nat_zone≥1` のとき natmgr がゾーンバインドを生成 | `natconfig:205`; `show/main.py:1609` |
| `neighbor_advertiser` | `get_table('VLAN_INTERFACE')` で IP リスト取得 | なし | gratuitous ARP / ND 送出対象 IP を VLAN_INTERFACE から収集 | `neighbor_advertiser:101,172,212,289` |
| FDB フィルタ (fdbutil) | `config_db_entries["VLAN_INTERFACE"]` 存在チェック | なし | VLAN が L3 有効化済みかを判定し FDB フィルタ動作を変える | `filter_fdb_entries.py:30-31` |
| GCU サービス検証 | 変更差分を `old/upd_vlan_intf` として比較 | なし | VLAN_INTERFACE 変更時のサービス再起動要否判定 | `services_validator.py:163-164` |
| OpenConfig REST/gNMI | `intfTN: "VLAN_INTERFACE"` にマッピング | なし | OpenConfig `interfaces/interface[type=vlan]` が VLAN_INTERFACE に対応 | `xfmr_intf.go:152,416-418` |

### 解決タイミングまとめ

1. **VLAN** が先に orchagent で確定している必要がある（`task_need_retry`）。
2. **VRF** が STATE_DB に登録されるまで VLAN_INTERFACE の VRF バインドは保留される。
3. DHCP relay/server コンテナは起動時・CONFIG_DB 変更通知時に VLAN_INTERFACE を再読み取りするため、**VLAN_INTERFACE への IP 追加は DHCP に即座に反映される**。
4. neighbor_advertiser はデーモン常駐型で CONFIG_DB を購読。IP 変更は次の gratuitous ARP サイクルで反映される。

<!-- /cross-refs -->

<!-- platform -->
## プラットフォーム差 (Phase H)

> 調査対象: `sonic-swss/orchagent/intfsorch.cpp`, `sonic-swss/cfgmgr/intfmgr.cpp`
> 調査日: 2026-05-16

### VOQ Chassis — システムインタフェース同期差

`DEVICE_METADATA|localhost.switch_type=voq` のシャーシ構成では、`VLAN_INTERFACE` テーブルへの SET/DEL に伴う RIF 作成・削除が追加の CHASSIS_APP_DB 同期を引き起こす[^ph1][^ph2]。

```cpp
// intfsorch.cpp:1314-1317
// RIF 作成直後に自動実行
if(isChassisDbInUse())
    voqSyncAddIntf(port.m_alias);  // CHASSIS_APP_DB::SYSTEM_INTERFACE_TABLE に書き込み

// intfsorch.cpp:1367-1370
// RIF 削除直後に自動実行
if(isChassisDbInUse())
    voqSyncDelIntf(port.m_alias);  // CHASSIS_APP_DB::SYSTEM_INTERFACE_TABLE から削除
```

`voqSyncAddIntf` はローカルポート（`SAI_SYSTEM_PORT_TYPE_REMOTE` でないもの）のみを同期する。リモートポートの IF は `CHASSIS_APP_DB::SYSTEM_INTERFACE_TABLE` を購読して受信し、`gNeighOrch->ifChangeInformRemoteNextHop` でネクストホップ状態を更新する。

VLAN IF へ IPv6 アドレスを付与する場合、VOQ 構成では `ip -6 address add ... metric 256` を付与する（通常構成は metric 指定なし）。VOQ システムでは eBGP / iBGP 経路の ECMP グループ一致のために metric=256 を明示する必要があるためである（`intfmgr.cpp:98-106`）。

| 構成 | 追加動作 |
|------|---------|
| VOQ chassis (local port/LAG) | RIF 作成・削除時に `CHASSIS_APP_DB::SYSTEM_INTERFACE_TABLE` へ `oper_status` を SET / DEL |
| VOQ chassis (inband port) | IP 追加/削除時に `addInbandNeighbor` / `delInbandNeighbor` を呼び出しリモート ASIC にネイバー伝播（`intfsorch.cpp:586-593`） |
| VOQ chassis (remote port) | `CHASSIS_APP_SYSTEM_INTERFACE_TABLE_NAME` からの通知でリモートネクストホップを更新（`intfsorch.cpp:881-892`） |
| VOQ chassis (IPv6 アドレス追加) | `ip -6 address add ... metric 256` を付与。通常構成は metric 指定なし（`intfmgr.cpp:103-106`） |
| 通常シングルスイッチ | CHASSIS_APP_DB 操作は一切なし |

> **注意**: `VLAN_INTERFACE` は VLAN SVI であり物理ポートではないため、`voqSyncAddIntf` 内の system port alias 解決は VLAN ポートに対して適用される。VLAN ポートの `m_system_port_info.type` が `SAI_SYSTEM_PORT_TYPE_REMOTE` となる場合、同期はスキップされる。

### SmartSwitch DPU — 現時点でのコード差なし

`sonic-swss/orchagent/intfsorch.cpp` および `cfgmgr/intfmgr.cpp` には SmartSwitch / DPU 固有の条件分岐は存在しない（2026-05-16 時点）。DPU 上の `VLAN_INTERFACE` テーブル処理は通常の物理スイッチと同一経路をたどる。SmartSwitch 固有のインタフェース管理は `dpuorch` / `midplaneorch` に委譲されており、本テーブルには影響しない。

[^ph1]: `sonic-swss/orchagent/intfsorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/intfsorch.cpp>
[^ph2]: `sonic-swss/cfgmgr/intfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>

<!-- /platform -->

<!-- glossary-links-injected: b8bde3f9637a -->
