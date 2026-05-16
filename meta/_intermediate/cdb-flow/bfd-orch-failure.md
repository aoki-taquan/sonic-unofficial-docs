# bfdorch — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-bfd-orch)

ソース: `sonic-net/sonic-swss/orchagent/bfdorch.cpp` (HEAD)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

### capability 照会・初期化の失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `sai_query_attribute_capability(SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY)` が `SAI_STATUS_SUCCESS` 以外を返す | `register_bfd_state_change_notification()` L276-283 | `false` を返却 → 以降 `create_bfd_session()` が即 reject | `LOG_ERROR` ("Unable to query the BFD change notification capability") | `bfdorch.cpp:276-283` |
| capability 取得は成功したが `capability.set_implemented == false` (BFD 通知未実装 ASIC) | `register_bfd_state_change_notification()` L286-289 | `false` を返却 → 以後セッション作成不能 | `LOG_ERROR` ("BFD register change notification not supported") | `bfdorch.cpp:286-289` |
| 通知ハンドラ登録 (`sai_switch_api->set_switch_attribute`) 失敗 | `register_bfd_state_change_notification()` L297-300 | `false` を返却 → 以後セッション作成不能 | `LOG_ERROR` ("Failed to register BFD notification handler") | `bfdorch.cpp:297-300` |
| `sai_query_attribute_capability(SUPPORTED_IPV4/IPV6_BFD_SESSION_OFFLOAD_TYPE)` 失敗 | `BgpGlobalStateOrch::offload_supported()` L769-772 | `false` 返却 → `use_software_bfd=true` 経路へ縮退 | `LOG_ERROR` ("Unable to query BFD offload capability") | `bfdorch.cpp:769-772` |
| `capability.get_implemented == false` (offload type 取得未実装) | `offload_supported()` L774-777 | `false` 返却 → software BFD 経路へ縮退 (致命的でない) | なし (silent) | `bfdorch.cpp:774-777` |
| offload type 取得 (`sai_switch_api->get_switch_attribute`) が失敗、または `u32list.count == 0` | `offload_supported()` L784-790 | `false` 返却 → software BFD 経路へ縮退 | `LOG_ERROR` ("Could not get supported BFD offload type, rv: %d") | `bfdorch.cpp:784-790` |

### SET 処理 (`create_bfd_session()`) の失敗経路

| 失敗条件 | 検出箇所 | 戻り値 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|---|
| `register_bfd_state_change_notification()` が事前に false を返している (capability 不在) | L309-312 | `false` | セッション作成 reject、SAI 呼ばず | `LOG_ERROR` ("BFD session for %s cannot be created") | `bfdorch.cpp:307-313` |
| 同一キーのセッションが既に `bfd_session_map` に存在 | L316-319 | `true` (no-op) | 重複作成スキップ。SAI 未呼出・STATE_DB 更新なし | `LOG_ERROR` ("BFD session for %s already exists") | `bfdorch.cpp:316-319` |
| key 分割で vrf 名が取れない | L323-326 | `false` | task 再試行対象 | `LOG_ERROR` ("Failed to parse key %s, no vrf is given") | `bfdorch.cpp:323-326` |
| key 分割で interface 名 (alias) が取れない | L330-333 | `false` | task 再試行対象 | `LOG_ERROR` ("Failed to parse key %s, no ifname is given") | `bfdorch.cpp:330-333` |
| `type` フィールドが `async_active`/`async_passive`/`demand_active`/`demand_passive` 以外 | L385 | (継続) | enum 値が更新されず以前の値で進行 | `LOG_ERROR` ("Invalid BFD session type %s") | `bfdorch.cpp:385` |
| 未知の属性フィールドが投入された | L406 | (継続) | 該当 fv は無視して次へ | `LOG_ERROR` ("Unsupported BFD attribute %s") | `bfdorch.cpp:402-406` |
| `local_addr` (src_ip) が未指定 | L409-413 | `true` (drop) | セッション作成スキップ。再試行されない (true を返すため task は consume 済み扱い) | `LOG_ERROR` ("Failed to create BFD session %s because source IP is not provided") | `bfdorch.cpp:409-413` |
| `alias != "default"` だが `gPortsOrch->getPort()` が失敗 (PORT 未準備) | L485-488 | `false` | task 再試行対象 (`doTask()` で next iteration へ繰越) | `LOG_ERROR` ("Failed to locate port %s") | `bfdorch.cpp:485-488` |
| `alias != "default"` かつ `dst_mac` 未指定 (hardware lookup 無効に MAC 必須) | L491-495 | `true` (drop) | セッション作成スキップ。再試行されない | `LOG_ERROR` ("destination MAC address required when hardware lookup not valid") | `bfdorch.cpp:491-495` |
| `alias != "default"` かつ `vrf_name != "default"` (HW lookup 無効に VRF 非対応) | L498-502 | `true` (drop) | セッション作成スキップ。再試行されない | `LOG_ERROR` ("vrf is not supported when hardware lookup not valid") | `bfdorch.cpp:498-502` |
| `alias == "default"` かつ `dst_mac` が指定された (HW lookup 有効に MAC 非対応) | L523-527 | `true` (drop) | セッション作成スキップ。再試行されない | `LOG_ERROR` ("destination MAC address not supported when hardware lookup valid") | `bfdorch.cpp:523-527` |
| `sai_bfd_api->create_bfd_session()` 1 回目失敗 | L547-552 | (retry へ) | `retry_create_bfd_session()` で UDP src port を変えながら最大 `NUM_BFD_SRCPORT_RETRIES = 3` 回再試行 | `LOG_WARN` ("BFD create using port number %d failed. Retrying with port number %d") | `bfdorch.cpp:547-552, 585-606` |
| retry 3 回後も `SAI_STATUS_SUCCESS` 以外 | L554-562 | `handleSaiCreateStatus()` の結果次第 (`task_success` 以外なら `parseHandleSaiStatusFailure()` で `false`/`true` 返却) | recover 不能なら task fail。recover 可能 (RETRY) なら次 iteration へ繰越。critical なら orchagent abort | `LOG_ERROR` ("Failed to create bfd session %s, rv:%d") | `bfdorch.cpp:554-562` |

### DEL 処理 (`remove_bfd_session()`) の失敗経路

| 失敗条件 | 検出箇所 | 戻り値 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|---|
| `bfd_session_map` にキーが存在しない (未作成セッションへの DEL) | L611-614 | `true` (no-op) | STATE_DB / map 操作なし | `LOG_ERROR` ("BFD session for %s does not exist") | `bfdorch.cpp:611-614` |
| `sai_bfd_api->remove_bfd_session()` 失敗 | L619-626 | `handleSaiRemoveStatus()` の結果次第 | recover 不能なら task fail → 次 iteration へ繰越。recover 可能なら破棄 | `LOG_ERROR` ("Failed to remove bfd session %s, rv:%d") | `bfdorch.cpp:619-626` |
| 不明な op (SET/DEL 以外) | `doTask()` L213 / L836 | (continue) | task を consume してスキップ | `LOG_ERROR` ("Unknown operation type %s") | `bfdorch.cpp:213, 836` |

### 検出ロジック補足

- **`return true` vs `return false` の意味**: `Orch` フレームワーク慣行で、`create_bfd_session()` が `true` を返すと `doTask()` は当該エントリを **consume** (`it_prev = consumer.m_toSync.erase(it_prev)`) し再試行しない。`false` は **retry 対象** として残す。`local_addr` 未指定や `dst_mac` 制約違反など「ユーザー設定上の誤り」は `true` を返して drop し、PORT/VRF 未準備など「依存リソースの一時的未到達」は `false` を返して次 epoch でリトライさせる設計 (`bfdorch.cpp:155-188`)。
- **UDP src port retry**: `NUM_BFD_SRCPORT_RETRIES = 3`、ポート範囲 `BFD_SRCPORTINIT = 49152` 〜 `BFD_SRCPORTMAX = 65535` (`bfdorch.cpp:20-22`)。`update_port_number()` は `bfd_src_port()` で擬似ランダムにポートを再生成し attrs を上書き。
- **capability 不在時の致命的挙動**: `m_bfdStateChangeNotificationSupported == false` のまま起動した swss コンテナでは、後から SAI 実装が改善されても **再起動なしには hardware BFD が動かない**。capability 評価は `BfdOrch` コンストラクタで 1 度のみ実施される (`bfdorch.cpp:111-139`)。
- **`use_software_bfd` 経路では SAI 失敗が発生しない**: SAI API を呼ばず STATE_DB `SOFTWARE_BFD_SESSION_TABLE` に転記するのみ (`bfdorch.cpp:133-139, 182-188`)。失敗経路は software BFD 経路では大幅に減る (`local_addr` 未指定など事前検証のみ)。
- **SAI status の handler**: `handleSaiCreateStatus(SAI_API_BFD, status)` / `handleSaiRemoveStatus(SAI_API_BFD, status)` は `orchagent/orch.cpp` 側で SAI status を `task_need_retry` / `task_failed` / `task_success` 等にマップし、critical (例: `SAI_STATUS_TABLE_FULL`) なら `parseHandleSaiStatusFailure()` で `false` を返却 → task 再試行。`SAI_STATUS_NOT_IMPLEMENTED` 等の取り扱いは SAI ベンダ実装に依存する。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `LOG_ERROR` (bfdorch.cpp 内) | 16 | `bfdorch.cpp:213, 282, 288, 299, 311, 318, 325, 332, 385, 406, 411, 487, 493, 500, 525, 556, 613, 621, 789, 832, 836` (一部重複) |
| `LOG_WARN` | 1 | `bfdorch.cpp:585-586` (src port retry) |
| `return false` (SET 失敗) | 6 | `bfdorch.cpp:283, 289, 300, 312, 326, 333, 488, 772` |
| `return true` (silent drop) | 4 | `bfdorch.cpp:319, 495, 502, 527, 614` |
| SAI status check (`status != SAI_STATUS_SUCCESS`) | 6 | `bfdorch.cpp:280, 297, 549, 554, 619, 769` |
| retry ループ | 1 | `retry_create_bfd_session()` L592-607 (max 3 回) |
<!-- /failure -->
