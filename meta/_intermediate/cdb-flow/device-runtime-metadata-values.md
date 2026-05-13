# DEVICE_RUNTIME_METADATA フィールド値分析

## サブキー依存挙動

### `ETHERNET_PORTS_PRESENT` (True/False)
- `True` → port_config.ini が存在。`has_per_asic_scope` を True に設定可能
- `False` → port_config.ini なし（supervisor 等）。init_cfg.json.j2 が `has_per_asic_scope = "False"` を生成

### `CHASSIS_METADATA.module_type` (supervisor/linecard)
- `supervisor` → init_cfg.json.j2 の条件式で per-asic インスタンスを False に設定（Jinja 条件分岐）
- `linecard` → per-asic インスタンス有効
- このキー自体が存在しない（非 chassis 箱）→ `CHASSIS_METADATA not in DEVICE_RUNTIME_METADATA` で linecard 相当として扱われる

### `MACSEC_SUPPORTED` (True/False)
- `True` → プラットフォーム JSON で MACsec 宣言あり。MACsec 関連の FEATURE エントリが init_cfg に含まれる
- `False` / 未設定 → MACsec FEATURE エントリは生成されない

## cross-cutting
- このテーブルは CONFIG_DB に永続化されない（sonic-cfggen のメモリ上のみ）
- YANG スキーマなし。手動で config_db.json に書いても無視される
- enum なし。値は Python bool 文字列 "True"/"False" または module_type 文字列
