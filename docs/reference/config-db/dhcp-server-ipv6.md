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

<!-- ordering -->
## 書込み順依存 (Phase B 調査)

`DHCP_SERVER_IPV6` は未実装だが、SONiC の DHCPv6 リレー機能（`DHCP_RELAY` テーブル / `dhcp6relay` プロセス）には以下の順序依存が確認されている。将来 `DHCP_SERVER_IPV6` が実装された場合も同等の VLAN 前提条件が継承される見込み。

### VLAN_INTERFACE 先行が必須

`dhcp6relay` の起動時 (`initialize_swss()` → `processRelayNotification()`) は `DHCP_RELAY|<vlan>` エントリを処理する際に CONFIG_DB の `VLAN_INTERFACE|<vlan>|*` キーを検索し、**IPv6 アドレス（コロン含む）が 1 件も存在しない VLAN は無条件でスキップ**する。

```
// dhcp6relay/src/config_interface.cpp:130-148
const std::string match_pattern = "VLAN_INTERFACE|" + vlan + "|*";
auto keys = config_db->keys(match_pattern);
...
if (!has_ipv6_address) {
    syslog(LOG_WARNING, "%s doesn't have IPv6 address configured, skip it", vlan.c_str());
    continue;
}
```

runtime 中の動的更新は「コンテナ再起動が必要」ログを出すのみで設定反映されないため、**DHCP_RELAY 書込み前に VLAN_INTERFACE への IPv6 アドレス付与が完了していること**が必要。

推奨書込み順序:

```
1. VLAN（ブリッジ定義）
2. VLAN_INTERFACE|<vlan>|<ipv6-prefix>  ← IPv6 グローバルアドレス
3. DHCP_RELAY|<vlan>（dhcpv6_servers を含む）
```

### dhcp6relay 起動条件（supervisor テンプレート）

`dhcpv6-relay.agents.j2` / `dhcp-relay.programs.j2` は supervisord エントリを Jinja2 で動的生成する。`dhcp6relay` プログラムは次の条件がすべて真のときのみ登録・起動される:

1. `VLAN_INTERFACE` にエントリが存在する
2. 当該 VLAN が `DHCP_RELAY` に存在し `dhcpv6_servers` が空でない
3. `dhcpv6_servers` に有効な IPv6 アドレスが 1 件以上含まれる

条件を満たさない状態でコンテナが起動すると `dhcp6relay` はそもそも supervisord に登録されない。

### systemd 起動順（dhcp-relay.service）

`dhcp_relay.service.j2` は以下の `After=` を持つ:

```
After=config-setup.service swss.service syncd.service teamd.service
```

`teamd.service` が完了して VLAN インターフェースが UP し LLA が生成された後に `dhcp-relay` コンテナが起動するため、**LLA 未生成によるソケット開設失敗は通常発生しない**。ただし `After=` は完了順序のみ保証し、CONFIG_DB への全データ書込みは `config-setup.service` の完了に依存する。

> Evidence: `sonic-net/sonic-dhcp-relay@dhcp6relay/src/config_interface.cpp:130-148`、`sonic-net/sonic-buildimage@dockers/docker-dhcp-relay/dhcpv6-relay.agents.j2:2-10`、`sonic-net/sonic-buildimage@files/build_templates/dhcp_relay.service.j2:4`

<!-- /ordering -->

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
