# counters-portchannel Phase C 調査証跡

## 対象ページ
`docs/reference/config-db/counters-portchannel.md`

## 調査ソース

- `sonic-swss/orchagent/portsorch.cpp` (master)
- `sonic-swss/orchagent/intfsorch.cpp` (master)
- `sonic-swss-common/common/schema.h`

## 発見した暗黙参照

### 1. gPortsOrch (APP_DB PORT / LAG テーブル経由)

`intfsorch.cpp:665` で `doTask()` 冒頭に `gPortsOrch->allPortsReady()` を呼び出す。
false の場合は即 return。PORTCHANNEL_INTERFACE 処理がブロックされる。
また `intfsorch.cpp:905` で `gPortsOrch->getPort(alias, port)` を呼び、
portsorch の `m_portList` に LAG エントリが存在しないと失敗して retry。

### 2. ASIC_DB VIDTORID

`intfsorch.cpp:68`: `m_asic_db = DBConnector("ASIC_DB")`
`intfsorch.cpp:75`: `m_vidToRidTable = Table(m_asic_db, "VIDTORID")`（gTraditionalFlexCounter 時のみ）
`intfsorch.cpp:1627`: タイマーループで `m_vidToRidTable->hget("", id, value)` が成功するまで
  addRifToFlexCounter を呼ばない。VID→RID マッピング確定まで約 1 s 周期で再試行。

### 3. COUNTERS_DB COUNTERS_RIF_TYPE_MAP

`intfsorch.cpp:71`: `m_rifTypeTable = Table(m_counter_db, COUNTERS_RIF_TYPE_MAP)`
`intfsorch.cpp:1535-1538`: `addRifToFlexCounter()` 内で RIF OID → type のマッピングも同時書き込み。
COUNTERS_RIF_NAME_MAP と COUNTERS_RIF_TYPE_MAP は同時に更新される。

### 4. FLEX_COUNTER_DB RIF_STAT グループ

`intfsorch.cpp:1551`: `startFlexCounterPolling(gSwitchId, key, counters_str, RIF_COUNTER_ID_LIST)`
  — FLEX_COUNTER_DB の `RIF_STAT_COUNTER_FLEX_COUNTER_GROUP:<rif_oid>` に
  `RIF_COUNTER_ID_LIST = "SAI_ROUTER_INTERFACE_STAT_IN_PACKETS,..."` を書き込む。
`intfsorch.cpp:1566`: `stopFlexCounterPolling()` で削除。

### 5. COUNTERS_DB (write) — COUNTERS_LAG_NAME_MAP / COUNTERS_RIF_NAME_MAP

`portsorch.cpp:762`: コンストラクタで `m_counterLagTable = Table(counter_db, COUNTERS_LAG_NAME_MAP)`
`portsorch.cpp:8022`: `addLag()` で `m_counterLagTable->set("", fields)` — LAG alias → OID を書き込む
`portsorch.cpp:8095`: `removeLag()` で `m_counterLagTable->hdel("", lag.m_alias)` — 削除

`intfsorch.cpp:70`: `m_rifNameTable = Table(m_counter_db, COUNTERS_RIF_NAME_MAP)`
`intfsorch.cpp:1537`: `m_rifNameTable->set("", rifNameVector)` — RIF alias → OID を書き込む

## 結論

YANG leafref として定義されていない暗黙参照は以下 4 つ:
1. `gPortsOrch` (APP_DB LAG/PORT 管理) — allPortsReady() + getPort() で参照
2. `ASIC_DB VIDTORID` — gTraditionalFlexCounter 時、RIF の VID→RID 確定待ちに使用
3. `COUNTERS_DB COUNTERS_RIF_TYPE_MAP` — COUNTERS_RIF_NAME_MAP と同時更新される隠しテーブル
4. `FLEX_COUNTER_DB RIF_STAT グループ` — RIF カウンタ収集用 per-OID エントリ
