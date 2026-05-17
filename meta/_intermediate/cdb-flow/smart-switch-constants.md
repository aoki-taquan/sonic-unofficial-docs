# smart-switch — Phase E: constants

slug: smart-switch
phase: E (constants)
date: 2026-05-17
sources:
  - src/sonic-yang-models/yang-models/sonic-smart-switch.yang:63-70,88-101,155-162
  - src/sonic-config-engine/config_samples.py:83-103,133-143
  - src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:17-31

## 調査結果

### MID_PLANE_BRIDGE — ハードコード定数

| 定数 / 値 | コード位置 | 意味 |
|---|---|---|
| `"bridge-midplane"` | `config_samples.py:88`; YANG `pattern` (`sonic-smart-switch.yang:65`) | ミッドプレーンブリッジ名。YANG pattern 制約により唯一有効な値 |
| `"169.254.200"` | `config_samples.py:85` (`mpbr_prefix`) | ミッドプレーンブリッジサブネットの第 1〜3 オクテット（link-local 帯域内） |
| `"169.254.200.254"` | `config_samples.py:86` (`mpbr_address`) | NPU 側ブリッジ IP（`mpbr_prefix + ".254"`）。`DHCP_SERVER_IPV4.bridge-midplane.gateway` に設定 |
| `"169.254.200.254/24"` | `config_samples.py:93` | `MID_PLANE_BRIDGE.GLOBAL.ip_prefix` の実装値 |

### DHCP_SERVER_IPV4_PORT — DPU IP 計算式

```python
# config_samples.py:102-103
dpu_id = int(midplane_interface.replace('dpu', ''))   # "dpu0" → 0
dhcp_ip = '{}.{}'.format(mpbr_prefix, dpu_id + 1)    # "169.254.200.<dpu_id+1>"
```

DPU アドレス割り当て実例:

| エントリキー | `ips[0]` |
|---|---|
| `bridge-midplane\|dpu0` | `169.254.200.1` |
| `bridge-midplane\|dpu1` | `169.254.200.2` |
| `bridge-midplane\|dpu2` | `169.254.200.3` |
| `bridge-midplane\|dpu3` | `169.254.200.4` |
| `bridge-midplane\|dpu7` | `169.254.200.8` |

NPU ブリッジ IP (`169.254.200.254`) は `dpu_id + 1` の最大値 `.8`（`dpu7`）と衝突しない設計。

### DHCP_SERVER_IPV4 — SmartSwitch 固定パラメータ

| フィールド | ハードコード値 | コード位置 |
|---|---|---|
| `mode` | `"PORT"` | `config_samples.py:137` |
| `netmask` | `"255.255.255.0"` | `config_samples.py:138` |
| `gateway` | `"169.254.200.254"` | `config_samples.py:135` |
| `lease_time` | `"3600"` (秒, 1 時間) | `config_samples.py:136` |
| `state` | `"enabled"` | `config_samples.py:139` |

この値は `generate_t1_smartswitch_switch_sample_config()` でハードコードされ、
`DHCP_SERVER_IPV4|bridge-midplane` エントリとして固定投入される。

### YANG pattern 制約（ハードコード範囲）

| テーブル | フィールド | YANG pattern | 実質制約 |
|---|---|---|---|
| `MID_PLANE_BRIDGE.GLOBAL` | `bridge` | `"bridge-midplane"` | 1 値のみ許可。変更不可 |
| `DPUS` | `dpu_name`, `midplane_interface` | `dpu[0-9]+` | `dpu` プレフィックス + 1 桁以上の数字 |
| `DPUS` | `midplane_interface` | `must (current() = current()/../dpu_name)` | `midplane_interface == dpu_name` を強制 |
| `DPU` | `dpu_id` | `[0-7]` | 0〜7 の 1 桁（最大 8 DPU）|

### dhcp_cfggen.py — CONFIG_DB テーブル名定数

| 定数名 | 値 | 行番号 |
|---|---|---|
| `MID_PLANE_BRIDGE` | `"MID_PLANE_BRIDGE"` | `dhcp_cfggen.py:18` |
| `MID_PLANE_BRIDGE_SUBNET_ID` | `10000` | `dhcp_cfggen.py:19` |
| `DPUS` | `"DPUS"` | `dhcp_cfggen.py:17` |
| `SMART_SWITCH_CHECKER` | `["DpusTableEventChecker", "MidPlaneTableEventChecker"]` | `dhcp_cfggen.py:23` |

`MID_PLANE_BRIDGE_SUBNET_ID = 10000` は SmartSwitch 環境での kea-dhcp4 subnet ID として固定使用される
（通常の VLAN では VLAN 番号を subnet ID に転用するが、SmartSwitch では固定値 10000 を使う）。

## 結論

YANG `default` 文によるデフォルト値はゼロ件。すべてのデフォルト・ハードコード値は `config_samples.py`
と `dhcp_cfggen.py` にコード埋め込みで定義される。`bridge-midplane` とサブネット `169.254.200.0/24`
は設計上の固定値であり、変更するには config_samples.py とハンドラ実装の両方を書き換える必要がある。
