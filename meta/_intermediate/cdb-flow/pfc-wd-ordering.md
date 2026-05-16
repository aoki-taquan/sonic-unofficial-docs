# PFC_WD — Phase B 書込み順依存スキャンノート

対象テーブル: `PFC_WD`
Consumer: `orchagent` / `PfcWdOrch` / `PfcWdSwOrch` (`sonic-swss/orchagent/pfcwdorch.cpp`)
スキャン範囲: `doTask()`, `createEntry()`, `PfcWdSwOrch::createEntry()`, `registerInWdDb()`, `orchdaemon.cpp:620-842` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. `allPortsReady()` — PORT テーブルが先行必須

- `doTask()` 冒頭 (`pfcwdorch.cpp:68-71`) で `gPortsOrch->allPortsReady()` を確認し、`false` の場合は即リターン（タスク保留）。
- `PFC_WD` エントリがどのタイミングで CONFIG_DB に書かれても、orchagent 内の `PORT` 初期化 (`PortsOrch::allPortsReady()`) が完了するまでは処理されない。
- **順序依存**: `PORT` テーブルの初期化（ポート設定、SAI オブジェクト生成）が完了していなければ `PFC_WD` エントリの処理は保留される。再試行は次回 consumer イベント到着時まで持ち越される。
- **緩和策**: orchagent は Consumer ループで再試行するため、`PORT` 完了後に自動的に処理が再開される。
- evidence: `pfcwdorch.cpp:68-71`

### 2. `PORT_QOS_MAP` / PFC 有効化 — pfcMask が先行必須

- `registerInWdDb()` (`pfcwdorch.cpp:533-608`) で `gPortsOrch->getPortPfcWatchdogStatus(port.m_port_id, &pfcMask)` を呼び、lossless TC の bitmask を取得する。
- `pfcMask == 0` の場合は `SWSS_LOG_NOTICE("No lossless TC found on port %s")` を出力し `false` を返す。
- `startWdOnPort()` は `registerInWdDb()` が `false` の場合 `SWSS_LOG_ERROR("Failed to start PFC Watchdog on port %s")` + `task_need_retry` を返す。
- **順序依存**: `PORT_QOS_MAP` で対象ポートの PFC が有効化 (`pfc_enable` bitmap 設定) されていなければ、`PFC_WD` エントリを書いても PFC WD は実際には機能しない（lossless TC なし扱い）。
- **推奨**: `PORT_QOS_MAP` の PFC 有効化を先に行ってから `PFC_WD` エントリを書く。
- evidence: `pfcwdorch.cpp:533-555`

### 3. `PFC_WD|GLOBAL` の POLL_INTERVAL — per-port エントリより先に書くことを推奨

- `PfcWdSwOrch::createEntry()` (`pfcwdorch.cpp:347-371`) は `key == "GLOBAL"` の場合に `m_pfcwdFlexCounterManager->updateGroupPollingInterval(stoi(value))` を呼ぶ。
- orchagent 起動時のデフォルトポーリング間隔は `PFC_WD_POLL_MSECS = 100` ms (`orchdaemon.cpp:24`)。`GLOBAL` エントリが書かれた時点で上書きされる。
- **順序依存（軽微）**: per-port エントリを先に書いてから `GLOBAL` の `POLL_INTERVAL` を書いた場合、先に書かれた per-port エントリは 100 ms ポーリングで動作し、その後 `POLL_INTERVAL` 変更が適用される。中間期間が短ければ実害はほぼない。
- **推奨**: `PFC_WD|GLOBAL` の `POLL_INTERVAL` を per-port エントリより先に書くことで一貫したポーリング間隔を保証できる。
- evidence: `pfcwdorch.cpp:354-356`, `orchdaemon.cpp:24`

### 4. Broadcom DLR — 最初のポートが action を決定する

- Broadcom platform + `checkPfcDlrInitEnable()` が true の場合: `m_pfcwd_ports` が空の状態で最初の per-port エントリを処理するとき、`SAI_SWITCH_ATTR_PFC_DLR_PACKET_ACTION` を switch-level で設定し `setPfcDlrPacketAction(action)` を記録する (`pfcwdorch.cpp:237-266`)。
- 2 ポート目以降は `getPfcDlrPacketAction() != action` の場合に `task_invalid_entry` を返す（全ポート同一 action 強制）。
- **順序依存**: Broadcom DLR モードでは**全 `PFC_WD` per-port エントリに同一の `action` を設定する必要がある**。最初に書いたエントリの action がスイッチレベルに設定されるため、後続エントリが異なる action の場合は reject される。
- **推奨**: Broadcom 環境では `action` を統一してから一括で `PFC_WD` エントリを書く。
- evidence: `pfcwdorch.cpp:237-266`

### 5. DEL 操作 — `m_pfcwd_ports` のクリーンアップ順序

- `deleteEntry()` (`pfcwdorch.cpp:322-339`) は `stopWdOnPort()` 成功後に `m_pfcwd_ports.erase(port.m_alias)` を呼ぶ。
- Broadcom DLR モードで全ポートを削除した後に再追加する場合、`m_pfcwd_ports` が空になった時点で再び最初のポートが switch-level action を決定するため、action 不一致は発生しない。
- **順序依存なし**（DEL は即時処理、保留なし）。
- evidence: `pfcwdorch.cpp:322-339`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | PORT 初期化完了 → PFC_WD エントリ処理 | **先行必須**（未完了時は保留・自動再試行） | doTask() が allPortsReady() で再試行 |
| 2 | PORT_QOS_MAP の PFC 有効化 → PFC_WD per-port エントリ | **推奨先行**（未設定時 lossless TC なしで WD 無効） | task_need_retry で再試行するが WD は実質無効 |
| 3 | PFC_WD\|GLOBAL POLL_INTERVAL → per-port エントリ | **推奨先行**（未設定時は 100ms デフォルト使用） | 後から設定しても次ポーリングサイクルから適用 |
| 4 | BRCM: 最初の per-port エントリ action → 後続エントリ | **同一 action 必須**（不一致は reject） | 全ポート同一 action で一括設定 |
| 5 | PFC_WD per-port DEL | 即時・順序依存なし | m_pfcwd_ports 自動クリーンアップ |
