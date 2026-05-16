# Phase A: MID_PLANE_BRIDGE / DHCP_SERVER_IPV4_PORT SmartSwitch — 暗黙デフォルト調査

対象テーブル: `MID_PLANE_BRIDGE`, `DHCP_SERVER_IPV4_PORT`（SmartSwitch 専用）
YANG モジュール: `sonic-smart-switch.yang`, `sonic-dhcp-server-ipv4.yang`
消費コード:
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py`
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py`
- `sonic-buildimage/src/sonic-config-engine/config_samples.py`

---

## 1. MID_PLANE_BRIDGE|GLOBAL — フィールドごとのデフォルト・制約

### 1-1. `bridge` フィールド

YANG 定義 (`sonic-smart-switch.yang:63-69`):
```yang
leaf bridge {
    type string {
        pattern "bridge-midplane";
    }
    description "Name of the midplane bridge";
    must "(current()/../ip_prefix)";
}
```

- YANG の `type string { pattern "bridge-midplane"; }` により許容値は `"bridge-midplane"` **固定のみ**。
- `default` 文なし。エントリが存在するなら値は常に `"bridge-midplane"` でなければならない。
- `must` 制約: `bridge` が存在するなら `ip_prefix` も必須（YANG レベルで強制）。

実装 (`dhcp_cfggen.py:85`):
```python
mid_plane_name = mid_plane["bridge"]
```
`"bridge"` キーを読み、後続でブリッジ名として `dhcpd.conf` へ展開。値が `"bridge-midplane"` 以外になることはスキーマ制約上あり得ない。

サンプル生成コード (`config_samples.py:88`):
```python
bridge_name = 'bridge-midplane'
```
ハードコード文字列が仕様の出典。

### 1-2. `ip_prefix` フィールド

YANG 定義 (`sonic-smart-switch.yang:72-74`):
```yang
leaf ip_prefix {
    type stypes:sonic-ip4-prefix;
    description "IP prefix of the midplane bridge";
}
```

- `default` 文なし。YANG は値を規定しない。
- SmartSwitch サンプル生成コード (`config_samples.py:85-93`):
  ```python
  mpbr_prefix = '169.254.200'
  mpbr_address = '{}.254'.format(mpbr_prefix)
  # ...
  data['MID_PLANE_BRIDGE'] = {
      "GLOBAL": {
          "bridge": bridge_name,
          "ip_prefix": "169.254.200.254/24"
      }
  }
  ```
  事実上のデフォルトは `169.254.200.254/24`（リンクローカル帯 RFC 5735 準拠）。
- テスト・mock データ (`mock_config_db_smart_switch.json`) でも同値が使用される。

実装上の依存 (`dhcp_cfggen.py:87-88`):
```python
"network": ipaddress.ip_network(mid_plane["ip_prefix"], strict=False),
"ip": mid_plane["ip_prefix"]
```
`ip_prefix` は `ip_network()` で解析され、DHCP サーバのサブネット計算に使用される。

---

## 2. DHCP_SERVER_IPV4_PORT — フィールドごとのデフォルト・制約

### 2-1. キー構造

```
DHCP_SERVER_IPV4_PORT|<bridge>|<dpu_interface>
```

YANG定義 (`sonic-dhcp-server-ipv4.yang:209-256`):
```yang
list DHCP_SERVER_IPV4_PORT_LIST {
    key "name port";
    leaf name { /* leafref -> DHCP_SERVER_IPV4 */ }
    leaf port {
        type union {
            type leafref { path "/port:...PORT_LIST/port:name"; }
            type leafref { path "/lag:...PORTCHANNEL_LIST/lag:name"; }
            type leafref { path "/smartswitch:...DPUS_LIST/smartswitch:midplane_interface"; }
        }
    }
    ...
}
```

SmartSwitch コンテキストでは `port` は `DPUS_LIST.midplane_interface` (`dpu0`, `dpu1`, ...) を参照する。

### 2-2. `ips` フィールド (leaf-list)

YANG定義:
```yang
leaf-list ips {
    must "(not(boolean(../ranges)))";
    type inet:ipv4-address;
    ordered-by user;
}
```

- `default` 文なし。
- `ips` と `ranges` の **排他制約** (`must` 文で強制)。
- サンプル生成コード (`config_samples.py:103`):
  ```python
  dpu_id = int(midplane_interface.replace('dpu', ''))
  dhcp_server_ports['{}|{}'.format(bridge_name, midplane_interface)] = {
      'ips': ['{}.{}'.format(mpbr_prefix, dpu_id + 1)]
  }
  ```
  DPU ごとの IP は `169.254.200.<dpu_id + 1>` で計算される。
  - `dpu0` → `169.254.200.1`
  - `dpu1` → `169.254.200.2`
  - `dpu2` → `169.254.200.3`
  - `dpu3` → `169.254.200.4`

- これらは YANG デフォルト値ではなく、**SmartSwitch 設定生成コードによるハードコードルール**である。

### 2-3. `ranges` フィールド (leaf-list)

- YANG 上は `ips` の代替手段。SmartSwitch 自動生成では使用されない（`ips` 固定）。
- `must "(not(boolean(../ips)))"` で `ips` と共存不可。

---

## 3. DPUS — SmartSwitch 側のマッピングテーブル

YANG定義 (`sonic-smart-switch.yang:81-106`):
```yang
container DPUS {
    list DPUS_LIST {
        key "dpu_name";
        leaf dpu_name { type string { pattern "dpu[0-9]+"; } }
        leaf midplane_interface {
            type string { pattern "dpu[0-9]+"; }
            must "(current() = current()/../dpu_name)";
        }
    }
}
```

`midplane_interface` は常に `dpu_name` と等しい制約 (`must` 文で強制)。すなわち:
- `DPUS|dpu0.midplane_interface = "dpu0"` (固定)
- これが `DHCP_SERVER_IPV4_PORT` の `port` フィールドへの leafref の対象。

---

## 4. DHCP_SERVER_IPV4 — SmartSwitch 自動生成時のデフォルト

SmartSwitch サンプル生成コード (`config_samples.py:133-141`):
```python
data['DHCP_SERVER_IPV4'] = {
    bridge_name: {
        'gateway': mpbr_address,       # "169.254.200.254" (ハードコード)
        'lease_time': '3600',          # 1 時間 (ハードコード)
        'mode': 'PORT',                # PORT モード固定
        'netmask': '255.255.255.0',    # /24 固定
        "state": "enabled"             # 有効状態で投入
    }
}
```

YANG の `lease_time` は `mandatory true` だが YANG の `default` 文はなし。
実装デフォルトは `3600` 秒 (1 時間)。

---

## 5. ハンドラ分岐: smart_switch フラグ

`dhcp_cfggen.py:67, 76, 84`:
```python
smart_switch = is_smart_switch(device_metadata)
mid_plane, dpus = self._parse_dpu(dpus_table, mid_plane_table) if smart_switch else ({}, {})
if smart_switch and "bridge" in mid_plane and "ip_prefix" in mid_plane:
```

- `DEVICE_METADATA|localhost.subtype == "SmartSwitch"` が判定条件 (`is_smart_switch()`)。
- `MID_PLANE_BRIDGE` と `DHCP_SERVER_IPV4_PORT` の処理はこのフラグが True の場合のみ実行。
- 非 SmartSwitch では `mid_plane = {}`, `dpus = {}` として空扱い。

`dhcprelayd.py:85, 102`:
```python
mid_plane_bridge_name = mid_plane_table.get("GLOBAL", {}).get("bridge", None)
elif dhcp_interface == mid_plane_bridge_name and self.smart_switch:
    checkers_to_be_enabled |= set([MID_PLANE_CHECKER])
```

- `dhcprelayd` でも同様に `smart_switch` フラグで分岐し、`bridge-midplane` インターフェース向けの MID_PLANE_CHECKER が有効化される。

---

## 6. 暗黙デフォルト・乖離サマリー

| # | テーブル | フィールド | YANG default | 実装デフォルト/制約 | 種別 |
|---|---------|-----------|-------------|-------------------|------|
| 1 | MID_PLANE_BRIDGE\|GLOBAL | `bridge` | なし | `"bridge-midplane"` 固定 (YANG pattern 制約) | YANG 制約 |
| 2 | MID_PLANE_BRIDGE\|GLOBAL | `ip_prefix` | なし | `169.254.200.254/24` (config_samples.py ハードコード) | 実装デフォルト |
| 3 | DHCP_SERVER_IPV4_PORT | `ips` | なし | `169.254.200.<dpu_id+1>` (config_samples.py 計算式) | 実装生成ルール |
| 4 | DPUS | `midplane_interface` | なし | `== dpu_name` (YANG must 制約) | YANG 制約 |
| 5 | DHCP_SERVER_IPV4 | `lease_time` | なし | `3600` (config_samples.py ハードコード) | 実装デフォルト |
| 6 | DHCP_SERVER_IPV4 | `gateway` | なし | `169.254.200.254` (mpbr_address 計算値) | 実装生成ルール |

---

## 証跡 (evidence)

- `sonic-net/sonic-buildimage` `src/sonic-config-engine/config_samples.py:81-151` SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
- `sonic-net/sonic-buildimage` `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:60-121` SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
- `sonic-net/sonic-buildimage` `src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py:75-117` SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
- `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-smart-switch.yang` SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
- `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang` SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
- `sonic-net/sonic-buildimage` `src/sonic-dhcp-utilities/tests/test_data/mock_config_db_smart_switch.json` SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
- `sonic-net/sonic-buildimage` `src/sonic-config-engine/tests/sample_output/t1-smartswitch.json` SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
