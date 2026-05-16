---
title: DHCP_SERVER_IPV6 テーブル
description: "DHCP_SERVER_IPV6 テーブル — 組み込み DHCPv6 サーバ機能の設定テーブル（2026-05 時点で未実装。SONiC master は DHCPv6 リレーのみ対応）。"
area: reference
hard: 0
verification: stub
monitor: not_implemented
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dhcpv6-relay.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - DHCP_SERVER_IPV4
    - DHCP_RELAY
  cli: []
  yang: []
  _no_related_cli: true
  _no_related_yang: true
---

# DHCP_SERVER_IPV6 テーブル

!!! warning "未実装"
    `DHCP_SERVER_IPV6` テーブルは **2026-05-14 時点で sonic-net/sonic-buildimage master に存在しない**。
    SONiC の組み込み DHCP サーバ機能は IPv4 専用（`DHCP_SERVER_IPV4`）のみ実装されている。
    このページは将来の実装に備えたプレースホルダーである。

## 概要

SONiC は DHCPv6 **リレー**機能（`DHCP_RELAY` テーブル）を持つが、DHCPv6 **サーバ**機能は未実装である。IPv4 側の対応テーブルである `DHCP_SERVER_IPV4` が `dhcpservd` + kea-dhcp4 によって実装されているのに対し、kea-dhcp6 を管理するデーモンおよび対応 CONFIG_DB テーブルは存在しない。

<!-- defaults -->
## フィールドデフォルト (Phase A 調査)

**調査結果: フィールドなし（テーブル未実装）**

SONiC master における `DHCP_SERVER_IPV6` テーブルの YANG モデル、Python デーモン、CLI プラグインは確認されなかった。コード由来のデフォルト値を抽出できるフィールドが存在しない。

実装済み IPv4 版との対比:

| 確認対象 | IPv4 (`DHCP_SERVER_IPV4`) | IPv6 (`DHCP_SERVER_IPV6`) |
|---------|--------------------------|--------------------------|
| YANG モデル | `sonic-dhcp-server-ipv4.yang` | なし |
| デーモン | `dhcpservd` (kea-dhcp4) | なし |
| CLI | `config dhcp_server ipv4` | なし |
| 主要フィールド | `state`, `lease_time`, `mode`, `gateway`, `netmask` | 未定義 |

> Evidence: sonic-buildimage@9ea932ec — `src/sonic-yang-models/yang-models/` にて `sonic-dhcp-server-ipv6.yang` 不在を確認。`doc/dhcp_server/port_based_dhcp_server_high_level_design.md` に「IPv4 Port Based DHCP_SERVER」と明記。

<!-- /defaults -->

<!-- pubsub -->
## 通信メカニズム (Phase G 調査)

> **調査根拠**: `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` 全行精読 (2026-05-16)

### DHCP_SERVER_IPV6 に関する結論

`DHCP_SERVER_IPV6` テーブルは未実装であるため、このテーブルを購読・監視するデーモンは存在しない。CONFIG_DB Subscribe、dhcrelay 制御、netlink 監視はすべて **`DHCP_RELAY` テーブルを対象とした `dhcp6relay` プロセス**が担っている。

### DHCPv6 リレー側の通信メカニズム（参照）

`DHCP_SERVER_IPV6` が将来実装される際の参照として、現在の DHCPv6 関連実装を記録する。

#### CONFIG_DB Subscribe (`dhcp6relay`)

`dhcp6relay` (`sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp`) は以下の方法で CONFIG_DB を購読する:

```
dhcp6relay 起動
  └─ initialize_swss()                             (config_interface.cpp:18-29)
       ├─ DBConnector("CONFIG_DB", 0)               ← Redis DB #4
       ├─ SubscriberStateTable(db, "DHCP_RELAY")   ← DHCP_RELAY テーブル購読
       │    └─ PSUBSCRIBE __keyspace@4__:DHCP_RELAY|*
       └─ swssSelect.addSelectable(&ipHelpersTable)
            └─ get_dhcp(vlans, table, dynamic=false, config_db)
                 └─ swssSelect.select(timeout_ms=1000)
                      └─ handleRelayNotification()
                           └─ pops() → processRelayNotification()
```

| 項目 | 値 |
|------|-----|
| 購読テーブル | `DHCP_RELAY`（`DHCP_SERVER_IPV6` は **なし**） |
| SWSS abstraction | `swss::SubscriberStateTable` + `swss::Select` |
| PSUBSCRIBE パターン | `__keyspace@4__:DHCP_RELAY\|*` |
| Select timeout | 1000 ms |
| ConsumerStateTable | **不使用** |
| NotificationConsumer | **不使用** |
| TTL / keyspace expire | **不使用** |

#### dhcrelay 制御

`dhcp6relay` はシグナルで制御される。`relay.cpp` で `libevent` を使って SIGINT / SIGTERM をキャッチし、`event_base_loopbreak()` でイベントループを終了する (`relay.cpp:1154-1220`)。

```
SIGTERM / SIGINT 受信
  └─ signal_callback(fd, event, base)              (relay.cpp:1214)
       └─ event_base_loopbreak(base)
```

**動的設定変更は非対応**: `DHCP_RELAY` エントリを変更しても `dynamic=true` フラグにより無視され、`LOG_WARNING "relay config changed, need restart container to take effect"` のみ出力される。設定反映にはコンテナ再起動が必須 (`config_interface.cpp:76-78`)。

#### netlink（間接利用）

`dhcp6relay` は netlink を直接使用しない。LLA（Link Local Address）の確認は `ip -6 addr show <vlan> scope link` コマンドを `popen()` で呼び出す方式を採用する (`config_interface.cpp:196-209`)。インタフェースインデックスの取得のみ `if_nametoindex()` を使用する (`relay.cpp:829`)。

```
// LLA 確認 (config_interface.cpp:196-209)
const std::string cmd = "ip -6 addr show " + vlan + " scope link 2> /dev/null";
popen(cmd.c_str(), "r")  // netlink ソケット直接使用なし
```

<!-- /pubsub -->

<!-- platform -->
## プラットフォーム差 (Phase H)

`DHCP_SERVER_IPV6` テーブル自体は未実装だが、DHCPv6 リレー (`dhcp6relay`) には以下のプラットフォーム差が確認された。

| 観点 | 結果 | 根拠 |
|------|------|------|
| DualToR | **差異あり** — MUX 状態に応じてパケット転送を制御 | `DEVICE_METADATA.localhost.subtype == "DualToR"` の場合のみ `-u Loopback0` オプションで起動。`dual_tor_sock = true` がセットされ、`HW_MUX_CABLE_TABLE` の `state` が `standby` なら転送スキップ (`relay.cpp:913-921`) |
| SmartSwitch DPU | **dhcp6relay 非対応** — DPU 経路実装なし | `dhcp4relay` は `is_SmartSwitch` フラグ・`DPUS` テーブル監視・`bridge-midplane` MAC 取得を実装するが、`dhcp6relay/src/` には SmartSwitch/DPU 関連コードが存在しない |
| IPv6 link-local アドレス (LLA) | **DHCPv6 固有の生成待機ロジック** | `check_is_lla_ready()` が `ip -6 addr show <vlan> scope link` で LLA 存在を確認。60 秒タイマー (`lla_check_callback`) でポーリングし、LLA 生成後にソケットを動的追加 (`relay.cpp:1288-1310`) |
| multi-asic | 影響なし | `initialize_swss()` は `CONFIG_DB` を namespace 引数なしで接続。`asicN` namespace を iterate しない |
| ASIC ベンダー | 影響なし | `dhcp6relay` は純粋 L3 UDP リレー処理。SAI / ASIC SDK 非経由 |

### DualToR 構成の詳細

DualToR 環境では `dhcpv6-relay.agents.j2:16` の Jinja2 条件により `dhcp6relay -u Loopback0` として起動する:

```jinja2
{% if 'subtype' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['subtype'] == 'DualToR' %} -u Loopback0 {% endif %}
```

`-u` フラグが渡ると:

1. Loopback0 の GUA アドレスに追加ソケットを作成（`prepare_lo_socket`）し、`server_callback_dualtor` イベントを登録する
2. クライアントからのパケット受信時に `HW_MUX_CABLE_TABLE|<intf>` で `state` を確認し、`standby` の場合は転送しない（active 側のみが中継を担う）
3. サーバからの応答は Loopback ソケット (`server_callback_dualtor`) 経由で受信し、クライアントへ中継する

### SmartSwitch DPU — DHCPv6 非対応

DHCPv4 側 (`dhcp4relay`) が SmartSwitch の `DPUS` テーブルを監視し DPU インターフェース (`dpu0..N`) 向けに `GIADDR` を書き換えるのに対し、**`dhcp6relay` には同等の実装がない**。SmartSwitch 環境での DPU への DHCPv6 アドレス配布は community master では未サポートである。

### IPv6 LLA 生成待機の仕組み

VLAN インターフェースに IPv6 GUA が設定されていても kernel による LLA (`fe80::`) 生成は数ミリ秒〜数秒の遅延がある。`dhcp6relay` は起動直後に `lla_check_callback` を手動実行し (`relay.cpp:1310`)、その後 60 秒ごとにポーリングする。LLA が確認されると `is_lla_ready = true` としてソケット作成・イベント登録を行う。LLA が未生成の VLAN はソケット作成をスキップし、次回タイマーで再試行する。

詳細根拠は `meta/_intermediate/cdb-flow/dhcp-server-ipv6-platform.md` を参照。
<!-- /platform -->

## DHCPv6 サポートの現状

SONiC の DHCPv6 対応は次の 2 要素のみ:

1. **DHCPv6 リレー** — `DHCP_RELAY` テーブル（sonic-dhcpv6-relay.yang）。VLAN ごとに `dhcpv6_servers`、`rfc6939_support`、`interface_id` を設定し、`dhcrelay` プロセスが DHCPv6 RELAY-FORWARD/REPLY をプロキシする
2. **DHCPv6 リレーカウンタ** — `show dhcp6relay_counters` CLI で統計確認可能

DHCPv6 サーバ機能（kea-dhcp6 管理、ステートフル/ステートレスアドレス配布）はコミュニティ版 master には存在しない。

## 関連ドキュメント

- [DHCP_SERVER_IPV4 テーブル](dhcp-server-ipv4.md) — 実装済み IPv4 版
- [DHCP_RELAY テーブル（DHCPv4）](dhcp-relay.md)
- [DHCPv4 リレー テーブル](dhcpv4-relay.md)

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`DHCP_SERVER_IPV4`](dhcp-server-ipv4.md)、[`DHCP_RELAY`](dhcp-relay.md)

<!-- ref-triangle:end -->
