# dot1x (PAC_PORT_CONFIG_TABLE / HOSTAPD_GLOBAL_CONFIG_TABLE) — Phase B: 書込み順依存

slug: dot1x
phase: B (ordering)
source: sonic-buildimage/src/sonic-pac/pacmgr/pacmgr_main.cpp, pacmgr.cpp, hostapdmgr/hostapdmgr.cpp

## 調査結果

### 起動シーケンス (pacmgrd)

pacmgr_main.cpp の `main()` は以下の順で初期化する:

1. `fpinfraInit()` — プラットフォームインタフェース基盤の初期化
2. `authmgrInit()` — 認証マネージャの初期化。失敗時は即 return -1
3. `osapiWaitForTaskInit(AUTHMGR_DB_TASK_SYNC, WAIT_FOREVER)` — authmgr 内部 DB タスクの完了を**無限待機**
4. `s.addSelectables(pacmgr.getSelectables())` — CONFIG_DB / STATE_DB 購読登録
5. メインループ開始 → `pacmgr.processDbEvent()` でイベント処理

CONFIG_DB のイベント受信は step 4 以降にのみ発生するため、`PAC_PORT_CONFIG_TABLE` や `HOSTAPD_GLOBAL_CONFIG_TABLE` の変更は authmgr 初期化完了後に初めて処理される。

### 起動シーケンス (hostapdmgrd)

hostapdmgr_main.cpp は authmgr 待機なしで即座に購読開始するが、hostapd プロセスの起動条件として `active_intf_cnt > 0`（authenticator ポートのconf ファイル生成済み）が必要。

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `authmgrInit()` 完了 → CONFIG_DB 購読開始 | **強制先行** (pacmgr_main.cpp L46-56) | authmgr 初期化失敗時は pacmgrd 自体が終了 |
| 2 | `port_pae_role=authenticator` 設定 → `dot1x_system_auth_control=true` 設定 | 推奨先行 | 逆順でも動作するが、global enable 時に既存ポートを走査して conf 生成するため、ポート設定が先の方が安全 |
| 3 | `RADIUS_SERVER` 設定 → hostapd 起動 | **強制先行** (hostapdmgr.cpp L300 `m_radiusServerInUse != ""` チェック) | RADIUS サーバ未設定の場合、`createConfFile()` は呼ばれず `active_intf_cnt` が増えないため hostapd が起動しない |
| 4 | STATE_DB `VLAN_TABLE` エントリ存在 → authmgr へ VLAN_ADD_NOTIFY | 到着順依存 (pacmgr.cpp L730) | VLAN が STATE_DB に登録される前に PAC ポートが authenticator になると、VLAN 通知が遅延する |
| 5 | `HOSTAPD_GLOBAL_CONFIG_TABLE` SET → `PAC_PORT_CONFIG_TABLE` DEL 処理 | 独立（DEL 処理は `doPacPortTableDeleteTask` で独立） | DEL は global auth 状態に依存しない |

### 主要な制約詳細

**authmgr 初期化待機 (依存 #1)**: `osapiWaitForTaskInit(AUTHMGR_DB_TASK_SYNC, WAIT_FOREVER)` は authmgr 内部タスクの DB 同期完了まで無限待機する（`pacmgr_main.cpp:52-56`）。この待機が終わらない限り CONFIG_DB の購読が開始されないため、SONiC 起動直後に `PAC_PORT_CONFIG_TABLE` を書き込んでも pacmgrd が受け取るのは authmgr 準備完了後となる。

**RADIUS サーバ必須条件 (依存 #3)**: `hostapdmgr.cpp` の `createConfFile()` は `m_radiusServerInUse` が空文字列の場合に `informHostapd("new", interfaces)` を呼ばず conf ファイルを作成しない。`dot1x_system_auth_control=true` を設定しても RADIUS サーバが未設定であれば hostapd は起動しない（`hostapdmgr.cpp:288-300`）。

**global enable タイミング (依存 #2)**: `dot1x_system_auth_control=true` 受信時、`hostapdmgrd` は `m_intf_info` をイテレートして `capabilities=authenticator` かつ `control_mode=auto` かつ `link_status=true` なインタフェースの conf を一括生成する（`hostapdmgr.cpp:285-302`）。このため、ポート設定を先に完了させてから global enable を行う方が「conf 生成漏れ」リスクが低い。ただし pacmgrd の `doPacPortTableSetTask()` は global auth 状態を参照しないため、ポートとグローバルの設定順が逆であっても pacmgrd 側の処理は完了する。

## evidence

- `sonic-buildimage/src/sonic-pac/pacmgr/pacmgr_main.cpp:44-65`
- `sonic-buildimage/src/sonic-pac/pacmgr/pacmgr.cpp:63-89,142-190,640-683,684-752`
- `sonic-buildimage/src/sonic-pac/hostapdmgr/hostapdmgr_main.cpp:25-99`
- `sonic-buildimage/src/sonic-pac/hostapdmgr/hostapdmgr.cpp:42-72,260-310,1136-1190`
