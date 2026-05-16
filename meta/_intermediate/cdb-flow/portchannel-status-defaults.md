# Phase A: APPL_DB LAG_TABLE portchannel-status コード由来デフォルト調査

## 対象ファイル

- `sonic-swss/teamsyncd/teamsync.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/teammgr.cpp` (同上)
- `sonic-swss/cfgmgr/portmgr.h` (同上)
- `sonic-swss/orchagent/portsorch.cpp` (同上)

## フィールド精読結果

### admin_status

- **書き込み元**: `TeamSync::addLag()` (teamsync.cpp:151)
- **コード**:
  ```cpp
  FieldValueTuple a("admin_status", admin_state ? "up" : "down");
  ```
- **由来**: `rtnl_link_get_flags(link) & IFF_UP` の結果。カーネル netlink RTM_NEWLINK イベントから取得
- **初期値**: カーネルが teamd デバイスを作成した直後の IFF_UP フラグ状態に依存
- **テンプレ注入 (teammgr.cpp:251)**:
  ```cpp
  string admin_status = DEFAULT_ADMIN_STATUS_STR;  // "down"
  ```
  → `portmgr.h:14` の `#define DEFAULT_ADMIN_STATUS_STR "down"` を使用
- **暗黙デフォルト**: `"down"` (CONFIG_DB に admin_status フィールドがない場合の teammgr.cpp フォールバック)
- teamsyncd は実際のカーネル IFF_UP フラグに従って書き込む。APPL_DB に書かれる実際の値はカーネル状態次第。

### oper_status

- **書き込み元**: `TeamSync::addLag()` (teamsync.cpp:152)
- **コード**:
  ```cpp
  FieldValueTuple o("oper_status", oper_state ? "up" : "down");
  ```
- **由来**: `rtnl_link_get_flags(link) & IFF_LOWER_UP` の結果
- **初期値**: LAG 作成直後はメンバが存在しないため IFF_LOWER_UP=false → `"down"`
- **暗黙デフォルト**: `"down"` (LAG 作成直後、メンバなし状態)

### mtu

- **書き込み元**: `TeamSync::addLag()` (teamsync.cpp:153)
- **コード**:
  ```cpp
  FieldValueTuple m("mtu", std::to_string(mtu));
  ```
  `mtu = rtnl_link_get_mtu(link)` — カーネル netlink から取得
- **テンプレ注入 (teammgr.cpp:252)**:
  ```cpp
  string mtu = DEFAULT_MTU_STR;  // "9100"
  ```
  → `portmgr.h:15` の `#define DEFAULT_MTU_STR "9100"`
- **teammgr.cpp 書き込み (line 512-515)**:
  ```cpp
  FieldValueTuple fv("mtu", mtu);
  m_appLagTable.set(alias, fvs);
  ```
- **暗黙デフォルト**: `"9100"` (CONFIG_DB に mtu フィールドがない場合の teammgr.cpp フォールバック)
- teamsyncd は RTM_NEWLINK 時にカーネルの実際の MTU を書き込む

### state

- **書き込み元**: `TeamSync::addLag()` (teamsync.cpp:175)
- **コード**:
  ```cpp
  FieldValueTuple s("state", "ok");
  fvVector.push_back(s);
  m_stateLagTable.set(lagName, fvVector);  // STATE_DB に書き込む
  ```
- **注意**: `state: "ok"` は STATE_DB LAG_TABLE (STATE_LAG_TABLE_NAME) に書かれる。APPL_DB LAG_TABLE とは別
- **APPL_DB への state 書き込み**: APPL_DB LAG_TABLE には `state` フィールドは書かれない

### tpid

- **書き込み元**: `TeamMgr::setLagTpid()` (teammgr.cpp:542-545)
- **コード**:
  ```cpp
  FieldValueTuple fv("tpid", tpid);
  m_appLagTable.set(alias, fvs);
  ```
- **由来**: CONFIG_DB PORTCHANNEL テーブルの `tpid` フィールドをそのまま APPL_DB に転写
- **暗黙デフォルト**: CONFIG_DB に `tpid` フィールドがない場合は APPL_DB に書かれない

### learn_mode

- **書き込み元**: `TeamMgr::setLagLearnMode()` (teammgr.cpp:556-559)
- **コード**:
  ```cpp
  FieldValueTuple fv("learn_mode", learn_mode);
  m_appLagTable.set(alias, fvs);
  ```
- **由来**: CONFIG_DB PORTCHANNEL テーブルの `learn_mode` フィールドをそのまま転写
- **暗黙デフォルト**: CONFIG_DB に `learn_mode` がない場合は APPL_DB に書かれない

### lag_id / switch_id (VoQ / CHASSIS のみ)

- **書き込み元**: `portsorch.cpp:11155`
  ```cpp
  FieldValueTuple li ("lag_id", to_string(spa_id));
  ```
- **用途**: VoQ/ChassisApp 環境の CHASSIS_APP_LAG_TABLE への書き込み
- **通常環境**: APPL_DB LAG_TABLE に lag_id/switch_id は書かれない

## 書き込みプロセスまとめ

| フィールド | 書き込み元 | ソースコード | デフォルト |
|-----------|-----------|------------|---------|
| `admin_status` | teamsyncd (addLag) + teammgrd | teamsync.cpp:151, teammgr.cpp:251,870 | `"down"` (portmgr.h:14) |
| `oper_status` | teamsyncd (addLag) | teamsync.cpp:152 | `"down"` (IFF_LOWER_UP 未セット) |
| `mtu` | teamsyncd (addLag) + teammgrd | teamsync.cpp:153, teammgr.cpp:252,513-515,824 | `"9100"` (portmgr.h:15) |
| `tpid` | teammgrd (setLagTpid) | teammgr.cpp:543-545 | 書かれない (CONFIG_DB に tpid がある場合のみ) |
| `learn_mode` | teammgrd (setLagLearnMode) | teammgr.cpp:557-559 | 書かれない (CONFIG_DB に learn_mode がある場合のみ) |

## STATE_DB との区別

teamsyncd の `m_stateLagTable.set(lagName, fvVector)` は STATE_DB の `LAG_TABLE` に書く。
APPL_DB LAG_TABLE に書かれるのは `admin_status`, `oper_status`, `mtu` の 3 フィールド (teamsyncd 経由)、
および `tpid`, `learn_mode` (teammgrd 経由)。`state: "ok"` は STATE_DB のみ。

## 証跡

- `teamsync.cpp:146-160`: `addLag()` — APPL_DB LAG_TABLE への 3 フィールド書き込み
- `portmgr.h:14-15`: `DEFAULT_ADMIN_STATUS_STR "down"`, `DEFAULT_MTU_STR "9100"` 定義
- `teammgr.cpp:251-252`: SET 処理で admin_status / mtu デフォルト変数初期化
- `teammgr.cpp:512-515, 542-545, 556-559`: setLagMtu / setLagTpid / setLagLearnMode 各実装
- `teamsync.cpp:175`: `state: "ok"` は STATE_DB のみへの書き込み
