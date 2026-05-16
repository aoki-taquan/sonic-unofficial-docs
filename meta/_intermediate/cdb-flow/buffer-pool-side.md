# BUFFER_POOL SET/DEL 副次 DB 書込 分析 (Phase F)

生成日: 2026-05-16
ソース:
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` — `BufferMgrDynamic::handleBufferPoolTable()`、STATE_DB 読み取り
- `sonic-swss/orchagent/bufferorch.cpp` — `BufferOrch::processBufferPool()`、`BufferOrch::initFlexCounterGroupTable()`、`BufferOrch::generateBufferPoolWatermarkCounterIdList()`
- `sonic-swss/orchagent/orch.h` — `ResponsePublisher m_publisher{"APPL_STATE_DB"}` 宣言
- `sonic-swss/orchagent/response_publisher.cpp` — `ResponsePublisher::publish()` → `APPL_STATE_DB` 書込み実装
- `sonic-swss/orchagent/saihelper.cpp` — `startFlexCounterPolling()` / `stopFlexCounterPolling()`

---

## buffermgrdyn (cfgmgr/buffermgrdyn.cpp)

`BufferMgrDynamic` は CONFIG_DB の `BUFFER_POOL` テーブルを購読し、APPL_DB へ展開する中間管理デーモン。
CONFIG_DB / APPL_DB 以外への副次書き込みは発生しない。

STATE_DB の `BUFFER_MAX_PARAM_TABLE` は **読み取り専用**（L133-137）。`buffermgrdyn.cpp` は STATE_DB への書き込みを行わない。

---

## BufferOrch (orchagent/bufferorch.cpp)

`BufferOrch` は APPL_DB の `APP_BUFFER_POOL_TABLE` を購読し、SAI API を呼び出す。
SET/DEL 処理後に 3 種類の DB に副次書き込みが発生する。

### SET (BUFFER_POOL|<pool_name>)

#### 1. APPL_STATE_DB / `APP_BUFFER_POOL_TABLE`

SAI buffer pool 作成/更新に成功し、かつ xoff (Shared Headroom Pool) フィールドが空でない場合のみ、
`m_publisher.publish()` が APPL_STATE_DB へ書き込む。

| トリガ | フィールド | 値 | evidence |
|--------|------------|-----|----------|
| SHP (xoff) 有効かつ SAI 適用成功 (SET) | `xoff` | 計算済み SHP サイズ (bytes, 文字列) | `bufferorch.cpp:555` |
| DEL 操作完了後 | — (エントリ削除) | — | `bufferorch.cpp:589` |

コード証跡:
- `bufferorch.cpp:549-556` — `if (!xoff.empty()) { m_publisher.publish(APP_BUFFER_POOL_TABLE_NAME, object_name, fvs, ReturnCode(SAI_STATUS_SUCCESS), true); }`
- `orch.h:382` — `ResponsePublisher m_publisher{"APPL_STATE_DB"}`
- `response_publisher.cpp:141-143` — 成功時は intent_attrs を state_attrs として APPL_STATE_DB に書き込む

!!! note "xoff なし（通常プール）の場合"
    `ingress_lossy_pool` や `egress_lossless_pool` など xoff フィールドを持たない通常プールでは、
    `xoff.empty()` が true のため `m_publisher.publish()` は呼ばれず APPL_STATE_DB への書き込みは発生しない。

#### 2. COUNTERS_DB / `COUNTERS_BUFFER_POOL_NAME_MAP`

SAI buffer pool オブジェクトを作成した際、プール名から SAI OID へのマッピングを
`COUNTERS_DB` の `COUNTERS_BUFFER_POOL_NAME_MAP` hash に登録する。

| トリガ | 操作 | フィールド | 値 | evidence |
|--------|------|-----------|-----|----------|
| SAI pool 作成成功 (SET, 新規プール) | `hset` | `<pool_name>` | SAI OID 文字列 | `bufferorch.cpp:546` |
| SAI pool 削除成功 (DEL) | `hdel` | `<pool_name>` | — | `bufferorch.cpp:586` |

コード証跡:
- `bufferorch.cpp:55` — `m_counterNameMapUpdater(new CounterNameMapUpdater("COUNTERS_DB", COUNTERS_BUFFER_POOL_NAME_MAP))`
- `bufferorch.cpp:546` — `m_counterNameMapUpdater->setCounterNameMap(object_name, sai_object)` (SET 時、新規作成のみ)
- `bufferorch.cpp:586` — `m_counterNameMapUpdater->delCounterNameMap(object_name)` (DEL 時)
- 定数: `COUNTERS_BUFFER_POOL_NAME_MAP = "COUNTERS_BUFFER_POOL_NAME_MAP"` (swss-common schema)

!!! note "既存プール更新時は登録スキップ"
    pool が既存 (`SAI_NULL_OBJECT_ID != sai_object`) の場合は `setCounterNameMap` が呼ばれず、
    COUNTERS_DB への書き込みは発生しない (`bufferorch.cpp:540-547` の条件分岐参照)。

#### 3. FLEX_COUNTER_DB / `BUFFER_POOL_WATERMARK`

バッファプール watermark のポーリング設定を FLEX_COUNTER_DB に書き込む。
`generateBufferPoolWatermarkCounterIdList()` が呼ばれたとき（FlexCounterOrch から
`FLEX_COUNTER_STATUS=enable` を受信した際）に全プール分を一括登録する。

| トリガ | 操作 | キー | フィールド | evidence |
|--------|------|------|-----------|----------|
| `FLEX_COUNTER_STATUS=enable` 受信 (FlexCounterOrch) | `set` | `BUFFER_POOL_WATERMARK:<sai_oid>` | `BUFFER_POOL_COUNTER_ID_LIST=<stat_list>` | `bufferorch.cpp:358` |
| プール削除時 (DEL) | `del` | `BUFFER_POOL_WATERMARK:<sai_oid>` | — | `bufferorch.cpp:281-282` |
| FLEX_COUNTER_GROUP_TABLE 初期化 (起動時) | `set` | `BUFFER_POOL_WATERMARK` (group) | plugin SHA, poll interval | `bufferorch.cpp:247-248` |

コード証跡:
- `bufferorch.cpp:62` — コンストラクタで `initFlexCounterGroupTable()` を呼び出し
- `bufferorch.cpp:247-252` — `setFlexCounterGroupParameter(BUFFER_POOL_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP, ...)` → FLEX_COUNTER_DB の `FLEX_COUNTER_GROUP_TABLE` に書き込む
- `bufferorch.cpp:358` — `startFlexCounterPolling(gSwitchId, key, statList, BUFFER_POOL_COUNTER_ID_LIST, stats_mode)` → `FLEX_COUNTER_DB` の `BUFFER_POOL_WATERMARK:<oid>` に書き込む
- `bufferorch.cpp:281-282` — `stopFlexCounterPolling(gSwitchId, key)` → DEL 時にエントリを削除
- 定数: `BUFFER_POOL_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP = "BUFFER_POOL_WATERMARK"` (swss-common)
- DB 番号: `FLEX_COUNTER_DB = 5` (`schema.h:18`)

!!! note "watermark clear 非対応 ASIC"
    SAI `clear_buffer_pool_stats` が `NOT_SUPPORTED` / `NOT_IMPLEMENTED` を返す ASIC では、
    `stats_mode=READ` で登録（`bufferorch.cpp:310-322`）。watermark clear は抑制される。

### DEL (BUFFER_POOL|<pool_name>)

| 操作 | 対象 DB / テーブル | キー / フィールド | evidence |
|------|--------------------|-----------------|----------|
| `m_publisher.publish(..., fvs={})` | APPL_STATE_DB / `APP_BUFFER_POOL_TABLE` | `<pool_name>` (エントリ削除) | `bufferorch.cpp:589` |
| `m_counterNameMapUpdater->delCounterNameMap(object_name)` | COUNTERS_DB / `COUNTERS_BUFFER_POOL_NAME_MAP` | field=`<pool_name>` | `bufferorch.cpp:586` |
| `clearBufferPoolWatermarkCounterIdList(sai_object)` → `stopFlexCounterPolling()` | FLEX_COUNTER_DB / `BUFFER_POOL_WATERMARK:<oid>` | `<oid>` (エントリ削除) | `bufferorch.cpp:281-282` |

---

## STATE_DB / BUFFER_MAX_PARAM_TABLE（読み取りのみ）

`buffermgrdyn.cpp` は `BUFFER_MAX_PARAM_TABLE` を **STATE_DB から読み取る**（L133-137, L1873-1966）。
MMU サイズや各ポートの最大 PG / キュー数の取得に使用する。書き込みは行わない。

---

## 副次書込なし

- **ASIC_DB**: SAI 経由で syncd が書き込む（orchagent の直接書込なし）。
- **STATE_DB** (BUFFER_MAX_PARAM_TABLE): `bufferorch`/`buffermgrdyn` は読み取りのみ。書き込みは `portsorch` が行う。

---

## 全体サマリ

| 副次書込先 DB | テーブル | トリガ | 書込デーモン |
|---|---|---|---|
| APPL_STATE_DB | `APP_BUFFER_POOL_TABLE` | SHP (xoff) 有効プールの SET/DEL 完了時 | `BufferOrch` (orchagent) |
| COUNTERS_DB | `COUNTERS_BUFFER_POOL_NAME_MAP` | 新規プール作成成功時 (SET) / DEL 時 | `BufferOrch` (orchagent) |
| FLEX_COUNTER_DB | `BUFFER_POOL_WATERMARK:<oid>` | FlexCounterOrch が enable 通知時 / DEL 時 | `BufferOrch` (orchagent) |
| FLEX_COUNTER_DB | `FLEX_COUNTER_GROUP_TABLE` (`BUFFER_POOL_WATERMARK`) | 起動時 1 回 (plugin SHA + poll interval) | `BufferOrch` (orchagent) |
