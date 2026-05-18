# portchannel-state — Phase H: プラットフォーム差異調査ノート

調査日: 2026-05-18
調査対象:
- `sonic-swss/teamsyncd/teamsync.cpp`
- `sonic-swss/teamsyncd/teamsyncd.cpp`
- `sonic-swss/cfgmgr/teammgr.cpp`
- `sonic-swss/cfgmgr/teammgrd.cpp`
- `sonic-swss/tlm_teamd/main.cpp`
- `sonic-swss/tlm_teamd/values_store.cpp`

## 調査結果サマリ

STATE_DB `LAG_TABLE` の書き込みは Linux netlink (`RTM_NEWLINK` / `RTM_DELLINK`) と `teamdctl` UNIX socket 経由の JSON dump に依存する。いずれも SAI を経由しないカーネル・ユーザー空間の仕組みであるため、プラットフォーム（ASIC ベンダー）差異は基本的に生じない。

## 観点別調査

### ASIC 種別 (Broadcom / Mellanox / Marvell / Innovium 等)

teamsyncd は Linux `libteam` + netlink だけを使用し、SAI API を呼ばない (`teamsync.cpp` に SAI インクルードなし)。tlm_teamd も `teamdctl` の UNIX ソケット経由であり ASIC 非依存。よってフィールド値・書き込みタイミング・テーブル構造はすべての ASIC で同一。

根拠: `teamsyncd.cpp:L30-38` — `DBConnector db("APPL_DB", 0)` と `TeamSync sync(&db, &stateDb, &s)` で起動。SAI 関連ライブラリのリンクなし。

### multi-asic (namespace 分離構成)

`teamsyncd` / `tlm_teamd` / `teammgrd` はいずれも `DBConnector("APPL_DB", 0)` / `DBConnector("STATE_DB", 0)` を無引数（デフォルト namespace）で開く (`teamsyncd.cpp:L31-32`, `teammgrd.cpp:L48-50`, `tlm_teamd/main.cpp:L91`)。multi-asic 環境では各 namespace に独立した `teamsyncd` / `tlm_teamd` / `teammgrd` インスタンスが起動し、それぞれ自 namespace の `STATE_DB::LAG_TABLE` に書き込む。フィールド定義・書き込み動作は namespace 間で同一。

### VOQ chassis (Virtual Output Queue)

VOQ chassis では LAG が `SYSTEM_LAG_TABLE` / `SYSTEM_LAG_ID_TABLE` (`orchagent/lagids.lua`) で管理されるが、これらは APPL_DB または CHASSIS_APP_DB 上のテーブルであり `STATE_DB::LAG_TABLE` とは別物。`teamsyncd` は VOQ 特有のコードパスを持たず、Linux netlink イベントに純粋に従って `STATE_DB::LAG_TABLE` を書く。VOQ 固有のシステム LAG ID 付与は orchagent 側 (`lagorch.cpp` / `lagids.lua`) が担い、STATE_DB LAG_TABLE には影響しない。

テスト根拠: `sonic-swss/tests/test_virtual_chassis.py` では `LAG_TABLE` (APP_DB) と `SYSTEM_LAG_TABLE` を別個に操作し、STATE_DB LAG_TABLE は VOQ パスでも通常と同一構造で書かれることを確認している (L602, L634-645)。

### warm restart

warm restart は ASIC / プラットフォーム非依存。`WarmStart::getWarmStartTimer(TEAMSYNCD_APP_NAME, "teamd")` でタイマーを取得し、設定がなければ `DEFAULT_WR_PENDING_TIMEOUT = 70` 秒を使用する (`teamsync.h:L16`, `teamsync.cpp:L39-40`)。タイマー値はプラットフォームではなく mgmt 設定に依存。

## 結論

プラットフォーム差異なし。STATE_DB `LAG_TABLE` への書き込み動作はすべての ASIC・構成で同一。
