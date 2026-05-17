# CONFIG_DB `DPU` テーブル — Phase G: 通信メカニズム スキャンノート

対象テーブル: `DPU`
スキャン範囲:
- `sonic-host-services/scripts/caclmgrd`（全体）
- `sonic-swss/orchagent/dash/dashenifwdorch.cpp`（DpuRegistry::populate 周辺）
- `sonic-swss/orchagent/orchdaemon.cpp`（DashEniFwdOrch 初期化箇所）
- `sonic-swss/orchagent/main.cpp`（switch_type / SmartSwitch 分岐）

---

## 購読構造の全体像

### 1. CONFIG_DB `DPU` → caclmgrd (`subscribe_dpu_table`)

- **購読方式**: `swsscommon.SubscriberStateTable(config_db_connector, "DPU")`
  (`caclmgrd:1163`)
- **Selectable 登録**: `sel.addSelectable(subscribe_dpu_table)` (`caclmgrd:1164`)
- **SELECT タイムアウト**: `SELECT_TIMEOUT_MS = 1000` ms (`caclmgrd:1114`)
- **Producer**: 起動時 `sonic-cfggen` / runtime は gNMI 経由 NC
- **Consumer**: `caclmgrd` メインループ (`caclmgrd:1262`)
  ```python
  key, op, fvs = subscribe_dpu_table.pop()
  if "dash-ha" in self.feature_present:
      self.update_dash_ha_rules(namespace, key, op, fvs)
  ```
- **ガード条件**: `FEATURE` テーブルに `"dash-ha"` が存在する場合のみ `update_dash_ha_rules` を実行。
  存在しない場合はポップするが何もしない (`caclmgrd:1265`)
- **`dashHaPortMap`**: `caclmgrd:130` にクラス変数として定義。`key`（DPU 名）→ `swbus_port` を保持し
  iptables ルールの差分管理に使用。

### 2. CONFIG_DB `DPU` → orchagent (`DpuRegistry` — 一括読み取り)

- **購読方式**: `swsscommon.Table`（keyspace 通知なし・一回読み）
  (`dashenifwdorch.cpp:225` `Table dpuTable(cfg_db, "DPU")`)
- **呼び出しタイミング**: `lazyInit()` → `ctx->populateDpuRegistry()` → `DpuRegistry::populate()`
  （最初の `addOperation` 呼び出し時に一度だけ実行）
- **Producer**: 起動時 `sonic-cfggen` が CONFIG_DB に書き込み済みであることを前提
- **Consumer**: `DashEniFwdOrch` / `DpuRegistry` — 内部ヒープ `dpus_name_map_` に格納
- **RT 変更の非対応**: orchagent は `SubscriberStateTable` を使用しないため、
  起動後の `DPU` SET/DEL イベントは orchagent に伝播しない。反映には `swss` コンテナ再起動が必要。
- **ガード条件**: `gMySwitchSubType == "SmartSwitch"` のときのみ `DashEniFwdOrch` が初期化される
  (`orchdaemon.cpp:613-617`)。

---

## データフロー概略

```
CONFIG_DB[DPU|<dpu_name>]  (SET: state, pa_ipv4, swbus_port, ...)
  │
  ├─→ SubscriberStateTable  (caclmgrd, SELECT_TIMEOUT=1000ms)
  │       pop() → key, op, fvs
  │       guard: "dash-ha" in feature_present
  │       update_dash_ha_rules(namespace, key, op, fvs)
  │         SET:  swbus_port → iptables INPUT +2 ACCEPT (IPv4+IPv6)
  │         DEL:  swbus_port → iptables DELETE
  │         UPDATE: old_port DELETE → new_port INSERT
  │
  └─→ Table (one-shot read, orchagent DpuRegistry::populate)
          DpuRegistry::processDpuTable()
            state == "down" → skip
            state == "active" → register { type=LOCAL, pa_v4 } in dpus_name_map_
          ※ 起動時のみ。RT 変更は orchagent に届かない
```

---

## 証跡ファイル

| 証跡 | 内容 |
|------|------|
| `caclmgrd:90` | `DPU_TABLE = "DPU"` 定数定義 |
| `caclmgrd:130` | `dashHaPortMap = {}` クラス変数 |
| `caclmgrd:1114` | `SELECT_TIMEOUT_MS = 1000` |
| `caclmgrd:1163-1164` | `SubscriberStateTable` 生成・登録 |
| `caclmgrd:1262-1266` | メインループでの `pop()` と `dash-ha` ガード |
| `caclmgrd:1082-1109` | `update_dash_ha_rules()` — SET/DEL/UPDATE 処理 |
| `caclmgrd:280-284` | `update_feature_present()` — FEATURE テーブル読み取り |
| `dashenifwdorch.cpp:212-264` | `DpuRegistry::populate()` / `processDpuTable()` |
| `dashenifwdorch.cpp:225` | `Table dpuTable(cfg_db, "DPU")` — one-shot 読み取り |
| `orchdaemon.cpp:613-618` | SmartSwitch 分岐で `DashEniFwdOrch` 生成 |
