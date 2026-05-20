---
title: 設定
description: 設定 — gNMI からの Get / Set / Subscribe は、対象の YANG path を OpenConfig / SONiC
  native のどちらで指定するかを最初に決める。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/management/gnmi-usage.md
- docs/management/openconfig-support-for-ethernet-interfaces.md
- docs/management/sonic-yang-model-guidelines.md
- docs/management/model-based-replace-delete-in-mgmt-framework-transformer.md
- docs/reference/config-db/telemetry.md
related:
  cli:
  - show ip
  - config bgp
  - show bgp
  - config portchannel
  - config vlan
  - show vlan
  config_db:
  - VLAN
  - VLAN_INTERFACE
  - VLAN_MEMBER
  - PORTCHANNEL
  - PORTCHANNEL_MEMBER
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  yang:
  - sonic-bgp-neighbor
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
  - sonic-bgp-aggregate-address
---

# 設定

[gNMI](../../reference/glossary.md#term-gnmi) からの Get / Set / Subscribe は、対象の [YANG](../../reference/glossary.md#term-yang) path を OpenConfig / [SONiC](../../reference/glossary.md#term-sonic) native のどちらで指定するかを最初に決める。ここでは代表機能 (interface, [VLAN](../../reference/glossary.md#term-vlan), [PortChannel](../../reference/glossary.md#term-portchannel), [BGP](../../reference/glossary.md#term-bgp)) について OpenConfig 側のマップを起点にする。実コマンド例と容量は [gNMI usage](../../management/gnmi-usage.md) にまとまっている。

## シナリオ 1: gNMI server 立ち上げ

DUT 側 (telemetry container) の起動と、client 側からの疎通確認まで。証明書は `/etc/sonic/telemetry/` 配下に置く。

```bash
# DUT 側
sudo systemctl start telemetry
sudo systemctl enable telemetry
redis-cli -n 4 HSET 'GNMI|gnmi' port 8080 client_auth true
redis-cli -n 4 HSET 'GNMI|certs' \
  server_crt /etc/sonic/telemetry/dut.crt \
  server_key /etc/sonic/telemetry/dut.key \
  ca_crt     /etc/sonic/telemetry/ca.crt
sudo systemctl restart telemetry

# client 側 (gNMI tools)
gnmi_capabilities -target_addr dut.example.com:8080 \
  -cert client.crt -key client.key -ca ca.crt
```

期待出力（一部）。

```yaml
supported_models: <
  name: "openconfig-interfaces"
  organization: "OpenConfig working group"
  version: "2.5.0"
>
supported_encodings: JSON_IETF
supported_encodings: PROTO
gNMI_version: "0.7.0"
```

設定後の確認。

```bash
$ ss -tlnp | grep 8080
LISTEN 0 128 *:8080 *:* users:(("telemetry",pid=12345,fd=7))

$ docker logs telemetry 2>&1 | tail -3
INFO[2026-05-11T03:14:21Z] Starting gNMI server on :8080
INFO[2026-05-11T03:14:21Z] Loaded server cert from /etc/sonic/telemetry/dut.crt
INFO[2026-05-11T03:14:21Z] Loaded CA cert from /etc/sonic/telemetry/ca.crt
```

## シナリオ 2: OpenConfig path で interface を Get / Set / Subscribe する

`Ethernet0` の MTU / admin-status を OpenConfig path 経由で読み書きする例。SONiC では `Ethernet0` のような物理ポート命名がそのまま name キーとして使われる。

Get:

```bash
gnmi_get -target_addr dut:8080 -cert client.crt -key client.key -ca ca.crt \
  -xpath '/interfaces/interface[name=Ethernet0]/state' \
  -encoding JSON_IETF
```

出力（抜粋）。

```json
{
  "openconfig-interfaces:state": {
    "name": "Ethernet0",
    "mtu": 9100,
    "admin-status": "UP",
    "oper-status": "UP",
    "ifindex": 5
  }
}
```

Set (MTU 変更、replace モード):

```bash
gnmi_set -target_addr dut:8080 -cert client.crt -key client.key -ca ca.crt \
  -replace '/interfaces/interface[name=Ethernet0]/config/mtu:::JSON_IETF:::9216'
```

Subscribe (ON_CHANGE で oper-status):

```bash
gnmi_cli -address dut:8080 -tls -client_crt client.crt -client_key client.key -ca_crt ca.crt \
  -query_type s \
  -query 'interfaces/interface[name=Ethernet0]/state/oper-status' \
  -streaming_type ON_CHANGE
```

## シナリオ 3: SONiC native YANG で BGP neighbor を作る

OpenConfig がカバーしない、または運用上 native のほうが薄く済む典型例として BGP neighbor 作成。`sonic-bgp-neighbor` を使う。

```bash
cat > /tmp/bgp_nbr.json <<'JSON'
{
  "sonic-bgp-neighbor:BGP_NEIGHBOR": {
    "BGP_NEIGHBOR_LIST": [
      {
        "neighbor": "10.0.0.1",
        "asn": 65001,
        "local_addr": "10.0.0.0",
        "admin_status": "up",
        "name": "spine-01"
      }
    ]
  }
}
JSON

gnmi_set -target_addr dut:8080 -cert client.crt -key client.key -ca ca.crt \
  -update '/sonic-bgp-neighbor:sonic-bgp-neighbor/BGP_NEIGHBOR:::JSON_IETF:::@/tmp/bgp_nbr.json'
```

確認 (DUT 側)。

```bash
$ redis-cli -n 4 KEYS 'BGP_NEIGHBOR|*'
1) "BGP_NEIGHBOR|10.0.0.1"

$ show ip bgp summary
Neighbor        V    AS    MsgRcvd    MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd
10.0.0.1        4 65001         12         12        0    0    0 00:00:42            5
```

## Get / Set / Subscribe の典型

gNMI の主要 RPC を SONiC 観点で短く整理する。

- **Get**: 単発取得。`encoding=JSON_IETF` で OpenConfig パスを与える形と、`encoding=JSON` で SONiC native YANG パスを与える形がある。
- **Set**: replace / update / delete を 1 リクエストで混在できる。replace は YANG モデル意味論で部分木を置換する。delete は OpenConfig 側で表現可能なノードのみ対応するため、SONiC native 側を併用するケースがある。詳細は [Model-based replace/delete in Transformer](../../management/model-based-replace-delete-in-mgmt-framework-transformer.md) を参照する。
- **Subscribe**: ON_CHANGE / SAMPLE / TARGET_DEFINED。[CONFIG_DB](../../reference/glossary.md#term-config_db) / [APPL_DB](../../reference/glossary.md#term-appl_db) / [STATE_DB](../../reference/glossary.md#term-state_db) / [COUNTERS_DB](../../reference/glossary.md#term-counters_db) をまたいで購読できる。

クライアント実装例、`gnmi_cli` / `gnmi_get` / `gnmi_set` の引数組み立て、TLS 設定は [gNMI usage](../../management/gnmi-usage.md) を参照する。

## OpenConfig パスのよく使うエントリ

### Ethernet interface

OpenConfig interface (`/openconfig-interfaces:interfaces/interface`) で MTU、admin-status、speed、FEC、auto-negotiation、subinterfaces を扱う。SONiC では `Ethernet0` のような物理ポート命名がそのまま name キーとして使われる。マップ範囲、操作可能フィールド、CONFIG_DB との対応は [OpenConfig support for ethernet interfaces](../../management/openconfig-support-for-ethernet-interfaces.md) を参照する。

### VLAN interface

OpenConfig は VLAN を、interface 直下の `switched-vlan` と独立した `vlans` の両方で表現する。SONiC では `VLAN` テーブルと `VLAN_INTERFACE` / `VLAN_MEMBER` テーブルにマップされる。OpenConfig VLAN の SONiC でのサポート範囲は [OpenConfig VLAN](../../switching/add-support-for-vlan-interface-using-openconfig-yang.md) を参照する。

### PortChannel (LAG)

OpenConfig `aggregate` interface として PortChannel を扱う。member 追加は `aggregate-id` を物理 interface に設定する形で表現される。SONiC native では `PORTCHANNEL` / `PORTCHANNEL_MEMBER` テーブルが対象。詳細は [OpenConfig PortChannel](../../switching/openconfig-support-for-portchannel-aggregate-interface.md) を参照する。

### BGP

BGP は OpenConfig BGP と SONiC native BGP の両方が定義され、Management Framework の選択 (`frr_mgmt_framework_config`) によって [FRR](../../reference/glossary.md#term-frr) への反映経路が変わる。OpenConfig 経由で書く場合は `frrcfgd` が CONFIG_DB の差分から FRR vty を生成する。詳細は [BGP / FRR Unified Mgmt Framework](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) と章 02 の [BGP - 設定](../02-bgp/setup.md) を参照する。

## SONiC native YANG の役割

OpenConfig がカバーしないフィールド (たとえば SONiC 固有の feature flag、[ASIC](../../reference/glossary.md#term-asic) 特有の counter、telemetry 設定、特定の hardware option) は SONiC native YANG から入る。Native YANG のモジュール命名と書き方は [SONiC YANG model guidelines](../../management/sonic-yang-model-guidelines.md) にまとまっている。

機能章別の YANG モジュール一覧は [YANG リファレンス](yang-reference.md) を参照する。

## CLI と gNMI の混在

CLI と gNMI を併用する運用では、同じノードを CLI で書いて gNMI で読むケースが多い。CLI が YANG から自動生成される機能領域では、両者の表現が一致するため `gnmi_get` の結果と `show` 出力を相互参照できる。自動生成範囲外の機能では、CLI が CONFIG_DB を直接更新するケースもあり、その場合 gNMI subscribe で「設定変更があった」と通知される。自動生成の仕組みは [CLI auto-generation tool](../../management/sonic-cli-auto-generation-tool.md) を参照する。

## CONFIG_DB / GNMI 関連 table

gNMI server の起動制御に使う table（旧 `TELEMETRY` は `db_migrator` の `migrate_gnmi()` で `GNMI` に移行済み）。

```json
{
  "GNMI": {
    "gnmi": {"port":"8080","client_auth":"true","log_level":"2"},
    "certs":{"server_crt":"/etc/sonic/telemetry/dut.crt",
             "server_key":"/etc/sonic/telemetry/dut.key",
             "ca_crt":"/etc/sonic/telemetry/ca.crt"}
  }
}
```

`client_auth=true` で mTLS、`false` で server 認証のみ。`log_level` は 0–9 で大きいほど詳細。

## よくある設定エラーと対処

| 症状 | 典型的な原因 | 対処 |
|---|---|---|
| `gnmi_capabilities` が `transport: authentication handshake failed` | DUT cert の SAN/CN が接続 FQDN と不一致 | `openssl x509 -in dut.crt -text -noout` で SAN を確認、cert 再発行 |
| `client_auth=true` で `peer certificate not provided` | client 側に `-cert/-key` を渡していない | client 側に DUT が信頼する CA 由来の cert/key を渡す |
| `Set` が `unknown path` で拒否される | OpenConfig path のうち SONiC 未対応の field | SONiC native YANG (`sonic-*`) に切り替えるか、CLI 経由で設定 |
| `Subscribe ON_CHANGE` が初回 sync 後に止まる | 対象 path が STATE_DB/COUNTERS_DB ではなく CONFIG_DB のみ | `SAMPLE` に切替、または STATE_DB 側の sibling path に変更 |
| `Set replace` で意図しないノードまで消える | replace の意味論 (部分木全置換) | 親 path を狭くする、または `update` を使う |
| FRR の BGP 設定が gNMI から反映されない | `frr_mgmt_framework_config` が無効 | `redis-cli -n 4 HSET 'DEVICE_METADATA|localhost' frr_mgmt_framework_config true` |
| gNMI server が起動しない (port LISTEN なし) | cert / key の permission または path 誤り | `docker logs telemetry` で読込エラーを確認、`chmod 600 dut.key` |

## 関連リファレンス

- [gNMI usage](../../management/gnmi-usage.md)
- [Model-based replace/delete in Transformer](../../management/model-based-replace-delete-in-mgmt-framework-transformer.md)
- [OpenConfig ethernet interfaces](../../management/openconfig-support-for-ethernet-interfaces.md)
- [OpenConfig VLAN](../../switching/add-support-for-vlan-interface-using-openconfig-yang.md)
- [OpenConfig PortChannel](../../switching/openconfig-support-for-portchannel-aggregate-interface.md)
- [BGP / FRR Unified Mgmt Framework](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md)
- [SONiC YANG model guidelines](../../management/sonic-yang-model-guidelines.md)
- [SONiC CLI auto-generation tool](../../management/sonic-cli-auto-generation-tool.md)
- 同章の [concept](concept.md) / [architecture](architecture.md) / [operations](operations.md) / [yang-reference](yang-reference.md)

<!-- glossary-links-injected: ec18b66e3507 -->
