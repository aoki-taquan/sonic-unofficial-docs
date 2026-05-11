---
title: 設定
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 設定

gNMI からの Get / Set / Subscribe は、対象の YANG path を OpenConfig / SONiC native のどちらで指定するかを最初に決める。ここでは代表機能 (interface, VLAN, PortChannel, BGP) について OpenConfig 側のマップを起点にする。実コマンド例と容量は [gNMI usage](../../management/gnmi-usage.md) にまとまっている。

## Get / Set / Subscribe の典型

gNMI の主要 RPC を SONiC 観点で短く整理する。

- **Get**: 単発取得。`encoding=JSON_IETF` で OpenConfig パスを与える形と、`encoding=JSON` で SONiC native YANG パスを与える形がある。
- **Set**: replace / update / delete を 1 リクエストで混在できる。replace は YANG モデル意味論で部分木を置換する。delete は OpenConfig 側で表現可能なノードのみ対応するため、SONiC native 側を併用するケースがある。詳細は [Model-based replace/delete in Transformer](../../management/model-based-replace-delete-in-mgmt-framework-transformer.md) を参照する。
- **Subscribe**: ON_CHANGE / SAMPLE / TARGET_DEFINED。CONFIG_DB / APPL_DB / STATE_DB / COUNTERS_DB をまたいで購読できる。

クライアント実装例、`gnmi_cli` / `gnmi_get` / `gnmi_set` の引数組み立て、TLS 設定は [gNMI usage](../../management/gnmi-usage.md) を参照する。

## OpenConfig パスのよく使うエントリ

### Ethernet interface

OpenConfig interface (`/openconfig-interfaces:interfaces/interface`) で MTU、admin-status、speed、FEC、auto-negotiation、subinterfaces を扱う。SONiC では `Ethernet0` のような物理ポート命名がそのまま name キーとして使われる。マップ範囲、操作可能フィールド、CONFIG_DB との対応は [OpenConfig support for ethernet interfaces](../../management/openconfig-support-for-ethernet-interfaces.md) を参照する。

### VLAN interface

OpenConfig は VLAN を、interface 直下の `switched-vlan` と独立した `vlans` の両方で表現する。SONiC では `VLAN` テーブルと `VLAN_INTERFACE` / `VLAN_MEMBER` テーブルにマップされる。OpenConfig VLAN の SONiC でのサポート範囲は [OpenConfig VLAN](../../switching/add-support-for-vlan-interface-using-openconfig-yang.md) を参照する。

### PortChannel (LAG)

OpenConfig `aggregate` interface として PortChannel を扱う。member 追加は `aggregate-id` を物理 interface に設定する形で表現される。SONiC native では `PORTCHANNEL` / `PORTCHANNEL_MEMBER` テーブルが対象。詳細は [OpenConfig PortChannel](../../switching/openconfig-support-for-portchannel-aggregate-interface.md) を参照する。

### BGP

BGP は OpenConfig BGP と SONiC native BGP の両方が定義され、Management Framework の選択 (`frr_mgmt_framework_config`) によって FRR への反映経路が変わる。OpenConfig 経由で書く場合は `frrcfgd` が CONFIG_DB の差分から FRR vty を生成する。詳細は [BGP / FRR Unified Mgmt Framework](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) と章 02 の [BGP - 設定](../02-bgp/setup.md) を参照する。

## SONiC native YANG の役割

OpenConfig がカバーしないフィールド (たとえば SONiC 固有の feature flag、ASIC 特有の counter、telemetry 設定、特定の hardware option) は SONiC native YANG から入る。Native YANG のモジュール命名と書き方は [SONiC YANG model guidelines](../../management/sonic-yang-model-guidelines.md) にまとまっている。

機能章別の YANG モジュール一覧は [YANG リファレンス](yang-reference.md) を参照する。

## CLI と gNMI の混在

CLI と gNMI を併用する運用では、同じノードを CLI で書いて gNMI で読むケースが多い。CLI が YANG から自動生成される機能領域では、両者の表現が一致するため `gnmi_get` の結果と `show` 出力を相互参照できる。自動生成範囲外の機能では、CLI が CONFIG_DB を直接更新するケースもあり、その場合 gNMI subscribe で「設定変更があった」と通知される。自動生成の仕組みは [CLI auto-generation tool](../../management/sonic-cli-auto-generation-tool.md) を参照する。

## 関連ページ

- [gNMI usage](../../management/gnmi-usage.md)
- [Model-based replace/delete in Transformer](../../management/model-based-replace-delete-in-mgmt-framework-transformer.md)
- [OpenConfig ethernet interfaces](../../management/openconfig-support-for-ethernet-interfaces.md)
- [OpenConfig VLAN](../../switching/add-support-for-vlan-interface-using-openconfig-yang.md)
- [OpenConfig PortChannel](../../switching/openconfig-support-for-portchannel-aggregate-interface.md)
- [BGP / FRR Unified Mgmt Framework](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md)
- [SONiC YANG model guidelines](../../management/sonic-yang-model-guidelines.md)
- [SONiC CLI auto-generation tool](../../management/sonic-cli-auto-generation-tool.md)
