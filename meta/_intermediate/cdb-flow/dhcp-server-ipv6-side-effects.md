# DHCP_SERVER_IPV6 — Phase F 副次 DB 書込スキャンノート

対象テーブル: `DHCP_SERVER_IPV6`（未実装）/ 実装済み関連: `DHCP_RELAY`
Consumer: `dhcp6relay` (`sonic-net/sonic-dhcp-relay dhcp6relay/`)
スキャン範囲: `dhcp6relay/src/relay.cpp`, `dhcp6relay/src/config_interface.cpp`

---

## 調査方針

`DHCP_SERVER_IPV6` テーブルは 2026-05-14 時点で未実装のため、
DHCPv6 リレー機能を担う `dhcp6relay` プロセスの副次 DB 書込を調査した。
将来の `DHCP_SERVER_IPV6` 実装時の参考情報として記録する。

---

## 検出した副次 DB 書込

### 1. STATE_DB — DHCPv6_COUNTER_TABLE

#### 1-1. テーブル名定義

```cpp
// relay.cpp:18
static std::string counter_table = "DHCPv6_COUNTER_TABLE|";
```

キー形式: `DHCPv6_COUNTER_TABLE|<vlan_ifname>`

#### 1-2. カウンタフィールド一覧（counterMap）

```cpp
// relay.cpp:52-68
std::map<int, std::string> counterMap = {
    {DHCPv6_MESSAGE_TYPE_UNKNOWN,             "Unknown"},
    {DHCPv6_MESSAGE_TYPE_SOLICIT,             "Solicit"},
    {DHCPv6_MESSAGE_TYPE_ADVERTISE,           "Advertise"},
    {DHCPv6_MESSAGE_TYPE_REQUEST,             "Request"},
    {DHCPv6_MESSAGE_TYPE_CONFIRM,             "Confirm"},
    {DHCPv6_MESSAGE_TYPE_RENEW,               "Renew"},
    {DHCPv6_MESSAGE_TYPE_REBIND,              "Rebind"},
    {DHCPv6_MESSAGE_TYPE_REPLY,               "Reply"},
    {DHCPv6_MESSAGE_TYPE_RELEASE,             "Release"},
    {DHCPv6_MESSAGE_TYPE_DECLINE,             "Decline"},
    {DHCPv6_MESSAGE_TYPE_RECONFIGURE,         "Reconfigure"},
    {DHCPv6_MESSAGE_TYPE_INFORMATION_REQUEST, "Information-Request"},
    {DHCPv6_MESSAGE_TYPE_RELAY_FORW,          "Relay-Forward"},
    {DHCPv6_MESSAGE_TYPE_RELAY_REPL,          "Relay-Reply"},
    {DHCPv6_MESSAGE_TYPE_MALFORMED,           "Malformed"}
};
```

#### 1-3. 初期化フロー（initialize_counter / clear_counter）

- `lla_check_callback()` (relay.cpp:1361) が LLA 確認後に `initialize_counter()` を呼び出す
- `initialize_counter()` (relay.cpp:273-279):
  1. `clear_counter(state_db)` — `DHCPv6_COUNTER_TABLE|*` パターンで既存エントリを全削除
  2. `state_db->hset(table_name, intr.second, toString(0))` — counterMap の全フィールドを "0" で初期化
- `clear_counter()` (relay.cpp:1342-1348): `state_db->del(itr)` で全エントリ削除

#### 1-4. カウンタ増分フロー（increase_counter）

- `increase_counter()` (relay.cpp:292-305):
  - `state_db->hget(table_name, type)` で現在値を取得
  - nullptr なら `hset(..., "1")`, 非 nullptr なら `hset(..., count + 1)`
- 呼び出し箇所:
  - `relay_client()` (relay.cpp:683,687) — クライアントパケット受信時（Malformed または msg_type に応じたフィールド）
  - `relay_relay_forw()` (relay.cpp:727) — サーバへの Relay-Forward 転送時
  - `relay_relay_reply()` (relay.cpp:809,816,841) — サーバ応答受信時（Malformed, Unknown, msg_type）
  - ループバック受信処理 (relay.cpp:1098) — ループバックソケットからの Relay-Reply 受信時
  - GUA ソケット受信処理 (relay.cpp:1142) — GUA ソケットからのサーバパケット受信時

---

## 設定ファイル書込

`dhcp6relay` は設定ファイルへの書込みを行わない。
CONFIG_DB は読み取り専用、STATE_DB の DHCPv6_COUNTER_TABLE のみへの書込みが確認された。

---

## 副次 DB 書込サマリ

| DB | テーブル | キー形式 | フィールド | タイミング |
|----|----------|----------|------------|------------|
| STATE_DB | `DHCPv6_COUNTER_TABLE` | `<vlan_ifname>` | `Unknown`, `Solicit`, `Advertise`, `Request`, `Confirm`, `Renew`, `Rebind`, `Reply`, `Release`, `Decline`, `Reconfigure`, `Information-Request`, `Relay-Forward`, `Relay-Reply`, `Malformed` | LLA 確認後に初期化 ("0")、各メッセージ受信時にインクリメント |

設定ファイル書込: **なし**

---

## Evidence

- `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.cpp:18` — counter_table 定義
- `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.cpp:52-68` — counterMap 定義
- `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.cpp:273-279` — initialize_counter()
- `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.cpp:292-305` — increase_counter()
- `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.cpp:1342-1348` — clear_counter()
- `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.cpp:1401` — lla_check_callback での initialize_counter 呼び出し
