# DHCP_RELAY — Phase A: コード由来の暗黙デフォルト調査

調査日: 2026-05-14  
対象ファイル:
- `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dhcpv6-relay.yang`
- `sonic-buildimage/dockers/docker-dhcp-relay/dhcpv6-relay.agents.j2`
- `sonic-buildimage/dockers/docker-dhcp-relay/cli/config/plugins/dhcp_relay.py`
- `sonic-buildimage/dockers/docker-dhcp-relay/cli-plugin-tests/mock_config.py`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`

---

## 1. フィールド列挙

DHCP_RELAY テーブルのフィールド（YANG定義ベース）:

| フィールド | YANG 型 | YANG default |
|---|---|---|
| `name` (key) | string | — |
| `dhcpv6_servers` | leaf-list of inet:ipv6-address (ordered-by user) | なし |
| `rfc6939_support` | string pattern "false\|true" | なし（YANG default 未定義） |
| `interface_id` | string pattern "false\|true" | なし（YANG default 未定義） |

---

## 2. コード由来の暗黙デフォルト一覧

### 2.1 `rfc6939_support` — ハードコード `true`（フォールバック）

**場所**: `config_interface.cpp:117`
```cpp
bool option_79_default = true;
```

**挙動**:
- フィールドが **未設定** の場合: `is_option_79 = true`（RFC 6939 Client Link-Layer Address Option 79 を付与）
- フィールドが `"false"` の場合のみ無効化（`config_interface.cpp:169`）
- フィールドが `"true"` の場合は変化なし（デフォルトのまま true）
- YANG には default 文がないが、**実装レベルのハードコードデフォルトは `true`**

**検出種類**: ハードコード固定値 / YANG-実装 discrepancy

---

### 2.2 `interface_id` — 環境依存デフォルト (DualToR 分岐)

**場所**: `config_interface.cpp:118-122`
```cpp
bool interface_id_default = false;

if (dual_tor_sock) {
    interface_id_default = true;
}
```

**挙動**:
- 非 DualToR 環境でフィールド **未設定**: `is_interface_id = false`（Interface-ID オプションなし）
- DualToR 環境（`dual_tor_sock` が存在）でフィールド **未設定**: `is_interface_id = true`（Interface-ID オプション有効）
- フィールドが `"true"` の場合のみ明示的に有効化（非 DualToR 環境でも override 可能）
- フィールドが `"false"` の場合は override 不可（デフォルトに依存、C++ 側で false への強制ロジックなし）

**検出種類**: プラットフォーム依存 / 経路依存乖離

---

### 2.3 YANG-実装 discrepancy（フィールドキー名の乖離）

**CRITICAL**: `rfc6939_support` / `interface_id` のキー名が YANG と実装で一致しない。

| 側面 | キー名 |
|---|---|
| YANG モデル (`sonic-dhcpv6-relay.yang`) | `rfc6939_support` / `interface_id` |
| YANG テスト (`tests_config/dhcpv6_relay.json`) | `rfc6939_support` / `interface_id` |
| sample_config_db.json | `rfc6939_support` / `interface_id` |
| **C++ 実装** (`config_interface.cpp:169,172`) | `dhcpv6_option\|rfc6939_support` / `dhcpv6_option\|interface_id` |
| **CLI テスト mock** (`mock_config.py`) | `dhcpv6_option\|rfc6939_support` |

**結論**:
- YANG 定義の `rfc6939_support` フィールドで `"false"` を設定しても、C++ daemon は `dhcpv6_option|rfc6939_support` を読む
- 結果として `rfc6939_support = "false"` は **silent drop** — daemon は読まず、デフォルト `true` のまま動作
- `interface_id = "true"` も同様に YANG 経由で設定しても daemon は読まない（非 DualToR 環境では有効化されない）
- CLI plugin (`dhcp_relay.py`) は `dhcpv6_servers` のみを DHCP_RELAY に書き込み、`rfc6939_support` / `interface_id` は書き込まない

**検出種類**: YANG-実装 discrepancy / silent drop+fallback

---

### 2.4 `dhcpv6_servers` — 空リスト時の silent skip

**場所**: `config_interface.cpp:176-179`
```cpp
if (intf.servers.empty()) {
    syslog(LOG_WARNING, "No servers found for VLAN %s, skipping configuration.", vlan.c_str());
    continue;
}
```

**挙動**:
- `dhcpv6_servers` が空 leaf-list（または未設定）の場合、その VLAN 設定は vlans マップに追加されない
- relay は無効（silent skip、エラーなし）

**検出種類**: silent drop+fallback

---

### 2.5 動的設定変更の dead consumer

**場所**: `config_interface.cpp:73-79`
```cpp
if (!dynamic) {
    handleRelayNotification(*ipHelpersTable, vlans, config_db);
} else {
    syslog(LOG_WARNING, "relay config changed, "
           "need restart container to take effect");
}
```

**挙動**:
- `dhcp6relay` 起動後に DHCP_RELAY が変更されても、dynamic=true パスに入り設定は適用されない
- ログに "need restart container" が出力されるのみ
- **コンテナ再起動が必要**

**検出種類**: dead consumer（動的変更未対応）/ 書込み順依存

---

### 2.6 minigraph 経由の書込み — `rfc6939_support`/`interface_id` 未設定

**場所**: `minigraph.py:1071-1078`
```python
dhcp_attributes['dhcpv6_servers'] = vdhcpserver_list
sonic_vlan_member_name = "Vlan%s" % (vlanid)
dhcp_relay_table[sonic_vlan_member_name] = dhcp_attributes
```

**挙動**:
- minigraph 経由で DHCP_RELAY を生成する際、`dhcpv6_servers` のみが書き込まれる
- `rfc6939_support` / `interface_id` は書き込まれない → daemon のハードコードデフォルト適用

**検出種類**: ビルド時デフォルト / silent drop（書込み入り口がフィールドを省略）

---

### 2.7 dhcpv6-relay.agents.j2 — DualToR 分岐フラグ

**場所**: `dhcpv6-relay.agents.j2:16`
```jinja2
{% if 'subtype' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['subtype'] == 'DualToR' %} -u Loopback0 {% endif %}
```

**挙動**:
- `DEVICE_METADATA.localhost.subtype == "DualToR"` の場合のみ `-u Loopback0` が dhcp6relay コマンドに付与
- この `-u` オプションが `dual_tor_sock` の生成を制御し、`interface_id` のデフォルトを決定する
- `interface_id` フィールドの実行時挙動は DEVICE_METADATA.subtype に **間接依存**

**検出種類**: プラットフォーム依存 / 前提条件依存

---

## 3. discrepancy サマリ

| フィールド | 検出種類 | 内容 |
|---|---|---|
| `rfc6939_support` | YANG-実装 discrepancy / silent drop | YANG は flat key、実装は `dhcpv6_option\|rfc6939_support` を読む。YANG経由設定は無効 |
| `rfc6939_support` | ハードコードデフォルト | 未設定時の実行時デフォルト = `true` (option 79 有効) |
| `interface_id` | YANG-実装 discrepancy / silent drop | 同上。YANG経由設定は無効 |
| `interface_id` | プラットフォーム依存 | DualToR: 未設定=true。非 DualToR: 未設定=false |
| `dhcpv6_servers` | silent drop | 空の場合、その VLAN は relay 無効（ログのみ） |
| (全フィールド) | dead consumer | 起動後の動的変更は無視、コンテナ再起動が必要 |
| `rfc6939_support`, `interface_id` | 書込み順依存 | minigraph/CLI は dhcpv6_servers のみ書込み、option系フィールドは書込まない |
