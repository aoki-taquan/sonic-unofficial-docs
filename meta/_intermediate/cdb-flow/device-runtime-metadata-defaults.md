# DEVICE_RUNTIME_METADATA フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `DEVICE_RUNTIME_METADATA` (仮想テーブル / 永続化されない)

## 調査対象ファイル

- `sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py`
  - `get_device_runtime_metadata()` (L735-747)
  - 補助: `is_chassis()` / `is_supervisor()` / `is_voq_chassis()` / `is_packet_chassis()` / `is_virtual_chassis()` / `is_disaggregated_chassis()` / `is_macsec_supported()` / `is_multi_npu()` / `get_path_to_port_config_file()` / `get_platform_env_conf_file_path()`
- `sonic-buildimage/files/build_templates/init_cfg.json.j2`
  - L67,75,90,106,107 が `DEVICE_RUNTIME_METADATA` を参照
- `sonic-host-services/scripts/featured` L145
  - `self._device_running_config = device_info.get_device_runtime_metadata()` で起動時取得

`hostcfgd` などからの書き込みパスは存在しない (テーブル全体がコード由来生成のため)。

---

## サブキー別 暗黙デフォルト

DEVICE_RUNTIME_METADATA は永続テーブルではなく、`sonic-cfggen` 実行時に Python が組み立てる辞書。フィールド値はユーザー設定不可で、**プラットフォーム検出結果から自動決定** される。

### `CHASSIS_METADATA` (サブキー自体の有無)

**コード由来デフォルト**: chassis 環境のみ存在、それ以外は **キー自体なし**

```python
# device_info.py:736-739
chassis_metadata = {}
if is_chassis():
    chassis_metadata = {'CHASSIS_METADATA': {
        'module_type' : 'supervisor' if is_supervisor() else 'linecard',
        'chassis_type': 'voq' if is_voq_chassis() else 'packet'}}
```

判定:

- `is_chassis()` = `(is_voq_chassis() and not is_disaggregated_chassis()) or is_packet_chassis() or is_virtual_chassis()` (L667-668)
- 非 chassis ホスト (典型 ToR / leaf) では辞書に **キー自体が作られない**。テンプレ側は `'CHASSIS_METADATA' in DEVICE_RUNTIME_METADATA` の存在チェックで分岐。

### `CHASSIS_METADATA.module_type`

**コード由来デフォルト**: `'supervisor' if is_supervisor() else 'linecard'`

```python
# device_info.py:699-712 (is_supervisor)
def is_supervisor():
    platform_env_conf_file_path = get_platform_env_conf_file_path()
    if platform_env_conf_file_path is None:
        return False
    # platform_env.conf に supervisor=1 行があれば True
```

- `platform_env.conf` 未配置プラットフォーム → `is_supervisor()=False` → `'linecard'`
- `platform_env.conf` に `supervisor=1` あり → `'supervisor'`
- enum 制約は YANG にない (仮想テーブルのため)。実体は 2 値。

### `CHASSIS_METADATA.chassis_type`

**コード由来デフォルト**: `'voq' if is_voq_chassis() else 'packet'`

```python
# device_info.py:630-634
def is_voq_chassis():
    switch_type = get_platform_info().get('switch_type')
    single_voq = is_chassis_config_absent()
    return bool(switch_type and (switch_type == 'voq' or switch_type == 'fabric')
                and not single_voq)
```

- `DEVICE_METADATA.localhost.switch_type` が `'voq'` または `'fabric'` で `chassisdb.conf` 存在 → `'voq'`
- それ以外 (`chassis-packet` 等) → `'packet'`

> **本ページ未記載**: 既存本文 (key 構造・サブキー表) は `module_type` のみで `chassis_type` を扱っていない。Phase A 範囲外として保留 (本文追補は Phase B で検討)。

### `ETHERNET_PORTS_PRESENT` (直値)

**コード由来デフォルト**: `bool(get_path_to_port_config_file(hwsku=None, asic=...))`

```python
# device_info.py:741
port_metadata = {'ETHERNET_PORTS_PRESENT':
    True if get_path_to_port_config_file(
        hwsku=None, asic="0" if is_multi_npu() else None) else False}
```

- ASIC ごとの `port_config.ini` を探索 (multi-npu の場合 `asic="0"`、それ以外 None)
- ファイル未検出 → `False` (supervisor / fabric card 等)
- 検出 → `True` (通常 ToR / linecard)
- **必ずキーが存在する** (chassis_metadata と異なり常時セット)

### `MACSEC_SUPPORTED` (直値)

**コード由来デフォルト**: `bool(is_macsec_supported())`

```python
# device_info.py:714-732 (is_macsec_supported)
def is_macsec_supported():
    supported = 0
    platform_env_conf_file_path = get_platform_env_conf_file_path()
    if platform_env_conf_file_path is None:
        return supported            # → 0 (False)
    with open(platform_env_conf_file_path) as f:
        for line in f:
            tokens = line.split('=')
            ...
            if tokens[0].lower() == 'macsec_enabled':
                supported = tokens[1].strip()
                break
    return int(supported)
```

判定:

- `platform_env.conf` が存在しない → `0` → `MACSEC_SUPPORTED=False`
- `platform_env.conf` に `macsec_enabled=` 行が無い → 初期値 `0` → `False`
- `macsec_enabled=1` → `True`
- **必ずキーが存在する** (キー欠落はテンプレ側で考慮不要)

---

## init_cfg.json.j2 側のデフォルト派生

`DEVICE_RUNTIME_METADATA` の値が `FEATURE` テーブル生成時に以下のように再投影される (テンプレ → CONFIG_DB のビルド時デフォルト):

| 条件 | 影響 (init_cfg.json.j2) |
|------|------------------------|
| `ETHERNET_PORTS_PRESENT=False` または `CHASSIS_METADATA.module_type=supervisor` | `FEATURE.bgp.state=disabled`, `has_per_asic_scope="False"` (L67, L107) |
| `ETHERNET_PORTS_PRESENT=False` | `FEATURE.teamd.state=disabled` (L75) |
| `CHASSIS_METADATA.module_type=linecard` | `has_global_scope="False"` (L106) |
| `MACSEC_SUPPORTED=False` または `DEVICE_METADATA.type` が `SpineRouter` 系でない | `FEATURE.macsec.state=disabled` (L90) |

これらはユーザーが `DEVICE_RUNTIME_METADATA` を書き換えても無効 (毎回コードで再生成されるため永続化されない)。

---

## まとめ

すべてのフィールドが **コード自動検出** で決まり、ユーザー入力経路は存在しない:

| サブキー / フィールド | コード由来デフォルト | 検出根拠 |
|-----------------------|---------------------|----------|
| `CHASSIS_METADATA` 自体 | 非 chassis ではキーなし | `is_chassis()` |
| `CHASSIS_METADATA.module_type` | `linecard` (platform_env.conf に `supervisor=1` なし) | `is_supervisor()` |
| `CHASSIS_METADATA.chassis_type` | `packet` (switch_type が voq/fabric 以外) | `is_voq_chassis()` |
| `ETHERNET_PORTS_PRESENT` | `True` (port_config.ini 検出時) / `False` (未検出) | `get_path_to_port_config_file()` |
| `MACSEC_SUPPORTED` | `False` (platform_env.conf 未配置 or macsec_enabled=0) | `is_macsec_supported()` |

CLI / sonic-cfggen 経由のユーザー書き込みパスは存在せず、`db_migrator` の対象でもない。
