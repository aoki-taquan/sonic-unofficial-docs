# DPU — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-17 (Task F Phase F / cdb_q67_f_dpu3)

## 調査対象

`docs/reference/config-db/dpu.md` の CONFIG_DB `DPU` テーブル変更時に、各購読者が APPL_DB / STATE_DB / COUNTERS_DB / その他副次 DB へ何らかの書き込みを行うか。

## 走査範囲

- `.cache/sonic-sources/sonic-swss/orchagent/dash/dashenifwdorch.cpp` (orchagent 購読者)
- `.cache/sonic-sources/sonic-swss/orchagent/dash/dashenifwdorch.h`
- `.cache/sonic-sources/sonic-host-services/scripts/caclmgrd` (caclmgrd 購読者)
- `.cache/sonic-sources/sonic-gnmi/pkg/interceptors/dpuproxy/resolver.go` (gnmi proxy)

---

## 走査結果

### 1. dashenifwdorch — DPU テーブルの購読方式

```bash
grep -n "DashEniFwdOrch\|APP_DASH_ENI_FORWARD" \
  .cache/sonic-sources/sonic-swss/orchagent/orchdaemon.cpp
```

- `orchdaemon.cpp:615`: `DashEniFwdOrch(m_configDb, m_applDb, APP_DASH_ENI_FORWARD_TABLE, gNeighOrch)`
  - `DashEniFwdOrch` が Orch2 として購読するのは **APPL_DB の `APP_DASH_ENI_FORWARD_TABLE`** であり、CONFIG_DB `DPU` テーブルではない
  - `DPU` テーブルは起動時の `lazyInit() → populateDpuRegistry() → DpuRegistry::populate()` で **一括読み取り**されるのみ。実行時の SET/DEL イベントは受け取らない

### 2. dashenifwdorch — APPL_DB / STATE_DB 書込スキャン

```bash
grep -n "ProducerStateTable\|StateTable\|NotificationProducer\|STATE_DB\|statedb" \
  .cache/sonic-sources/sonic-swss/orchagent/dash/dashenifwdorch.cpp
```

結果 (主要なもの):
- `L403-405`: `rule_table_`（`APP_ACL_RULE_TABLE_NAME`）/ `acl_table_type_` / `acl_table_` の `ProducerStateTable` を APPL_DB に作成
  - これらの書込は ENI SET/DEL イベント（`addOperation` / `delOperation` / `createAclRule`）によって発火するものであり、`DPU` テーブルの SET/DEL には直接連動しない

**結論**: CONFIG_DB `DPU` テーブルの変更に伴う `dashenifwdorch` からの APPL_DB / STATE_DB 書込は **存在しない**（DPU テーブルは init 時に static に読まれるのみ）。

### 3. caclmgrd — `update_dash_ha_rules()` iptables 副作用

```bash
grep -n "update_dash_ha_rules\|add_dash_ha_rules\|remove_dash_ha_rules\|make_dash_ha_rules" \
  .cache/sonic-sources/sonic-host-services/scripts/caclmgrd
```

- `caclmgrd:1163-1164`: `subscribe_dpu_table = swsscommon.SubscriberStateTable(config_db_connector, "DPU")`
  - リアルタイムで CONFIG_DB `DPU` テーブルを購読
- `caclmgrd:1262`: `key, op, fvs = subscribe_dpu_table.pop()` → `update_dash_ha_rules(namespace, key, op, fvs)` (`caclmgrd:1082-1110`)

SET イベント時の `update_dash_ha_rules()` 処理:
1. `swbus_port` フィールドを取得
2. 旧ポートがあれば `remove_dash_ha_rules(namespace, old_port)`:
   - `iptables -D INPUT -p tcp --dport <old_port> -j ACCEPT`
   - `ip6tables -D INPUT -p tcp --dport <old_port> -j ACCEPT`
3. 新ポートで `add_dash_ha_rules(namespace, new_port)`:
   - `iptables -I INPUT 2 -p tcp --dport <new_port> -j ACCEPT`
   - `ip6tables -I INPUT 2 -p tcp --dport <new_port> -j ACCEPT`
4. `self.dashHaPortMap[key] = new_port` (プロセス内メモリのみ; DB 書込なし)

DEL イベント時:
1. `remove_dash_ha_rules(namespace, port)` でルール削除
2. `self.dashHaPortMap.pop(key)` (メモリ削除のみ)

**結論**: caclmgrd の副作用は **Linux カーネルの iptables/ip6tables ルール操作** のみ。APPL_DB / STATE_DB / COUNTERS_DB への書込は一切なし。

```bash
grep -n -E "STATE_DB|APPL_DB|COUNTERS_DB|swsscommon\.Table\|ProducerStateTable" \
  .cache/sonic-sources/sonic-host-services/scripts/caclmgrd | grep -v "#\|DPU_TABLE\|config_db"
```

関連行なし（DB 書込は `FipsCfg` / `RestartWaiter` 限定; `CaclMgr` 本体の ACL/DPU 処理は DB 書込を行わない）。

### 4. sonic-gnmi dpuproxy — 読み取りのみ

```bash
cat .cache/sonic-sources/sonic-gnmi/pkg/interceptors/dpuproxy/resolver.go
```

- `GetDPUInfo()`: `stateClient.HGetAll()` (STATE_DB) / `configClient.HGetAll()` (CONFIG_DB) を読み取るのみ
- 書込 API (`HSet`/`Set` など) の呼出なし

**結論**: sonic-gnmi dpuproxy は CONFIG_DB `DPU` テーブルの参照専用で副次 DB 書込を行わない。

---

## 結論まとめ

| 購読者 | DB 書込 | 副作用の内容 |
|--------|---------|-------------|
| `orchagent` (`DashEniFwdOrch`) | なし | DPU テーブルは起動時 `populateDpuRegistry()` の static 読み込みのみ。実行時 SET/DEL は受け取らない |
| `caclmgrd` | なし | `swbus_port` SET/DEL に応じて `iptables`/`ip6tables` INPUT ルールをカーネルに追加・削除。Redis DB への書込は皆無 |
| `sonic-gnmi` DPU proxy | なし | CONFIG_DB / STATE_DB の読み取り専用 |

CONFIG_DB `DPU` テーブルの変更に伴う **APPL_DB / STATE_DB / COUNTERS_DB へのレコード書込は存在しない**。

唯一の実行時副作用は `caclmgrd` による **Linux iptables/ip6tables ルールのリアルタイム反映** (`swbus_port` フィールド変化に連動)。
