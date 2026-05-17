# DPU — Phase H 調査メモ (platform 差異)

調査日: 2026-05-17
対象テーブル: CONFIG_DB `DPU`

## 調査対象ファイル

- `sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py` — is_smartswitch / is_dpu / get_num_dpus
- `sonic-buildimage/src/sonic-config-engine/smartswitch_config.py` — platform.json → CONFIG_DB 書き込み
- `sonic-buildimage/src/sonic-config-engine/config_samples.py` — generate_t1_smartswitch_* 系
- `sonic-platform-common/sonic_platform_base/chassis_base.py` — is_smartswitch / is_dpu API 定義
- `sonic-buildimage/platform/mellanox/mlnx-platform-api/smart_switch/dpuctl/main.py` — Mellanox 固有実装
- `sonic-utilities/scripts/reboot_smartswitch_helper` — SmartSwitch リブート補助スクリプト

---

## プラットフォーム識別ロジック

### `is_smartswitch()` — NPU 側 SmartSwitch 判定

`device_info.is_smartswitch()` は `platform.json` に `"DPUS"` キーが存在する場合に True を返す。
SmartSwitch の NPU ノードは `platform.json` に `DPUS` セクションを持つ。

```python
# device_info.py:671-682
def is_smartswitch():
    platform_data = get_platform_json_data()
    if platform_data:
        return "DPUS" in platform_data
    return False
```

### `is_dpu()` — DPU ノード自身の判定

`device_info.is_dpu()` は `platform.json` に `"DPU"` キーが存在する場合に True を返す。
DPU ノード (switch_type=dpu) は `platform.json` に `DPU` セクションを持つ。

```python
# device_info.py:685-695
def is_dpu():
    platform_data = get_platform_json_data()
    if platform_data:
        return 'DPU' in platform_data
    return False
```

**重要**: CONFIG_DB の `DPU` テーブルは SmartSwitch NPU ノード (`is_smartswitch() == True`) にのみ存在する。
DPU ノード自身 (`is_dpu() == True`) の CONFIG_DB には `DPU` テーブルは書き込まれない。

## platform.json 構造の違い

| ノード種別 | platform.json の判定キー | `DPU` テーブル存在 | `DPUS` テーブル存在 |
|----------|------------------------|-------------------|-------------------|
| SmartSwitch NPU | `DPUS` キーあり | **あり** (minigraph 由来) | あり |
| DPU ノード | `DPU` キーあり | なし | なし |
| 通常スイッチ | どちらもなし | なし | なし |

## platform.json サンプル (SmartSwitch NPU)

`src/sonic-config-engine/tests/data/smartswitch/sample_switch_platform.json`:

```json
{
    "DPUS": {
        "dpu0": { "midplane_interface": "dpu0" },
        "dpu1": { "midplane_interface": "dpu1" },
        "dpu2": { "midplane_interface": "dpu2" },
        "dpu3": { "midplane_interface": "dpu3" }
    }
}
```

SmartSwitch NPU の `platform.json` は `DPUS` のみ持ち、`DPU` テーブルの具体的フィールド値 (pa_ipv4, gnmi_port 等) は minigraph パーサが CONFIG_DB に直接書き込む。

## Mellanox SmartSwitch 固有実装

Mellanox SmartSwitch (`mlnx-platform-api`) は `DpuCtlPlat` クラスを実装し、DPU のリセット / パワーオン / パワーオフ / 状態取得 (`dpu_status_update()`) をプラットフォーム API 経由で行う。この実装は CONFIG_DB `DPU` テーブルを直接参照せず、`DPU_STATE` テーブル (CHASSIS_STATE_DB) を通じて状態を更新する。

## reboot_smartswitch_helper の DPU 参照

`scripts/reboot_smartswitch_helper` は DPU リブート時に以下を実施:

1. `sonic-db-cli CONFIG_DB keys "DPU|*${DPU_NAME}"` で DPU エントリを検索
2. `sonic-db-cli CONFIG_DB hget "$k" 'gnmi_port'` で `gnmi_port` を取得
3. `sonic-db-cli CONFIG_DB HGET "DHCP_SERVER_IPV4_PORT|bridge-midplane|${DPU_NAME}" "ips@"` で DPU IP を取得
4. 取得した IP + gnmi_port を使って gNMI 経由で DPU リブートを実行

## DEVICE_METADATA 設定 (SmartSwitch 固有)

SmartSwitch のサンプル設定生成時 (`config_samples.py`):

| 設定 | NPU (`switch`) ノード | DPU ノード |
|-----|----------------------|-----------|
| `subtype` | `SmartSwitch` | `SmartSwitch` |
| `switch_type` | 未設定 (通常 T1) | `dpu` |
| `type` | `LeafRouter` | `SmartSwitchDPU` |

NPU ノードでは `MID_PLANE_BRIDGE` / `DHCP_SERVER_IPV4` / `DHCP_SERVER_IPV4_PORT` が設定されるが、DPU ノードには設定されない。`DPU` テーブル自体は minigraph パーサが NPU ノード CONFIG_DB にのみ書き込む。

## 非対応プラットフォームでの挙動

`DPU` テーブルへのアクセスは SmartSwitch (`is_smartswitch() == True`) 環境のみを想定。非 SmartSwitch 環境 (通常 T1 / T2 スイッチ) では:

- `DashEniFwdOrch` 自体が `orchdaemon` に登録されない (`orchdaemon.cpp:615` 参照; SmartSwitch かつ非 DPU ノードの場合のみ登録)
- `caclmgrd` は `subscribe_dpu_table` を登録するが `feature_present` に `"dash-ha"` が存在しない限り DPU イベントを処理しない
- `sonic-gnmi` DPU proxy は SmartSwitch 環境のみで有効
