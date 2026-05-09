---
title: VLAN インタフェースの OpenConfig YANG 対応（REST / gNMI）
area: switching
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/mgmt/OpenConfig_VLAN_Interface.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - VLAN
    - VLAN_INTERFACE
    - VLAN_MEMBER
  cli: []
  yang:
    - openconfig-interfaces
    - openconfig-vlan
---

!!! warning "裏取りステータス: HLD-only"
    HLD は 2025-05 (Rev 0.1)。`sonic-mgmt-common` の transformer 経路、REST/gNMI ハンドラ実装、エラーハンドリングは要裏取り。**詳細な REST/gNMI ペイロード例や全テストケースは原文 HLD `doc/mgmt/OpenConfig_VLAN_Interface.md` を参照**。

# VLAN インタフェースの OpenConfig YANG 対応（REST / gNMI）

## 概要

SONiC は従来 VLAN インタフェース設定を **SONiC 独自 YANG** 経由で REST / gNMI に公開していた。本機能はこれに加えて **OpenConfig YANG モデル** (`openconfig-interfaces` + `openconfig-vlan` + `openconfig-if-ip`) でも同等の操作（GET / SET / DELETE）を可能にする[^1]。

実装は `sonic-mgmt-common` の **transformer** 経路を使う（translib ベースではない）。コード追加対象は Management Framework / gnmi コンテナ[^1]。

スコープと非スコープ[^1]:

- ✅ VLAN interface / VLAN member の設定・取得
- ✅ Ethernet / PortChannel を VLAN メンバとして add/del
- ✅ VLAN インタフェース上の IPv4 / IPv6 アドレス設定
- ❌ KLISH CLI（既存 SONiC CLI に変更なし）
- ❌ Subinterface 設定

## 動作仕様

### サポートされる OpenConfig YANG ツリー（追加分）

`openconfig-interfaces:interfaces/interface[<name>]` 配下に次のノードを実装する[^1]:

```
oc-eth:ethernet/oc-vlan:switched-vlan/config
  interface-mode  : ACCESS | TRUNK
  access-vlan     : vlan-id
  trunk-vlans*    : vlan-id (list)

oc-lag:aggregation/oc-vlan:switched-vlan/config
  (Ethernet と同じ 3 フィールド、PortChannel 用)

oc-vlan:routed-vlan/config
  vlan          : "Vlan<id>"
  oc-ip:ipv4/addresses/address[<ip>]/config { ip, prefix-length }
  oc-ip:ipv6/addresses/address[<ip>]/config { ip, prefix-length }
  oc-ip:ipv6/config/enabled
```

`switched-vlan` は L2 メンバ（access / trunk）、`routed-vlan` は VLAN にぶら下がる L3 IP の表現。

### バックエンドマッピング

```mermaid
flowchart LR
  CTL[Client<br>REST / gNMI] --> MF[Management Framework<br>REST / gnmi コンテナ]
  MF --> XF[transformer<br>(sonic-mgmt-common)]
  XF --> CDB[(CONFIG_DB:<br>VLAN / VLAN_INTERFACE /<br>VLAN_MEMBER)]
```

CONFIG_DB / APP_DB / STATE_DB / ASIC_DB / COUNTER_DB のスキーマには **変更が無い**[^1]。透過的に既存テーブルにマップする transformer ロジックだけが追加される。

### REST API

#### GET

leaf レベルでも GET 可能[^1]。原文 HLD に出力例多数（IPv4 設定済 / IPv6 設定済 / メンバ trunk 単一・複数 / access 等）。代表例:

```bash
curl -k "https://<dut>/restconf/data/openconfig-interfaces:interfaces/interface=Vlan10" \
  -H "accept: application/yang-data+json"
```

応答（IPv4 あり）:

```json
{"openconfig-interfaces:interface":[{
  "config":{"enabled":true,"name":"Vlan10"},
  "openconfig-vlan:routed-vlan":{
    "config":{"vlan":"Vlan10"},
    "openconfig-if-ip:ipv4":{
      "addresses":{"address":[{"config":{"ip":"133.3.3.4","prefix-length":24}, "ip":"133.3.3.4"}]}}},
  "state":{"admin-status":"UP","enabled":true,"mtu":9100,"name":"Vlan10"}}]}
```

#### PATCH / PUT / POST / DELETE

それぞれ標準 RESTCONF セマンティクス。各操作の対応 OpenConfig path は HLD 内に表で網羅されている[^1]。

### gNMI

`Set` / `Get` / `Subscribe` をサポートする[^1]:

- `Set`: REPLACE / UPDATE / DELETE のいずれも OpenConfig パスで指定
- `Get`: leaf / container / list のいずれも可
- `Subscribe`: ON_CHANGE / SAMPLE モード対応（state ノード中心）

### エラーハンドリング

許されない操作（例: Vlan が存在しないのにメンバ追加、IPv4 アドレスに IPv6 を入れる等）は transformer 段で検出して RESTCONF / gRPC エラーで返す[^1]。詳細なエラーカタログは原文 HLD §5 を参照。

<!-- evidence:
source: sonic-net/SONiC/doc/mgmt/OpenConfig_VLAN_Interface.md#L150-L175 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  This feature adds support for OpenConfig based YANG models using transformer based implementation instead of translib infra.
  ... There are no changes to CONFIG DB schema definition.
reasoning: transformer 実装と CONFIG_DB 不変の根拠。
-->

## 設定

### 関連する CONFIG_DB

| Table | 用途 |
|-------|------|
| `VLAN` | VLAN 自体（`Vlan<id>`、`mtu`、`admin_status` 等）|
| `VLAN_INTERFACE` | VLAN インタフェース上の IPv4 / IPv6 アドレス |
| `VLAN_MEMBER` | port / portchannel と VLAN の関連付け（access / trunk）|

`switched-vlan.interface-mode` (`ACCESS` / `TRUNK`) は `VLAN_MEMBER.tagging_mode` (`untagged` / `tagged`) にマップされる想定。

### 関連する CLI

CLI に変更はない[^1]。`config vlan add/del/member` 等の既存 SONiC ネイティブ CLI と OpenConfig 経路は **同じ CONFIG_DB を共有** する。

### 設定例（REST）

PATCH で trunk メンバ追加:

```bash
curl -k -X PATCH \
  "https://<dut>/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet0/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan" \
  -H "Content-Type: application/yang-data+json" \
  -d '{"openconfig-vlan:switched-vlan":{"config":{"interface-mode":"TRUNK","trunk-vlans":[10,20]}}}'
```

詳細なペイロード例は原文 HLD `doc/mgmt/OpenConfig_VLAN_Interface.md` の §3.3 / §6 を参照[^1]。

## 制限事項

- **subinterface 非対応**: 本 HLD のスコープ外[^1]。
- **CLI から OpenConfig 経路は呼ばれない**: 既存 KLISH CLI は SONiC YANG 経由のまま。OpenConfig は REST / gNMI 専用。
- **transformer 経由のため、translib との並走に注意**: SONiC YANG 経路と OpenConfig 経路で同じ CONFIG_DB に書くため、両系統からの同時更新で一時的な不整合が起こりうる。
- **詳細仕様は原文必読**: 本ページは概要のみ。テーブル形式の OpenConfig→SONiC YANG マッピング、エラーケース 20 種等は原文 HLD §3〜§6 にある[^1]。

## 干渉する機能

- **既存の SONiC YANG 経路**: `sonic-vlan` / `sonic-vlan-interface` を経由した REST / gNMI と CONFIG_DB を共有。両経路で同一エンティティを操作する場合の最終整合性に注意[^1]。
- **VLAN 機能本体（VlanMgr / orchagent）**: CONFIG_DB 経由なので本機能から透過的に動く。スキーマ変更なし。
- **interface-mode の trunk/access 切替**: 既存メンバの mode 変更は CONFIG_DB レベルで `tagging_mode` を書き換えるが、TRUNK の VLAN リスト操作は `VLAN_MEMBER` キーの追加・削除で表現される。

## トラブルシューティング

- PATCH が 4xx で失敗: OpenConfig YANG パスのスペル、`Vlan<id>` の表記、許可されないモード組合せを確認。
- 操作は通るが反映されない: CONFIG_DB を直接 redis で見て `VLAN_MEMBER` / `VLAN_INTERFACE` の状態を確認。VlanMgr のログ参照。
- gNMI Subscribe が来ない: state コンテナを subscribe しているか、ON_CHANGE / SAMPLE のモード設定を確認。

## 引用元

[^1]: `sonic-net/SONiC` `doc/mgmt/OpenConfig_VLAN_Interface.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
