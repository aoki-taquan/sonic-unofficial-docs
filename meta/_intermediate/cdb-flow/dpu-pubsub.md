# DPU — Phase G: 通信メカニズム (pub/sub) 調査メモ

生成日: 2026-05-17 (Task F Phase G / cdb_q67_f_dpu3)

対象: `docs/reference/config-db/dpu.md` — CONFIG_DB `DPU` テーブルへの subscribe 経路を網羅する。

---

## 調査対象ファイル

- `sonic-host-services/scripts/caclmgrd`
- `sonic-swss/orchagent/dash/dashenifwdorch.cpp` / `.h`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-gnmi/pkg/interceptors/dpuproxy/resolver.go`

---

## 1. caclmgrd — `SubscriberStateTable` (Python / swsscommon)

```bash
grep -n "subscribe_dpu_table\|SubscriberStateTable.*DPU" \
  .cache/sonic-sources/sonic-host-services/scripts/caclmgrd
```

- `caclmgrd:1163`: `subscribe_dpu_table = swsscommon.SubscriberStateTable(config_db_connector, self.DPU_TABLE)`
  - `DPU_TABLE = "DPU"` (`caclmgrd:90`)
- `caclmgrd:1164`: `sel.addSelectable(subscribe_dpu_table)`
  - `swsscommon.Select` に登録し、メインループで `sel.select()` を 1 秒タイムアウトでポーリング

```python
# caclmgrd:1262-1267
while True:
    key, op, fvs = subscribe_dpu_table.pop()
    if not key:
        break
    if "dash-ha" in self.feature_present:
        self.update_dash_ha_rules(namespace, key, op, fvs)
```

**subscribe の仕組み**:
- `SubscriberStateTable` は内部で Redis keyspace notification を使用
  (`__keyspace@<db>__:DPU|*` の psubscribe に相当)
- `op` は `SET` / `DEL` のみ。フィールド単位のイベントではなくキー単位
- `fvs` は通知発生時点でのフィールド・バリューリスト (keyspace 通知時に HGETALL して取得)

**条件付き実行**:
- `"dash-ha" in self.feature_present` が True の場合のみ `update_dash_ha_rules()` を呼ぶ
  - `feature_present` は `/etc/sonic/features.json` から `update_feature_present()` で取得 (`caclmgrd:280-284`)
  - dash-ha feature が無効の環境では DPU イベントを受け取っても何もしない

**コールバックシグネチャ**:
- `update_dash_ha_rules(namespace, key, op, data)` — `key` は DPU エントリ名 (例: `dpu0`)、`op` は `SET`/`DEL`、`data` はフィールドリスト

**source**: `sonic-host-services/scripts/caclmgrd:1163-1164, 1262-1267, 1082-1110`

---

## 2. orchagent (DashEniFwdOrch) — 起動時 bulk read (SubscriberStateTable 非使用)

```bash
grep -n "Table dpuTable\|SubscriberStateTable.*DPU\|DPU.*SubscriberStateTable" \
  .cache/sonic-sources/sonic-swss/orchagent/dash/dashenifwdorch.cpp
```

- `dashenifwdorch.cpp:225`: `Table dpuTable(cfg_db, DashEniFwd::DPU_TABLE);`
  - `swss::Table` (HGETALL 相当) → subscribe 型 API ではない
  - `DpuRegistry::populate()` で起動時に一括読み取りするだけ

```bash
# orchdaemon.cpp:615
DashEniFwdOrch *dash_eni_fwd_orch = new DashEniFwdOrch(m_configDb, m_applDb, APP_DASH_ENI_FORWARD_TABLE, gNeighOrch);
```

- `DashEniFwdOrch` が Orch2 として購読するのは `APP_DASH_ENI_FORWARD_TABLE` (APPL_DB) であり、CONFIG_DB `DPU` テーブルではない
- `DPU` テーブルへの runtime subscribe は存在しない。実行時 SET/DEL イベントは orchagent に届かない。

---

## 3. sonic-gnmi dpuproxy — 読み取り専用 (subscribe なし)

`resolver.go` の `GetDPUInfo()` は gRPC リクエストの都度 `configClient.HGetAll()` を呼ぶ点呼型アクセス。
keyspace subscribe / channel subscribe は使用していない。

---

## 結論

| # | コンシューマ | subscribe API | 購読テーブル | 条件 |
|---|------------|--------------|------------|------|
| 1 | `caclmgrd` | `SubscriberStateTable` (Python swsscommon) | CONFIG_DB `DPU` | `"dash-ha"` feature 有効時のみ `update_dash_ha_rules()` を実行 |
| 2 | `DashEniFwdOrch` (orchagent) | なし (起動時 HGETALL のみ) | — | subscribe 不使用; 再起動後の変更は反映されない |
| 3 | sonic-gnmi dpuproxy | なし (都度 HGETALL) | — | subscribe 不使用 |

CONFIG_DB `DPU` テーブルへの **runtime subscribe は `caclmgrd` の `SubscriberStateTable` が唯一**。
他 2 コンシューマは subscribe を行わない。
