# FLEX_COUNTER_TABLE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-flex-counter)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/flexcounterorch.cpp`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `key` が `flexCounterGroupMap` に存在しないグループ名 | `doTask()` L183-188 | エントリを `m_toSync` から除去してスキップ（設定未適用） | `SWSS_LOG_NOTICE("Invalid flex counter group input, %s")` | `flexcounterorch.cpp:183-188` |
| `FLEX_COUNTER_STATUS` に `enable`/`disable` 以外の値 | `doTask()` L380 | `setFlexCounterGroupOperation()` に不正値が渡る。各 orch ブロックは `value == "enable"` / `value == "disable"` の分岐でいずれも hit せず silent skip | なし（ログ未出力） | `flexcounterorch.cpp:235-393` |
| `FLEX_COUNTER_STATUS` の不正値がフィールドループ末尾に到達 | `doTask()` L395-397 | `SWSS_LOG_NOTICE("Unsupported field %s")` — ただし `FLEX_COUNTER_STATUS_FIELD` は `else` 分岐に入らないため実際にはログも出ない | なし | `flexcounterorch.cpp:395-397` |
| `POLL_INTERVAL` 不正値（非数値・範囲外） | `setFlexCounterGroupPollInterval()` (内部) | syncd 側でバリデーション。YANG `range 100..4294967295` に反するが CLI を介さず直接 redis-cli 書き込みした場合はオーケストラ側でフィルタなし・syncd が拒否するかどうかはプラットフォーム依存 | なし（orchagent 側ログなし） | `flexcounterorch.cpp:200-215` |
| `gPortsOrch == nullptr` のとき PORT / QUEUE / PG / WRED 系を `enable` | `doTask()` L235 | `gPortsOrch` null チェックで全ブロックをスキップ → カウンタ ID リスト未投入・SAI 設定ゼロ | なし（silent drop） | `flexcounterorch.cpp:235` |
| `gCoppOrch == nullptr` のとき `FLOW_CNT_TRAP` を `enable` | `doTask()` L311 | `gCoppOrch` null チェックで `generateHostIfTrapCounterIdList()` 呼び出しスキップ → trap flow counter 未設定 | なし（silent drop） | `flexcounterorch.cpp:311` |
| `gFlowCounterRouteOrch` が null または `getRouteFlowCounterSupported() == false` で `FLOW_CNT_ROUTE` を `enable` | `doTask()` L324 | ルートフローカウンタ設定ゼロ・`m_route_flow_counter_enabled` は更新されない | なし（silent drop） | `flexcounterorch.cpp:324` |
| `allPortsReady() == false` の間に SET | `doTask()` 早期 return | エントリが `m_toSync` に蓄積されたまま今回の doTask では適用されない。全ポート ready 後の次 doTask で一括処理 | なし | `flexcounterorch.cpp` (allPortsReady guard) |
| warm-reboot 中（delay timer 未満 60s）に SET | `doTask()` delay guard | `m_delayTimerExpired == false` の間は全 SET が無視される | なし | `flexcounterorch.cpp:127-137` |
| `create_only_config_db_buffers` 読み取りで `std::system_error` | コンストラクタ L122-124 | `SWSS_LOG_ERROR` のみ・`m_createOnlyConfigDbBuffers` はデフォルト (`false`) のまま・バッファカウンタ設定が異なる動作になる可能性 | `SWSS_LOG_ERROR("System error reading create_only_config_db_buffers: %s")` | `flexcounterorch.cpp:122-124` |
| `BUFFER_QUEUE` key が `port:queue_index` 形式でない（トークン数 ≠ 2） | `getQueueConfigurations()` L559-562 | `SWSS_LOG_ERROR` → エントリスキップ（そのキューのカウンタ設定は適用されない） | `SWSS_LOG_ERROR("Invalid BUFFER_QUEUE key: [%s]")` | `flexcounterorch.cpp:559-562` |
| queue インデックスが非整数または範囲外 | `getQueueConfigurations()` L599-601 | `std::invalid_argument` をキャッチ → `SWSS_LOG_ERROR` → そのポートの queue カウンタ設定はスキップ | `SWSS_LOG_ERROR("Invalid queue index [%s] for port [%s]")` | `flexcounterorch.cpp:599-601` |
| `BUFFER_PG` key が `port:pg_index` 形式でない（トークン数 ≠ 2） | `getPgConfigurations()` L628-631 | `SWSS_LOG_ERROR` → エントリスキップ | `SWSS_LOG_ERROR("Invalid BUFFER_PG key: [%s]")` | `flexcounterorch.cpp:628-631` |
| PG インデックスが非整数または範囲外 | `getPgConfigurations()` L661-663 | `std::invalid_argument` をキャッチ → `SWSS_LOG_ERROR` → そのポートの PG カウンタ設定はスキップ | `SWSS_LOG_ERROR("Invalid pg index [%s] for port [%s]")` | `flexcounterorch.cpp:661-663` |

### 検出ロジック補足

- **不正グループ名は即座に erase**: `flexCounterGroupMap.count(key) == 0` の場合、`m_toSync` から消去して処理終了。リトライなし。
- **`FLEX_COUNTER_STATUS` 不正値の silent 挙動**: `value == "enable"` / `value == "disable"` どちらにも該当しない場合、各 orch への通知ブロックがすべてスキップされる。`setFlexCounterGroupOperation()` に不正値が渡るが orchagent 側エラーログなし。syncd 側で拒否されるか否かはプラットフォーム依存。
- **POLL_INTERVAL コード上バリデーションなし**: orchagent は受け取った文字列をそのまま `setFlexCounterGroupPollInterval()` 経由で syncd へ渡す。YANG `range 100..4294967295` に反する値は CLI では拒否されるが、redis-cli で直接書き込んだ場合は syncd 任せ。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `SWSS_LOG_ERROR` | 5 | `flexcounterorch.cpp:124, 561, 600, 630, 662` |
| `SWSS_LOG_NOTICE` (Invalid group) | 1 | `flexcounterorch.cpp:185` |
| `SWSS_LOG_NOTICE` (Unsupported field) | 1 | `flexcounterorch.cpp:397` |
| null guard (gPortsOrch) | 1 | `flexcounterorch.cpp:235` |
| null guard (gCoppOrch) | 1 | `flexcounterorch.cpp:311` |
| null guard (gFlowCounterRouteOrch) | 1 | `flexcounterorch.cpp:324` |
| `std::invalid_argument` catch | 2 | `flexcounterorch.cpp:599, 661` |

<!-- /failure -->
