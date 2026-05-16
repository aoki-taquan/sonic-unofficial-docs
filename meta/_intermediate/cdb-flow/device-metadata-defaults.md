# device-metadata Phase A: 暗黙デフォルト・fallback 調査 (2026-05-14 追記)

## Phase A 新規発見サマリ

| # | フィールド | 発見種別 | 詳細 |
|---|-----------|---------|------|
| D1 | `docker_routing_config_mode` | YANG-実装 discrepancy | YANG default `"unified"` に対し minigraph/frrcfgd は `"separated"` を実効デフォルトとして使用 |
| D2 | `synchronous_mode` | silent coerce | `swss_vars.j2:9` で非`"disable"` 全部 `"enable"` 扱い (typo/不正値でも警告なし) |
| D3 | `synchronous_mode` (dpu) | dead consumer | `switch_type=="dpu"` のとき orchagent.sh が ZMQ モード強制、`synchronous_mode` 完全無視 |
| D4 | `suppress-fib-pending` | 経路依存乖離 | YANG default `disabled`、LeafRouter では minigraph が `enabled` を自動書き込み |
| D5 | `switch_type` | ハードコード fallback | YANG 説明のみ `npu`、DB 未設定 = npu 動作だが明示なし |
| D6 | `dhcp_server` | 経路依存乖離 | BmcMgmtToRRouter のみ minigraph が `enabled` を書き込む |
| D7 | `orch_northbond_dash_zmq_enabled` | dead consumer 可能性 | YANG default `true` だがコード側直接参照未確認 |
| D8 | `storage_device` | silent drop | キー不在 = false として存在チェックで評価 |

---

# device-metadata Phase A: LSP trace 証跡

## 訪問した file × function 一覧

| ファイル | 参照方法 | 確認内容 |
|---------|---------|---------|
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | 全行読書 | `bgp_asn`, `suppress-fib-pending`, `bgp_router_id`, `type`, `deployment_id` の fallback 確認 |
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py` | 全行読書 | `DEVICE_METADATA` テーブル読み取り; `type`/`subtype` 条件分岐で AsPathMgr 登録 |
| `sonic-host-services/scripts/hostcfgd` | 全行読書 + grep | `hostname`/`timezone`/`syslog_with_osversion` の get fallback 確認 |
| `sonic-buildimage/dockers/docker-orchagent/orchagent.sh` | 全行読書 | `switch_type`, `synchronous_mode`, `async_swss_rec`, `ring_thread_enabled`, `subtype` |
| `sonic-buildimage/dockers/docker-orchagent/buffermgrd.sh` | 全行読書 | `buffer_model` fallback: 非 dynamic → static pg_profile_lookup.ini |
| `sonic-buildimage/dockers/docker-orchagent/switch.json.j2` | 全行読書 | `type` → `hash_seed` / `ordered_ecmp` 分岐; `switch_type` 分岐 |
| `sonic-buildimage/dockers/docker-orchagent/orch_zmq_tables.conf.j2` | 全行読書 | `orch_northbond_dash_zmq_enabled` (!= "false") / `orch_northbond_route_zmq_enabled` (== "true") |
| `sonic-buildimage/files/build_templates/swss_vars.j2` | 全行読書 | `synchronous_mode` Jinja fallback: disable 以外は "enable" |
| `sonic-buildimage/dockers/docker-fpm-frr/frr/frr_vars.j2` | 全行読書 | `frr_mgmt_framework_config` / `docker_routing_config_mode` キーが無い場合 "" |
| `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2` | 全行読書 (前140行) | `bgp_adv_lo_prefix_as_128` / `bgp_router_id` / `type` 分岐 |
| `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/general/instance.conf.j2` | 全行読書 | `default_bgp_status`: field 無い場合は shutdown なし (= up 扱い) |
| `sonic-buildimage/dockers/docker-fpm-frr/frr/zebra/zebra.conf.j2` | 全行読書 | `zebra_nexthop` / `nexthop_group` 分岐: フィールド無し → 両方 enabled |
| `sonic-swss/orchagent/flexcounterorch.cpp` | 部分読書 L105-138 | `create_only_config_db_buffers`: field 無し → `m_createOnlyConfigDbBuffers = false` (C++ default) |
| `sonic-swss/orchagent/flexcounterorch.h` | grep | `m_createOnlyConfigDbBuffers = false` |
| `sonic-utilities/config/main.py` | grep + 部分読書 | `default_pfcwd_status`: `config reload` で内部 default `enable` (type が MgmtToRRouter 等でなければ) |

## LSP workspaceSymbol で確認した consumer 数

entry point grep で特定したファイル: 155+ ファイル (tests 含む)
production consumer (非テスト):
- sonic-bgpcfgd: 8 ファイル
- sonic-swss cfgmgr: 8 ファイル
- sonic-host-services: 2 ファイル (featured, hostcfgd)
- sonic-buildimage dockers: 30+ J2/sh ファイル
- sonic-utilities: 3 ファイル

完全読書した関数数: 18 関数・スクリプト区間

## 各 field の dataflow chain

### `synchronous_mode`
```
CONFIG_DB DEVICE_METADATA|localhost.synchronous_mode
  → swss_vars.j2:9 (Jinja): if != "disable" → "enable"  (コード fallback: 非 disable 全部 enable)
  → orchagent.sh:37-41: SYNC_MODE; if enable → -s フラグ
```

### `buffer_model`
```
CONFIG_DB DEVICE_METADATA|localhost.buffer_model
  → buffermgrd.sh:3 hget buffer_model
  → if == "dynamic" → buffermgrd -a asic_table.json
  → else (非 dynamic / 未設定) → buffermgrd -l pg_profile_lookup.ini  (コード fallback: static モード)
```

### `bgp_adv_lo_prefix_as_128`
```
CONFIG_DB DEVICE_METADATA|localhost.bgp_adv_lo_prefix_as_128
  → bgpd.main.conf.j2:32-37 (J2 prefix-list)
  → bgpd.main.conf.j2:165-173 (J2 BGP address-family)
  → field 無い / != "true" → /64 広告  (コード fallback: /64)
```

### `default_bgp_status`
```
CONFIG_DB DEVICE_METADATA|localhost.default_bgp_status
  → general/instance.conf.j2:13 (J2)
  → 'default_bgp_status' NOT IN dict または != 'down' → neighbor shutdown なし (= up 扱い)
  (コード fallback: "up")
```

### `create_only_config_db_buffers`
```
CONFIG_DB DEVICE_METADATA|localhost.create_only_config_db_buffers
  → flexcounterorch.cpp:114 hget; field 無い場合 hget returns false → m_createOnlyConfigDbBuffers 初期値 false
  (コード fallback: false)
```

### `orch_northbond_dash_zmq_enabled`
```
CONFIG_DB DEVICE_METADATA|localhost.orch_northbond_dash_zmq_enabled
  → orch_zmq_tables.conf.j2:1: != "false" → DASH テーブル群を ZMQ 経由で受信
  (コード fallback: YANG default true → != "false" → テーブル有効)
```

### `orch_northbond_route_zmq_enabled`
```
CONFIG_DB DEVICE_METADATA|localhost.orch_northbond_route_zmq_enabled
  → orch_zmq_tables.conf.j2:27: == "true" → ROUTE_TABLE ZMQ 受信
  (コード fallback: field 無い → != "true" → テーブル無効)
```

### `frr_mgmt_framework_config`
```
CONFIG_DB DEVICE_METADATA|localhost.frr_mgmt_framework_config
  → frr_vars.j2:3-7: field なければ "" (空文字)
  → frrcfgd.py で "" / "false" → bgpcfgd がテンプレ展開担当 (= YANG default false と一致)
```

### `docker_routing_config_mode`
```
CONFIG_DB DEVICE_METADATA|localhost.docker_routing_config_mode
  → frr_vars.j2:8-13: field なければ ""
  → frrcfgd.py:2170 else 節: "" → "separated" として扱う (コード fallback: "separated")
```

### `timezone`
```
CONFIG_DB DEVICE_METADATA|localhost.timezone
  → hostcfgd:1500: dev_meta.get('localhost', {}).get('timezone')  → None
  → apply_timezone_if_needed: if new_tz is None → return (timedatectl 呼び出しなし)
  → YANG default: "UTC" (システムは起動時に timedatectl で別途設定済みのため問題なし)
```

### `hostname`
```
CONFIG_DB DEVICE_METADATA|localhost.hostname
  → hostcfgd:1496: dev_meta.get('localhost', {}).get('hostname', '')  → ""
  → hostname_update: if not new_hostname → return (エラーログのみ)
  → 実質: 未設定時は hostname-config サービス再起動なし (空文字は許可されない)
```

### `syslog_with_osversion`
```
CONFIG_DB DEVICE_METADATA|localhost.syslog_with_osversion
  → hostcfgd:1502: .get('syslog_with_osversion')  → None
  → rsyslog_config(): if None → return (rsyslog-config restart なし)
  → rsyslog-config.sh:28-30: 空の場合 → "false"  (コード fallback: false)
```

### `bgp_router_id`
```
CONFIG_DB DEVICE_METADATA|localhost.bgp_router_id
  → bgpd.main.conf.j2:142-152: 'bgp_router_id' not in dict → Loopback0 or Loopback4096 の IPv4 を使用
  → managers_bgp.py:186-188: bgp_router_id not configured かつ lo_ipv4 is None → peer 追加を待機
```

### `ring_thread_enabled`
```
CONFIG_DB DEVICE_METADATA|localhost.ring_thread_enabled
  → orchagent.sh:121-123: hget; if == "true" → -R フラグ
  → else / 未設定 → -R なし  (コード fallback: false)
```

### `mac`
```
CONFIG_DB DEVICE_METADATA|localhost.mac
  → orchagent.sh:12-15: SWSS_VARS の mac; if "None" or empty → eth0 の MAC を fallback
  (コード fallback: eth0 の MAC アドレス)
```

### `switch_type` (未設定時)
```
CONFIG_DB DEVICE_METADATA|localhost.switch_type
  → orchagent.sh:22-33: hget; if x"" (空) → else 節 → -b 1024
  → swss_vars.j2:15: "{{ DEVICE_METADATA.localhost.switch_type }}" → "" (空文字列出力)
  → switch.json.j2:35: if not switch_type or switch_type != "dpu" → ecmp_hash_seed 等を設定
  (コード fallback: npu 扱い; YANG でも npu が実質 default)
```

## 検出した fallback パターン総数: 15 件

| # | field | パターン種別 | コード fallback | evidence |
|---|---|---|---|---|
| 1 | `synchronous_mode` | Jinja else | "enable" | swss_vars.j2:9 |
| 2 | `buffer_model` | sh else | static (pg_profile_lookup.ini) | buffermgrd.sh:13-15 |
| 3 | `bgp_adv_lo_prefix_as_128` | Jinja else | /64 広告 | bgpd.main.conf.j2:168 |
| 4 | `default_bgp_status` | Jinja absent check | up (shutdown なし) | instance.conf.j2:13 |
| 5 | `create_only_config_db_buffers` | C++ member default | false | flexcounterorch.h:86 |
| 6 | `orch_northbond_dash_zmq_enabled` | Jinja != "false" | enabled (DASH ZMQ 有効) | orch_zmq_tables.conf.j2:1 |
| 7 | `orch_northbond_route_zmq_enabled` | Jinja == "true" | disabled (ROUTE ZMQ 無効) | orch_zmq_tables.conf.j2:27 |
| 8 | `frr_mgmt_framework_config` | Jinja absent | "" → bgpcfgd 担当 | frr_vars.j2:3-7 |
| 9 | `docker_routing_config_mode` | Jinja absent | "" → "separated" 扱い | frr_vars.j2:8-13; frrcfgd.py:2170 |
| 10 | `timezone` | Python .get() | None → timedatectl 呼ばず | hostcfgd:1500 |
| 11 | `hostname` | Python .get('', '') | "" → hostname-config restart なし | hostcfgd:1496 |
| 12 | `syslog_with_osversion` | sh fallback | "" → "false" | rsyslog-config.sh:28-30 |
| 13 | `bgp_router_id` | Jinja absent | Loopback0/4096 IPv4 を使用 | bgpd.main.conf.j2:144,151 |
| 14 | `ring_thread_enabled` | sh absent | false (-R なし) | orchagent.sh:122 |
| 15 | `mac` | sh absent/None | eth0 MAC | orchagent.sh:13-15 |
