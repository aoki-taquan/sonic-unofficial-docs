# SmartSwitch MID_PLANE_BRIDGE / DHCP_SERVER_IPV4_PORT — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/smart-switch.md`
解析日: 2026-05-17
根拠ソース:
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang` (sha `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-smart-switch.yang` (sha `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`)
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py`
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py`
- `sonic-buildimage/src/sonic-config-engine/config_samples.py`

---

## 目的

`MID_PLANE_BRIDGE` および `DHCP_SERVER_IPV4_PORT` が CONFIG_DB に書かれたとき、
`dhcpservd` / `dhcprelayd` が**暗黙的に**参照する他テーブルのキー / フィールドを網羅する。
YANG の明示的 leafref に加え、コード側の implicit 依存も列挙する。

---

## 1. DEVICE_METADATA テーブル (SmartSwitch 経路分岐の前提)

### 参照箇所

`dhcp_cfggen.py:65-67` — `generate()` の冒頭:

```python
device_metadata = self.db_connector.get_config_db_table("DEVICE_METADATA")
smart_switch = is_smart_switch(device_metadata)
# is_smart_switch(): device_metadata.get("localhost",{}).get("subtype","") == "SmartSwitch"
```

`dhcprelayd.py:64-65` — `start()` の冒頭:

```python
device_metadata = self.db_connector.get_config_db_table(DEVICE_METADATA)
self.smart_switch = is_smart_switch(device_metadata)
```

### 依存内容

| 参照元の挙動 | 参照先テーブル | 参照先フィールド | 参照タイミング |
|---|---|---|---|
| SmartSwitch 経路の有効化 | `DEVICE_METADATA` | `localhost.subtype` (`"SmartSwitch"`) | 起動時 `generate()` / `start()` |

### 特記事項

- `subtype != "SmartSwitch"` の場合、`MID_PLANE_BRIDGE` / `DHCP_SERVER_IPV4_PORT` / `DPUS` が
  CONFIG_DB に存在しても SmartSwitch 向け DHCP 設定は**完全スキップ**される。
- YANG leafref ではなくコード側の implicit 参照。

---

## 2. DPUS テーブル (midplane_interface 参照)

### YANG leafref (明示)

`sonic-dhcp-server-ipv4.yang:231-233` — `DHCP_SERVER_IPV4_PORT.port` フィールド:

```yang
type leafref {
    path "/smartswitch:sonic-smart-switch/smartswitch:DPUS/smartswitch:DPUS_LIST/smartswitch:midplane_interface";
}
```

### コード参照

`dhcp_cfggen.py:74,119` — `_parse_dpu()`:

```python
dpus_table = self.db_connector.get_config_db_table(DPUS)
dpus = set([dpu_value["midplane_interface"] for dpu_value in dpus_table.values()
           if "midplane_interface" in dpu_value])
```

### 依存内容

| 参照元フィールド | 参照先テーブル | 参照先フィールド | 参照タイミング |
|---|---|---|---|
| `DHCP_SERVER_IPV4_PORT.port` (`dpu0` 等) | `DPUS` | `midplane_interface` (YANG leafref) | YANG バリデーション時・`_parse_dpu()` 実行時 |

### 特記事項

- `DPUS.<dpu_name>.midplane_interface` が存在しない状態で `DHCP_SERVER_IPV4_PORT` を書くと
  YANG leafref 制約違反で reject される。
- `sonic-smart-switch.yang:101` の `must "(current() = current()/../dpu_name)"` により
  `midplane_interface` は常に `dpu_name` と同値でなければならない。

---

## 3. DHCP_SERVER_IPV4 テーブル (name の leafref 源)

### YANG leafref (明示)

`sonic-dhcp-server-ipv4.yang:61-63` — `DHCP_SERVER_IPV4.name` フィールド (SmartSwitch 分岐):

```yang
type leafref {
    path "/smartswitch:sonic-smart-switch/smartswitch:MID_PLANE_BRIDGE/smartswitch:GLOBAL/smartswitch:bridge";
}
```

`sonic-dhcp-server-ipv4.yang:217-219` — `DHCP_SERVER_IPV4_PORT.name` フィールド:

```yang
type leafref {
    path "...DHCP_SERVER_IPV4/DHCP_SERVER_IPV4_LIST/name";
}
```

### 依存内容

| 参照元フィールド | 参照先テーブル | 参照先フィールド | 参照タイミング |
|---|---|---|---|
| `DHCP_SERVER_IPV4.name` (SmartSwitch 用) | `MID_PLANE_BRIDGE\|GLOBAL` | `bridge` (`"bridge-midplane"`) | YANG バリデーション時 |
| `DHCP_SERVER_IPV4_PORT.name` | `DHCP_SERVER_IPV4` | `name` (キー) | YANG バリデーション時 |

### コード参照 (dhcprelayd)

`dhcprelayd.py:82-103` — `refresh_dhcrelay()`:

```python
dhcp_server_ipv4_table = self.db_connector.get_config_db_table(DHCP_SERVER_IPV4)
mid_plane_bridge_name = mid_plane_table.get("GLOBAL", {}).get("bridge", None)
for dhcp_interface, config in dhcp_server_ipv4_table.items():
    if config["state"] == "enabled":
        ...
    elif dhcp_interface == mid_plane_bridge_name and self.smart_switch:
        checkers_to_be_enabled |= set([MID_PLANE_CHECKER])
```

- `dhcprelayd` は `DHCP_SERVER_IPV4.state == "enabled"` を確認して midplane ブリッジ向け
  relay を起動する。`DHCP_SERVER_IPV4|bridge-midplane` が不在の場合 `MID_PLANE_CHECKER` は
  有効化されない。

### 特記事項

- `DHCP_SERVER_IPV4_PORT` は `DHCP_SERVER_IPV4` が先に存在することを YANG leafref で強制する。
- SmartSwitch では `DHCP_SERVER_IPV4.name = "bridge-midplane"` が
  `MID_PLANE_BRIDGE|GLOBAL.bridge` への leafref となり、ブリッジが先行して存在する必要がある。

---

## 4. DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS テーブル (オプション参照)

### YANG leafref (明示)

`sonic-dhcp-server-ipv4.yang:96-97` — `DHCP_SERVER_IPV4.customized_options`:

```yang
type leafref {
    path "...DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS/DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS_LIST/name";
}
```

### 依存内容

| 参照元フィールド | 参照先テーブル | 参照先フィールド | 参照タイミング |
|---|---|---|---|
| `DHCP_SERVER_IPV4.customized_options` | `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS` | `name` (キー) | YANG バリデーション時 |

### 特記事項

- SmartSwitch 構成では通常 `customized_options` は設定しないため、このリファレンスは
  オプション設定時のみ適用される。

---

## cross-refs ブロック (最終形)

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`MID_PLANE_BRIDGE` および `DHCP_SERVER_IPV4_PORT` は CONFIG_DB の複数テーブルを YANG leafref
またはコード側の implicit 参照で依存する。

| 参照元テーブル | 参照元フィールド | 参照先テーブル | 参照先フィールド | 参照種別 | 参照箇所 |
|---|---|---|---|---|---|
| `DHCP_SERVER_IPV4` | `name` (SmartSwitch 用値 `"bridge-midplane"`) | `MID_PLANE_BRIDGE\|GLOBAL` | `bridge` | YANG leafref | `sonic-dhcp-server-ipv4.yang:61-63` |
| `DHCP_SERVER_IPV4_PORT` | `name` | `DHCP_SERVER_IPV4` | `name` (キー) | YANG leafref | `sonic-dhcp-server-ipv4.yang:217-219` |
| `DHCP_SERVER_IPV4_PORT` | `port` (`dpu0` 等) | `DPUS` | `midplane_interface` | YANG leafref | `sonic-dhcp-server-ipv4.yang:231-233` |
| `dhcpservd` (コード) | — | `DEVICE_METADATA` | `localhost.subtype` | 暗黙参照 | `dhcp_cfggen.py:65-67` |
| `dhcpservd` (コード) | — | `DPUS` | `midplane_interface` | 暗黙参照 | `dhcp_cfggen.py:74,119` |
| `dhcprelayd` (コード) | — | `DHCP_SERVER_IPV4` | `state` | 暗黙参照 | `dhcprelayd.py:82-103` |

### 解決タイミング

- YANG leafref は CONFIG_DB への書き込み時に `sonic-cfggen` / CLI の YANG バリデーションで確認される。
  参照先が存在しない場合は書き込みが reject される。
- `dhcpservd` の暗黙参照は `generate()` 呼び出し時 (起動時 + テーブル変更イベント時) に評価される。
  `DEVICE_METADATA.subtype` が `"SmartSwitch"` でない場合、`MID_PLANE_BRIDGE` / `DPUS` /
  `DHCP_SERVER_IPV4_PORT` への参照コードは実行されない。

### 必須先行順序

```
DEVICE_METADATA|localhost.subtype = "SmartSwitch"   ← SmartSwitch 経路を有効化
DPUS|<dpu_name>                                      ← DHCP_SERVER_IPV4_PORT.port の leafref 源
MID_PLANE_BRIDGE|GLOBAL                              ← DHCP_SERVER_IPV4.name の leafref 源
DHCP_SERVER_IPV4|bridge-midplane                    ← DHCP_SERVER_IPV4_PORT.name の leafref 源
DHCP_SERVER_IPV4_PORT|bridge-midplane|<dpu>         ← 全依存が揃ってから書き込む
```
<!-- /cross-refs -->
```
