# counter-buffer ordering (Phase B)

調査対象: `sonic-swss/orchagent/bufferorch.cpp`, `flexcounterorch.cpp`, `orchdaemon.cpp`

## 依存グラフ (コード由来)

```
orchdaemon 初期化順
  1. PortsOrch (gPortsOrch) — ポート OID 生成・allPortsReady() を提供
  2. BufferOrch (gBufferOrch) — BUFFER_POOL SAI オブジェクト生成
  3. WatermarkOrch            — テレメトリタイマー管理
  4. FlexCounterOrch          — FLEX_COUNTER_STATUS=enable を受信してカウンタ登録をトリガー
```

## BUFFER_POOL SAI オブジェクト生成順序

`bufferorch.cpp:2040 (doTask)` が厳密な処理順を定義:

```
1. pool_consumer->drain()    — APP_BUFFER_POOL_TABLE を先に処理
2. profile_consumer->drain() — APP_BUFFER_PROFILE_TABLE を次に処理
3. その他の consumer を drain — BUFFER_PG / BUFFER_QUEUE / BUFFER_PORT_INGRESS_PROFILE_LIST 等
```

コメントには SAI ドキュメント (SAI-Proposal-buffers-Ver4.docx) を明示引用:
> buffer pool → buffer profile → {buffer port ingress/egress profile list, buffer queue, buffer pq table}

`doTask(Consumer)` の先頭ガード (`bufferorch.cpp:2090-2099`) で VOQ 系は `isInitDone()`, 非 VOQ は `isConfigDone()` が true でなければ早期 return する。

## BUFFER_POOL_WATERMARK カウンタ登録の 2 段階起動

```
段階 1: BufferOrch コンストラクタ (bufferorch.cpp:234-250)
  - watermark_bufferpool.lua を BUFFER_POOL_WATERMARK グループに登録
  - BUFFER_POOL_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS (="60000") を設定
  - この時点ではプール OID は未生成のためポーリングは実質無効

段階 2: FlexCounterOrch::doTask — FLEX_COUNTER_STATUS=enable 受信時
  (flexcounterorch.cpp:287-289)
  - gBufferOrch->generateBufferPoolWatermarkCounterIdList() を呼出し
  - この関数が全既存プール OID に対して COUNTER_ID_LIST を FLEX_COUNTER_DB に push
  - m_isBufferPoolWatermarkCounterIdListGenerated フラグを true にして再重複を防止
```

段階 2 が段階 1 よりも **必ず後** に実行されるのは:
- FlexCounterOrch は orchdaemon 初期化リストで BufferOrch より後に生成される
- `m_delayTimerExpired` フラグが false のうちは `doTask` が早期 return する
- `allPortsReady()` が false なら処理をスキップ (flexcounterorch.cpp:166-169)

## Queue / PG カウンタ登録と BufferOrch の協調

`getPgConfigurations()` / `getQueueConfigurations()` (flexcounterorch.cpp) は
`gBufferOrch->getBufferObjectsWithNonZeroProfile()` を呼んで非ゼロプロファイル付き
PG / Queue エントリを取得してから `gPortsOrch->addPriorityGroupFlexCounters()` 等を呼ぶ。

つまり PG / Queue のカウンタ登録は:
1. BufferOrch が BUFFER_PG / BUFFER_QUEUE レコードを SAI に適用し終わる
2. FlexCounterOrch が `FLEX_COUNTER_STATUS=enable` を受信する
の **両方** が完了して初めて行われる。

## BUFFER_POOL 名→OID マッピングの書き込みタイミング差異

| 対象 | 書き込みタイミング | 関数 |
|------|----------------|------|
| BUFFER_POOL | create_buffer_pool 成功直後 | `m_counterNameMapUpdater->setCounterNameMap()` (bufferorch.cpp:546) |
| BUFFER_PG / BUFFER_QUEUE | FLEX_COUNTER_STATUS=enable 受信後 | `FlexCounterOrch::doTask` → `gPortsOrch->generatePriorityGroupMap()` |

コメント原文 (bufferorch.cpp:542-545):
> "In pg and queue case, this mapping installment is deferred to FlexCounterOrch at a reception of field FLEX_COUNTER_STATUS"

## 証跡

- `bufferorch.cpp:2040-2073` — doTask 処理順コメントと実装
- `bufferorch.cpp:2090-2099` — portsorch isConfigDone ガード
- `bufferorch.cpp:234-250` — コンストラクタでの lua/group 登録
- `bufferorch.cpp:286-361` — generateBufferPoolWatermarkCounterIdList
- `bufferorch.cpp:540-546` — BUFFER_POOL OID 生成直後のマッピング
- `flexcounterorch.cpp:145-289` — doTask / FLEX_COUNTER_STATUS 分岐全体
- `flexcounterorch.cpp:166-169` — allPortsReady ガード
- `flexcounterorch.cpp:621-624` — getPgConfigurations → gBufferOrch 連携
- `orchdaemon.cpp:232,394,437,625` — PortsOrch→BufferOrch→WatermarkOrch→FlexCounterOrch 生成順
