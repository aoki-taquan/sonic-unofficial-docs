# portchannel-state — Phase B 書込み順依存 調査メモ

## 調査対象

`STATE_DB LAG_TABLE` の書込み順依存を `teamsyncd/teamsync.cpp` と `cfgmgr/teammgr.cpp` から導出する。

## 主要コードパス

### 書込みまでの必須ステップ

```
CONFIG_DB PORTCHANNEL SET
  → teammgrd::doLagTask()          (teammgr.cpp:234)
      → addLag()                   (teammgr.cpp:564)
          → teamd -r -t <alias> ... (exec: teamd デーモン起動)
          ← teamd 起動成功
      → setLagAdminStatus / setLagMtu
  ↓
  Linux カーネルが RTM_NEWLINK (type=team) を emit
  ↓
teamsyncd::onMsg()                  (teamsync.cpp:101)
  → addLag(lagName, ifindex, ...)   (teamsync.cpp:146)
      → m_lagTable.set(lagName, fvVector)    # APP_LAG_TABLE 書込み
      → TeamPortSync::TeamPortSync()         # team_init(ifindex) — teamsync.cpp:299
          ← team_init 成功
      → m_stateLagTable.set(lagName, fvVector)  # STATE_DB LAG_TABLE 書込み
```

### 依存 #1: teamd 起動 → kernel RTM_NEWLINK → STATE_DB 書込み (強制先行)

teammgr.cpp:640 で exec(teamd cmd) が失敗すると task_need_retry を返し、
LAG_TABLE には何も書かれない。
teamd 起動成功後に Linux カーネルが RTM_NEWLINK を emit し、
teamsyncd がこれを受信して初めて LAG_TABLE への書込みが開始される。

### 依存 #2: team_init() 成功 → STATE_DB 書込み (強制先行)

teamsync.cpp:L191-193 コメント:
"STATE_DB is written only after the team instance is successfully created
 to prevent dependent services (e.g. intfmgrd) from acting on a LAG that
 teamd has not yet finished setting up."

team_init(ifindex) が EADDRNOTAVAIL で失敗すると system_error が throw され
catch ブロック (L208-213) で捕捉、LAG_TABLE には書かれない。
次の RTM_NEWLINK イベントで再試行する。

### 依存 #3: LAG_TABLE エントリ存在 → メンバ追加 (強制先行)

teammgr.cpp:357:
  if (!isPortStateOk(member) || !isLagStateOk(lag))
      { it++; continue; }  // retry
isLagStateOk() は m_stateLagTable.get(alias, temp) で LAG_TABLE エントリを確認。
LAG_TABLE エントリが存在しない限り PORTCHANNEL_MEMBER は処理されず m_toSync に残留する。

### 依存 #4: LAG_TABLE エントリ存在 → intfmgrd / vlanmgrd / nbrmgrd / stpmgrd 処理 (強制先行)

各 daemon が LAG インタフェースを扱う前に isLagStateOk() または
m_stateLagTable.get() で LAG_TABLE を確認する:
- intfmgr.cpp:663 — PortChannel prefix の INTERFACE 設定前
- vlanmgr.cpp:497 — LAG を VLAN メンバに追加する前
- nbrmgr.cpp:47 — LAG の隣接エントリ処理前
- stpmgr.cpp:1296 — STP ポート処理前

### 依存 #5: warm restart 時の書込み遅延

teamsync.cpp:L197-203:
warm restart モード (m_warmstart==true) の場合、
m_stateLagTable.set() の代わりに m_stateLagTablePreserved[lagName] = fvVector に一時保存。
applyState() が m_pending_timeout 秒後に呼ばれるまで LAG_TABLE には書かれない。
この間 intfmgrd 等は LAG_TABLE を見つけられず再試行し続ける。

### 依存 #6: tlm_teamd フィールド追記は teamsync 書込みと非同期

tlm_teamd は teamdctl JSON dump を定期ポーリングで解析し LAG_TABLE を SET で追記する。
teamsync.cpp が書いたベースフィールド (admin_status, oper_status, mtu, state) の後、
setup.* / runner.* / team_device.* フィールドは tlm_teamd の次ポーリング周期まで遅延する。
観測者は state=ok エントリを見た後も tlm_teamd フィールドが空の中間状態を観測しうる。

## 証拠コード

- teamsync.cpp:L146-225 — addLag() 全体。team_init 成功後のみ STATE_DB 書込み
- teamsync.cpp:L84-98 — applyState() warm restart 後の一括書込み
- teamsync.cpp:L191-213 — STATE_DB 書込みガードとコメント
- teammgr.cpp:L67-101 — isPortStateOk() / isLagStateOk()
- teammgr.cpp:L357 — メンバ追加前の LAG readiness ガード
- teammgr.cpp:L564-644 — addLag() で teamd 起動
