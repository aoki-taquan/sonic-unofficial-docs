# MUX_LINKMGR — Phase D 失敗挙動中間ファイル

生成日: 2026-05-16
ソース: sonic-linkmgrd (sonic-net/sonic-linkmgrd)

## 調査対象ファイル

- `src/DbInterface.cpp` — CONFIG_DB 購読ハンドラ・xcvrd 通信
- `src/MuxPort.cpp` — MUX state パース・プローブ応答処理
- `src/MuxManager.cpp` — processProbeMuxState・ログレベル更新
- `src/link_manager/LinkManagerStateMachineActiveStandby.cpp` — Error 状態遷移

---

## 1. 不正値 (Invalid value)

### LINK_PROBER 数値フィールド (`interval_v4`, `interval_v6`, `positive_signal_count`, `negative_signal_count`, `suspend_timer`, `interval_pck_loss_count_update`)

- `processMuxLinkmgrConfigNotifiction()` (`DbInterface.cpp:1128-1163`) で `boost::lexical_cast<uint32_t>` によりパース
- 数値変換に失敗すると `boost::bad_lexical_cast` 例外が catch され `MUXLOGWARNING` を出力して **処理を継続**（フィールド更新はスキップされる）
- 例: `interval_v4 = "abc"` → `MUXLOGWARNING: bad lexical cast: ...` を出力し、内部タイマー値は変更されない

### LINK_PROBER enum フィールド (`use_well_known_mac`, `src_mac`)

- `use_well_known_mac`: コードは `v == "enable"` で判定 (`DbInterface.cpp:1143`)。YANG enum は `enabled`/`disabled` だが末尾 `d` が不一致 → **`enabled` を書いても常に false (動的MAC)** として処理される。警告ログなし、サイレント誤動作
- `src_mac`: コードは `v == "ToRMac"` で判定 (`DbInterface.cpp:1145`)。不一致の場合は false (= VlanMac) として処理される。警告ログなし

### MUXLOGGER `log_verbosity` 不正値

- `MuxManager::updateLogVerbosity()` (`MuxManager.cpp:170`) は `trace/debug/info/warning/error/fatal` 以外の値を受け取った場合、マッチせずデフォルトの info レベルが維持される。警告ログなし

### TIMED_OSCILLATION `oscillation_enabled` 不正値

- `DbInterface.cpp:1192-1197`: `"true"` / `"false"` のみ分岐。それ以外の値は**いずれの分岐にも入らず無視**される。`setOscillationEnabled()` は呼ばれない。警告ログなし

### TIMED_OSCILLATION `interval_sec` 不正値

- `DbInterface.cpp:1198-1204`: `boost::lexical_cast<uint32_t>` で変換失敗時は `MUXLOGWARNING` を出力してスキップ
- 設定可能でも `300` 秒未満の値は `MuxConfig.h:338` の setter 内で `300` に clamp される

---

## 2. xcvrd 通信失敗

### MUX state プローブ (Active-Standby)

- `handleProbeMuxState()` (`DbInterface.cpp:439-444`) は APP_DB に `command = probe` を書き込んで xcvrd に I2C 読み取りを要求する
- xcvrd から応答が返ってきたとき `processMuxResponseNotifiction()` (`DbInterface.cpp:1325-1352`) で `response` フィールドをパース
- xcvrd が `"unknown"` を返した場合: `MuxPort::handleProbeMuxState()` (`MuxPort.cpp:299`) で `Unknown` ラベルへマップ → `handleProbeMuxStateNotification()` へ post → 状態機械は `MuxState::Unknown` へ遷移
- xcvrd が応答しない（タイムアウト）場合: linkmgrd 側にプローブ応答待ちタイマーはなく、状態機械は `Unknown` 状態のまま留まる。`swssSelect.select()` の `DEFAULT_TIMEOUT_MSEC` ループ (`DbInterface.cpp:1875`) はデータ受信を待つ polling であり、xcvrd 無応答を「失敗」と認識する機構はない

### MUX state プローブ (Active-Active / gRPC)

- xcvrd が gRPC 通信失敗時に `"failure"` を返した場合: `MuxPort::handleProbeMuxState()` (`MuxPort.cpp:304-311`) で `handleProbeMuxFailure()` へ post。Active-Active ポートにのみ適用
- Active-Standby ポートで `"failure"` 文字列が来た場合: いずれの条件にもマッチせず `Unknown` ラベルのまま `handleProbeMuxStateNotification()` へ post → `MuxState::Unknown` へ遷移

---

## 3. SAI 失敗 / orchagent 経由の Error 状態

- linkmgrd は SAI を**直接呼び出さない**。MUX state の切替は orchagent 経由で行われる
- orchagent が MUX switchover を SAI に要求した結果、失敗した場合: orchagent は STATE_DB の MUX state テーブルを `"error"` に更新する
- linkmgrd は `processMuxStateNotifiction()` (`DbInterface.cpp:1481-1505`) で STATE_DB を購読し、`"error"` 文字列を受け取ると `MuxPort::handleMuxState()` (`MuxPort.cpp:335`) で `MuxState::Error` ラベルへマップ
- 状態機械: `MuxState::Error` に入ると `enterLinkProberState(..., Wait)` を実行 (`LinkManagerStateMachineActiveStandby.cpp:1160-1161`) し `LinkProberState::Wait` へ遷移
- `{LinkProberActive, MuxError, LinkUp}` 遷移関数 (`LinkManagerStateMachineActiveStandby.cpp:1324-1334`): 新旧リンクプローバ状態が変わっていれば `enterMuxWaitState()` を呼びプローブを再試行する
- `{LinkProberStandby, MuxError, LinkUp}` 遷移関数 (`LinkManagerStateMachineActiveStandby.cpp:1341-1352`): 同様に `enterMuxWaitState()` を呼びプローブを再試行する
- `swssSelect.select()` が `Select::ERROR` を返した場合: `MUXLOGERROR("Error had been returned in select")` を出力して continue（ループ継続）(`DbInterface.cpp:1877-1879`)

---

## 4. エラーログ一覧

| エラー | ログレベル | ログ内容 | ソース |
|--------|-----------|---------|--------|
| 数値フィールドの不正値 (bad_lexical_cast) | WARNING | `"bad lexical cast: ..."` | `DbInterface.cpp:1162-1163, 1201-1202` |
| select() が ERROR を返した | ERROR | `"Error had been returned in select"` | `DbInterface.cpp:1878` |
| select() が OBJECT 以外を返した | ERROR | `"Unknown return value from Select: ..."` | `DbInterface.cpp:1883` |
| 不明オブジェクト | ERROR | `"Unknown object returned by select"` | `DbInterface.cpp:1912` |
| スロットル: ToR MAC 不正 | FATAL | `"Received Loopback2/3 IP: ... error code: ..."` | `DbInterface.cpp:699,720` |

---

## 5. まとめ

| ケース | 処置 | 警告/エラー |
|--------|------|------------|
| 数値フィールド不正値 | 更新スキップ、直前値維持 | MUXLOGWARNING |
| `use_well_known_mac = "enabled"` | サイレントに false (動的MAC) として動作 | なし（実装バグ） |
| `oscillation_enabled` に `true`/`false` 以外 | 無視、現在値維持 | なし |
| xcvrd が `"unknown"` を返す | MuxState::Unknown へ遷移 | なし |
| xcvrd が `"failure"` を返す (Active-Active) | handleProbeMuxFailure() 呼び出し | なし |
| xcvrd 無応答 | 状態 Unknown のまま留まる | なし（タイムアウト検知なし） |
| orchagent が SAI 失敗で `"error"` を STATE_DB に書く | MuxState::Error → LinkProberState::Wait へ遷移、プローブ再試行 | なし |
| select() が ERROR を返す | ループ継続 | MUXLOGERROR |
