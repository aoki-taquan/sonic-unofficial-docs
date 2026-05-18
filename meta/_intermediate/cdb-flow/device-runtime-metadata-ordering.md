# DEVICE_RUNTIME_METADATA — 書込み順依存 (Phase B)

## 調査対象

- `src/sonic-py-common/sonic_py_common/device_info.py` (get_device_runtime_metadata, L735-747)
- `src/system-health/health_checker/sysmonitor.py` (L210-237)
- `files/build_templates/init_cfg.json.j2` (L67,75,90,106-107)

## 結論

`DEVICE_RUNTIME_METADATA` は CONFIG_DB に永続化されないインメモリ辞書。通常の SET/DEL シーケンス依存は存在しないが、呼び出し内部に以下の順序制約がある:

1. プラットフォームファイル (`platform_env.conf`, `port_config.ini`) の存在 → `get_device_runtime_metadata()` 構築
2. `get_device_runtime_metadata()` 完了 → FEATURE state 評価 (init_cfg.json.j2 / sysmonitor.py)
3. `DEVICE_METADATA` 取得 → `DEVICE_RUNTIME_METADATA` と結合 (sysmonitor.py L219-220)
4. サブ辞書の update 順: chassis_metadata → port_metadata → macsec_support_metadata (後勝ち、現在キー重複なし)

## Evidence

- `device_info.py:735-747`: `get_device_runtime_metadata()` 実装
- `sysmonitor.py:210-237`: FEATURE テーブル評価ループ、最大3回リトライ
- `init_cfg.json.j2:67,75,90,106-107`: DEVICE_RUNTIME_METADATA を参照するJinja条件式
