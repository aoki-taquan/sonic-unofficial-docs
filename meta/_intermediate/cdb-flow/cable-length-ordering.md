# CABLE_LENGTH — Phase B 書込み順依存スキャンノート

対象テーブル: `CABLE_LENGTH`
Consumer: `buffermgr` (static モード) / `buffermgrdyn` (dynamic モード)
スキャン範囲: `buffermgr.cpp` 全行 + `buffermgrdyn.cpp` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. PORT (speed) が先行必須 — buffermgr / buffermgrdyn 共通

- **buffermgr**: `doCableTask()` (buffermgr.cpp:101-113) が cable length を `m_cableLenLookup` に格納後、即 `doSpeedUpdateTask()` を呼び出す。`doSpeedUpdateTask()` は `m_speedLookup[port]` を参照するが、PORT テーブルから speed がまだ届いていなければ `speed` が空文字になり、headroom 計算に用いる `buffer_profile_key` が `pg_lossless__<cable>_profile` という不正キーになる。
- **buffermgrdyn**: `handleCableLenTable()` (buffermgrdyn.cpp:2155-2159) で `effectiveSpeed.empty()` を確認し、空の場合は `SWSS_LOG_WARN` を出力して処理を中断する。リトライは行わない（ログだけ残り、headroom は計算されない）。speed が後で届いた際、`handlePortTable()` 内で改めて `refreshPgsForPort()` が呼ばれる。
- **推奨**: `PORT` テーブルに `speed` を設定してから `CABLE_LENGTH` を書き込む。

  evidence: `buffermgr.cpp:101-109`, `buffermgrdyn.cpp:2155-2159`

### 2. PORT_QOS_MAP (`pfc_enable`) が先行必須 — buffermgr (static モード)

- `doSpeedUpdateTask()` (buffermgr.cpp:165-178) は `m_portStatusLookup.count(port) == 0` の場合に `task_need_retry` を返す。`m_portStatusLookup` は `PORT_QOS_MAP` テーブルから `admin_status` / `pfc_enable` を受信して初めて設定される。
- PORT_QOS_MAP が未着の場合はコメントに「The notification is cleared」と明記されており (`buffermgr.cpp:175`)、CABLE_LENGTH の通知は取り消しされ、PG は `pfc_enable` が届いた時点の `PORT_QOS_MAP` ハンドラから再処理される。
- **推奨**: `PORT_QOS_MAP` エントリを先に書いてから `CABLE_LENGTH` を書く。PORT_QOS_MAP が後着した場合でも自動回復するが、その間 lossless PG 設定は適用されない。

  evidence: `buffermgr.cpp:165-178`, `buffermgr.cpp:517-539`

### 3. BUFFER_POOL が先行必須 — buffermgrdyn (dynamic モード)

- `allocateProfile()` (buffermgrdyn.cpp:978) は `m_bufferPoolReady` が false の場合に `task_need_retry` を返す。これは `handleCableLenTable()` → `refreshPgsForPort()` → `allocateProfile()` の経路上に存在する。
- BUFFER_POOL が未設定、または `ingress_lossless_pool` の SAI 登録が完了していない場合、headroom プロファイルの生成・APPL_DB 書き込みが保留される。BUFFER_POOL 登録後にリトライキューから自動的に再処理される。

  evidence: `buffermgrdyn.cpp:978`, `buffermgrdyn.cpp:894`

### 4. PortInitDone (STATE_DB) が先行必須 — buffermgrdyn (dynamic モード)

- `checkSharedBufferPoolSize()` (buffermgrdyn.cpp:826-856) は `m_portInitDone` フラグを確認し、`APPL_DB.PortInitDone` が存在するまでバッファプールサイズ更新を延期する。
- CABLE_LENGTH を書いても `m_portInitDone = false` のうちは `refreshPgsForPort()` は PORT_INITIALIZING → PORT_READY の遷移待ちになり、headroom 計算はスキップされる (buffermgrdyn.cpp:1485-1487)。
- portsyncd が `PortInitDone` を APPL_DB に書いた後、buffermgrdyn が `m_portInitDone = true` にセットし、pending 中の計算が一括処理される。

  evidence: `buffermgrdyn.cpp:826-856`, `buffermgrdyn.cpp:1485-1487`

### 5. CABLE_LENGTH と BUFFER_PG の依存方向

- `BUFFER_PG` エントリは `buffermgrdyn` が CABLE_LENGTH + speed + mtu を揃えた時点で **自動生成** される（`refreshPgsForPort` → `allocateProfile` → APPL_DB 書き込み）。
- つまり `CABLE_LENGTH` が先行テーブルであり、`BUFFER_PG` は下流（出力）テーブルである。手動で `BUFFER_PG` を先に書いても `buffermgrdyn` が上書きする。
- **注意**: dynamic モードでは `BUFFER_PG` を直接書くことは非推奨。

  evidence: `buffermgrdyn.cpp:1425-1445`, `buffermgrdyn.cpp:1523-1524`

### 6. DEL 時の順序制約（PORT admin down / "0m" 特殊値）

- PORT が admin down 状態では `refreshPgsForPort()` を呼ばない (buffermgrdyn.cpp:1454-1456)。admin down ポートに CABLE_LENGTH を書いても headroom 変更は反映されない。
- `cable_length = "0m"` は lossless PG を削除する特殊値 (buffermgrdyn.cpp:1492)。DEL 相当の操作として機能する。
- PORT DEL 後に CABLE_LENGTH エントリが残っていても `m_portInfoLookup` から参照されないため実害はない。

  evidence: `buffermgrdyn.cpp:1454-1456`, `buffermgrdyn.cpp:1492`

---

## 順序依存サマリ

| # | 先行テーブル | 依存先 | 方向 | 待機動作 | evidence |
|---|---|---|---|---|---|
| 1 | `PORT` (speed フィールド) | `CABLE_LENGTH` | 先行必須 | buffermgr: 計算スキップ / buffermgrdyn: WARN ログ・リトライなし | buffermgr.cpp:101-109, buffermgrdyn.cpp:2155 |
| 2 | `PORT_QOS_MAP` (pfc_enable) | `CABLE_LENGTH` | 先行推奨 (static モード) | 通知クリア → PORT_QOS_MAP 着信時に自動再処理 | buffermgr.cpp:165-178 |
| 3 | `BUFFER_POOL` (ingress_lossless_pool) | `CABLE_LENGTH` → headroom 計算 | 先行必須 (dynamic モード) | task_need_retry → BUFFER_POOL 確立後自動リトライ | buffermgrdyn.cpp:978 |
| 4 | PortInitDone (STATE_DB / APPL_DB) | CABLE_LENGTH headroom 適用 | 先行必須 (dynamic モード) | PORT_INITIALIZING 待機 → PortInitDone 後一括処理 | buffermgrdyn.cpp:826 |
| 5 | `CABLE_LENGTH` → `BUFFER_PG` (自動生成) | 下流出力 | CABLE_LENGTH が上流 | buffermgrdyn が自動生成・上書き | buffermgrdyn.cpp:1523 |
| 6 | PORT admin down | CABLE_LENGTH 適用ブロック | 特殊条件 | admin up になるまで headroom 変更は保留 | buffermgrdyn.cpp:1454 |
