# WARM_RESTART フィールド暗黙デフォルト調査 (Phase A)

調査日: 2026-05-14
対象: `docs/reference/config-db/warm-restart.md`

---

## フィールド一覧と暗黙デフォルト

### `module` (key)

- YANG enum: `bgp` / `teamd` / `swss` / `system` のみ。デフォルトなし。
- キー不在 = エントリ自体が存在しない → 各 consumer は warm-restart 無効と同義に扱う。

### `bgp_eoiu`

- YANG `default` 節: **なし**。
- コード由来デフォルト:
  - `supervisord.conf.j2` (sonic-buildimage/dockers/docker-fpm-frr) の条件分岐:
    ```jinja2
    {% if WARM_RESTART.bgp.bgp_eoiu is defined and WARM_RESTART.bgp.bgp_eoiu == "true" %}
    [program:bgp_eoiu_marker]
    ```
  - フィールド不在 (未設定) = `bgp_eoiu_marker` プロセスが supervisord に登録されない。
  - **実質デフォルト = `false` 相当 (EOIU 待機なし)**。
  - `config warm_restart bgp_eoiu` コマンドの `default='true'` は **CLI 引数省略時のデフォルト**であり、DB 書き込み前のデフォルトではない (config/main.py:4083)。
  - EOIU なしの場合、fpmsyncd は `bgp_timer` (または `DEFAULT_ROUTING_RESTART_INTERVAL = 120 秒`) のタイムアウト後に reconcile する。

### `bgp_timer`

- YANG `default` 節: **なし**。
- コード由来デフォルト (`fpmsyncd.cpp:46,157-165`):
  ```cpp
  const uint32_t DEFAULT_ROUTING_RESTART_INTERVAL = 120;
  time_t warmRestartIval = sync.getWarmStartHelper().getRestartTimer();
  if (!warmRestartIval) {
      warmStartTimer.setInterval(timespec{DEFAULT_ROUTING_RESTART_INTERVAL, 0});
  }
  ```
  - `getRestartTimer()` → `WarmStart::getWarmStartTimer("bgp", "bgp")` → `WARM_RESTART|bgp` の `bgp_timer` フィールドを hget。
  - 未設定または `strtoul` が 0 / ULONG_MAX の場合 → **ハードコードフォールバック: 120 秒**。
  - YANG range `1..3600` は validation 層のみ。実装上の上限は `MAXIMUM_WARMRESTART_TIMER_VALUE = 9999`。
- **既存ドキュメントの「典型値 300 秒」は典拠不明**。実装フォールバックは 120 秒。

### `teamsyncd_timer`

- YANG `default` 節: **なし**。
- コード由来デフォルト:
  - `WarmStart::getWarmStartTimer("teamsyncd", "teamd")` が `WARM_RESTART|teamd` の `teamsyncd_timer` をクエリ。
  - 未設定 = 0 が返る (`strtoul` の空文字列 → 0)。
  - `AppRestartAssist` コンストラクタ (`warmRestartAssist.cpp:43-46`) でフォールバック:
    ```cpp
    m_reconcileTimer = DEFAULT_INTERNAL_TIMER_VALUE;  // = 5 秒
    ```
  - **実質デフォルト: 5 秒** (AppRestartAssist::DEFAULT_INTERNAL_TIMER_VALUE)。
  - ただし teamsyncd は `AppRestartAssist` を直接使うのではなく、teamd container 側の独自タイマロジックを持つ可能性あり (teamd.sh は timer 値を読まず SIGUSR1 でシャットダウンを制御)。実質的な reconcile タイマは teamd 内部の値。

### `neighsyncd_timer`

- YANG `default` 節: **なし**。
- コード由来デフォルト (`neighsync.h:10`, `neighsync.cpp:30`):
  ```cpp
  #define DEFAULT_NEIGHSYNC_WARMSTART_TIMER 5
  m_AppRestartAssist = new AppRestartAssist(pipelineAppDB, "neighsyncd", "swss", DEFAULT_NEIGHSYNC_WARMSTART_TIMER);
  ```
  - `AppRestartAssist` コンストラクタ (`warmRestartAssist.cpp:55-65`):
    - `WarmStart::getWarmStartTimer("neighsyncd", "swss")` = `WARM_RESTART|swss` の `neighsyncd_timer` をクエリ。
    - 設定値が有効 (!=0, !=ULONG_MAX, <=9999) なら設定値を使用。
    - 未設定の場合 `defaultWarmStartTimerValue = 5` → `m_reconcileTimer = 5 秒`。
  - **実質デフォルト: 5 秒** (DEFAULT_NEIGHSYNC_WARMSTART_TIMER)。
  - 既存ドキュメントの「典型値 110 秒」は `RESTORE_NEIGH_WAIT_TIME_OUT = 180` (隣接テーブル restore 待ちタイムアウト) と混同している可能性がある。110 秒はコード中に明示的な根拠なし。

---

## 追加検出事項

### dead field / 書き込み順依存

- `bgp_timer` は `WARM_RESTART|bgp` に書かれるが、`WarmStart::getWarmStartTimer` のクエリは `timer_name = app_name + "_timer"` の形式なので `getWarmStartTimer("bgp", "bgp")` → `bgp_timer` フィールドが正しく取得される。
- `fpmsyncd` は `eoiu_hold` という **undocumented フィールド** も `getWarmStartTimer("eoiu_hold", "bgp")` で `WARM_RESTART|bgp` の `eoiu_hold_timer` をクエリする (`fpmsyncd.cpp:226`)。このフィールドは YANG にもドキュメントにも存在しない。未設定なら `DEFAULT_EOIU_HOLD_INTERVAL = 3 秒` にフォールバック。

### warm-restart 有効化の実際の経路

- `check_warm_boot()` (bgp.sh/teamd.sh/swss.sh) は **CONFIG_DB ではなく STATE_DB** の `WARM_RESTART_ENABLE_TABLE|system` / `WARM_RESTART_ENABLE_TABLE|<service>` を参照。
- `WarmStart::checkWarmStart()` も STATE_DB を参照 (`warm_restart.cpp:95,103`)。
- **CONFIG_DB の WARM_RESTART テーブルには `enable` フィールドが存在しない** (YANG で未定義)。enable は STATE_DB 側が正。

### finalize-warmboot.sh の独立性

- `finalize-warmboot.sh` は CONFIG_DB の WARM_RESTART テーブルを読まない。`STATE_DB:WARM_RESTART_ENABLE_TABLE|system` と `STATE_DB:WARM_RESTART_TABLE|<component>` のみ参照。
- reconcile 待ち上限: `60 × 5秒 = 300 秒` (ハードコード)。タイマ設定値は参照しない。

### fast-reboot の WARM_RESTART テーブル削除

- `finalize_fast_reboot()` は `CONFIG_DB DEL "WARM_RESTART|teamd"` を実行 (`finalize-warmboot.sh:176`)。
- fast-reboot 後に teamsyncd_timer が消える副作用がある。

### YANG-実装 discrepancy

| 観点 | YANG | 実装 |
|------|------|------|
| `bgp_timer` range | `1..3600` | 上限チェックなし (MAXIMUM_WARMRESTART_TIMER_VALUE=9999 まで許容) |
| `neighsyncd_timer` range | `1..9999` | 同上 |
| `eoiu_hold_timer` フィールド | 未定義 | fpmsyncd が `WARM_RESTART|bgp` から読む |
| `enable` フィールド | 未定義 | CLI `config warm_restart enable` は STATE_DB に書く (CONFIG_DB には書かない) |

---

## 参照コード

| ファイル | 関連箇所 |
|---------|---------|
| `sonic-swss-common/common/warm_restart.cpp` | `getWarmStartTimer()` — timer lookup, fallback 0 |
| `sonic-swss/warmrestart/warmRestartAssist.h` | `DEFAULT_INTERNAL_TIMER_VALUE = 5` |
| `sonic-swss/warmrestart/warmRestartAssist.cpp` | constructor fallback logic |
| `sonic-swss/neighsyncd/neighsync.h` | `DEFAULT_NEIGHSYNC_WARMSTART_TIMER = 5` |
| `sonic-swss/neighsyncd/neighsync.cpp` | `AppRestartAssist("neighsyncd", "swss", 5)` |
| `sonic-swss/fpmsyncd/fpmsyncd.cpp` | `DEFAULT_ROUTING_RESTART_INTERVAL = 120`, `DEFAULT_EOIU_HOLD_INTERVAL = 3` |
| `sonic-swss/fpmsyncd/routesync.cpp:162` | `WarmStartHelper(..., "bgp", "bgp")` |
| `sonic-buildimage/dockers/docker-fpm-frr/.../supervisord.conf.j2:239` | bgp_eoiu 条件分岐 |
| `sonic-buildimage/files/image_config/warmboot-finalizer/finalize-warmboot.sh` | reconcile 待ち 300 秒, CONFIG_DB 不参照 |
| `sonic-utilities/config/main.py:4083` | bgp_eoiu CLI default='true' (引数省略デフォルト) |
