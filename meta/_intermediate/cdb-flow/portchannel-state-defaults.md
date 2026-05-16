# Phase A — STATE_DB LAG_TABLE フィールド コード由来デフォルト調査

## 調査対象

- STATE_DB テーブル: `LAG_TABLE` (`STATE_LAG_TABLE_NAME` = `"LAG_TABLE"` — `sonic-swss-common/common/schema.h:422`)
- 主要書き込み元: `sonic-swss/teamsyncd/teamsync.cpp` (`TeamSync::addLag`)
- 補助書き込み元: `sonic-swss/tlm_teamd/values_store.h` (`ValuesStore::m_lag_paths`)

## SHA

- sonic-swss HEAD: `4305596156d70e9797e8a881b3d19b46de0bce0d`
- ファイル: `teamsyncd/teamsync.cpp`, `tlm_teamd/values_store.h`

## フィールド一覧とデフォルト

### teamsync.cpp::addLag() が書き込む主フィールド (L146-176)

| フィールド | 書き込み値 / ロジック | コード根拠 |
|-----------|---------------------|----------|
| `admin_status` | Linux netlink `IFF_UP` フラグから `"up"` / `"down"` | `teamsync.cpp:L115-116,L151` |
| `oper_status` | Linux netlink `IFF_LOWER_UP` フラグから `"up"` / `"down"` | `teamsync.cpp:L116,L152` |
| `mtu` | `rtnl_link_get_mtu(link)` → `std::to_string(mtu)` | `teamsync.cpp:L140,L153` |
| `state` | `"ok"` (固定リテラル) | `teamsync.cpp:L175` |

- `admin_status` / `oper_status` は起動時デフォルトなし。カーネル netlink NEWLINK イベントで受信した実際のフラグ値を文字列化して書き込む。
- `mtu` はカーネルから読み取った実際の MTU 値を文字列化する。デフォルト 9100 (portmgr.h) はカーネル側の初期値として適用されるが STATE_DB 書き込みはカーネル実測値。
- `state` は `"ok"` のみ。エラー状態は STATE_DB に書かれず、エントリ自体が削除される (`removeLag`)。

### tlm_teamd/values_store.h が書き込む補助フィールド (m_lag_paths, L48-56)

teamsyncd の TeamPortSync 初期化後、tlm_teamd が teamdctl JSON dump を解析して STATE_DB `LAG_TABLE` に追記するフィールド。

| フィールド (JSON path) | 型 | 説明 |
|-----------------------|----|------|
| `setup.kernel_team_mode_name` | string | teamd が選択した runner モード名 (例: `"lacp"`) |
| `setup.pid` | integer | teamd プロセスの PID |
| `runner.active` | boolean | LAG が active (ポートが集約中) かどうか |
| `runner.fallback` | boolean | fallback モードが有効か。CONFIG_DB `PORTCHANNEL.fallback` から来る |
| `runner.fast_rate` | boolean | LACP fast rate が有効か。CONFIG_DB `PORTCHANNEL.fast_rate` から来る |
| `team_device.ifinfo.dev_addr` | string | LAG の MAC アドレス |
| `team_device.ifinfo.ifindex` | integer | LAG の ifindex |

- これらは teamdctl の JSON dump に依存するため、初期値は teamd の設定次第。
- `runner.active` は初期 false → ポート集約完了で true に変化。
- `runner.fallback` / `runner.fast_rate` は CONFIG_DB から teamd に渡した設定値の反映。

## DEFAULT_ADMIN_STATUS_STR / DEFAULT_MTU_STR

- `portmgr.h:14`: `#define DEFAULT_ADMIN_STATUS_STR "down"`
- `portmgr.h:15`: `#define DEFAULT_MTU_STR "9100"`

これらは teammgr.cpp が CONFIG_DB PORTCHANNEL テーブルから読み取れない場合のフォールバックであり、STATE_DB に直接書かれるデフォルトではない。実際の STATE_DB 値はカーネル netlink から取得した実測値。

## STATE_LAG_TABLE の消費者

- `intfmgr.cpp`: LAG が STATE_LAG_TABLE に存在するかチェックして LAG 上のインタフェース設定を進める
- `vlanmgr.cpp`: VLAN メンバとして LAG を追加する前に LAG の state チェック
- `nbrmgr.cpp`: 隣接エントリ処理前に LAG state チェック
- `stpmgr.cpp`: STP ポート処理前に LAG state チェック
- `tlm_teamd/main.cpp`: teamd JSON dump を定期 poll して LAG_TABLE / LAG_MEMBER_TABLE を更新

## 結論

STATE_DB `LAG_TABLE` の書き込みは `teamsync.cpp::addLag()` が担い、フィールドは 4 つ:
- `admin_status`: `"up"` / `"down"` (カーネル IFF_UP)
- `oper_status`: `"up"` / `"down"` (カーネル IFF_LOWER_UP)
- `mtu`: カーネル実測値の文字列
- `state`: 常に `"ok"` (エラー時はエントリ削除)

加えて tlm_teamd が teamdctl JSON から 7 フィールドを追記する。
これらに固定のコードレベルデフォルトはなく、カーネルおよび teamd の実行時状態を反映する。
