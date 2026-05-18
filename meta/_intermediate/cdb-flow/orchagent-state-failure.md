# orchagent-state Phase D — 失敗挙動 調査証跡

調査日: 2026-05-18
対象ページ: docs/reference/config-db/orchagent-state.md

## 調査ファイル

- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/fdborch.cpp`
- `sonic-swss/orchagent/vrforch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/main.cpp`
- `sonic-swss/orchagent/macsecorch.cpp`
- `sonic-swss/cfgmgr/vrfmgr.cpp`
- `sonic-swss-common/common/warm_restart.cpp`

## 主要根拠

### PORT_TABLE
- `portsorch.cpp:3127-3155`: `getPortSupportedSpeeds()` SAI 失敗時 `supported_speeds.clear()` → 空文字列が書かれる
- `portsorch.cpp:3279-3284`: `getPortSupportedFecModes()` 非サポート時 `return;` → `supported_fecs` フィールド未書き込み
- `portsorch.cpp:2181-2205`: `initHostTxReadyState()` — SAI set 失敗は `SWSS_LOG_ERROR` のみ

### FDB_TABLE
- `fdborch.cpp:711, 927`: `allPortsReady()` == false → 即 `return`、暗黙 retry
- `fdborch.cpp:479, 524`: SAI `create_fdb_entry` 失敗 → `it++`（retry 保留）
- `fdborch.cpp:680-701`: VLAN / ポート変換失敗 → `return false`

### VRF_OBJECT_TABLE
- `vrforch.cpp:99-104`: SAI `create_virtual_router` 失敗 → `hset()` 呼ばれない
- `vrforch.cpp:134-138`: `set_virtual_router_attribute` 失敗 → 同上
- `vrforch.cpp:115-118`: VNI マップ更新失敗 → `return false`（hset より前）
- `vrfmgr.cpp:208`: `isVrfObjExist()` が false → 削除を即時完了扱い

### WARM_RESTART_TABLE
- `orchdaemon.cpp:1193-1205`: `warmRestoreValidation()` — pending task あっても `state="restored"` は書かれる
- `orchdaemon.cpp:1204`: `WarmStart::setWarmStartState("orchagent", WarmStart::RESTORED)` は `ts.empty()` 関わらず実行

### FIPS_MACSEC_POST_TABLE
- `main.cpp:789-793`: MACsec 非サポート → `post_state="disabled"`
- `main.cpp:927-931`: POST capability クエリ失敗 → `post_state="disabled"` + `SWSS_LOG_ERROR`
- `macsecorch.cpp:710, 791`: POST コールバック FAIL → `post_state="fail"`
