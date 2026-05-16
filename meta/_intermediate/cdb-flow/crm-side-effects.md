# CRM 副次 DB 書込 分析 (Phase F)

ソース: `sonic-swss/orchagent/crmorch.cpp`, `sonic-swss-common/common/schema.h`

## CrmOrch (orchagent/crmorch.cpp)

CONFIG_DB の `CRM|Config` を直接購読し、SAI リソースカウンタをポーリングしながら副次 DB 書込を行う。
cfgmgr/orchmgr 中間層はなく、orchagent が直接 CONFIG_DB → COUNTERS_DB へ書き込む。

---

## 1. COUNTERS_DB 書込

### テーブル: `CRM` (定数 `COUNTERS_CRM_TABLE` = `"CRM"`)

書込タイミング: `polling_interval` 秒ごとのタイマーで `updateCrmCountersTable()` が呼ばれる。

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_countersCrmTable->set(key, [{crm_stats_*_used, N}])` | COUNTERS_DB / `CRM` | リソースキー (例: `"STATS"`, ACL OID 文字列) / `crm_stats_<resource>_used` | 各リソースの `usedCounter` を毎 poll 更新 (`crmorch.cpp:1082`) |
| `m_countersCrmTable->set(key, [{crm_stats_*_available, N}])` | COUNTERS_DB / `CRM` | 同上 / `crm_stats_<resource>_available` | 各リソースの `availableCounter` を毎 poll 更新 (`crmorch.cpp:1106`) |
| `m_countersCrmTable->del("STATS")` | COUNTERS_DB / `CRM` | `"STATS"` | orchagent 起動時 (コンストラクタ) に既存統計を一括消去 (`crmorch.cpp:414`) |
| `m_countersCrmTable->del(aclKey)` | COUNTERS_DB / `CRM` | ACL テーブル OID キー | ACL テーブル削除時 (`crmorch.cpp:616`) |
| `m_countersCrmTable->del(dashAclKey)` | COUNTERS_DB / `CRM` | DASH ACL グループキー | DASH ACL グループ追加/削除時 (`crmorch.cpp:730, 736`) |

`crm_stats_*` フィールド名は `crmUsedCntsTableMap` / `crmAvailCntsTableMap` で定義。例:

| フィールド名 | リソース |
|---|---|
| `crm_stats_ipv4_route_used` / `_available` | IPv4 ルート |
| `crm_stats_ipv6_route_used` / `_available` | IPv6 ルート |
| `crm_stats_ipv4_nexthop_used` / `_available` | IPv4 ネクストホップ |
| `crm_stats_acl_table_used` / `_available` | ACL テーブル |
| `crm_stats_fdb_entry_used` / `_available` | FDB エントリ |
| `crm_stats_dash_eni_used` / `_available` | DASH ENI (DPU のみ) |
| … (全 40+ リソース) | |

---

## 2. syslog アラート書込 (THRESHOLD_EXCEEDED / THRESHOLD_CLEAR)

STATE_DB への書込はない。アラートは `SWSS_LOG_WARN` (syslog WARN レベル) として出力される。
加えて `event_publish(g_events_handle, "chk_crm_threshold", &params)` で SONiC Event フレームワーク経由の発行も行う。

| 書込先 | 内容 | 条件 |
|--------|------|------|
| syslog (WARN) | `"<resource> THRESHOLD_EXCEEDED for <type> <N>%% Used count <U> free count <F>"` | `utilization >= highThreshold` かつ `exceededLogCounter < 10` (`crmorch.cpp:1175`) |
| syslog (WARN) | `"<resource> THRESHOLD_CLEAR for <type> <N>%% Used count <U> free count <F>"` | `utilization <= lowThreshold` かつ `exceededLogCounter > 0` (`crmorch.cpp:1183`) |
| Event (`chk_crm_threshold`) | `{percent, used_cnt, free_cnt}` | THRESHOLD_EXCEEDED 時のみ (`crmorch.cpp:1178`) |

`exceededLogCounter` が 10 (`CRM_EXCEEDED_MSG_MAX`) 以上になると syslog を停止。`threshold_type` フィールド変更時にリセット。

---

## 3. STATE_DB 書込

CrmOrch 単体では STATE_DB への書込を行わない。

---

## 4. LOGLEVEL / SWSS_LOG 書込

特別な LOGLEVEL テーブル書込はない。`SWSS_LOG_WARN` / `SWSS_LOG_NOTICE` / `SWSS_LOG_ERROR` は orchagent プロセスの標準 syslog ハンドラ経由で出力される。

---

## COUNTERS_DB スキーマまとめ

| 定数 | 実テーブル名 | 定義箇所 |
|---|---|---|
| `COUNTERS_CRM_TABLE` | `"CRM"` | `sonic-swss-common/common/schema.h:237` |
| `CRM_COUNTERS_TABLE_KEY` | `"STATS"` | `sonic-swss/orchagent/crmorch.cpp:10` |

確認コマンド:
```bash
sonic-db-cli COUNTERS_DB hgetall 'CRM|STATS'
sonic-db-cli COUNTERS_DB hgetall 'CRM|ACL_STATS:INGRESS:PORT'
crm show resources all
```
