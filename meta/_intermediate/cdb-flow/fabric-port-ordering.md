# fabric-port Phase B — 書込み順依存調査メモ

## 調査対象
- `sonic-swss/orchagent/fabricportsorch.cpp`
- `sonic-swss/cfgmgr/fabricmgr.cpp`

## 発見した順序依存

### 依存 #1: SAI getFabricPortList() 完了待ち
- `m_getFabricPortListDone` フラグ制御 (fabricportsorch.cpp:1568-1576)
- false の間は updateFabricPortState() / updateFabricDebugCounters() が全スキップ
- 30秒ポーリング (FABRIC_POLL) で再試行

### 依存 #2: monState=enable ゲート (強制先行)
- doFabricPortTask() 冒頭で checkFabricPortMonState() を呼び出す
- APPL_DB FABRIC_MONITOR_DATA.monState != "enable" なら即 return
- source: fabricportsorch.cpp:1394-1399
- monState を後から enable にしても pending 変更は再適用されない

### 依存 #3: STATE_DB エントリ存在 → forceUnisolateStatus 比較
- STATE_DB FABRIC_PORT_TABLE|PORT<lane> が不在の場合は FORCE_UN_ISOLATE=0 扱い
- forceUnisolateStatus=0 の SET は差分なし (0==0) で force unisolate がスキップ
- source: fabricportsorch.cpp:1499-1516

### 依存 #4: 3フィールド完全性チェック (強制先行)
- alias + lanes + isolateStatus が全て揃うまで SAI 操作を実行しない
- 欠落時は APPL_DB から hget で補完を試みる
- 補完も失敗なら m_toSync.erase(it) で silent drop (INFO ログのみ)
- source: fabricportsorch.cpp:1436-1484

### 依存 #5: 非同期パイプライン遅延
- CONFIG_DB 変更 → fabricmgrd (1秒ポーリング) → APPL_DB → FabricPortsOrch
- 即時反映ではなく最大数秒の遅延が発生

## 重要な発見
- monState ゲートが最も影響大: FABRIC_MONITOR.monState=disable 状態では
  CONFIG_DB をいくら変更しても SAI への反映が一切行われない
- 3フィールド完全性 silent drop は運用時のデバッグを困難にする
  (ログがデフォルト設定では表示されない INFO レベル)
