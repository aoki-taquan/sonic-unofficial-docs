# CABLE_LENGTH Phase D — 失敗挙動・retry 分岐 中間ファイル

<!-- phase: D (failure-behavior) -->
<!-- source: sonic-swss/cfgmgr/buffermgrdyn.cpp, cfgmgr/buffermgr.cpp -->

## 対象ページ

`docs/reference/config-db/cable-length.md`

## 検出した失敗・retry 分岐

### [dynamic モード] buffermgrdyn.cpp — handleCableLenTable

#### 1. speed 未設定 → 計算延期 (no retry)

- **箇所**: `buffermgrdyn.cpp:2155-2159`
- **条件**: `portInfo.effective_speed.empty()` が真
- **挙動**: `SWSS_LOG_WARN("Speed for %s hasn't been configured yet, unable to calculate headroom")` を出力して `continue`。当該ポートはスキップ、他ポートの処理は継続。retry キューには積まれない。
- **復帰**: speed が CONFIG_DB の `PORT` テーブルから届いたタイミングで `handlePortTable` が `refreshPgsForPort` を呼び出す。

#### 2. PORT_INITIALIZING → PORT_READY へ遷移してから refreshPgsForPort

- **箇所**: `buffermgrdyn.cpp:2182-2184`
- **条件**: `portInfo.state == PORT_INITIALIZING` かつ speed と cable_length が両方揃った
- **挙動**: `portInfo.state = PORT_READY` にセットしてから `refreshPgsForPort` を呼ぶ。cable_length が先着した場合は mtu を `DEFAULT_MTU_STR="9100"` で仮置きする (line 2174)。

#### 3. refreshPgsForPort が task_need_retry → 即 return

- **箇所**: `buffermgrdyn.cpp:2200-2201`
- **条件**: `refreshPgsForPort` の戻り値が `task_need_retry`
- **挙動**: `handleCableLenTable` は即 `task_need_retry` を返し、Consumer フレームワークがメッセージを再キューに戻す。後続ポートは処理されない。
- **典型的発生**: `allocateProfile` 内でバッファプールがまだ生成されていないとき (buffermgrdyn.cpp:978-979)。

#### 4. refreshPgsForPort が task_failed → failed_item_count 加算

- **箇所**: `buffermgrdyn.cpp:2202-2205`
- **条件**: `refreshPgsForPort` の戻り値が `task_failed`
- **挙動**: `failed_item_count` をインクリメントして処理継続。全ポート完了後 `failed_item_count > 0` なら `task_failed` 返却。
- **典型的発生**: headroom 上限超過 (`buffermgrdyn.cpp:1541-1546`)。

#### 5. headroom 上限超過 → task_failed (non-recoverable)

- **箇所**: `buffermgrdyn.cpp:1537-1546`
- **条件**: `isHeadroomResourceValid()` が偽
- **挙動**: `SWSS_LOG_ERROR("Update speed (%s) and cable length (%s) for port %s failed, accumulative headroom size exceeds the limit")` を出力し `task_failed` 返却。設定変更 (cable 短縮 or PG 削減) が必要。

#### 6. PORT_ADMIN_DOWN → no-op

- **箇所**: `buffermgrdyn.cpp:2191-2194`
- **条件**: `portInfo.state == PORT_ADMIN_DOWN`
- **挙動**: `SWSS_LOG_INFO("Nothing to be done when port %s's cable length updated")` のみ出力。`task_success` 返却。cable_length キャッシュ (`portInfo.cable_length`) は更新済みなので、admin-up 時に正しい値で計算される。

#### 7. Lua headroom 計算失敗 → WARN (サイズは空)

- **箇所**: `buffermgrdyn.cpp:622, 648`
- **条件**: Lua スクリプトの戻り値が空またはフォーマット不正
- **挙動**: `SWSS_LOG_WARN("Failed to calculate headroom for %s")` 出力。プロファイルの xon/xoff/size フィールドが空のまま APPL_DB に書かれる危険あり。

---

### [static モード] buffermgr.cpp — doCableTask / doSpeedUpdateTask

#### 8. cable_length == "None" → silent skip

- **箇所**: `buffermgr.cpp:104`
- **条件**: `cable_length == "None"`
- **挙動**: `doCableTask` がキャッシュを更新せず `task_success` 返却。ログなし。

#### 9. pg_profile_lookup.ini にエントリなし → task_invalid_entry

- **箇所**: `buffermgr.cpp:238-242`
- **条件**: `m_pgProfileLookup[speed][cable]` にエントリが存在しない
- **挙動**: `SWSS_LOG_ERROR("Unable to create/update PG profile for port %s. No PG profile configured for speed %s and cable length %s")` 出力、`task_invalid_entry` 返却。エントリはドロップ（retry なし）。`pg_profile_lookup.ini` にその speed/cable 組み合わせを追加するか、ケーブル長を有効値に変更する必要がある。

#### 10. PORT ステータス未取得 → task_need_retry

- **箇所**: `buffermgr.cpp:165-170`
- **条件**: `m_portStatusLookup.count(port) == 0`
- **挙動**: `SWSS_LOG_INFO("pfc_enable status is not available for port %s")` 出力、`task_need_retry` 返却。`PORT_QOS_MAP` 通知が来るまで待機。

#### 11. lossless pool 未生成 → task_need_retry

- **箇所**: `buffermgr.cpp:253-258`
- **条件**: `getPgPoolMode()` が空文字を返す
- **挙動**: `SWSS_LOG_INFO("PG lossless pool is not yet created")` 出力、`task_need_retry` 返却。スイッチ初期化が完了してプール生成されると自動復帰。

---

## 失敗パターン一覧表

| # | モード | 条件 | 戻り値 | retry? | ログレベル |
|---|--------|------|--------|--------|-----------|
| 1 | dynamic | speed 未設定 | (continue) | なし | WARN |
| 2 | dynamic | PORT_INITIALIZING + speed/cable 揃い | task_success (遷移) | — | INFO |
| 3 | dynamic | allocateProfile → pool 未準備 | task_need_retry | あり | INFO |
| 4 | dynamic | headroom 上限超過 | task_failed | なし | ERROR |
| 5 | dynamic | PORT_ADMIN_DOWN | task_success | — | INFO |
| 6 | dynamic | Lua 計算失敗 | (継続、サイズ空) | なし | WARN |
| 7 | static | cable="None" | task_success | なし | (なし) |
| 8 | static | pg_profile_lookup miss | task_invalid_entry | なし | ERROR |
| 9 | static | PORT status 未取得 | task_need_retry | あり | INFO |
| 10 | static | lossless pool 未生成 | task_need_retry | あり | INFO |
