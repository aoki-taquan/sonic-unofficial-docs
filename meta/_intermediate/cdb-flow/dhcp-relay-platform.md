# DHCP_RELAY — プラットフォーム差調査 (Task F Phase H)

対象ソース:
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py`
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/common/utils.py`
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/common/dhcp_db_monitor.py`
- `sonic-buildimage/dockers/docker-dhcp-relay/dhcpv4-relay.agents.j2`
- `sonic-buildimage/dockers/docker-dhcp-relay/dhcpv6-relay.agents.j2`
- `sonic-buildimage/dockers/docker-dhcp-relay/dhcpv4-sonic-relay.agents.j2`
- `sonic-buildimage/dockers/docker-dhcp-relay/docker-dhcp-relay.supervisord.conf.j2`

## 結論

**プラットフォーム差あり（3 軸）**:

1. **SmartSwitch DPU — mid-plane bridge 対応** — `DEVICE_METADATA.subtype == "SmartSwitch"` の場合、`DHCP_SERVER_IPV4` の対象インタフェースとして VLAN だけでなく `MID_PLANE_BRIDGE` も監視対象となり、DPU 向け IPv4 DHCP relay が有効化される
2. **DualToR — Interface-ID オプションデフォルト差** — `DEVICE_METADATA.subtype == "DualToR"` の場合、`dhcp6relay` の `-u Loopback0` オプションが有効になり `interface_id` デフォルトが `false` → `true` に変化する
3. **IPv4 vs IPv6 relay の実装差** — IPv6 relay は `DHCP_RELAY` テーブルを参照し `dhcp6relay` で処理、IPv4 relay は `VLAN.dhcp_servers` + `dhcrelay` または `DEVICE_METADATA.has_sonic_dhcpv4_relay` フラグで分岐する新旧 2 経路が存在する

## 1. SmartSwitch DPU — mid-plane bridge 対応

### 検出方法

`utils.py:153-161`:
```python
def is_smart_switch(device_metadata):
    return device_metadata.get("localhost", {}).get("subtype", "") == "SmartSwitch"
```

`dhcprelayd.py:64-65`:
```python
device_metadata = self.db_connector.get_config_db_table(DEVICE_METADATA)
self.smart_switch = is_smart_switch(device_metadata)
```

### 動作差

| 項目 | 通常スイッチ | SmartSwitch (DPU) |
|------|------------|-------------------|
| リレー対象インタフェース | `VLAN` テーブルのインタフェースのみ | VLAN + `MID_PLANE_BRIDGE.GLOBAL.bridge` も対象 |
| イベント監視テーブル | `VlanTableEventChecker` / `VlanIntfTableEventChecker` | 上記に加え `MidPlaneTableEventChecker` を有効化 |
| dhcp_server feature 無効化時の checker 解除 | VLAN 系 checker のみ解除 | MID_PLANE_CHECKER も解除対象に追加 |
| DPU の DHCP 割当先 | N/A | `DHCP_SERVER_IPV4_PORT` で `bridge-midplane|dpu0` 等を指定し個別 IP を割当 |

`dhcprelayd.py:97-103`:
```python
if dhcp_interface not in vlan_table and dhcp_interface != mid_plane_bridge_name:
    dhcp_interfaces.discard(dhcp_interface)
    continue
...
elif dhcp_interface == mid_plane_bridge_name and self.smart_switch:
    checkers_to_be_enabled |= set([MID_PLANE_CHECKER])
```

SmartSwitch では `bridge-midplane` インタフェース経由で DPU に DHCP アドレスを配布する。`DPUS` テーブルで各 DPU の `midplane_interface` を定義し、`DHCP_SERVER_IPV4_PORT|bridge-midplane|dpu0` 形式で IP を割当てる。

### DHCP_RELAY テーブルへの影響

SmartSwitch 環境では `DHCP_RELAY` テーブル（DHCPv6 リレー設定）は引き続き VLAN に基づいて動作する。mid-plane bridge の DHCP サービスは `DHCP_SERVER_IPV4` / `MID_PLANE_BRIDGE` テーブルで管理され、`DHCP_RELAY` テーブルとは独立した経路である。

## 2. DualToR — `interface_id` デフォルト差

### 検出方法

`dhcpv6-relay.agents.j2:16`:
```jinja
{% if 'subtype' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['subtype'] == 'DualToR' %} -u Loopback0 {% endif %}
```

起動時に `DEVICE_METADATA.localhost.subtype == "DualToR"` を評価し、真の場合 `dhcp6relay` に `-u Loopback0` オプションを付与する。

### 動作差

| 環境 | `dhcp6relay` 起動オプション | `interface_id` ハードコードデフォルト |
|------|--------------------------|--------------------------------------|
| 通常スイッチ | `-u` オプションなし | `false`（Interface-ID なし） |
| DualToR | `-u Loopback0` 付き | `true`（Interface-ID オプション挿入） |

`config_interface.cpp:117-122`:
```cpp
bool option_79_default = true;
bool interface_id_default = false;
if (dual_tor_sock) {
    interface_id_default = true;
}
```

DualToR 環境では `dual_tor_sock` が生成され、`interface_id` のデフォルトが自動的に `true` になる。この分岐は YANG `interface_id` フィールドへの YANG-実装 discrepancy と組み合わさり、DualToR では設定なしでも Interface-ID が付与される。

また DualToR では `HW_MUX_CABLE_TABLE|<port>` の `state == "standby"` ポートからのパケットをリレーしない制御も追加される (`relay.cpp:915`)。

## 3. IPv4 vs IPv6 relay の実装差

### アーキテクチャの違い

| 比較項目 | DHCPv4 relay | DHCPv6 relay |
|---------|-------------|-------------|
| 設定テーブル | `VLAN.dhcp_servers`（旧方式）または `DHCP_SERVER_IPV4`（新方式） | `DHCP_RELAY` テーブル専用 |
| プロセス名 | `dhcrelay`（ISC DHCP）または `dhcp4relay`（SONiC 独自） | `dhcp6relay`（SONiC 独自） |
| 切替フラグ | `DEVICE_METADATA.localhost.has_sonic_dhcpv4_relay == "True"` | 切替なし。dhcp6relay のみ |
| DualToR オプション | `-U Loopback0 -dt`（大文字 U、`-dt` フラグ付き） | `-u Loopback0`（小文字 u） |
| deployment_id 分岐 | `deployment_id == "8"` 時に `-si` オプション追加 | deployment_id 依存なし |
| アドレス優先度 | 上流 IF の IPv4 アドレス持ちインタフェースを `-iu` で列挙 | 全 DHCP_RELAY エントリを一括処理 |
| ランタイム変更 | dhcprelayd が refresh_dhcrelay() で kill + 再起動 | コンテナ再起動が必要（dead consumer） |

### `has_sonic_dhcpv4_relay` フラグ

`docker-dhcp-relay.supervisord.conf.j2`:
```jinja
{% if 'has_sonic_dhcpv4_relay' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['has_sonic_dhcpv4_relay'] == 'True' %}
{% include 'dhcpv4-sonic-relay.agents.j2' %}
{% else %}
{#  従来の ISC dhcrelay をVLAN ごとに起動 #}
{% include 'dhcpv4-relay.agents.j2' %}
{% endif %}
```

`has_sonic_dhcpv4_relay = "True"` の場合、SONiC 独自の `dhcp4relay` が `dhcprelayd.py` 経由で管理され、DHCP_SERVER_IPV4 テーブルを参照して動的に relay 設定を更新できる。`"False"` の場合は従来の ISC `dhcrelay` を VLAN ごとに supervisord から直接起動し、`DHCP_RELAY` テーブルは DHCPv6 専用となる。

`dhcprelayd.py:112`:
```python
if feature_table.get("localhost", {}).get("has_sonic_dhcpv4_relay", "False") == "False":
    self._start_dhcrelay_process(dhcp_interfaces, dhcp_server_ip, force_kill)
```

`has_sonic_dhcpv4_relay == "True"` 環境では `dhcprelayd` が dhcrelay プロセスを直接起動せず、`dhcp4relay` デーモンに委任する。

## まとめ表

| 差分軸 | 影響 | 検出方法 | ソース |
|--------|------|----------|--------|
| SmartSwitch DPU | mid-plane bridge が DHCP 対象に追加、MidPlaneTableEventChecker 有効化 | `DEVICE_METADATA.subtype == "SmartSwitch"` | `dhcprelayd.py:65,102`, `utils.py:161` |
| DualToR | `interface_id` デフォルト `true`、standby ポートのリレー無効、DHCPv4 `-dt` フラグ | `DEVICE_METADATA.subtype == "DualToR"` | `dhcpv6-relay.agents.j2:16`, `config_interface.cpp:121` |
| `has_sonic_dhcpv4_relay` フラグ | DHCPv4 relay が ISC dhcrelay か SONiC dhcp4relay か切替 | `DEVICE_METADATA.localhost.has_sonic_dhcpv4_relay` | `supervisord.conf.j2`, `dhcprelayd.py:112` |
| IPv4 vs IPv6 relay | relay プロセス・テーブル・ランタイム変更可否が異なる | プロトコル種別 | `dhcpv4-relay.agents.j2`, `dhcpv6-relay.agents.j2` |

## 証跡

- `dhcprelayd.py:64-65,97-103,112,169-170` (SmartSwitch 判定、mid-plane bridge 分岐、has_sonic_dhcpv4_relay) 読了
- `utils.py:153-161` (is_smart_switch) 読了
- `dhcp_db_monitor.py:349-386` (MidPlaneTableEventChecker, DpusTableEventChecker) 読了
- `dhcpv4-relay.agents.j2:14-18` (DualToR `-U Loopback0 -dt`, deployment_id `-si`) 読了
- `dhcpv6-relay.agents.j2:9-12` (DualToR `-u Loopback0`) 読了
- `docker-dhcp-relay.supervisord.conf.j2:29-46` (has_sonic_dhcpv4_relay 分岐) 読了
- `config_interface.cpp:117-122` (interface_id_default DualToR 変化) — 既存調査結果参照
