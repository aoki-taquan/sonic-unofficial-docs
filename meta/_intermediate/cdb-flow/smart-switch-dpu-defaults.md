# SmartSwitch DPU CONFIG_DB — Phase A: コード由来デフォルト調査

## 調査対象テーブル

- `MID_PLANE_BRIDGE|GLOBAL`
- `DPUS|<dpu_name>`
- `DPU|<dpu_name>`
- `REMOTE_DPU|<dpu_name>`
- `VDPU|<vdpu_id>`
- `DASH_HA_GLOBAL_CONFIG|global`

## 主要ソース

| ソース | パス | SHA |
|--------|------|-----|
| YANG モデル | `src/sonic-yang-models/yang-models/sonic-smart-switch.yang` | 9ea932ec |
| config_samples.py | `src/sonic-config-engine/config_samples.py` | 9ea932ec |
| smartswitch_config.py | `src/sonic-config-engine/smartswitch_config.py` | 9ea932ec |
| mock_config_db_smart_switch.json | `src/sonic-dhcp-utilities/tests/test_data/mock_config_db_smart_switch.json` | 9ea932ec |
| sample_config_db.json (yang tests) | `src/sonic-yang-models/tests/files/sample_config_db.json` | 9ea932ec |
| module.py (Mellanox) | `platform/mellanox/mlnx-platform-api/sonic_platform/module.py` | 9ea932ec |
| dashhaorch.cpp | `orchagent/dash/dashhaorch.cpp` | sonic-swss master |

---

## MID_PLANE_BRIDGE|GLOBAL

### フィールド別デフォルト

| フィールド | YANG 規約 | コード由来デフォルト | 出典 |
|-----------|---------|-----------------|------|
| `bridge` | pattern `bridge-midplane` (固定値) | `"bridge-midplane"` | config_samples.py:88 |
| `ip_prefix` | `sonic-ip4-prefix` | `"169.254.200.254/24"` | config_samples.py:93 |

**コード証拠**:
```python
# config_samples.py:88-94
bridge_name = 'bridge-midplane'
data['MID_PLANE_BRIDGE'] = {
    "GLOBAL": {
        "bridge": bridge_name,
        "ip_prefix": "169.254.200.254/24"
    }
}
```

YANG の `bridge` leaf には `must "(current()/../ip_prefix)"` 制約があり、ip_prefix なしの bridge 設定は YANG バリデーションで拒否される。

---

## DPUS|<dpu_name>

### フィールド別デフォルト

| フィールド | 型 | コード由来値 | 出典 |
|-----------|-----|------------|------|
| `midplane_interface` | string pattern `dpu[0-9]+` | `<dpu_name>` と同値 (例: `dpu0`) | YANG:101 `must` 制約 |

**YANG 制約**:
```yang
# sonic-smart-switch.yang:101
must "(current() = current()/../dpu_name)";
```
`midplane_interface` は必ず `dpu_name` と同一値。つまり `DPUS|dpu0` の `midplane_interface` は常に `"dpu0"`。

**DHCP サーバーへの波及**:
```python
# config_samples.py:102-103
dpu_id = int(midplane_interface.replace('dpu', ''))  # 0, 1, 2, ...
dhcp_server_ports['{}|{}'.format(bridge_name, midplane_interface)] = {
    'ips': ['{}.{}'.format(mpbr_prefix, dpu_id + 1)]  # 169.254.200.1, .2, ...
}
```
DPU 番号が 0 始まりで、割り当て IP は `169.254.200.(dpu_id+1)` となる。

---

## DPU|<dpu_name>

### フィールド別デフォルト

| フィールド | YANG 型 | デフォルト | コード証拠 |
|-----------|--------|----------|---------|
| `state` | `admin_status` (up/down) | 明示なし（YANG default なし）| minigraph / platform.json から設定 |
| `local_port` | `interface_name` | 明示なし | minigraph から |
| `vip_ipv4` | `ipv4-address` | 明示なし | minigraph から |
| `vip_ipv6` | `ipv6-address` | 明示なし | minigraph から |
| `pa_ipv4` | `ipv4-address` | 明示なし | minigraph から |
| `pa_ipv6` | `ipv6-address` | 明示なし | minigraph から |
| `midplane_ipv4` | `ipv4-address` | `169.254.200.(dpu_id+1)` | module.py:490 |
| `dpu_id` | string `[0-7]` | 明示なし | minigraph から |
| `vdpu_id` | string 1..255 | 明示なし | minigraph から |
| `gnmi_port` | `port-number` | `50052` (テスト実例) | sample_config_db.json |
| `orchagent_zmq_port` | `port-number` | `50` (テスト実例) | sample_config_db.json |
| `swbus_port` | `port-number` | `23607` (テスト実例) | sample_config_db.json |

**midplane_ipv4 の計算式（Mellanox platform）**:
```python
# platform/mellanox/mlnx-platform-api/sonic_platform/module.py:490
return f"169.254.200.{int(self.dpu_id) + 1}"
# dpu_id=0 → 169.254.200.1
# dpu_id=1 → 169.254.200.2
# ...
```

`gnmi_port`, `orchagent_zmq_port`, `swbus_port` は YANG に default 値の定義がなく、minigraph または platform.json から書き込まれる。テスト実例の値 (`50052`, `50`, `23607`) はリファレンス値であり、ベンダー・platform によって異なる可能性がある。

---

## REMOTE_DPU|<dpu_name>

### フィールド別デフォルト

| フィールド | YANG 型 | デフォルト |
|-----------|--------|----------|
| `type` | string 1..255 | 明示なし（設定必須）|
| `pa_ipv4` | `ipv4-address` | 明示なし |
| `pa_ipv6` | `ipv6-address` | 明示なし |
| `npu_ipv4` | `ipv4-address` | 明示なし |
| `npu_ipv6` | `ipv6-address` | 明示なし |
| `dpu_id` | string `[0-7]` | 明示なし |
| `swbus_port` | `port-number` | `23606`〜`23607` (テスト実例) | sample_config_db.json |

すべてのフィールドが minigraph または operator 設定由来。YANG に default 定義なし。

---

## VDPU|<vdpu_id>

### フィールド別デフォルト

| フィールド | YANG 型 | テスト実例値 | 備考 |
|-----------|--------|-----------|------|
| `profile` | string 1..255 | `"none"` | sample_config_db.json; YANG 記述「currently unused, reserved for future use」|
| `tier` | string 1..255 | `"none"` | 同上 |
| `main_dpu_ids` | string pattern | `"dpu0"` | カンマ区切りで複数 DPU 指定可 |

`profile` と `tier` は YANG コメントで「将来用」と明記されており、現時点では機能しない。デフォルト値 `"none"` はテスト実例からの観察値。YANG に formal default なし。

---

## DASH_HA_GLOBAL_CONFIG|global

### フィールド別デフォルト

| フィールド | YANG 型 | テスト実例値 | 備考 |
|-----------|--------|-----------|------|
| `vnet_name` | leafref (VNET) | — | YANG `status deprecated`（`dpu_vnet` 推奨）|
| `dpu_vnet` | leafref (VNET) | — | `vnet_name` の後継 |
| `dpu_vlan` | string 1..255 | — | DPU VLAN 識別子 |
| `cp_data_channel_port` | `port-number` | `11362` | sample_config_db.json |
| `dp_channel_dst_port` | `port-number` | `11368` | sample_config_db.json |
| `dp_channel_src_port_min` | `port-number` | `49152` | sample_config_db.json |
| `dp_channel_src_port_max` | `port-number` | `53247` | sample_config_db.json |
| `dp_channel_probe_interval_ms` | uint32 | `100` | sample_config_db.json |
| `dp_channel_probe_fail_threshold` | uint32 | `3` | sample_config_db.json |
| `dpu_bfd_probe_interval_in_ms` | uint32 | `100` | sample_config_db.json |
| `dpu_bfd_probe_multiplier` | uint32 | `3` | sample_config_db.json |

すべて YANG default なし。テスト実例の値は `sonic-yang-models/tests/files/sample_config_db.json` から。実運用値は minigraph または operator 設定で上書きされる。

`dp_channel_src_port_min: 49152` = Linux エフェメラルポート範囲開始と一致。`dp_channel_src_port_max: 53247` = 49152 + 4095 (4096 ポート幅)。

---

## 特記事項

1. **MID_PLANE_BRIDGE の ip_prefix** は `169.254.200.254/24` に固定（link-local 範囲ではなく APIPA 近接帯）。YANG の pattern 制約で `bridge-midplane` のみ許可。
2. **DPUS の midplane_interface** は YANG の `must` 制約により `dpu_name` と必ず同値。
3. **DPU の midplane_ipv4** は Mellanox platform 実装で `169.254.200.(dpu_id+1)` として計算されるが、これは platform 固有ロジック。他 platform では異なる可能性。
4. **DASH_HA_GLOBAL_CONFIG** の全フィールドはオプションで、YANG に formal default なし。テスト値はリファレンス実例。
5. **`vnet_name`** は YANG で `status deprecated`。新規設定では `dpu_vnet` を使用すること。
