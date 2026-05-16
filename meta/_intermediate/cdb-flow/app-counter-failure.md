# CONFIG_DB アプリケーション フローカウンタ — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-app-counter)

対象テーブル: `FLEX_COUNTER_TABLE|FLOW_CNT_TRAP`, `FLEX_COUNTER_TABLE|FLOW_CNT_ROUTE`, `FLOW_COUNTER_ROUTE_PATTERN`

ソース:

- `sonic-net/sonic-swss/orchagent/flexcounterorch.cpp` (723 行, master)
- `sonic-net/sonic-swss/orchagent/flex_counter/flex_counter_manager.cpp` (286 行)
- `sonic-net/sonic-swss/orchagent/flex_counter/flex_counter_stat_manager.cpp` (94 行)
- `sonic-net/sonic-swss/orchagent/flex_counter/flow_counter_handler.cpp` (62 行)
- `sonic-net/sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp` (997 行)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

### FlexCounterOrch 入口 (CONFIG_DB → handler ディスパッチ, `flexcounterorch.cpp:179-426`)

| 失敗条件 | 検出箇所 | 動作 | ログ | evidence |
|---|---|---|---|---|
| `FLEX_COUNTER_TABLE` の key が `flexCounterGroupMap` に未登録 (未知 group / FLOW_CNT_TRAP・FLOW_CNT_ROUTE 以外の typo 含む) | L183-188 | `m_toSync.erase()` で **即破棄・retry なし** | `LOG_NOTICE ("Invalid flex counter group input, %s")` | `flexcounterorch.cpp:183-188` |
| `FLEX_COUNTER_TABLE` SET 内の未対応フィールド (`FLEX_COUNTER_STATUS` / `POLL_INTERVAL` / bulk_chunk_size 系以外) | L396-399 | フィールド単位 skip (handler 全体は失敗にしない) | `LOG_NOTICE ("Unsupported field %s")` | `flexcounterorch.cpp:396-399` |
| `DEVICE_METADATA\|localhost` 読み取りで `std::system_error` (Redis 通信障害) | L122-126 | catch して続行 (`m_createOnlyConfigDbBuffers` は初期値 false のまま) | `LOG_ERROR ("System error reading create_only_config_db_buffers")` | `flexcounterorch.cpp:122-126` |
| `POLL_INTERVAL` 値の数値検証 | なし | flexcounterorch は文字列のまま `setFlexCounterGroupOperation` に渡す。**syncd 側 FlexCounter で interval パース失敗時に拒否**。orchagent では検出されない | (なし) | `flexcounterorch.cpp:203-` 周辺 |
| `FLEX_COUNTER_STATUS` 値の検証 | なし | `enable` / `disable` 以外は文字列のまま syncd に渡され、syncd 側で `disable` 相当として扱われる (`FlexCounter::updateStatus` で比較) | (なし) | (orchagent 側は素通し) |

> `Invalid flex counter group input` ログは `FLOW_CNT_TRAP` / `FLOW_CNT_ROUTE` のスペルミス時に唯一出る痕跡。retry されず CONFIG_DB に書き戻りも発生しないため、ユーザー視点では「設定したのに何も起きない」障害として表面化する。

### FlexCounterManager 共有・重複生成 (`flex_counter_manager.cpp:62-93`)

`createFlexCounterManager()` は group_name 単位で 1 インスタンスを `FlexManagerDirectory` に保持し、2 回目以降の `createFlexCounterManager` 呼び出しでパラメータが食い違うと **null 返却で manager 不発**となる。flexcounterorch 自身は 1 ヶ所からしか呼ばないが、`FLOW_CNT_TRAP` (copporch) と `FLOW_CNT_ROUTE` (flowcounterrouteorch) は別 group のため衝突しない。プラグイン拡張で同 group を再宣言した場合の挙動として記録する。

| 失敗条件 | 検出箇所 | 動作 | ログ | evidence |
|---|---|---|---|---|
| 既存 manager と `stats_mode` 不一致 | L71-76 | `return NULL` (新 manager 作らず) | `LOG_ERROR ("Stats mode mismatch with already created flex counter manager %s")` | `flex_counter_manager.cpp:71-76` |
| 既存 manager と `polling_interval` 不一致 | L77-82 | `return NULL` | `LOG_ERROR ("Polling interval mismatch ...")` | `flex_counter_manager.cpp:77-82` |
| 既存 manager と `enabled` 不一致 | L83-88 | `return NULL` | `LOG_ERROR ("Enabled field mismatch ...")` | `flex_counter_manager.cpp:83-88` |

### FlexCounterManager 統計登録 (`flex_counter_manager.cpp:208-225`)

| 失敗条件 | 検出箇所 | 動作 | ログ | evidence |
|---|---|---|---|---|
| `counter_type` が `counter_id_field_lookup` に未登録 (flow counter で SAI_OBJECT_TYPE_COUNTER 系のみ許可) | L212-217 | **早期 return、`startFlexCounterPolling` 呼び出さず**。COUNTERS_DB への書き込みも開始されない | `LOG_ERROR ("Could not update flex counter id list for group '%s': counter type not found.")` | `flex_counter_manager.cpp:212-217` |

### FlexCounterStatManager (`flex_counter_stat_manager.cpp:60-87`)

| 失敗条件 | 検出箇所 | 動作 | ログ | evidence |
|---|---|---|---|---|
| `removeFlexCounterStat` 呼び出し時に `object_id` が `object_stats` に未登録 (二重削除 / race) | L66-72 | `return` (例外なし、後処理スキップ) | `LOG_WARN ("Could not find flex stat '%s' on object '%s'")` | `flex_counter_stat_manager.cpp:66-72` |

### FlowCounterHandler SAI 失敗 (`flow_counter_handler.cpp`)

| 失敗条件 | 検出箇所 | 動作 | ログ | evidence |
|---|---|---|---|---|
| `sai_counter_api->create_counter` が `SAI_STATUS_SUCCESS` 以外 | L20-26 | `return false` → 呼び出し元 `bindFlowCounter` で route binding を中止 | `LOG_WARN ("Failed to create generic counter")` | `flow_counter_handler.cpp:20-26` |
| `sai_counter_api->remove_counter` 失敗 | L32-38 | `return false` (counter OID は orchagent ハッシュから削除済みなのでリーク) | `LOG_ERROR ("Failed to remove generic counter: ...")` | `flow_counter_handler.cpp:32-38` |
| `sai_query_attribute_capability(SAI_ROUTE_ENTRY_ATTR_COUNTER_ID)` 失敗 / `set_implemented = false` | L54-61 | `return false` → `mRouteFlowCounterSupported = false` → 以降 `FLOW_CNT_ROUTE` を `enable` にしても **no-op**, STATE_DB `FLOW_COUNTER_CAPABILITY_TABLE` に `support=false` を書き込み | `LOG_WARN ("Could not query route entry attribute SAI_ROUTE_ENTRY_ATTR_COUNTER_ID %d")` / `LOG_NOTICE ("Route flow counter is not supported on this platform")` | `flow_counter_handler.cpp:51-62`, `flowcounterrouteorch.cpp:165-178` |

### FlowCounterRouteOrch CONFIG_DB 受信系 (`flowcounterrouteorch.cpp`)

#### `FLOW_COUNTER_ROUTE_PATTERN` doTask (L60-99)

| 失敗条件 | 検出箇所 | 動作 | ログ | evidence |
|---|---|---|---|---|
| `max_match_count = 0` (ユーザー誤設定) | L80-86 | **値を 30 (`ROUTE_PATTERN_DEFAULT_MAX_MATCH_COUNT`) に上書きして続行**。retry や reject なし | `LOG_WARN ("Max match count for route pattern cannot be 0, set it to default value 30")` | `flowcounterrouteorch.cpp:80-86` |
| `max_match_count` が非数値文字列 | L80 (`std::stoul`) | `std::invalid_argument` 例外が `doTask` まで伝播 (catch なし) → orchagent クラッシュ要因。**CONFIG_DB 直書き編集時のみ発生** (CLI 側で int 強制) | (なし、例外スタックトレース) | `flowcounterrouteorch.cpp:80` |
| 既存パターンと overlap する key を SET | `validateRoutePattern` L573-588 | **bind 段階で `false` 返却**。新パターンの bind は実行されず、`mRoutePatternSet` には残るがカウンタは作られない | `LOG_ERROR ("Configured route pattern %s is conflict with existing one %s")` | `flowcounterrouteorch.cpp:573-588` |
| 存在しない pattern を DEL | `removeRoutePattern` L266-275 | early return | `LOG_ERROR ("Trying to remove route pattern %s, but it does not exist")` | `flowcounterrouteorch.cpp:266-275` |
| VRF 名が未解決 (該当 VRF がまだ作られていない) | L971-975 | bind 処理が `false` 返却で **次回 doTask タイマー (1 秒) で再試行** (`mPendingAddToFlexCntr` 経由) | `LOG_NOTICE ("VRF/VNET name %s is not resolved")` | `flowcounterrouteorch.cpp:971-975` |
| route が削除された等で VRF OID → 名前逆引き失敗 | L417-422, L848-854 | カウンタ作成スキップ。例外なし | `LOG_WARN ("Failed to get VRF name for vrf id %s")` / `LOG_ERROR ("Failed to get VRF/VNET name for vrf id %s")` | `flowcounterrouteorch.cpp:417-422, 848-854` |

#### Route binding SAI 失敗 (L457-486)

| 失敗条件 | 検出箇所 | 動作 | ログ | evidence |
|---|---|---|---|---|
| SAI `create_counter` 失敗 | L461-465 | `return false`、route 未バインド。再試行は `pendingUpdateFlexDb` 経由のタイマーで自然に行われる | `LOG_ERROR ("Failed to create generic counter")` | `flowcounterrouteorch.cpp:461-465` |
| SAI `set_route_entry_attribute(SAI_ROUTE_ENTRY_ATTR_COUNTER_ID)` 失敗 | L476-483 | **生成済み generic counter を `removeGenericCounter` で巻き戻し**、`return false` | `LOG_WARN ("Failed to bind route entry vrf=%s prefix=%s to flow counter")` | `flowcounterrouteorch.cpp:476-483` |
| SAI `set_route_entry_attribute(NULL_OID)` (unbind) 失敗 | L501-506 | warning のみで処理続行、counter は最終的に `removeGenericCounter` で削除 | `LOG_WARN ("Failed to unbind route entry vrf=%s prefix=%s from flow counter")` | `flowcounterrouteorch.cpp:501-506` |

#### max_match_count 上限超過時の打ち切り (L800-820)

| 失敗条件 | 検出箇所 | 動作 | ログ | evidence |
|---|---|---|---|---|
| パターンにマッチするルート数が `max_match_count` を超過 | L800-820 | **超過分にはカウンタを bind しない** (silent drop)。ユーザー視点では「途中までしかカウントされない」現象 | `LOG_NOTICE ("Current bound route flow counter count is %zu, new limit is %zu, old limit is %zu")` (limit 変更時のみ) | `flowcounterrouteorch.cpp:800-820` |

### FLEX_COUNTER_TABLE 側固有の `interval` / `status` 不正

flexcounterorch は `POLL_INTERVAL` を数値検証せずに syncd 側 `FlexCounter` へ転送する。syncd 側で:

- 数値以外 / 負値: `std::invalid_argument` が `swss::loglevel::WARN` で握り潰される (`sairedis FlexCounter.cpp` の `tryReadValue` 系)
- 0 / 過小値 (< `MIN_POLLING_INTERVAL_MS`): タイマー再起動時に **直前の有効値を維持**、CONFIG_DB 上の不正値は無視

これらは orchagent 側からは観測不能で、`COUNTERS_DB` の更新頻度変化のみが症状になる。

### retry 経路まとめ (CONFIG_DB アプリケーション フローカウンタ系)

| retry 種別 | トリガ | 仕組み |
|---|---|---|
| VRF 未解決時の route pattern 再 bind | `mPendingAddToFlexCntr` 非空 | `mFlexCounterUpdTimer` (1 秒周期, `FLEX_COUNTER_UPD_INTERVAL = 1`) が `doTask(SelectableTimer&)` で再試行 (`flowcounterrouteorch.cpp:43-46, 100-145`) |
| SAI route bind 失敗 | `bindFlowCounter` 失敗時 | route が再度 routeorch から通知されるか、pattern が再 SET されない限り **自動 retry なし** |
| SAI create_counter 失敗 | binding 中断 | pending list には残るので **タイマーで再試行される** |
| `Invalid flex counter group input` | 未知 group key | **retry なし、即捨て** |

### grep カバレッジ

| ファイル | `SWSS_LOG_ERROR` | `SWSS_LOG_WARN` | `SWSS_LOG_NOTICE` | `return false` |
|---|---|---|---|---|
| `flexcounterorch.cpp` | ~10 (buffer 系含む) | 0 | 数件 (`Invalid flex counter group input` 等) | 該当箇所なし (early return / erase) |
| `flex_counter_manager.cpp` | 4 (manager 不整合 3 + counter type 未登録 1) | 0 | 0 | 関数戻り値経由 |
| `flex_counter_stat_manager.cpp` | 0 | 1 (object 未登録) | 0 | 0 |
| `flow_counter_handler.cpp` | 1 (remove) | 2 (create / capability query) | 0 | 3 |
| `flowcounterrouteorch.cpp` | 数件 (overlap / remove non-existent / VRF resolve 等) | 4 (bind/unbind/VRF) | 多数 (進捗・no-support 等) | 数十 |

### ユーザー視点の代表的な失敗症状

1. **`FLEX_COUNTER_STATUS=enable` を書いたのにカウンタが現れない**
    - 原因候補: group key の typo (`Invalid flex counter group input`)、SAI capability 不足 (`Route flow counter is not supported on this platform`)、`max_match_count` 超過。
2. **`max_match_count=0` を設定したのに 30 にされる** — Phase D で挙動として確定 (silent fallback)。
3. **route flow counter が VRF 作成直後に出ない** — 1 秒タイマーの再試行が走るため数秒のラグ。
4. **POLL_INTERVAL に文字列を入れても何も起きない** — orchagent 段では検証されず syncd 側で握り潰される。

<!-- /failure -->
