# SFLOW_SESSION — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-17 (q67-f-sflow-sess2-next)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/cfgmgr/sflowmgr.cpp`, `sonic-swss/orchagent/sfloworch.cpp`

### sflowmgrd (CFG_SFLOW_SESSION_TABLE_NAME) — SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| per-port SET 時にポートが `m_sflowPortConfMap` に未登録 | `sflowmgr.cpp:522-528` | `it++; continue` で当該エントリを永続スキップ。リトライなし。ポートが後から PORT テーブルに追加されても SFLOW_SESSION の再処理は行われない | なし | `sflowmgr.cpp:524-527` |
| `m_gEnable == false` (SFLOW|global admin_state=up が未設定) の状態で per-port SET | `sflowmgr.cpp:531-534` | `if (m_gEnable)` ブロックに入らず `m_appSflowSessionTable.set()` を呼ばない。APP_DB への反映が遅延する。グローバルが後から up になると `sflowHandleSessionAll()` / `sflowHandleSessionLocal()` が再適用して回復する | なし | `sflowmgr.cpp:531` |
| `sample_rate` フィールドが "error" 文字列で到達 (`findSamplingRate()` が ERROR_SPEED を返した場合) | `sfloworch.cpp:275-279` / `sflowmgr.cpp:391` | SflowOrch 側で `rate == 0` として処理される。新規ポートの場合 `it++; continue` でスキップ | なし (mgrd 側で SWSS_LOG_ERROR) | `sflowmgr.cpp:390-393`, `sfloworch.cpp:275-282` |
| `alias` が `m_sflowPortConfMap` に存在しない状態で `findSamplingRate()` 呼び出し | `sflowmgr.cpp:389-393` | `SWSS_LOG_ERROR` 出力後 `ERROR_SPEED` を返す。後続の APP_DB 書き込みでは `sample_rate=error` が入る | SWSS_LOG_ERROR ("%s not found in port configuration map") | `sflowmgr.cpp:390-392` |
| `sflowHandleService()` (hsflowd restart/stop) の実行が rc != 0 で失敗 | `sflowmgr.cpp:67-71` | `SWSS_LOG_ERROR` を出力するが例外送出・リトライはなく処理継続。hsflowd が起動しなくても CONFIG_DB → APP_DB 書き込みは続行する | SWSS_LOG_ERROR ("Command '%s' failed with rc %d") | `sflowmgr.cpp:69-71` |

### sflowmgrd (CFG_SFLOW_SESSION_TABLE_NAME) — DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| per-port DEL 時にポートが `m_sflowPortConfMap` に未登録 | `sflowmgr.cpp:149-162` | `m_sflowPortConfMap.find(key)` が `end()` を返すため `erase` も `del()` も呼ばれずサイレントスキップ | なし | `sflowmgr.cpp:149-150` |
| `SFLOW_SESSION|all` DEL 時に `m_intfAllConf == true` (既に true) の状態 | `sflowmgr.cpp:556-563` | `if (!m_intfAllConf)` ブロックをスキップ。`sflowHandleSessionAll()` は呼ばれず、現状維持。DEL が実質 no-op になる | なし | `sflowmgr.cpp:556-563` |
| per-port DEL 後に `m_intfAllConf == true` かつ `findSamplingRate()` が ERROR_SPEED を返す | `sflowmgr.cpp:576-581` | `sflowGetGlobalInfo()` 内で `sample_rate=error` が APP_DB に書き込まれる | なし | `sflowmgr.cpp:576-581` |

### SflowOrch (APP_SFLOW_SESSION_TABLE) — SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `m_sflowStatus == false` (APP_SFLOW_TABLE SET が未到着) の状態で SESSION SET | `sfloworch.cpp:389-392` | `return` でループ全体を抜ける。未処理エントリが m_toSync に残留し次回 `doTask()` 呼び出しで再処理を試みる。APP_SFLOW_TABLE SET が来るまで永続的に先頭エントリが再試行対象となる | なし | `sfloworch.cpp:389-392` |
| `gPortsOrch->allPortsReady()` が false | `sfloworch.cpp:370-373` | `return` でループ全体をスキップ。m_toSync にエントリが残留し PortsOrch 完了後に処理される | なし | `sfloworch.cpp:370-373` |
| `rate == 0` (error 文字列由来) の新規ポート | `sfloworch.cpp:410-415` | `it++; continue` でスキップ。ポートが m_sflowPortInfoMap に登録されないため SAI 設定なし | なし | `sfloworch.cpp:410-415` |
| `sai_samplepacket_api->create_samplepacket()` が SAI エラーを返す | `sfloworch.cpp:29-39` | `SWSS_LOG_ERROR` + `handleSaiCreateStatus()` で判定。`task_success` 以外の場合 `parseHandleSaiStatusFailure()` が false を返し、上位の `sflowCreateSession()` も false を返す。呼び出し元でさらに `it++; continue` でスキップ | SWSS_LOG_ERROR ("Failed to create sample packet session with rate %d") | `sfloworch.cpp:33-38` |
| `sai_port_api->set_port_attribute()` (ingress/egress samplepacket) が SAI エラー | `sfloworch.cpp:122-132`, `138-150` | `SWSS_LOG_ERROR` + `handleSaiSetStatus()` で判定。false を返し、上位で `it++; continue` | SWSS_LOG_ERROR ("Failed to set session ... on port ...") | `sfloworch.cpp:126-132` |
| `sflowUpdateRate()` 中の旧セッション破棄 (`sflowDestroySession()`) が SAI エラー | `sfloworch.cpp:97-105` | `SWSS_LOG_ERROR` のみ。`m_sflowRateSampleMap.erase()` はスキップされ、旧セッションオブジェクトが残留する。rate カウントは `ref_count--` 済みで 0 になっているが SAI 上のセッションは残存する可能性あり | SWSS_LOG_ERROR ("Failed to clean old session ... with rate %d") | `sfloworch.cpp:99-105` |

### SflowOrch (APP_SFLOW_SESSION_TABLE) — DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| DEL 時にポートが `m_sflowPortInfoMap` に未登録 | `sfloworch.cpp:331-357` | `m_sflowPortInfoMap.find(port_id)` が `end()` を返すため何もしない。サイレントスキップ | なし | `sfloworch.cpp:331-332` |
| `sflowDelPort()` が SAI エラーで false を返す | `sfloworch.cpp:338-340` | `handleSflowSessionDel()` が false を返し、上位の DEL ループで `it++; continue` | なし (`sflowDelPort()` 内で SWSS_LOG_ERROR) | `sfloworch.cpp:338-340` |
| `sflowDestroySession()` が SAI エラーで false を返す (ref_count が 0 になった場合) | `sfloworch.cpp:349-354` | `handleSflowSessionDel()` が false を返す。`m_sflowRateSampleMap.erase()` は呼ばれず SAI 上のセッションが残存するがソフトウェア上は ref_count=0 で参照が切れた状態になる | SWSS_LOG_ERROR (sflowDestroySession 内) | `sfloworch.cpp:349-354` |

### ログ集計

| ログレベル | 出力箇所 | 内容 |
|---|---|---|
| SWSS_LOG_ERROR | `sflowmgr.cpp:70` | hsflowd service start/stop 失敗 |
| SWSS_LOG_ERROR | `sflowmgr.cpp:391` | ポートが m_sflowPortConfMap に未登録で findSamplingRate 失敗 |
| SWSS_LOG_ERROR | `sfloworch.cpp:33` | sai_samplepacket_api create 失敗 |
| SWSS_LOG_ERROR | `sfloworch.cpp:52` | sai_samplepacket_api remove 失敗 |
| SWSS_LOG_ERROR | `sfloworch.cpp:126` | SAI_PORT_ATTR_INGRESS_SAMPLEPACKET_ENABLE set 失敗 |
| SWSS_LOG_ERROR | `sfloworch.cpp:143` | SAI_PORT_ATTR_EGRESS_SAMPLEPACKET_ENABLE set 失敗 |
| SWSS_LOG_ERROR | `sfloworch.cpp:99` | 旧セッション破棄失敗 |
| SWSS_LOG_ERROR | `sfloworch.cpp:170` | SAI port ingress session delete 失敗 |
| SWSS_LOG_ERROR | `sfloworch.cpp:185` | SAI port egress session delete 失敗 |

<!-- /failure -->
