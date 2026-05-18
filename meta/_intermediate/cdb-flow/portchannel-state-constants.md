# portchannel-state — Phase E ハードコード定数 調査メモ

## 調査対象

teamsync.h, teamsync.cpp, teammgr.cpp, portmgr.h, shellcmd.h, schema.h から
STATE_DB LAG_TABLE の動作に関わるマジックナンバー・定数を収集する。

## 検出定数一覧

### teamsync.h

- `DEFAULT_WR_PENDING_TIMEOUT = 70` (uint32_t)
  warm restart 時の STATE_DB 書き込み遅延タイムアウト (秒)。
  `WarmStart::getWarmStartTimer()` が設定されていない場合のフォールバック。
  teamsync.cpp:L40

- `TEAMSYNCD_APP_NAME = "teamsyncd"`
  WarmStart フレームワークへの登録名。warm restart 検出・状態管理に使用。
  teamsync.h:14

- `TEAM_DRV_NAME = "team"`
  netlink NEWLINK イベントから LAG を識別するドライバ名。
  rtnl_link_get_type() の戻り値と strcmp() で比較。
  teamsync.cpp:24, 111

### teamsync.cpp (TeamPortSync コンストラクタ)

- `max_retries = 3`
  team_init() / teamdctl_connect() 失敗時の最大リトライ回数 (int)。
  teamsync.cpp:L286

- `sleep(1)` (リトライ間隔)
  リトライ間の待機時間 1 秒。固定値。
  teamsync.cpp:L363

### schema.h (sonic-swss-common)

- `STATE_LAG_TABLE_NAME = "LAG_TABLE"` (schema.h:422)
  STATE_DB 内のテーブル名定数。

- `APP_LAG_TABLE_NAME = "LAG_TABLE"` (schema.h:43)
  APP_DB 内のテーブル名定数。APP_DB と STATE_DB で同じ名前 "LAG_TABLE" を使用。

- `CFG_LAG_TABLE_NAME = "PORTCHANNEL"` (schema.h:354)
  CONFIG_DB の設定テーブル名。

### portmgr.h (teammgr.cpp から #include)

- `DEFAULT_ADMIN_STATUS_STR = "down"`
  CONFIG_DB PORTCHANNEL に admin_status が未指定の場合のデフォルト値。
  portmgr.h:14

- `DEFAULT_MTU_STR = "9100"`
  CONFIG_DB PORTCHANNEL に mtu が未指定の場合のデフォルト値 (文字列)。
  portmgr.h:15

### shellcmd.h

- `TEAMD_CMD = "/usr/bin/teamd"`
  teamd バイナリの絶対パス。TeamMgr::addLag() がこのパスで exec() する。
  shellcmd.h:13

### teammgr.cpp コンストラクタ

- 起動時 LAG_TABLE クリア
  TeamMgr() コンストラクタ (L43-50) が STATE_DB LAG_TABLE の既存エントリを
  getKeys() → del() ですべて削除してから動作開始する。
  これは teammgrd 再起動時に古い state=ok エントリが残らないようにするため。

### warmboot ダンプパス

- `/var/warmboot/teamd/`
  warmstart 時の teamd 設定ダンプを読み書きするパス。
  TeamMgr::addLag() が warm restart 時にここから partner MAC を読む。
  teammgr.cpp:L573

### partner_system_id_offset

- `partner_system_id_offset = 40`
  warmboot ダンプファイル内で partner system MAC のバイトオフセット。
  teammgr.cpp:L581

## 証拠コード

- teamsync.h:L14,L16 — TEAMSYNCD_APP_NAME, DEFAULT_WR_PENDING_TIMEOUT
- teamsync.cpp:L24,L286,L363 — TEAM_DRV_NAME, max_retries, sleep(1)
- portmgr.h:L14-15 — DEFAULT_ADMIN_STATUS_STR, DEFAULT_MTU_STR
- shellcmd.h:L13 — TEAMD_CMD
- schema.h:L43,L354,L422 — テーブル名定数
- teammgr.cpp:L43-50,L573,L581 — 起動時クリア, warmboot パス
