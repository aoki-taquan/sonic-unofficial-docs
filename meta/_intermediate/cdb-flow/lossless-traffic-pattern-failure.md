# LOSSLESS_TRAFFIC_PATTERN — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-19 (chore/q67-f-batch1031)

調査対象:
- `sonic-net/sonic-swss` `cfgmgr/buffermgrdyn.cpp`
  - `calculateHeadroomSize()` L603-649
  - `allocateProfile()` L961-1012
  - `doTask(Consumer&)` ディスパッチャ L3574-3610
- `sonic-net/sonic-swss` `cfgmgr/buffer_headroom_mellanox.lua` L91-94
- `sonic-net/sonic-swss` `cfgmgr/buffer_headroom_barefoot.lua` L80-83

<!-- failure -->
## Phase D: 失敗挙動マトリクス

`LOSSLESS_TRAFFIC_PATTERN` は `m_bufferTableHandlerMap` に登録されていない。
`buffermgrdyn` が CONFIG_DB をサブスクライブする対象テーブルではなく、ベンダー別 Lua プラグイン
(`buffer_headroom_<vendor>.lua`) が `calculateHeadroomSize()` の呼び出し時に CONFIG_DB から
直接 `KEYS LOSSLESS_TRAFFIC_PATTERN*` + `HGETALL` でフェッチする構造になっている。

したがって「`LOSSLESS_TRAFFIC_PATTERN` の変更が `task_need_retry` / `task_failed` を返す」という直接パスは存在せず、
障害の影響は Lua スクリプトから `calculateHeadroomSize()` を経由して上位の `allocateProfile()` / `handleBufferPgTable()` に伝播する。

### A. Lua 呼び出し失敗 — `calculateHeadroomSize()` キャッチ

| 失敗条件 | 発生源 | `calculateHeadroomSize` の動作 | 影響 | evidence |
|---|---|---|---|---|
| `LOSSLESS_TRAFFIC_PATTERN` エントリが 0 件 → `lossless_traffic_keys[1]` が `nil` → `HGETALL nil` → Lua エラー | `buffer_headroom_mellanox.lua:91-94` / `buffer_headroom_barefoot.lua:80-83` | `catch (...)` で例外を捕捉 → `SWSS_LOG_WARN "Lua scripts for headroom calculation were not executed successfully"` | `headroom.xoff` / `headroom.xon` / `headroom.size` が空文字列のまま。BUFFER_PROFILE が空フィールドで APPL_DB に書き込まれる | `buffermgrdyn.cpp:647-649` |
| `mtu` フィールドが欠落または非数値 → `tonumber(nil)` → Lua 算術エラー | `buffer_headroom_mellanox.lua:96-98` / `buffer_headroom_barefoot.lua:87-89` | 上と同経路 | 同上（headroom 全フィールドが空） | `buffermgrdyn.cpp:647-649` |
| `small_packet_percentage` フィールドが欠落または非数値 → `tonumber(nil)` → Lua 算術エラー | `buffer_headroom_mellanox.lua:100-101` / `buffer_headroom_barefoot.lua:89-92` | 上と同経路 | 同上 | `buffermgrdyn.cpp:647-649` |
| Lua スクリプト自体が存在しない (プラットフォーム名不一致) | `buffermgrdyn.cpp:76-79` 初期化失敗 | `m_headroomSha` が空 → `runRedisScript` がスキップされ `ret.empty()` → `SWSS_LOG_WARN "Failed to calculate headroom"` | headroom フィールドが空のまま APPL_DB に書き込まれる | `buffermgrdyn.cpp:620-626` |

> **重要**: `calculateHeadroomSize()` は失敗しても例外を呼び元に伝播させず、空フィールドのまま `return` する。`allocateProfile()` 側は headroom 計算失敗を検知せず `task_success` を返す（L1011）。

### B. 下流 SAI 反映での retry 検出

`calculateHeadroomSize()` が空 xoff を返した場合、`BUFFER_PROFILE` が空 xoff で APPL_DB に書き込まれる。
その後 `handleBufferPgTable()` が当該プロファイルの SAI 反映を確認するために `isProfileAppliedToSai()` (L2054-2101) を呼ぶ。

| 確認ポイント | 失敗条件 | 挙動 | evidence |
|---|---|---|---|
| `m_applStateBufferProfileTable.hget(profileName, "xoff", xoff)` | xoff が空 (Lua 失敗起因) | `SWSS_LOG_INFO "Lossless buffer profile %s has not been applied to SAI yet, retrying"` → `return false` | `buffermgrdyn.cpp:2067-2070` |
| xoff 値が APPL_DB の期待値と不一致 | Lua 部分成功で xoff 計算値が誤っている場合 | `SWSS_LOG_INFO "... xoff mismatch ..., retrying"` → `return false` | `buffermgrdyn.cpp:2072-2075` |

`isProfileAppliedToSai()` が `false` を返すと呼び元 (`handleBufferPgTable()` 等) が `task_need_retry` を返し、
次回 doTask で再試行される。**ただし再試行のたびに `calculateHeadroomSize()` が再実行され、
`LOSSLESS_TRAFFIC_PATTERN` が依然 0 件であれば同じ Lua エラーが繰り返される**（無限 retry ループ）。

### C. ディスパッチャ共通処理 (buffermgrdyn.cpp:3591-3608)

`LOSSLESS_TRAFFIC_PATTERN` 自体のエントリ変更は `m_bufferTableHandlerMap` に未登録のため
`SWSS_LOG_ERROR "No handler for key:%s found."` が出力され全エントリが erase される。
この挙動は通常問題にならない（`LOSSLESS_TRAFFIC_PATTERN` の変更通知は `buffermgrdyn` のサブスクリプション対象外であるため、通常 `m_toSync` に入らない）。

| ステータス | doTask 動作 | evidence |
|---|---|---|
| `task_need_retry` | エントリ残置 (`it++`) → 次回 doTask まで保留 | `buffermgrdyn.cpp:3597-3600` |
| `task_failed` | エントリ erase + ERROR ログ | `buffermgrdyn.cpp:3593-3596` |

### D. 失敗パターンサマリ

| # | トリガー | 直接挙動 | 下流挙動 | 自動回復 |
|---|---------|---------|---------|---------|
| 1 | `LOSSLESS_TRAFFIC_PATTERN` エントリ 0 件 | Lua エラー → `catch(...)` WARN | headroom 空フィールド → APPL_DB 書込 → SAI 反映チェック失敗 → `task_need_retry` ループ | `LOSSLESS_TRAFFIC_PATTERN|AZURE` を CONFIG_DB に SET すると Lua 成功 → ループ解消 |
| 2 | `mtu` / `small_packet_percentage` 欠落または非数値 | 同上 | 同上 | 正しい値を SET して再試行 |
| 3 | Lua スクリプトファイル不存在 (platform 名不一致) | `ret.empty()` → WARN | headroom 空フィールド → 以降同じ経路 | プラットフォーム名修正 + `swss` コンテナ再起動 |

### スキャン証跡

- `calculateHeadroomSize()` L603-649 全行読了
- `allocateProfile()` L961-1012 全行読了
- `isProfileAppliedToSai()` L2054-2101 全行読了
- `doTask(Consumer&)` L3574-3610 全行読了
- `buffer_headroom_mellanox.lua` L91-106 全行読了
- `buffer_headroom_barefoot.lua` L80-95 全行読了

<!-- /failure -->
