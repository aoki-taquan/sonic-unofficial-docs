# BREAKOUT_CFG — プラットフォーム / SAI Capability 差異調査 (Phase H)

## 調査対象

テーブル: `BREAKOUT_CFG`
調査日: 2026-05-18

## 結論

DPB の利用可否は ASIC ではなくプラットフォームの **ポート設定ファイル形式** によって決まる。
`platform.json` + `hwsku.json` を持つプラットフォームのみ DPB が有効。
`port_config.ini` 形式のプラットフォームでは `config interface breakout` 自体が実行不能となる。

## プラットフォームファイル形式による DPB 有効性

### 判定ロジック（portconfig.py）

`get_breakout_mode()` (`portconfig.py:452-465`):

```python
if port_config_file.endswith('.json'):
    hwsku_json_file = get_hwsku_file_name(hwsku, platform)
    return parse_breakout_mode(hwsku_json_file)
else:
    return None   # port_config.ini 形式 → DPB 無効
```

### config/main.py の早期終了

```python
breakout_cfg_file = device_info.get_path_to_port_config_file()
if not os.path.isfile(breakout_cfg_file) or not breakout_cfg_file.endswith('.json'):
    click.secho("[ERROR] Breakout feature is not available without platform.json file", fg='red')
    raise click.Abort()
```

(`main.py:5468-5471`)

| プラットフォームファイル形式 | DPB 有効 | `BREAKOUT_CFG` 書込み | エラー |
|--------------------------|---------|---------------------|--------|
| `platform.json` + `hwsku.json` (新形式) | **有効** | 起動時 `sonic-cfggen` が自動生成 | なし |
| `port_config.ini` (旧形式) | **無効** | 書き込まれない | `[ERROR] Breakout feature is not available without platform.json file` |
| `platform.json` なし / ファイル不在 | **無効** | 書き込まれない | 同上 |

### 統計（sonic-buildimage device/ ディレクトリ）

- `platform.json` を持つプラットフォーム: 167 件
- `port_config.ini` を持つプラットフォーム: 413 件
- **多数の既存プラットフォームが `port_config.ini` 形式のため DPB 非対応**

## breakout_modes のプラットフォーム差異

`platform.json` を持つプラットフォームでも、各ポートが対応する `breakout_modes` はハードウェアレーン構成によって異なる。

### Arista 7050CX3-32S (x86_64-arista_7050cx3_32s) — 代表例

`Ethernet0` の `breakout_modes`:

| モード | 意味 |
|--------|------|
| `1x100G[50G,40G,25G,10G]` | 4 レーン集約（デフォルト） |
| `2x50G[40G,25G,10G]` | 2 レーン × 2 分割 |
| `4x25G[10G]` | 1 レーン × 4 分割 |

ASIC (Broadcom Trident3) が 4 レーン / 100G ポートを前提としており、400G / 800G 世代とは構成が異なる。

### プラットフォーム世代別の典型 breakout モード

| 世代 / ASIC | 典型ポート速度 | 代表的 breakout モード |
|------------|------------|----------------------|
| 10G/25G 世代 (Trident2/3) | 100G × 32 等 | `4x25G[10G]`, `2x50G`, `1x100G` |
| 100G 世代 (Tomahawk/Mellanox Spectrum) | 400G QSFP-DD 等 | `1x400G`, `2x200G`, `4x100G` |
| 800G 世代 | 800G | `1x800G`, `2x400G`, `8x100G` 等 |

## SAI 制約

DPB の実装は SAI ポート削除・作成 API (`sai_port_api->remove_port()` / `create_port()`) に依存する。
SAI プロバイダが DPB 非対応のシミュレーター等では ASIC_DB への OID 変化が生じないため、
`_verifyAsicDB()` が 60 秒タイムアウトになる。

現行コードに SAI capability クエリによる DPB 有効/無効チェックはなく、実行時にタイムアウトで失敗する。

## Evidence

- `sonic-buildimage/src/sonic-config-engine/portconfig.py:452-465`（SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`）
- `sonic-utilities/config/main.py:5467-5471`（SHA `39732bceb8bdefe706518ab40623bbbba6ff33b9`）
- `sonic-buildimage/device/arista/x86_64-arista_7050cx3_32s/platform.json:211-230`
- `sonic-swss/cfgmgr/portmgrd.cpp`（sonic-swss）
- `sonic-platform-common/tests/platform_json/hwsku.json`（default_brkout_mode の実例）
