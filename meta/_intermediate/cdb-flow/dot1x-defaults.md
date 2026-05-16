# DOT1X / PAC フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: CONFIG_DB `PAC_PORT_CONFIG_TABLE` / `HOSTAPD_GLOBAL_CONFIG_TABLE`

## 調査対象ファイル

- `sonic-buildimage/src/sonic-pac/pacmgr/pacmgr.h` — `AUTHMGR_*_DEF` マクロ定義
- `sonic-buildimage/src/sonic-pac/pacmgr/pacmgr.cpp` — `doPacPortTableSetTask()` 初期化ブロック (l.200-211)
- `sonic-buildimage/src/sonic-pac/authmgr/common/auth_mgr_common.h` — `DOT1X_PAE_PORT_*` 定数
- `SONiC/doc/pac/Port Access Control.md` — HLD (CLI デフォルト値の記述)

---

## フィールド別 暗黙デフォルト

### `port_control_mode` (PAC_PORT_CONFIG_TABLE)

**コード由来デフォルト**: `AUTHMGR_PORT_FORCE_AUTHORIZED` = `"force-authorized"`

```cpp
// pacmgr.h:41
#define AUTHMGR_PORT_CONTROL_MODE_DEF  AUTHMGR_PORT_FORCE_AUTHORIZED
// pacmgr.cpp:200
pacPortConfigCache.port_control_mode = AUTHMGR_PORT_CONTROL_MODE_DEF;
```

`doPacPortTableSetTask()` が呼ばれるたびに `port_control_mode` を `AUTHMGR_PORT_FORCE_AUTHORIZED` で初期化し、その後 DB フィールドで上書き。DB にフィールドが無い場合（または DEL 後）は `force-authorized` のまま。

HLD CLI 記述: "Default is force-authorized."

---

### `host_control_mode` (PAC_PORT_CONFIG_TABLE)

**コード由来デフォルト**: `AUTHMGR_MULTI_HOST_MODE` = `"multi-host"`

```cpp
// pacmgr.h:42
#define AUTHMGR_HOST_CONTROL_MODE_DEF  AUTHMGR_MULTI_HOST_MODE
// pacmgr.cpp:201
pacPortConfigCache.host_control_mode = AUTHMGR_HOST_CONTROL_MODE_DEF;
```

HLD CLI 記述: "Default is multi-host."

---

### `port_pae_role` (PAC_PORT_CONFIG_TABLE)

**コード由来デフォルト**: `DOT1X_PAE_PORT_NONE_CAPABLE` = `0x00` = `"none"`

```cpp
// pacmgr.h:49
#define AUTHMGR_PORT_PAE_ROLE_DEF  DOT1X_PAE_PORT_NONE_CAPABLE
// auth_mgr_common.h:318
#define  DOT1X_PAE_PORT_NONE_CAPABLE 0x00
// pacmgr.cpp:207
pacPortConfigCache.port_pae_role = AUTHMGR_PORT_PAE_ROLE_DEF;
```

`"none"` は PAC 機能が当該ポートで無効であることを意味する。`"authenticator"` にセットすると PAC が有効化。

HLD CLI 記述: "Default is none."

---

### `reauth_enable` (PAC_PORT_CONFIG_TABLE)

**コード由来デフォルト**: `FD_AUTHMGR_PORT_REAUTH_ENABLED`（HLD より `false` = 無効）

```cpp
// pacmgr.h:43
#define AUTHMGR_REAUTH_ENABLE_DEF FD_AUTHMGR_PORT_REAUTH_ENABLED
// pacmgr.cpp:202
pacPortConfigCache.reauth_enable = AUTHMGR_REAUTH_ENABLE_DEF;
```

`FD_AUTHMGR_PORT_REAUTH_ENABLED` はビルド時生成の `defaultconfig.h` で定義（ソース shallow clone では未確認）。HLD CLI の記述: "Default is disabled."

---

### `reauth_period` / `reauth_period_from_server` (PAC_PORT_CONFIG_TABLE)

**コード由来デフォルト**: `FD_AUTHMGR_PORT_REAUTH_PERIOD` / `FD_AUTHMGR_PORT_REAUTH_PERIOD_FROM_SERVER`

```cpp
// pacmgr.h:44-45
#define AUTHMGR_REAUTH_PERIOD_DEF FD_AUTHMGR_PORT_REAUTH_PERIOD
#define AUTHMGR_REAUTH_PERIOD_FROM_SERVER_DEF FD_AUTHMGR_PORT_REAUTH_PERIOD_FROM_SERVER
```

HLD CLI の記述: "Default is 'server'." → `reauth_period_from_server = true` がデフォルト。
`reauth_period_from_server == true` のとき、`pacmgr.cpp:387-393` が `AUTHMGR_PORT_REAUTH_PERIOD_DEF` (= `FD_AUTHMGR_PORT_REAUTH_PERIOD`) を authmgr に設定する。

show コマンドのサンプル出力 (HLD l.736): `Reauth-Period: 60 / Reauth-from-Server: False` → サンプルは手動設定値。

---

### `max_users_per_port` (PAC_PORT_CONFIG_TABLE)

**コード由来デフォルト**: `FD_AUTHMGR_PORT_MAX_USERS`（HLD より `16`）

```cpp
// pacmgr.h:46
#define AUTHMGR_MAX_USERS_PER_PORT_DEF FD_AUTHMGR_PORT_MAX_USERS
```

HLD CLI 記述: "Default is 16." / Scalability: "16 authenticated clients per port."

---

### `max_reauth_attempts` (PAC_PORT_CONFIG_TABLE)

**コード由来デフォルト**: `3`（リテラル定義）

```cpp
// pacmgr.h:47
#define AUTHMGR_MAX_REAUTH_ATTEMPTS_DEF 3
// pacmgr.cpp:205
pacPortConfigCache.max_reauth_attempts = AUTHMGR_MAX_REAUTH_ATTEMPTS_DEF;
```

---

### `method_list` / `priority_list` (PAC_PORT_CONFIG_TABLE)

**コード由来デフォルト**: `[dot1x, mab]`

```cpp
// pacmgr.h:50-53
#define AUTHMGR_PRIORITY_LIST_0_DEF  AUTHMGR_METHOD_8021X
#define AUTHMGR_PRIORITY_LIST_1_DEF  AUTHMGR_METHOD_MAB
#define AUTHMGR_METHOD_LIST_0_DEF  AUTHMGR_METHOD_8021X
#define AUTHMGR_METHOD_LIST_1_DEF  AUTHMGR_METHOD_MAB
// pacmgr.cpp:208-211
pacPortConfigCache.priority_list[INDEX_0] =  AUTHMGR_METHOD_8021X;
pacPortConfigCache.priority_list[INDEX_1] =  AUTHMGR_METHOD_MAB;
pacPortConfigCache.method_list[INDEX_0] =  AUTHMGR_METHOD_8021X;
pacPortConfigCache.method_list[INDEX_1] =  AUTHMGR_METHOD_MAB;
```

HLD CLI 記述: "Default order is 802.1x,mab." / "Default priority is 802.1x,mab."

---

### `dot1x_system_auth_control` (HOSTAPD_GLOBAL_CONFIG_TABLE)

**コード由来デフォルト**: `false` = 802.1x 無効

```cpp
// pacmgr.cpp:62 — pac_hostapd_glbl_info_t が memset(0) で初期化
memset(&m_glbl_info, 0, sizeof(m_glbl_info));
// → m_glbl_info.enable_auth = 0 (false)
```

HLD CLI 記述: "Default is disabled." (802.1x system-auth-control)

---

## 要約表

| フィールド | テーブル | コード由来デフォルト | ソース |
|-----------|---------|-------------------|--------|
| `port_control_mode` | PAC_PORT_CONFIG_TABLE | `force-authorized` | `pacmgr.h:41`, `pacmgr.cpp:200` |
| `host_control_mode` | PAC_PORT_CONFIG_TABLE | `multi-host` | `pacmgr.h:42`, `pacmgr.cpp:201` |
| `port_pae_role` | PAC_PORT_CONFIG_TABLE | `none` (PAC 無効) | `pacmgr.h:49`, `auth_mgr_common.h:318` |
| `reauth_enable` | PAC_PORT_CONFIG_TABLE | `false` (無効) | `pacmgr.h:43`; HLD CLI |
| `reauth_period_from_server` | PAC_PORT_CONFIG_TABLE | `true` (サーバから取得) | `pacmgr.h:45`; HLD CLI |
| `reauth_period` | PAC_PORT_CONFIG_TABLE | `FD_AUTHMGR_PORT_REAUTH_PERIOD` (≈60s) | `pacmgr.h:44` |
| `max_users_per_port` | PAC_PORT_CONFIG_TABLE | `16` | `pacmgr.h:46`; HLD Scalability |
| `max_reauth_attempts` | PAC_PORT_CONFIG_TABLE | `3` | `pacmgr.h:47` (リテラル) |
| `method_list` | PAC_PORT_CONFIG_TABLE | `[dot1x, mab]` | `pacmgr.h:52-53`, `pacmgr.cpp:210-211` |
| `priority_list` | PAC_PORT_CONFIG_TABLE | `[dot1x, mab]` | `pacmgr.h:50-51`, `pacmgr.cpp:208-209` |
| `dot1x_system_auth_control` | HOSTAPD_GLOBAL_CONFIG_TABLE | `false` (無効) | `pacmgr.cpp:74`; HLD CLI |

---

## 証拠リンク

- `pacmgr.h:41-53` — `AUTHMGR_*_DEF` マクロ
- `pacmgr.cpp:200-211` — `doPacPortTableSetTask()` 初期化ブロック
- `pacmgr.cpp:74` — `memset(&m_glbl_info, 0, ...)` (enable_auth = 0)
- `auth_mgr_common.h:318-319` — `DOT1X_PAE_PORT_NONE_CAPABLE` / `DOT1X_PAE_PORT_AUTH_CAPABLE`
- `SONiC/doc/pac/Port Access Control.md:712-721` — CLI デフォルト値テーブル
