# dpb — Phase H: プラットフォーム差異

## 調査対象

- `sonic-buildimage/src/sonic-config-engine/portconfig.py`
- `sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py`
- `sonic-utilities/config/main.py`
- `sonic-swss/orchagent/portsorch.cpp`
- `device/arista/x86_64-arista_7050cx3_32c/platform.json`
- `device/arista/x86_64-arista_7060dx5_64s/Arista-7060DX5-64S/hwsku.json`

## 調査結果

### 1. platform.json / port_config.ini 二分岐

`get_path_to_port_config_file()` (`device_info.py:445`) はプラットフォームディレクトリを走査して返却するファイルを決定する:

1. `hwsku.json` が存在 **かつ** `platform.json` が存在 **かつ** `interfaces` キーが空でない → `platform.json` を返す
2. 上記以外 → `port_config.ini` を返す（`asic` 引数あり時は `hwsku/<asic>/port_config.ini`）

`breakout()` CLI (`main.py:5467-5471`) は `get_path_to_port_config_file()` を引数なしで呼び出す。戻り値が `.json` 拡張子でない（= `port_config.ini`）か、ファイルが存在しない場合は即 Abort。

```python
breakout_cfg_file = device_info.get_path_to_port_config_file()
if not os.path.isfile(breakout_cfg_file) or not breakout_cfg_file.endswith('.json'):
    click.secho("[ERROR] Breakout feature is not available without platform.json file", ...)
    raise click.Abort()
```

### 2. multi-ASIC 対応状況

`get_path_to_port_config_file()` は `asic` 引数を受け付けるが、`breakout()` CLI は引数なしで呼び出すため、**multi-ASIC 環境での ASIC 個別 DPB は CLI レベルで未対応**。

`portconfig.py` の `get_port_config(asic_name=...)` は `get_asic_id_from_name()` でASIC ID を解決し `hwsku/<asic_id>/port_config.ini` を参照するが、DPB CLI フローはこの経路を使用しない。

### 3. hwsku.json の default_brkout_mode

`BREAKOUT_CFG` の初期値は `hwsku.json` の `interfaces.<port>.default_brkout_mode` から取得される:

```json
"Ethernet0": {
    "default_brkout_mode": "1x400G[200G,100G,50G,40G,25G,10G]",
    "fec": "rs"
}
```

`default_brkout_mode` が `hwsku.json` に存在しないポートは `parse_breakout_mode()` に含まれず、BREAKOUT_CFG エントリが生成されない (`portconfig.py:425-432`)。

### 4. breakout_modes は platform.json で定義

利用可能なモード一覧は `platform.json` の `interfaces.<port>.breakout_modes` キーに格納される:

```json
"Ethernet1/1": {
    "breakout_modes": {
        "1x100G[50G,40G,25G,10G]": ["Ethernet1/1"],
        "2x50G[40G,25G,10G]":       ["Ethernet1/1", "Ethernet1/3"],
        "4x25G[10G]":                ["Ethernet1/1", "Ethernet1/2", "Ethernet1/3", "Ethernet1/4"]
    }
}
```

`_validate_interface_mode()` は `breakout_modes` に target mode が含まれるかを確認する (`main.py:5208`)。ASIC が物理的に対応しないモードは `platform.json` 側に記載されていないため自動排除される。

### 5. portsorch での ASIC lane バリデーション

portsorch は DPB 後に追加されたポートの `lanes` が `m_portListLaneMap`（SAI 初期化時に ASIC から取得）に存在するかを確認する (`portsorch.cpp:4026-4032`)。`platform.json` の lane 定義と ASIC 物理 lane が不一致な場合ここで失敗する。Mellanox 固有の DPB 分岐はなく、`isMlnxPlatform()` による特殊処理は Trim Stat 計算のみ (`portsorch.cpp:858-863`)。

### 6. Virtual Switch (VS) プラットフォーム

SONiC-VS (`kvmx86_64-kvm_x86_64-r0`) は `port_config.ini` ベースのため DPB が無効。`platform.json` / `hwsku.json` が提供されないためテーブル自体が生成されない。

## Evidence

- `device_info.py:445-509`: `get_path_to_port_config_file()` 実装
- `portconfig.py:199-210`: platform.json / port_config.ini 分岐
- `portconfig.py:425-432`: `default_brkout_mode` 欠落時のスキップ
- `main.py:5467-5471`: `.json` チェック
- `main.py:5208`: `_validate_interface_mode` モード検証
- `portsorch.cpp:4026-4032`: lane バリデーション
- `portsorch.cpp:858-863`: isMlnxPlatform 分岐（Trim Stat のみ）
- `device/arista/x86_64-arista_7050cx3_32c/platform.json`: breakout_modes 実例
- `device/arista/x86_64-arista_7060dx5_64s/Arista-7060DX5-64S/hwsku.json`: default_brkout_mode 実例
