---
title: DHCP_SERVER_IPV6 テーブル
description: "DHCP_SERVER_IPV6 テーブル — 組み込み DHCPv6 サーバ機能の設定テーブル（2026-05 時点で未実装。SONiC master は DHCPv6 リレーのみ対応）。"
area: reference
hard: 0
verification: stub
monitor: not_implemented
last_verified: 2026-05-16
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dhcpv6-relay.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-dhcp-relay
    path: dhcp6relay/src/relay.h
    ref: 7316417034fee6a6c6002490362c9bc75eeafde1
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
    `DHCP_SERVER_IPV6` テーブルは **2026-05-16 時点で sonic-net/sonic-buildimage master に存在しない**。
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

<!-- failure -->
## 失敗挙動 (Phase D 調査)

`DHCP_SERVER_IPV6` テーブルは未実装のため直接の失敗パスは存在しないが、DHCPv6 リレー機能（`DHCP_RELAY` テーブル / `dhcp6relay` プロセス）に以下の失敗挙動が確認されている。将来 `DHCP_SERVER_IPV6` が実装された場合も同等の前提条件・失敗パスが継承される見込み。

### 1. 不正 server_ip（`dhcpv6_servers`）→ LOG_WARNING + 不正アドレスのまま送信継続

`dhcp6relay/src/relay.cpp:476-486` — `prepare_relay_config()`:

```cpp
if(inet_pton(AF_INET6, server.c_str(), &tmp.sin6_addr) != 1)
{
    syslog(LOG_WARNING, "inet_pton: Failed to convert IPv6 address\n");
}
// ★ 変換失敗しても servers_sock.push_back(tmp) は実行される
interface_config.servers_sock.push_back(tmp);
```

`inet_pton()` が 1 を返さなかった場合（不正 IPv6 文字列）でも `servers_sock` にゼロ初期化の `sockaddr_in6` がプッシュされる。**エラー時に `continue` / `return` がなく、不正アドレスへの送信を試みる**。送信失敗は `sendto()` で `LOG_ERR` が出るが retry なし。

また `config_interface.cpp:176-179` で `dhcpv6_servers` が空の場合:

```cpp
if (intf.servers.empty()) {
    syslog(LOG_WARNING, "No servers found for VLAN %s, skipping configuration.", vlan.c_str());
    continue;
}
```

servers が空 VLAN はスキップ（CONFIG_DB にエントリが残存しても dhcp6relay は無視する）。

### 2. VLAN 未解決 → LOG_WARNING + VLAN スキップ（サービス不提供）

`config_interface.cpp:130-148` — `processRelayNotification()`:

```cpp
const std::string match_pattern = "VLAN_INTERFACE|" + vlan + "|*";
auto keys = config_db->keys(match_pattern);
...
if (!has_ipv6_address) {
    syslog(LOG_WARNING, "%s doesn't have IPv6 address configured, skip it", vlan.c_str());
    continue;
}
```

- `VLAN_INTERFACE` テーブルにキーが存在しない場合: `LOG_WARNING "%s doesn't exist in VLAN_INTERFACE table, skip it"`
- IPv6 アドレス（`:` を含む文字列）が 1 件もない場合: `LOG_WARNING "%s doesn't have IPv6 address configured, skip it"`
- いずれも `continue` でスキップ。**該当 VLAN への DHCPv6 リレーは提供されない**。rollback なし・DB 状態変更なし。

### 3. dhcrelay 起動失敗 → exit(EXIT_FAILURE) または retry 後 exit

`relay.cpp:588-658` — `prepare_vlan_sockets()`:

- VLAN ソケット（GUA/LLA）生成失敗: `LOG_ERR "socket: Failed to create gua/lla socket on interface %s\n"` → return -1
- GUA/LLA アドレス取得失敗: `LOG_WARNING "Retry #%d to bind to sockets on interface %s\n"` → 5 秒 sleep × 最大 6 回リトライ
- 6 回全リトライ失敗後:

```
LOG_ERR "bind: Failed to bind socket to global ipv6 address on interface %s after %d retries with %s"
```

→ return -1 → 呼び出し元で `exit(EXIT_FAILURE)`

`relay.cpp:412-434` — `sock_open()`:

- L2 raw ソケット生成失敗: `LOG_ERR "socket: Failed to create socket\n"` → return -1
- bind 失敗: `LOG_ERR "bind: Failed to bind to specified interface\n"` → close + return -1
- BPF filter attach 失敗: `LOG_ERR "setsockopt: Failed to attach filter\n"` → close + return -1

**supervisord / systemd による自動再起動に委ねる。`ERROR_TABLE` への書き込みはなし**（dhcp6relay は ERROR_TABLE を使用しない）。

### 4. runtime 設定変更は再起動まで反映されない（hot-reload 不可）

`config_interface.cpp:76-78`:

```cpp
syslog(LOG_WARNING, "relay config changed, need restart container to take effect");
```

CONFIG_DB の `dhcpv6_servers` を変更しても dhcp6relay は無視する。**DB 状態と実動作が乖離したまま継続**。再起動するまで新設定は反映されない。

> Evidence: `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.cpp:476-486`、`dhcp6relay/src/config_interface.cpp:130-148,176-179`

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E — コード由来)

`DHCP_SERVER_IPV6` テーブル自体は未実装だが、DHCPv6 プロトコル処理に直接関係する定数は **dhcp6relay**（`sonic-dhcp-relay` リポジトリ）の `relay.h` にハードコードされている。将来の `DHCP_SERVER_IPV6` 実装でも同一ポート・hop 上限が継承される見込みのため記録する。

### UDP ポート定数

| 定数名 | 値 | 用途 | ソース |
|--------|----|------|--------|
| `RELAY_PORT` | `547` | DHCPv6 サーバ／リレー間 UDP ポート (RFC 8415 §7.2) | relay.h L22 |
| `CLIENT_PORT` | `546` | DHCPv6 クライアント向け UDP ポート (RFC 8415 §7.2) | relay.h L23 |

BPF フィルタは `"udp and port 547"` を使用する。`dhcp6relay` は L2 ソケットを開きポート 547 宛のパケットを直接キャプチャする（`relay.cpp:403`）。

### ホップ上限

| 定数名 | 値 | 用途 | ソース |
|--------|----|------|--------|
| `HOP_LIMIT` | `8` | RELAY-FORWARD の hop_count がこの値以上のパケットはドロップ | relay.h L24 |

コメントに `"HOP_LIMIT reduced from 32 to 8 as stated in RFC8415"` と明記されている。ドロップ時は `syslog(LOG_WARNING, ...)` を出力する（`relay.cpp:747-751`）。新規クライアントパケットは hop_count=0 で開始し、中継ごとに +1 される（`relay.cpp:692, 758`）。**CONFIG_DB から上書き不可のハードコード定数**。

### その他の主要定数

| 定数名 | 値 | 用途 | ソース |
|--------|----|------|--------|
| `DHCPv6_OPTION_LIMIT` | `147` | サポートする DHCPv6 オプション上限 (IANA Option Codes 準拠) | relay.h L25 |
| `RAWSOCKET_RECV_SIZE` | `1048576` (1 MiB) | L2 ソケット受信バッファサイズ上限 | relay.h L27 |
| `BUFFER_SIZE` | `9200` | パケット処理バッファサイズ（ジャンボフレーム対応） | relay.h L29 |
| `OPTION_RELAY_MSG` | `9` | DHCPv6 Option 9 (Relay Message) | relay.h L33 |
| `OPTION_INTERFACE_ID` | `18` | DHCPv6 Option 18 (Interface-ID、RFC 3315) | relay.h L34 |
| `OPTION_CLIENT_LINKLAYER_ADDR` | `79` | DHCPv6 Option 79 (Client Link-Layer Address、RFC 6939) | relay.h L35 |

> Evidence: `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.h:22-37` (SHA: 7316417034fee6a6c6002490362c9bc75eeafde1)

<!-- /constants -->

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
