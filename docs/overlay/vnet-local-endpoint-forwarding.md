---
title: VNET の Local Endpoint Forwarding（DPU 直結 nexthop の最適化）
area: overlay
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/smart-switch/high-availability/vnet_local_endpoint_forwarding.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - VNET_ROUTE_TUNNEL_TABLE
    - ACL_TABLE
    - ACL_RULE
  cli: []
  yang: []
---

!!! warning "裏取りステータス: HLD-only"
    このページは Smart Switch HA 関連 HLD（短い拡張仕様）のみを根拠にしている。`VNET_ROUTE_TUNNEL_TABLE` の `check_directly_connected` フィールド、`VnetOrch` の ARP 検査ロジック、`VNET_LOCAL_ENDPOINT_REDIRECT` ACL テーブルタイプ、`hamgrd` の連携経路は未裏取り。Overlay ECMP enhancements HLD と smart-switch-ha-hld との依存関係も別途整理が必要。

# VNET の Local Endpoint Forwarding（DPU 直結 nexthop の最適化）

## 概要

Smart Switch（NPU + 複数 DPU 構成）における HA 動作では、NPU から **local DPU** または **remote DPU** へパケットを送り分ける必要がある。詳細は別 HLD `smart-switch-ha-hld.md` の 4.2 節（data path HA）に記述されている[^1]。

このページが扱う HLD は、その流れの中で 2 つの最適化を定義する小さな拡張仕様である[^1]:

1. **directly connected nexthop の扱い**: local DPU が NPU から直結（ARP で見える）であるとき、tunnel route ではなく **通常の ECMP route** で扱うようにする。
2. **HA failover 時の transient state でのドロップ防止**: failover の瞬間に **high-priority ACL** で TUNNEL_TERM フラグを見て、必ず **local nexthop へ redirect** する。

## 動作仕様

### `VNET_ROUTE_TUNNEL_TABLE` の拡張

`VNET_ROUTE_TUNNEL_TABLE` に optional フィールド `check_directly_connected` を追加する[^1]:

```text
key   = VNET_ROUTE_TUNNEL_TABLE:<vnet_name>:<prefix>
field = check_directly_connected = BOOLEAN  (optional)
```

`true` の場合、`VnetOrch` は **ARP テーブルを引いて nexthop が directly connected かどうか確認** する[^1]:

- 直結の nexthop については **tunnel route ではなく、通常の ECMP route** を使う。
- ECMP route は通常の VxLAN ECMP route と同じく、**BFD liveness に追従** して更新される[^1]。

これは "Overlay ECMP enhancements - support for directly connected nexthops" の延長線上の設計[^1]。

```mermaid
flowchart TD
    VRT[VNET_ROUTE_TUNNEL_TABLE\ncheck_directly_connected=true] --> VO[VnetOrch]
    VO --> A{ARP に存在?}
    A -- yes --> ECMP[通常 ECMP route\n+ BFD 追従]
    A -- no --> TUN[tunnel route\n(従来どおり)]
```

### Failover transient state の問題

HA failover では一瞬「旧 active が standby に降格、旧 standby はそのまま standby」という **両方が standby** に近い transient state ができる。この間にパケットが正規ルートで処理されるとドロップが発生する可能性がある[^1]。

対策として、**high-priority ACL** を使って **TUNNEL_TERM フラグが立った（= tunnel decap 済の）パケット** を local nexthop に強制リダイレクトする[^1]。

### ACL の構造

`VnetOrch` が必要に応じて以下を APP_DB に投入する[^1]:

```mermaid
flowchart LR
    HAMGRD[hamgrd] --> VRTT[(VNET_ROUTE_TUNNEL_TABLE)]
    VRTT --> VO[VnetOrch]
    VXTT[(VXLAN_TUNNEL|tunnel_name)] --> VTO[VxlanTunnelOrch]
    VNT[(VNET|vnet_name)] --> VTO
    VO -->|create tunnel nh| VTO --> SAI[SAI/SDK]
    VO --> ART[(ACL_RULE_TABLE)]
    ART --> AO[AclOrch]
    IO[IntfOrch] -->|get local endpoint intf alias| VO
    AO --> SAI
```

`check_directly_connected=true` のエンドポイントが ARP で **neighbor として確認** できる場合のみ、**TUNNEL_TERM を match する ACL ルール** を追加する。全シナリオで作るとリソースを浪費するため、**local endpoint と確定したもののみ** ACL 化する設計[^1]。

### ACL テーブルタイプとルール

新規の ACL テーブルタイプ `VNET_LOCAL_ENDPOINT_REDIRECT`[^1]:

| 観点 | 値 |
|------|----|
| `MATCHES` | `DST_IP`, `DST_IPV6`, `TUNNEL_TERM` |
| `ACTIONS` | `REDIRECT_ACTION` |
| `BIND_POINTS` | `PORT`, `PORTCHANNEL` |

ACL テーブル定義例[^1]:

```json
{
  "ACL_TABLE": {
    "VNET_LOCAL_ENDPOINT": {
      "STAGE": "INGRESS",
      "TYPE": "VNET_LOCAL_ENDPOINT_REDIRECT",
      "PORTS": ["<Ingress front panel ports>"]
    }
  }
}
```

ACL ルール例[^1]:

```json
{
  "ACL_RULE": {
    "VNET_LOCAL_ENDPOINT:<vnet_name>_<prefix>_IN_TUNN_TERM": {
      "PRIORITY": "9998",
      "DST_IP": "1.1.1.1/32",
      "TUNN_TERM": "true",
      "REDIRECT": "<local nexthop interface>"
    }
  }
}
```

priority 9998 という高い値で、**通常の forwarding 経路よりも先にこの ACL が効く** 設計。tunnel decap 後のパケット（`TUNN_TERM=true`）で DST が当該 prefix のものは、必ず local nexthop に飛ぶ。

<!-- evidence:
source: sonic-net/SONiC/doc/smart-switch/high-availability/vnet_local_endpoint_forwarding.md#L31-L34 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  During an HA failover, the HA pair briefly enters a transient state...
  To handle this scenario, **high-priority** ACL rules matching tunnel termination flag are used to ensure redirects always go to the local nexthop.
reasoning: failover transient 対策として high-priority ACL + TUNNEL_TERM match を使うという中核ロジックの根拠。
-->

### 連携モジュール

ACL 投入と nexthop 解決のために複数 orch が連携する[^1]:

| モジュール | 役割 |
|------------|------|
| `hamgrd` | HA 状態管理。`VNET_ROUTE_TUNNEL_TABLE` への書き込み源 |
| `VnetOrch` | tunnel nexthop の作成、ARP 確認、ACL ルール投入の起点 |
| `VxlanTunnelOrch` | tunnel nexthop の SAI への降ろし |
| `IntfOrch` | local endpoint の interface alias 解決 |
| `AclOrch` | ACL ルールを SAI に降ろす |

`VnetOrch` から `IntfOrch` を引いて local endpoint の interface alias を取り、それを ACL の `REDIRECT` ターゲットに使う[^1]。

## 設定

### 関連する CONFIG_DB

| Table | Key | フィールド | 用途 |
|-------|-----|-----------|------|
| `VNET_ROUTE_TUNNEL_TABLE` | `<vnet>:<prefix>` | `check_directly_connected` (BOOLEAN, optional) | 直結チェックの opt-in |
| `ACL_TABLE` | `VNET_LOCAL_ENDPOINT` | `STAGE`, `TYPE=VNET_LOCAL_ENDPOINT_REDIRECT`, `PORTS` | 専用 ACL テーブル |
| `ACL_RULE` | `VNET_LOCAL_ENDPOINT:<vnet>_<prefix>_IN_TUNN_TERM` | `PRIORITY=9998`, `DST_IP`, `TUNN_TERM`, `REDIRECT` | 自動投入される redirect ルール |

`hamgrd` が `VNET_ROUTE_TUNNEL_TABLE` を編集することでパイプラインが起動する。`ACL_TABLE_TYPE` / `ACL_TABLE` / `ACL_RULE` は `VnetOrch` が必要に応じて自動投入する想定[^1]。

### 関連する CLI

該当する直接の CLI は HLD 内で定義されていない。Smart Switch / HA の管理 CLI 経由で `VNET_ROUTE_TUNNEL_TABLE` が更新される運用前提。

## 制限事項

- **`check_directly_connected` は optional**。指定が無い場合は従来どおり tunnel route のみで処理される。
- ACL を追加する条件は **ARP で nexthop が neighbor として確認できる場合のみ**[^1]。ARP の解決に失敗している間は ACL が立たないため、failover transient の保護効果も得られない時間帯がある可能性。
- ACL リソース（特にハードウェア TCAM）を消費する。directly connected な nexthop が多数ある環境では `VNET_LOCAL_ENDPOINT` テーブルのエントリが増えてリソース上限に達するリスクがある（HLD 内に明示の制限値はない）。
- HLD 自体に **packet flow diagram は TODO** とマーキングされている[^1]。詳細経路は smart-switch-ha-hld 4.2 章および Overlay ECMP enhancements 3.3 章を併読する必要がある。

## 干渉する機能

- **`smart-switch-ha-hld` の 4.2 節（data path HA）**: 本ページは「local endpoint と判別できた場合の最適化」のみを定義する。NPU→DPU 全体のパケットフローはこの本体 HLD を参照[^1]。
- **Overlay ECMP enhancements**: directly connected nexthop の取り扱いは Overlay ECMP enhancements の 3.3 章で定義されている設計を踏襲する。BFD liveness 連動の ECMP route も同経路[^1]。
- **BFD**: directly connected nexthop の通常 ECMP route は BFD で生死判定される。BFD が UP→DOWN になると ECMP メンバから外れる挙動。
- **`VxlanTunnelOrch`**: tunnel nexthop の作成自体はこちらの責務。`VnetOrch` から呼ばれて SAI に降ろす[^1]。
- **`AclOrch`**: 自動投入される ACL を SAI に降ろす。priority 9998 の ACL がポート bind されるため、既存の運用 ACL と priority が競合しないよう設計する必要がある[^1]。

## トラブルシューティング

- failover 直後に DROP が出る: ACL ルール `VNET_LOCAL_ENDPOINT:*` が CONFIG_DB / APP_DB に投入されているか確認。`check_directly_connected=true` 設定漏れ、または ARP 未解決のため ACL が立っていない可能性[^1]。
- tunnel route のままで local DPU 直結を生かせない: `VNET_ROUTE_TUNNEL_TABLE` の `check_directly_connected` を `true` に設定する。`VnetOrch` のログで ARP 確認結果を見る[^1]。
- ACL 数が肥大: directly connected nexthop が大量にある場合に発生しうる。設計上は local endpoint と確定したものに **限定して** 作る前提だが、prefix 単位での増加を見積もる必要[^1]。
- redirect が想定と違う interface に飛ぶ: `IntfOrch` から取得する `local nexthop interface` の alias が想定どおりか確認。`VnetOrch` のログで使用された interface 名を追う[^1]。

## 引用元

[^1]: `sonic-net/SONiC` `doc/smart-switch/high-availability/vnet_local_endpoint_forwarding.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
