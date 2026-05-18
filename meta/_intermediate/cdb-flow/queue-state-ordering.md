# queue-state ordering (Phase B) — 調査メモ

## 対象テーブル
`STATE_DB QUEUE_COUNTER_CAPABILITIES`

## 書込み主体
`PortsOrch::initCounterCapabilities()` — `portsorch.cpp:1850-1922`

## 呼び出し箇所
`portsorch.cpp:1107` — PortsOrch コンストラクタ末尾で 1 回のみ

## 検出された順序依存

1. **初期化フェーズ → SAI クエリ**: 全 4 キーを `"false"` で初期化した後に SAI クエリを実行（強制先行）。
2. **SAI 成功時 → 個別キー上書き**: `sai_query_stats_capability()` が `SAI_STATUS_SUCCESS` を返した場合のみ `"true"` に上書き。
3. **BUFFER_OVERFLOW リトライ**: `SAI_STATUS_BUFFER_OVERFLOW` 時は list を拡張して再クエリ（最大 1 回）。
4. **consumer 参照タイミング**: orchagent 起動完了前に参照すると `None` が返る。

## evidence
- `portsorch.cpp:1871-1875` — 初期化（`"false"` 書込み）
- `portsorch.cpp:1882-1888` — SAI クエリ + BUFFER_OVERFLOW リトライ
- `portsorch.cpp:1889-1918` — 成功時の `"true"` 上書き
- `portsorch.cpp:1919-1922` — 失敗時のログ（`"false"` のまま確定）
