# DHCP_SERVER_IPV6 — Phase C 暗黙参照調査 (cross-table refs)

調査日: 2026-05-16  
対象ページ: `docs/reference/config-db/dhcp-server-ipv6.md`  
調査ソース:
- `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp`
- `sonic-dhcp-relay/dhcp6relay/src/relay.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dhcpv6-relay.yang`

---

## 調査背景

`DHCP_SERVER_IPV6` テーブルは 2026-05-16 時点で未実装。ただし、SONiC の DHCPv6 実装は `DHCP_RELAY` テーブル経由で `dhcp6relay` デーモン（sonic-dhcp-relay リポジトリ）によって提供されており、DHCPv6 エコシステム全体の暗黙参照を把握するため、dhcp6relay ソースを調査する。これにより、将来 DHCP_SERVER_IPV6 が実装された場合に準拠すべき CONFIG_DB テーブル依存関係が明確になる。

---

## 検出した暗黙参照

### 1. CONFIG_DB: VLAN_INTERFACE (必須・実行時参照)

**参照元**: `dhcp6relay/src/config_interface.cpp:130-143`

```cpp
const std::string match_pattern = "VLAN_INTERFACE|" + vlan + "|*";
auto keys = config_db->keys(match_pattern);
if (keys.empty()) {
    syslog(LOG_WARNING, "%s doesn't exist in VLAN_INTERFACE table, skip it", vlan.c_str());
    continue;
}
```

`DHCP_RELAY|<vlan>` エントリ処理時、daemon は `VLAN_INTERFACE|<vlan>|*` パターンで CONFIG_DB をスキャンし、対象 VLAN が IPv6 アドレスを持つかを確認する。IPv6 アドレスが設定されていない VLAN は `LOG_WARNING` を出してスキップされる。

- **leafref 定義なし** — `sonic-dhcpv6-relay.yang` には `VLAN_INTERFACE` への leafref が存在しない
- **暗黙的必須条件**: `VLAN_INTERFACE|<vlan>|<ipv6-prefix>` エントリが存在しないと DHCPv6 リレー（および将来のサーバ）は当該 VLAN で機能しない

### 2. CONFIG_DB: VLAN_MEMBER (実行時参照・ポートマッピング)

**参照元**: `dhcp6relay/src/relay.cpp:856-862`

```cpp
auto match_pattern = std::string("VLAN_MEMBER|") + vlan + std::string("|*");
auto keys = cfgdb->keys(match_pattern);
for (auto &itr : keys) {
    auto found = itr.find_last_of('|');
    auto interface = itr.substr(found + 1);
    vlan_map[interface] = vlan;
}
```

`update_vlan_mapping()` が `VLAN_MEMBER|<vlan>|*` から vlan member interface 一覧を取得し、パケット受信時の interface→vlan 逆引きマップを構築する。VLAN_MEMBER エントリが存在しないと client パケットを受け付けられない。

- **leafref 定義なし** — YANG モデルに記載なし
- `relay.cpp:17`: `static std::string vlan_member = "VLAN_MEMBER|";` として定数化

---

## SAI 参照

なし。`dhcp6relay` は Linux カーネルの L4 UDP relay であり SAI/ASIC に一切触れない。将来的な DHCP_SERVER_IPV6 実装（kea-dhcp6 管理デーモン相当）も同様に SAI 非依存となる見込み。

---

## 暗黙参照まとめ表

| 参照先 | DB | 参照方向 | 条件 | leafref | 証拠 |
|---|---|---|---|---|---|
| `VLAN_INTERFACE\|<vlan>\|*` | CONFIG_DB | 読み取り (IPv6アドレス必須チェック) | 常時 | なし | config_interface.cpp:130 |
| `VLAN_MEMBER\|<vlan>\|*` | CONFIG_DB | 読み取り (ポートマップ構築) | 常時 | なし | relay.cpp:856 |

---

## 備考

- `DHCP_SERVER_IPV6` は未実装のため、本調査は DHCPv6 エコシステム（`DHCP_RELAY` / `dhcp6relay`）の暗黙参照を代理調査したもの
- 将来 kea-dhcp6 管理デーモンが実装される場合、`VLAN_INTERFACE` / `VLAN_MEMBER` への依存は `DHCP_SERVER_IPV4` の `VLAN` / `VLAN_INTERFACE` 依存（`dhcp-server-ipv4-cross-refs.md` 参照）と同等以上になる見込み
- `DHCP_RELAY` テーブルとの詳細な暗黙参照（DEVICE_METADATA, HW_MUX_CABLE_TABLE, DHCPv6_COUNTER_TABLE）は `dhcp-relay-cross-refs.md` を参照
