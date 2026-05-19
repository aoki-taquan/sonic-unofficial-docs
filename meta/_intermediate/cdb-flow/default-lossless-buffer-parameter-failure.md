# DEFAULT_LOSSLESS_BUFFER_PARAMETER — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-19 (q67-f-batch869)

調査対象:
- `sonic-net/sonic-swss` `cfgmgr/buffermgrdyn.cpp`
  ref `4305596156d70e9797e8a881b3d19b46de0bce0d`
  - `handleDefaultLossLessBufferParam()` L1978-2033
  - `isSharedHeadroomPoolEnabledInSai()` L2034-2051
  - `doTask(Consumer&)` ディスパッチャ L3574-3610

<!-- failure -->
## Phase D: 失敗挙動マトリクス

`buffermgrdyn` の `handleDefaultLossLessBufferParam()` (L1978-2033) が返す
`task_process_status` と、ディスパッチャ `doTask()` (L3574-3610) による最終処置を示す。

### ディスパッチャ共通処理 (buffermgrdyn.cpp:3591-3608)

| 返却ステータス | doTask 動作 | ログ | evidence |
|---|---|---|---|
| `task_success` (default) | エントリ erase → 次エントリ処理 | なし | `buffermgrdyn.cpp:3605-3606` |
| `task_need_retry` | エントリ残置 (`it++`) → 次回 doTask まで保留 | `SWSS_LOG_INFO "Unable to process table update. Will retry..."` | `buffermgrdyn.cpp:3597-3600` |
| `task_failed` | エントリ erase → **ループ継続**（残タスクも処理される） | `SWSS_LOG_ERROR "Failed to process table update"` | `buffermgrdyn.cpp:3593-3596` |
| `task_invalid_entry` | エントリ erase → ループ継続 | `SWSS_LOG_ERROR "Failed to process invalid entry, drop it"` | `buffermgrdyn.cpp:3601-3604` |
| テーブル未登録 | 全エントリ erase → return | `SWSS_LOG_ERROR "No handler for key:%s found."` | `buffermgrdyn.cpp:3580-3586` |

> `buffermgrdyn` の `task_failed` はエントリを drop するが doTask 全体を打ち切らない。他の orch (orchagent) とは異なり、同一 doTask 呼び出し内で残タスクの処理を継続する。

### handleDefaultLossLessBufferParam — 失敗・retry 経路 (L1978-2033)

| 失敗条件 | 検出箇所 | 返却ステータス | ログ | 復旧方法 |
|---|---|---|---|---|
| `ingress_lossless_pool` が `m_bufferPoolLookup` に未登録 | L1985-1988 | `task_need_retry` | `SWSS_LOG_INFO "%s has not been configured, need to retry"` | `BUFFER_POOL|ingress_lossless_pool` が `handleBufferPoolTable()` 経由でキャッシュに登録されると自動解消 |
| SET/DEL 以外の op コマンド受信 | L2009-2012 | `task_failed` | `SWSS_LOG_ERROR "Unsupported command %s received for DEFAULT_LOSSLESS_BUFFER_PARAMETER table"` | エントリ drop（再送が必要）。通常は発生しない（CONFIG_DB からの SET/DEL のみ想定） |
| `over_subscribe_ratio` が 0→非ゼロ遷移 かつ `m_portInitDone=true` かつ SHP が SAI に未反映 | L2019-2024 | `task_need_retry` | `SWSS_LOG_INFO "Shared headroom pool is enabled but has not been applied to SAI, retrying"` (`isSharedHeadroomPoolEnabledInSai()` 内 L2046) | `BufferOrch` が `ingress_lossless_pool.xoff` を APPL_STATE_DB に書き込むと自動解消 |

### isSharedHeadroomPoolEnabledInSai — retry 判定ロジック (L2034-2051)

この関数は `handleDefaultLossLessBufferParam` から `over_subscribe_ratio` を 0 から非ゼロに変更する際のみ呼ばれる。

```
1. recalculateSharedBufferPool() を呼び出し APPL_DB を flush
2. APPL_STATE_DB の BUFFER_POOL_TABLE|ingress_lossless_pool.xoff を hget
3. xoff が非ゼロであれば SAI 反映済み → return true
4. xoff が空またはゼロ → return false → task_need_retry
```

evidence: `buffermgrdyn.cpp:2034-2051`

### refreshSharedHeadroomPool 内部の失敗パス (L1592-1715)

`over_subscribe_ratio` 変更時に `refreshSharedHeadroomPool()` が呼ばれ、全 lossless プロファイルが再計算される。この再計算中にも失敗パスが存在する:

| 失敗条件 | 挙動 | ログ | evidence |
|---|---|---|---|
| Lua プラグインによるヘッドルーム計算失敗 | 個別プロファイルのヘッドルーム計算をスキップ（プロファイル更新なし） | `SWSS_LOG_WARN "Failed to calculate headroom for %s"` | `buffermgrdyn.cpp:622-648` |
| バッファプール再計算 Lua スクリプト失敗 | プール更新をスキップ | `SWSS_LOG_WARN "Lua scripts for buffer calculation were not executed successfully"` | `buffermgrdyn.cpp:815` |
| プール xoff 値が MMU サイズ超過 | xoff を無視してプールサイズのみ更新継続 | `SWSS_LOG_ERROR "Buffer pool %s: Invalid xoff %s, exceeding the mmu size %s, ignored xoff"` | `buffermgrdyn.cpp:757-758` |
| プールサイズが MMU サイズ超過 | エラーログのみ（配列更新は継続） | `SWSS_LOG_ERROR "Buffer pool %s: Invalid size %s, exceeding the mmu size %s"` | `buffermgrdyn.cpp:788` |

> refreshSharedHeadroomPool 内の失敗は `handleDefaultLossLessBufferParam` に `task_need_retry` / `task_failed` を伝播しない。Lua 計算失敗は WARN ログのみで処理続行する（SAI への反映が不完全になる可能性がある）。

### 失敗パターンサマリ

| # | トリガー | ステータス | 自動回復 | 最終処置 |
|---|---------|-----------|---------|---------|
| 1 | `ingress_lossless_pool` キャッシュ未登録 | `task_need_retry` | あり（BUFFER_POOL SET 到着後） | エントリ残置・自動再処理 |
| 2 | SET/DEL 以外の op | `task_failed` | なし（drop） | エントリ erase・ERROR ログ |
| 3 | SHP 有効化時 SAI 未反映 | `task_need_retry` | あり（APPL_STATE_DB 更新後） | エントリ残置・自動再処理 |
| 4 | Lua ヘッドルーム計算失敗 | —（handler 継続） | なし（WARN のみ） | プロファイル計算スキップ |

### config rollback

- `task_failed` や `task_invalid_entry` でエントリが drop されても、CONFIG_DB のエントリ自体は消えない。`m_defaultThreshold` / `m_overSubscribeRatio` の内部状態も変更前のまま残る（SET が途中で失敗した場合 CONFIG_DB と内部状態が乖離する）。
- 乖離を解消するには CONFIG_DB に同じ key を再度 SET するか、`buffermgrd` を再起動する必要がある。

### スキャン証跡

- `handleDefaultLossLessBufferParam` L1978-2033 全行読了
- `isSharedHeadroomPoolEnabledInSai` L2034-2051 全行読了
- `doTask(Consumer&)` L3574-3610 全行読了
- `refreshSharedHeadroomPool` L1592-1715 全行読了（Lua 失敗 WARN パス確認）

<!-- /failure -->
