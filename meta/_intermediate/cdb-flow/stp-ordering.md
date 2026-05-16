# STP ordering — Phase B 調査メモ

調査対象:
- sonic-swss/cfgmgr/stpmgrd.cpp
- sonic-swss/cfgmgr/stpmgr.cpp
- sonic-swss/cfgmgr/stpmgr.h

## 1. 起動前提条件: PORT_INIT_DONE

`stpmgrd` 起動直後に `isPortInitDone()` (stpmgr.cpp:1257-1273) を呼び、
APPL_DB の APP_PORT_TABLE に `PortInitDone` キーが出現するまで 1 秒ポーリングで
ブロッキング待機する。つまり **portsyncd / orchagent が PORT テーブルを初期化するまで
stpmgrd は STP 処理を開始できない**。

## 2. CONFIG_DB 購読テーブルと処理順

stpmgrd.cpp:43-64 が TableConnector を生成し、doTask() でディスパッチする。

処理依存グラフ (stpmgr.cpp:51-86, 179-188, 444-450, 630-638, 1023-1031, 1155-1160):

```
PORT_INIT_DONE (APPL_DB) ← 前提
          │
          ▼
  STP|GLOBAL  ──────────────────────────────────────┐
  (doStpGlobalTask)                                  │
  stpGlobalTask = true 以降のみ他タスクを実行         │
          │                                          │
          ├──────────────────┐                       │
          ▼                  ▼                       │
  STP_PORT                STP_MST                   │
  (doStpPortTask)         (doStpMstGlobalTask)       │
  stpPortTask = true      guard: stpGlobalTask       │
          │                  │                       │
          ├──────────────────┤                       │
          ▼                  ▼                       │
  STP_VLAN                STP_MST_INST               │
  (doStpVlanTask)         (doStpMstInstTask)         │
  guard: stpGlobalTask    guard: stpGlobalTask       │
  + (stpPortTask or       + stpPortTask              │
    STP_PORT 空)          stpMstInstTask = true      │
  + isVlanStateOk()          │                       │
  (STATE_VLAN 確認)          ▼                       │
          │              STP_MST_PORT                │
          │              (doStpMstInstPortTask)       │
          │              guard: stpGlobalTask         │
          │              + stpMstInstTask             │
          │              + stpPortTask                │
          ▼                                          │
  STP_VLAN_PORT ◄────────────────────────────────────┘
  (doStpVlanPortTask)
  guard: stpGlobalTask + stpVlanTask + stpPortTask
```

### PVST 処理順まとめ

| ステップ | テーブル | guard 条件 |
|---------|---------|-----------|
| 1 | PORT_INIT_DONE 待機 | なし (blocking wait) |
| 2 | `STP\|GLOBAL` | なし (最初に受信でフラグ立て) |
| 3 | `STP_PORT` | `stpGlobalTask == true` |
| 4 | `STP_VLAN` | `stpGlobalTask && (stpPortTask or PORT 空)` + STATE_VLAN 存在確認 |
| 5 | `STP_VLAN_PORT` | `stpGlobalTask && stpVlanTask && stpPortTask` |

### MST 処理順まとめ

| ステップ | テーブル | guard 条件 |
|---------|---------|-----------|
| 1 | PORT_INIT_DONE 待機 | なし |
| 2 | `STP\|GLOBAL` | なし |
| 3 | `STP_PORT` | `stpGlobalTask == true` |
| 4 | `STP_MST` | `stpGlobalTask == true` |
| 5 | `STP_MST_INST` | `stpGlobalTask && stpPortTask` |
| 6 | `STP_MST_PORT` | `stpGlobalTask && stpMstInstTask && stpPortTask` |

## 3. VLAN 依存: STATE_VLAN チェック

`doStpVlanTask()` (stpmgr.cpp:210) は SET 操作時に `isVlanStateOk(key)` を呼ぶ。
STATE_VLAN テーブルにエントリが存在しない VLAN は処理を **skip (it++) して次ループへ持ち越す**。
→ VLAN がまだ State DB に登録されていない場合、STP_VLAN の SET は無限に defer される。

同じく `doStpMstInstTask()` (stpmgr.cpp:1027) も
`stpGlobalTask == false || (stpPortTask == false && !isStpPortEmpty())` でガードされる。

## 4. LAG 依存

`doStpPortTask()` はポートが PortChannel の場合に `isLagEmpty(key)` を確認する。
LAG にメンバーが存在しない場合、SET 操作をスキップする (stpmgr.cpp:648-653)。
これは `doLagMemUpdateTask()` が `m_lagMap` を更新した後に自動的に再処理される仕組みではなく、
次回 SELECT ループでの再試行に依存する。

## 5. warm-reboot 挙動

stpmgrd.cpp:39-40:
```cpp
WarmStart::initialize("stpmgrd", "stpd");
WarmStart::checkWarmStart("stpmgrd", "stpd");
```

`WarmStart::checkWarmStart()` を呼び出しているが、stpmgr.cpp 内で
warm boot 状態に応じた reconciliation ロジックや `setWarmStartState()` 呼び出しは **存在しない**。
つまり **stpmgrd は warm reboot を宣言するが、reconcile フェーズを実装していない**。

cold reboot と同一フロー (PORT_INIT_DONE 待機 → CONFIG_DB 再読み込み) で起動する。
STP トポロジ情報は stpd (STP デーモン) 側で保持・復旧する設計と推測される。

## 証跡

- stpmgrd.cpp:39-40, 43-64, 72
- stpmgr.cpp:42, 51-86, 179-188, 210, 344-346, 444-450, 630-638, 1023-1031, 1155-1160, 1257-1273, 1276-1290, 1326-1338
