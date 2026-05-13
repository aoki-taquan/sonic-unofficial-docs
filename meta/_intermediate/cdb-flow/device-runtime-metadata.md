# DEVICE_RUNTIME_METADATA — 例外条件分析

## consumer 一覧

| consumer | 用途 | ソースパス |
|---|---|---|
| sonic-py-common / device_info.py | get_device_runtime_metadata() でランタイム情報を収集・返却 | sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py:735-747 |
| init_cfg.json.j2 | Feature の初期 state / scope を DEVICE_RUNTIME_METADATA から動的決定 | sonic-buildimage/files/build_templates/init_cfg.json.j2:67,75,90,106,107 |

## 例外条件

### ETHERNET_PORTS_PRESENT が False の場合
- init_cfg.json.j2:67 — `ETHERNET_PORTS_PRESENT` が False の場合、bgp feature の初期 state を `disabled` に設定。ポートが存在しない (supervisor linecard 等) システムでは BGP が無効化される。
- init_cfg.json.j2:75 — `teamd` feature も同様に `ETHERNET_PORTS_PRESENT=False` で `disabled` にフォールバック。

### CHASSIS_METADATA が存在する場合の role 判定
- init_cfg.json.j2:67 — `CHASSIS_METADATA` が存在しかつ `module_type` が `supervisor` の場合、bgp feature を `disabled` に設定。
- init_cfg.json.j2:106-107 — `has_global_scope` と `has_per_asic_scope` は CHASSIS_METADATA の `module_type` を参照して動的に決定。linecard では `has_global_scope=False`。supervisor では `has_per_asic_scope=False`。

### MACSEC_SUPPORTED が False の場合
- init_cfg.json.j2:90 — device type が SpineRouter 系であっても `MACSEC_SUPPORTED=False` の場合、macsec feature は `disabled` のまま。get_device_runtime_metadata() が `is_macsec_supported()` を確認し、platform_env.conf の `macsec_enabled` フラグを参照する。フラグ不在または 0 の場合は False を返す。
