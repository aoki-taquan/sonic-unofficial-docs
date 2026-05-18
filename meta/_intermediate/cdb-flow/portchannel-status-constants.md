# portchannel-status — Phase E ハードコード定数調査メモ

対象ファイル: `docs/reference/config-db/portchannel-status.md`

## 調査ソース

- `sonic-swss/cfgmgr/portmgr.h`
- `sonic-swss/cfgmgr/shellcmd.h`
- `sonic-swss/cfgmgr/teammgr.cpp`
- `sonic-swss/teamsyncd/teamsync.h`
- `sonic-swss/teamsyncd/teamsync.cpp`

## 検出定数一覧

| 定数 / マクロ名 | 値 | 定義ファイル | 意味 |
|---|---|---|---|
| `DEFAULT_ADMIN_STATUS_STR` | `"down"` | `portmgr.h:14` | teammgrd が doLagTask() で admin_status を初期化するデフォルト値 |
| `DEFAULT_MTU_STR` | `"9100"` | `portmgr.h:15` | teammgrd が doLagTask() で mtu を初期化するデフォルト値 |
| `TEAMD_CMD` | `"/usr/bin/teamd"` | `shellcmd.h:13` | teamd プロセス起動コマンドのフルパス |
| `TEAMDCTL_CMD` | `"/usr/bin/teamdctl"` | `shellcmd.h:14` | teamdctl コマンドのフルパス (teammgrd が LAG key 生成に使用) |
| `DEFAULT_WR_PENDING_TIMEOUT` | `70` 秒 | `teamsync.h:16` | warm reboot 時に teamsyncd が RTM_NEWLINK イベントを集積する最大待機秒数 |
| `partner_system_id_offset` | `40` bytes | `teammgr.cpp:581` | warmboot dump ファイル内で partner MAC アドレスを読む固定オフセット |
| `TEAMSYNCD_APP_NAME` | `"teamsyncd"` | `teamsync.h:14` | WarmStart::initialize() に渡すアプリケーション名 |
| LAG dump パス | `"/var/warmboot/teamd/"` | `teammgr.cpp:573` | warmboot 時に teamd 状態を保存するディレクトリパス |
| teamd runner 名 | `"lacp"` | `teammgr.cpp:609` | teamd 設定 JSON に固定埋め込みされる runner 名。LACP 専用 |
| teamd `"active": true` | `true` | `teammgr.cpp:608` | teamd LACP runner の active モード固定値 |
