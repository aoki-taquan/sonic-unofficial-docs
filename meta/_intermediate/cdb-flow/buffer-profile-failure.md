# BUFFER_PROFILE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-buffer-profile)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-swss/cfgmgr/buffermgrdyn.cpp`, `cfgmgr/buffermgr.cpp`, `orchagent/bufferorch.cpp`

### buffermgrdyn — handleBufferProfileTable() 失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `pool` フィールドが空文字列 | `handleBufferProfileTable()` L2738-2745 | `task_failed` → Consumer が当該エントリを廃棄 | `LOG_ERROR("Pool for BUFFER_PROFILE %s hasn't been specified")` | `buffermgrdyn.cpp:2740-2745` |
| `pool` が `m_bufferPoolLookup` に未登録 (プール未準備) | `handleBufferProfileTable()` L2708-2715 | `task_need_retry` → Consumer backoff 後に再試行 | `SWSS_LOG_INFO("Pool %s hasn't been configured yet, need retry")` | `buffermgrdyn.cpp:2710-2715` |
| `threshold_mode` がプールの `mode` と不一致 (`dynamic_th` vs `static` pool 等) | `handleBufferProfileTable()` L2724-2735 | `task_failed` → エントリ廃棄 | `LOG_ERROR("Buffer profile %s's mode %s doesn't match with buffer pool %s whose mode is %s")` | `buffermgrdyn.cpp:2726-2735` |
| `dynamic_th`/`static_th` の閾値モードが既存プロファイルの設定と不整合 | `handleBufferProfileTable()` L2771-2782 | `task_failed` → エントリ廃棄 | `LOG_ERROR("Buffer profile %s's mode %s doesn't align with buffer pool %s whose mode is %s")` | `buffermgrdyn.cpp:2773-2782` |
| `lossless=true` なのに egress pool を参照 (方向不一致) | `handleBufferProfileTable()` L2807-2814 | `task_failed` → エントリ廃棄 | `LOG_ERROR("BUFFER_PROFILE %s is ingress but referencing an egress pool %s")` | `buffermgrdyn.cpp:2809` |
| DEL 操作でプロファイルがポート PG から参照中 (`port_pgs` 非空) | `handleBufferProfileTable()` L2851-2858 | `task_need_retry` → 参照解除まで削除保留 | `SWSS_LOG_WARN("BUFFER_PROFILE %s for headroom override is referenced and cannot be removed for now")` | `buffermgrdyn.cpp:2857-2858` |
| DEL 対象が `static_configured` でない (`dynamic_calculated` な自動生成プロファイルを手動で DEL) | `handleBufferProfileTable()` L2862-2864 | `task_invalid_entry` → エントリ廃棄 | `LOG_ERROR("Try to remove non-static-configured profile %s")` | `buffermgrdyn.cpp:2862-2863` |
| `op` が `SET`/`DEL` 以外 | `handleBufferProfileTable()` L2882-2883 | `task_invalid_entry` → エントリ廃棄 | `LOG_ERROR("Unknown operation type %s")` | `buffermgrdyn.cpp:2882` |

### buffermgrdyn — headroom 超過・リソース枯渇

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| ポートの累積 headroom サイズが per-port 上限を超過 (速度/ケーブル長更新時) | `doSpeedOrCableLengthUpdateTask()` L1539-1546 | `task_failed` → プロファイル参照を `releaseProfile()` してロールバック | `LOG_ERROR("Update speed (%s) and cable length (%s) for port %s failed, accumulative headroom size exceeds the limit")` | `buffermgrdyn.cpp:1541-1546` |
| プロファイル更新時に参照中 PG でリソース制限違反 | `doUpdateBufferProfileForSize()` L1853-1857 | `task_failed` → プロファイル変更を APPL_DB へ反映しない | `LOG_ERROR("BUFFER_PROFILE %s cannot be updated because %s referencing it violates the resource limitation")` | `buffermgrdyn.cpp:1855-1857` |

### bufferorch — processBufferProfile() 失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| プロファイルが `m_pendingRemove` 状態で SET 到着 | `processBufferProfile()` L616-619 | `task_need_retry` → 削除完了後に再処理 | `SWSS_LOG_NOTICE("Entry %s %s is pending remove, need retry")` | `bufferorch.cpp:616-619` |
| `pool` 参照が未解決 (`ref_resolve_status::not_resolved`) | `processBufferProfile()` L646-649 | `task_need_retry` → プール到着後に再試行 | `SWSS_LOG_INFO("Missing or invalid pool reference specified")` | `bufferorch.cpp:646-649` |
| `pool` 参照解決その他エラー | `processBufferProfile()` L651-652 | `task_failed` → エントリ廃棄 | `LOG_ERROR("Resolving pool reference failed")` | `bufferorch.cpp:651-652` |
| `packet_discard_action` に `drop`/`trim` 以外の値 | `processBufferProfile()` L740-743 | `task_failed` → エントリ廃棄 | `LOG_ERROR("Failed to parse buffer profile(%s) field(%s): invalid value(%s)")` | `bufferorch.cpp:740-743` |
| `packet_discard_action=trim` かつ `isTrimmingProhibited()` が true (ingress PG/profile list への適用) | `processBufferProfile()` L757-763 | `task_failed` → エントリ廃棄 | `LOG_ERROR("Failed to configure buffer profile(%s): trimming is prohibited by dependency constraint check")` | `bufferorch.cpp:757-763` |
| SAI `set_buffer_profile_attribute` が `SAI_STATUS_ATTR_NOT_IMPLEMENTED_0` (ASIC 非対応属性の SET) | `processBufferProfile()` L773-776 | `task_ignore` → ハードウェア非反映のまま成功扱い | `SWSS_LOG_NOTICE("...not implemented. Ignoring it")` | `bufferorch.cpp:773-776` |
| SAI `set_buffer_profile_attribute` がその他エラー (1回リトライ後も失敗) | `processBufferProfile()` L787-795 | `handleSaiSetStatus()` に委譲 → 通常 `task_need_retry` または `task_failed` | `LOG_ERROR("Failed to modify buffer profile, name:..., will retry once")` | `bufferorch.cpp:791` |
| SAI `create_buffer_profile` 失敗 | `processBufferProfile()` L803-810 | `handleSaiCreateStatus()` に委譲 → 通常 `task_need_retry` | `LOG_ERROR("Failed to create buffer profile %s with type %s, rv:%d")` | `bufferorch.cpp:805` |
| DEL 時にプロファイルが PG/Queue から参照中 | `processBufferProfile()` L837-843 | `m_pendingRemove = true` → `task_need_retry` → 参照解除まで削除保留 | `SWSS_LOG_NOTICE("Can't remove object %s due to being referenced (%s)")` | `bufferorch.cpp:839-843` |
| SAI `remove_buffer_profile` 失敗 | `processBufferProfile()` L860-866 | `handleSaiRemoveStatus()` に委譲 | `LOG_ERROR("Failed to remove buffer profile %s with type %s, rv:%d")` | `bufferorch.cpp:862` |
| `op` が `SET`/`DEL` 以外 | `processBufferProfile()` L885-886 | `task_invalid_entry` → エントリ廃棄 | `LOG_ERROR("Unknown operation type %s")` | `bufferorch.cpp:885` |

### SAI create-only 属性への SET — サイレントスキップ挙動

| 属性 | 動作 | evidence |
|---|---|---|
| `pool` (既存 SAI オブジェクトへの変更) | SAI 呼び出しせずスキップ (`continue`)。エラーなし | `bufferorch.cpp:654-659` |
| `dynamic_th` (既存 SAI オブジェクトへの threshold_mode 変更) | `THRESHOLD_MODE` SAI 属性への SET をスキップ。`SHARED_DYNAMIC_TH` 値は SET を試行 | `bufferorch.cpp:692-706` |
| `static_th` (既存 SAI オブジェクトへの threshold_mode 変更) | `THRESHOLD_MODE` SAI 属性への SET をスキップ。`SHARED_STATIC_TH` 値は SET を試行 | `bufferorch.cpp:710-724` |

### buffermgr (static model) — BUFFER_PROFILE パススルー失敗

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| ポートの速度/ケーブル長の組み合わせに対応する PG プロファイルがテンプレートに未定義 | `doSpeedUpdateTask()` L238-242 | `task_invalid_entry` → エントリ廃棄。BUFFER_PROFILE は作成されない | `LOG_ERROR("No PG profile configured for speed %s and cable length %s")` | `buffermgr.cpp:240-242` |
| PG lossless pool が未作成 (static model 初期化中に speed 通知が来た場合) | `doSpeedUpdateTask()` L252-258 | `task_need_retry` → pool 作成後に再試行 | `SWSS_LOG_INFO("PG lossless pool is not yet created")` | `buffermgr.cpp:257-258` |
| ケーブル長が未設定のままポート速度通知が来た | `doSpeedUpdateTask()` L152-155 | `task_need_retry` → ケーブル長設定後に再試行 | `SWSS_LOG_INFO("Unable to create/update PG profile for port %s. Cable length is not set")` | `buffermgr.cpp:154-155` |

### リトライ・廃棄の判断フロー

```
handleBufferProfileTable() / processBufferProfile()
  ↓
  task_need_retry   → Consumer が backoff 後に再試行
                      (例: pool 未準備, pendingRemove 状態, pool 参照未解決, DEL 参照中)
  task_failed       → Consumer が当該エントリを廃棄
                      (例: pool 空, threshold_mode 不一致, lossless+egress, trim 禁止, headroom 超過)
  task_invalid_entry → Consumer が当該エントリを廃棄
                      (例: 不明な op, 非 static_configured プロファイルの DEL)
  task_ignore       → bufferorch が当該 SET を成功扱いで無視
                      (例: SAI_STATUS_ATTR_NOT_IMPLEMENTED_0)
  task_success      → 正常完了
```

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `task_need_retry` (BUFFER_PROFILE 関連) | 7 | `buffermgrdyn.cpp:2715, 2858; bufferorch.cpp:619, 649, 843; buffermgr.cpp:155, 258` |
| `task_failed` (BUFFER_PROFILE 関連) | 7 | `buffermgrdyn.cpp:2735, 2745, 2782, 2814, 1546, 1857; bufferorch.cpp:652, 743, 763` |
| `task_invalid_entry` (BUFFER_PROFILE 関連) | 3 | `buffermgrdyn.cpp:2863, 2882; bufferorch.cpp:242, 885` |
| `task_ignore` | 1 | `bufferorch.cpp:776` |
| create-only スキップ | 3 属性 | `bufferorch.cpp:656-659, 694-696, 712-714` |
| `LOG_ERROR` (BUFFER_PROFILE 直接) | 12 | buffermgrdyn.cpp:2726, 2740, 2773, 2809, 2862, 1541, 1855; bufferorch.cpp:651, 740, 759, 791, 805, 862; buffermgr.cpp:240 |

<!-- /failure -->
