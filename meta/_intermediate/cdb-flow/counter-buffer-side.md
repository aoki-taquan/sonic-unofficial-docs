# counter-buffer Phase F — 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-17 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/counter-buffer.md` 配下の CONFIG_DB バッファカウンタ関連設定変更時に、
`portsorch` / `bufferorch` / `watermarkorch` / `flexcounterorch` が
COUNTERS_DB / APPL_STATE_DB / FLEX_COUNTER_TABLE など副次 DB・テーブルへ
何らかの書き込みを行うか。

## 走査範囲

- `sonic-swss/orchagent/bufferorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/watermarkorch.cpp`
- `sonic-swss/orchagent/flexcounterorch.cpp`

## 走査結果

### 1. COUNTERS_DB — 名前 → OID マップ書き込み

#### Buffer Pool (bufferorch.cpp)

バッファプール作成時に `m_counterNameMapUpdater->setCounterNameMap(object_name, sai_object)` を呼び出し、
`COUNTERS_DB / COUNTERS_BUFFER_POOL_NAME_MAP` に `pool_name → SAI OID` を即座に登録する。
(`bufferorch.cpp:546`)

削除時は `m_counterNameMapUpdater->delCounterNameMap(object_name)` でエントリを削除する。
(`bufferorch.cpp:586`)

Buffer Pool のマップ登録は FlexCounterOrch を経由せず、bufferorch が直接行う点が
Queue / PG との大きな違い（後者は FlexCounterOrch の `FLEX_COUNTER_STATUS:enable` 受信後にマップ登録される）。

#### Queue / Port (portsorch.cpp)

ポート追加時に `COUNTERS_PORT_NAME_MAP` へポート OID を登録 (`portsorch.cpp:4118`)。
Queue 初期化時に以下の 4 テーブルを一括更新:

| テーブル | 内容 |
|---------|------|
| `COUNTERS_QUEUE_NAME_MAP` | `port:queue_idx → OID` |
| `COUNTERS_QUEUE_PORT_MAP` | `OID → port OID` |
| `COUNTERS_QUEUE_INDEX_MAP` | `OID → queue index` |
| `COUNTERS_QUEUE_TYPE_MAP` | `OID → SAI_QUEUE_TYPE_*` |

PG 初期化時は `COUNTERS_PG_NAME_MAP` / `COUNTERS_PG_PORT_MAP` / `COUNTERS_PG_INDEX_MAP`
の 3 テーブルを一括更新 (`portsorch.cpp:8882-8884, 8937-8939`)。

### 2. APPL_STATE_DB — shared headroom pool 結果フィードバック (bufferorch.cpp)

Buffer Pool が `xoff` フィールドを持つ（shared headroom pool 設定）場合、
SAI 適用成功後に `ResponsePublisher::publish()` を介して
`APPL_STATE_DB / BUFFER_POOL_TABLE | <pool_name>` に `{xoff: <bytes>}` を書き込む。
(`bufferorch.cpp:555`, `orch.h:382` — `ResponsePublisher m_publisher{"APPL_STATE_DB"}`)

Buffer Profile の lossless 変更・削除時も `APPL_STATE_DB / BUFFER_PROFILE_TABLE | <profile_name>`
に結果を publish する。(`bufferorch.cpp:832, 880`)

Buffer Pool 削除時は空 fvs で publish し、APPL_STATE_DB エントリを削除する。
(`bufferorch.cpp:589`)

### 3. FLEX_COUNTER_GROUP_TABLE / FLEX_COUNTER_TABLE (syncd DB)

#### Buffer Pool Watermark (bufferorch.cpp)

`initFlexCounterGroupTable()` 呼び出し時に `FLEX_COUNTER_GROUP_TABLE | BUFFER_POOL_WATERMARK`
へポーリング間隔 (60000ms) と Lua plugin SHA を書き込む (`bufferorch.cpp:247-251`)。

`generateBufferPoolWatermarkCounterIdList()` 呼び出し時に
`FLEX_COUNTER_TABLE | BUFFER_POOL_WATERMARK:<oid>` へ `BUFFER_POOL_COUNTER_ID_LIST` を書き込む。
各プールの SAI clear_stats 能力に応じて `STATS_MODE_READ` / `STATS_MODE_READ_AND_CLEAR` が
個別に設定される (`bufferorch.cpp:333-358`)。

`clearBufferPoolWatermarkCounterIdList()` 呼び出し時は
`stopFlexCounterPolling()` を通じて `FLEX_COUNTER_TABLE | BUFFER_POOL_WATERMARK:<oid>` を削除。
(`bufferorch.cpp:282`)

#### Queue / PG (portsorch.cpp)

portsorch の `addQueueFlexCounters()` / `addPriorityGroupFlexCounters()` が
`FLEX_COUNTER_TABLE | QUEUE_STAT_COUNTER:<oid>` 等へ counter_id_list を書き込む。
FlexCounterOrch が `FLEX_COUNTER_STATUS:enable` を受信した後に限り実行される。

### 4. GB_COUNTERS_DB (portsorch.cpp — gearbox 環境のみ)

Gearbox が有効な環境では、`COUNTERS_PORT_NAME_MAP` を
`GB_COUNTERS_DB` にも別途書き込む (`portsorch.cpp:10392-10393`)。
通常のネットワーク環境では GB_COUNTERS_DB への書き込みは発生しない。

## 副次書き込みまとめ

| トリガー | 副次 DB / テーブル | 内容 |
|---------|------------------|------|
| Buffer Pool CREATE | `COUNTERS_DB / COUNTERS_BUFFER_POOL_NAME_MAP` | pool_name → OID 登録 |
| Buffer Pool DELETE | `COUNTERS_DB / COUNTERS_BUFFER_POOL_NAME_MAP` | エントリ削除 |
| Buffer Pool CREATE (xoff) | `APPL_STATE_DB / BUFFER_POOL_TABLE` | xoff bytes 結果通知 |
| Buffer Pool DELETE | `APPL_STATE_DB / BUFFER_POOL_TABLE` | エントリ削除 |
| Buffer Profile SET (lossless) | `APPL_STATE_DB / BUFFER_PROFILE_TABLE` | 結果通知 |
| Buffer Profile DEL | `APPL_STATE_DB / BUFFER_PROFILE_TABLE` | エントリ削除 |
| bufferorch 初期化 | `FLEX_COUNTER_GROUP_TABLE / BUFFER_POOL_WATERMARK` | Lua SHA + interval |
| Buffer Pool WM enable | `FLEX_COUNTER_TABLE / BUFFER_POOL_WATERMARK:<oid>` | counter_id_list |
| Buffer Pool WM disable/DELETE | `FLEX_COUNTER_TABLE / BUFFER_POOL_WATERMARK:<oid>` | エントリ削除 |
| Port 追加 | `COUNTERS_DB / COUNTERS_PORT_NAME_MAP` | port_name → OID |
| Queue 初期化 | `COUNTERS_DB / COUNTERS_QUEUE_{NAME,PORT,INDEX,TYPE}_MAP` | Queue メタ情報 |
| PG 初期化 | `COUNTERS_DB / COUNTERS_PG_{NAME,PORT,INDEX}_MAP` | PG メタ情報 |
| Port 削除 | `COUNTERS_DB / COUNTERS_PORT_NAME_MAP` | エントリ削除 |
| Gearbox 有効時 Port 追加 | `GB_COUNTERS_DB / COUNTERS_PORT_NAME_MAP` | port_name → OID |
