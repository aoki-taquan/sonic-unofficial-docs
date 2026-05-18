# SYSTEM_DEFAULTS ハードコード定数調査メモ (Phase E)

ソース調査対象:
- `sonic-buildimage/files/build_templates/swss_vars.j2` (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-buildimage/src/sonic-config-engine/config_samples.py` (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-buildimage/dockers/docker-fpm-frr/frr/supervisord/supervisord.conf.j2` (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-swss/orchagent/muxorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/aclorch.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-defaults.yang` (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)

## 検出した定数

### YANG 制約定数

- `name` leaf: length 1..32 (`sonic-system-defaults.yang` L27-29)
- `status` leaf: `admin_mode` typedef = enum { `enabled`, `disabled` } のみ (`sonic-types.yang` L113-118)

### swss_vars.j2 内の文字列リテラル

- `"dscp_remapping"`: `swss_vars.j2` L14。`tunnel_qos_remap.status == "enabled"` のとき `"enable"`、それ以外 `"disable"` (note: `enable`/`disable` であり YANG の `enabled`/`disabled` とスペルが異なる)

### config_samples.py 内の文字列リテラル

- `"polaris"`: 鍵名 — Pensando hwsku (`'pensando' in hwsku.lower()`) のみ (`config_samples.py:181`)
- `"software_bfd"`: 鍵名 — SmartSwitch DPU プロファイルで強制注入 (`config_samples.py:186`)
- `"enabled"`: 注入時の固定値 (`config_samples.py:182, 187`)

### supervisord.conf.j2 内の文字列リテラル

- `/usr/local/bin/bfdmon`: `software_bfd.status == "enabled"` のときに起動するバイナリパス (`supervisord.conf.j2:215`)

### muxorch.cpp 内の文字列リテラル

- `"mux_tunnel_egress_acl"`: hget キー名 (`muxorch.cpp:1389`)
- `"enabled"`: 比較値 — `value != "enabled"` で `is_ingress_acl_` を決定 (`muxorch.cpp:1390`)
- `INGRESS_TABLE_DROP` = `"IngressTableDrop"`: `mux_tunnel_egress_acl` が `enabled` 以外のとき使用する ACL テーブル名 (`aclorch.h:111`, `muxorch.cpp:48,1393`)
- `EGRESS_TABLE_DROP` = `"EgressTableDrop"`: `mux_tunnel_egress_acl` が `enabled` のとき使用する ACL テーブル名 (`aclorch.h:112`, `muxorch.cpp:1393`)

### bgpcfgd/main.py 内の文字列リテラル

- `'software_bfd'`: hget キー名 (`main.py:118`)
- `'status'`: フィールド名 (`main.py:118`)
- `'enabled'`: 比較値 (`main.py:118`)

## まとめ

SYSTEM_DEFAULTS は CONFIG_DB / YANG の値をそのまま渡すシンプルなテーブルで、YANG 側の制約 (name長 1-32, status = enabled/disabled) と、参照側コードの文字列リテラル (mux_tunnel_egress_acl, software_bfd, polaris, IngressTableDrop 等) がハードコード定数の主体。
