# DHCP_RELAY — Phase C 暗黙参照調査 (cross-table refs)

調査日: 2026-05-14  
対象ページ: `docs/reference/config-db/dhcp-relay.md`  
調査ソース:
- `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp`
- `sonic-dhcp-relay/dhcp6relay/src/relay.cpp`
- `sonic-dhcp-relay/dhcp6relay/src/main.cpp`
- `sonic-buildimage/dockers/docker-dhcp-relay/dhcpv6-relay.agents.j2`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` (L1060-1078, L2645)

---

## 検出した暗黙参照

### 1. CONFIG_DB: VLAN_INTERFACE (必須・実行時参照)

**参照元**: `config_interface.cpp:130-143`

```cpp
const std::string match_pattern = "VLAN_INTERFACE|" + vlan + "|*";
auto keys = config_db->keys(match_pattern);
```

`DHCP_RELAY|<vlan>` エントリを処理するとき、daemon は `VLAN_INTERFACE|<vlan>|*` パターンで CONFIG_DB をスキャンし、対象 VLAN が IPv6 アドレスを持つかどうかを確認する。IPv6 アドレスが見つからない場合は `LOG_WARNING` を出してスキップ。

- **leafref 定義なし** — YANG モデルには `VLAN_INTERFACE` への参照が存在しない
- **暗黙的必須条件**: `VLAN_INTERFACE|<vlan>|<ipv6-prefix>` エントリが存在しないと `DHCP_RELAY` の当該行は機能しない

### 2. CONFIG_DB: VLAN_MEMBER (実行時参照・ポートマッピング)

**参照元**: `relay.cpp:856-863`

```cpp
auto match_pattern = std::string("VLAN_MEMBER|") + vlan + std::string("|*");
auto keys = cfgdb->keys(match_pattern);
for (auto &itr : keys) {
    auto found = itr.find_last_of('|');
    auto interface = itr.substr(found + 1);
    vlan_map[interface] = vlan;
}
```

`update_vlan_mapping()` が `VLAN_MEMBER|<vlan>|*` から vlan member interface 一覧を取得し、パケット受信時の interface→vlan 逆引きマップを構築する。メンバーが存在しないと client パケットを受け付けられない。

### 3. CONFIG_DB: DEVICE_METADATA (間接・起動時参照)

**参照元**: `dhcpv6-relay.agents.j2:16`

```jinja2
{% if 'subtype' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['subtype'] == 'DualToR' %} -u Loopback0 {% endif %}
```

supervisord の j2 テンプレートが `DEVICE_METADATA.localhost.subtype` を読み、`DualToR` の場合に `-u Loopback0` オプションを `dhcp6relay` コマンドラインに追加する。これにより `dual_tor_sock = true` が設定され、`interface_id` デフォルト値が `false` → `true` に変わる（`config_interface.cpp:120-122`）。

- `DHCP_RELAY` テーブル自体への leafref なし
- `DEVICE_METADATA.localhost.subtype` の値が `interface_id` の実効デフォルト値を決定する

### 4. STATE_DB: HW_MUX_CABLE_TABLE (DualToR 専用・実行時参照)

**参照元**: `relay.cpp:1249-1251`, `relay.cpp:915`

```cpp
std::shared_ptr<swss::Table> mStateDbMuxTablePtr = std::make_shared<swss::Table>(
    state_db.get(), "HW_MUX_CABLE_TABLE"
);
// client_callback内:
config.mux_table->hget(intf, "state", state);
if (state != "standby") { ... }
```

DualToR 環境では、クライアントパケット受信時に `STATE_DB::HW_MUX_CABLE_TABLE|<port>` の `state` フィールドを参照する。`state == "standby"` のポートからのパケットはリレーしない（active/standby 制御）。

- CONFIG_DB の `DHCP_RELAY` テーブルとの leafref なし — 完全に暗黙の cross-DB 参照
- `MUX_CABLE` (CONFIG_DB) が HW_MUX_CABLE_TABLE (STATE_DB) に対応する

### 5. STATE_DB: DHCPv6_COUNTER_TABLE (書き込み先・副作用)

**参照元**: `relay.cpp:18`, `relay.cpp:273-278`

```cpp
static std::string counter_table = "DHCPv6_COUNTER_TABLE|";
// initialize_counter: state_db->hset(table_name, intr.second, toString(0));
// increase_counter: state_db->hset(table_name, type, toString(count + 1));
```

`dhcp6relay` は各 VLAN ごとに `STATE_DB::DHCPv6_COUNTER_TABLE|<vlan>` を書き込む。`DHCP_RELAY` に登録されている全 VLAN のカウンタが初期化・更新される。`show dhcprelay counters` の参照先。

### 6. minigraph.py 経路 (書き込み入り口の追加情報)

**参照元**: `minigraph.py:1071-1078`

minigraph XML の `<Dhcpv6Relays>` 要素 (`;` 区切り) が `dhcpv6_servers` リストに変換されて `DHCP_RELAY` に書き込まれる。`rfc6939_support` / `interface_id` は書き込まれない。minigraph 経路は `VLAN` テーブルとの整合性を前提とする (vlanid → `Vlan<id>` のキー生成)。

---

## SAI 参照

なし。`dhcp6relay` は Linux カーネルの L4 UDP relay であり SAI/ASIC に一切触れない。

---

## 暗黙参照まとめ表

| 参照先 | DB | 参照方向 | 条件 | leafref | 証拠 |
|---|---|---|---|---|---|
| `VLAN_INTERFACE\|<vlan>\|*` | CONFIG_DB | 読み取り (必須チェック) | 常時 | なし | config_interface.cpp:130 |
| `VLAN_MEMBER\|<vlan>\|*` | CONFIG_DB | 読み取り (ポートマップ) | 常時 | なし | relay.cpp:856 |
| `DEVICE_METADATA.localhost.subtype` | CONFIG_DB | 読み取り (j2テンプレ) | 起動時 | なし | dhcpv6-relay.agents.j2:16 |
| `HW_MUX_CABLE_TABLE\|<port>` | STATE_DB | 読み取り (mux state) | DualToR のみ | なし | relay.cpp:1250, 915 |
| `DHCPv6_COUNTER_TABLE\|<vlan>` | STATE_DB | 書き込み (カウンタ) | 常時 | なし | relay.cpp:18, 273-304 |
