# DPU テーブル — プラットフォーム差調査 (Phase H)

Task F Phase H: CONFIG_DB `DPU` テーブルのプラットフォーム・ベンダー依存を調査した。

## 主要調査ソース

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:82-85,144-146,720-729,1412-1420,1576-1579`
- `sonic-platform-common/sonic_platform_base/chassis_base.py:317-333`
- `sonic-platform-common/sonic_platform_base/module_base.py:37,69,177-189`
- `sonic-buildimage/src/sonic-config-engine/smartswitch_config.py:22-48`
- `sonic-buildimage/src/sonic-config-engine/config_samples.py:81-207`
- `sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py:671-694,1043-1101`
- `sonic-utilities/utilities_common/chassis.py:21-40`
- `sonic-utilities/scripts/reboot_smartswitch_helper:16-26,33-48`
- `sonic-swss/orchagent/orchdaemon.cpp:613-618`
- `sonic-swss/orchagent/main.cpp:260-275`

## 結論

`DPU` テーブル構造（YANG スキーマ）はプラットフォーム非依存。ただし以下の 4 点でプラットフォーム差が生じる:

1. **SmartSwitch 判定** — `platform.json[DPUS]` の有無 (device_info.is_smartswitch) により DashEniFwdOrch 初期化が分岐
2. **DPU テーブル書き込み元** — SmartSwitch では `smartswitch_config.py` が `platform.json` から `DPU` セクションを読み込む。DPU ノード (`switch_type=dpu`) では `platform.json[DPU]` が空 dict
3. **`dpu_reboot_timeout`** — `platform.json` に `dpu_reboot_timeout` キーがあれば chassisd が 360 秒デフォルトを上書き。プラットフォームごとに変更可能
4. **`gnmi_port` 読み取り** — `reboot_smartswitch_helper` が CONFIG_DB `DPU|*` を `sonic-db-cli` で直接参照。gNMI 接続確認に使用

## 詳細

### 1. SmartSwitch 判定 — `is_smartswitch()` と `is_dpu()` 分岐

`device_info.is_smartswitch()` (`device_info.py:671-680`) は `platform.json` に `"DPUS"` キーが存在すれば `True` を返す:

```python
# sonic_py_common/device_info.py:671-680
def is_smartswitch():
    platform_data = get_platform_json_data()
    if platform_data:
        return "DPUS" in platform_data   # DPUS セクションの有無で判定
    return False
```

`is_dpu()` (`device_info.py:685-694`) は `platform.json` に `"DPU"` キー（大文字）が存在すれば `True` を返す:

```python
# sonic_py_common/device_info.py:685-694
def is_dpu():
    platform_data = get_platform_json_data()
    if platform_data:
        return 'DPU' in platform_data    # DPU セクションの有無で判定
    return False
```

これにより chassisd エントリポイント (`chassisd:1576`) が SmartSwitch NPU 側と DPU 側で処理を分岐する:

```python
# chassisd:1576-1579
if chassis.is_smartswitch() and chassis.is_dpu():
    chassisd = DpuChassisdDaemon(...)    # DPU ノード: 状態ポーリング専用
else:
    chassisd = ChassisdDaemon(...)       # NPU 側 / 標準 chassis
```

orchagent では `gMySwitchSubType == "SmartSwitch"` のときのみ `DashEniFwdOrch` が起動し `DPU` テーブルを購読する (`orchdaemon.cpp:613-618`)。

### 2. DPU テーブル書き込み元と platform.json 形式

`smartswitch_config.py:22-48` は `platform.json` から `DPU` セクションと `DPUS` セクションを抽出して CONFIG_DB に書き込む:

```python
# smartswitch_config.py:43-46
if DPU_TABLE in platform_json:
    config[DPU_TABLE] = platform_json[DPU_TABLE]
if DPUS_TABLE in platform_json:
    config[DPUS_TABLE] = platform_json[DPUS_TABLE]
```

テスト用サンプル (`sample_dpu_platform.json`) の DPU ノード側 `platform.json`:
```json
{ "DPU": {} }   # DPU ノードでは空 dict が典型
```

SmartSwitch NPU 側の `platform.json` には `DPUS` セクション（ミッドプレーンインターフェース）のみ存在し、`DPU` セクション（CONFIG_DB に書き込む IP/ポート群）は minigraph 由来で別途設定される。

### 3. `dpu_reboot_timeout` — platform.json による上書き

`SmartSwitchModuleUpdater.__init__()` (`chassisd:720-729`) は `/usr/share/sonic/platform/platform.json` を読み込み `dpu_reboot_timeout` キーがあれば 360 秒デフォルトを上書きする:

```python
# chassisd:722-727
if os.path.isfile(PLATFORM_JSON_FILE):
    with open(PLATFORM_JSON_FILE, 'r') as f:
        platform_cfg = json.load(f)
    self.dpu_reboot_timeout = int(
        platform_cfg.get("dpu_reboot_timeout", DEFAULT_DPU_REBOOT_TIMEOUT)  # default=360
    )
```

DPU リブート最大許容時間は `MAX_DPU_REBOOT_DURATION = 800` 秒で固定。`dpu_reboot_timeout` はリブート完了を待つタイムアウト。この値は CONFIG_DB の `DPU` テーブルとは無関係だが、DPU リブート時の gnmi 接続確認（`gnmi_port` 参照）に間接影響する。

### 4. `gnmi_port` — `reboot_smartswitch_helper` による直接参照

`reboot_smartswitch_helper` スクリプト (`sonic-utilities:40-47`) は CONFIG_DB `DPU|*` を `sonic-db-cli` で直接参照し `gnmi_port` を取得する:

```bash
# sonic-utilities/scripts/reboot_smartswitch_helper:40-47
function get_gnmi_port()
{
    local DPU_NAME=${1:-dpu0}
    for k in $(sonic-db-cli CONFIG_DB keys "DPU|*$DPU_NAME"); do
        sonic-db-cli CONFIG_DB hget "$k" 'gnmi_port'
    done
}
```

`is_smartswitch()` と `is_dpu()` は `utilities_common.chassis` モジュール経由で `device_info` の同名関数を呼ぶ。このスクリプトは SmartSwitch プラットフォームでのみ実行され、非 SmartSwitch 環境での `DPU` テーブル参照はない。

## まとめ

| 差分ポイント | 具体的内容 | 証跡 |
|------------|-----------|------|
| SmartSwitch 判定 | `platform.json[DPUS]` 有無で `is_smartswitch()` が決まる。この戻り値が orchagent `DashEniFwdOrch` 起動のゲートになる | `device_info.py:671-680`, `orchdaemon.cpp:613` |
| DPU テーブル書き込み元 | SmartSwitch: `smartswitch_config.py` が `platform.json[DPU]` を CONFIG_DB に転記。DPU ノード: `platform.json[DPU]` は空 dict が典型 | `smartswitch_config.py:43-46` |
| `dpu_reboot_timeout` | `platform.json` の任意キー。デフォルト 360 秒。プラットフォームごとに変更可能 | `chassisd:720-729` |
| `gnmi_port` 直接参照 | `reboot_smartswitch_helper` が CONFIG_DB `DPU|*` から `gnmi_port` を直接読み取る。欠如時は gNMI 接続確認なしでリブートが進む | `reboot_smartswitch_helper:40-47` |
| CONFIG_DB テーブル構造 | YANG スキーマは完全にプラットフォーム非依存。フィールド値（IP アドレス等）は minigraph / platform.json 由来でプラットフォーム固有の値になる | `sonic-smart-switch.yang` |
