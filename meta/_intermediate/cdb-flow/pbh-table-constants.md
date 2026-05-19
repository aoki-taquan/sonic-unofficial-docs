# pbh-table constants (Phase E)

## 調査対象

- `sonic-swss/orchagent/pbh/pbhschema.h`
- `sonic-swss/orchagent/pbh/pbhcap.cpp`
- `sonic-swss/orchagent/pbhorch.cpp` (pbhTableType 定数)
- `sonic-swss-common/common/schema.h` (STATE_PBH_CAPABILITIES_TABLE_NAME)

## コード由来のハードコード定数

### 1. `pbhschema.h` — PBH_TABLE フィールド名文字列定数

`PBH_TABLE_INTERFACE_LIST = "interface_list"`, `PBH_TABLE_DESCRIPTION = "description"` が CONFIG_DB フィールド名として定義される。

### 2. `pbhcap.cpp` — プラットフォーム・capability・STATE_DB キー定数

- `PBH_PLATFORM_ENV_VAR = "ASIC_VENDOR"` — ASIC ベンダー判定の環境変数名
- `PBH_PLATFORM_GENERIC = "generic"`, `PBH_PLATFORM_MELLANOX = "mellanox"`, `PBH_PLATFORM_UNKN = "unknown"` — 対応ベンダー文字列
- `PBH_TABLE_CAPABILITIES_KEY = "table"` — STATE_DB capability エントリのキー
- `PBH_FIELD_CAPABILITY_ADD = "ADD"` / `UPDATE` / `REMOVE` / `UNKNOWN` — field capability 値
- `PBH_STATE_DB_NAME = "STATE_DB"`, `PBH_STATE_DB_TIMEOUT = 0` — capability 書き込み先 DB / タイムアウト

### 3. `pbhorch.cpp` — ハードコードされた SAI ACL テーブル型定義

`pbhTableType` (static const, `pbhorch.cpp:243-253`): PBH テーブルの SAI ACL テーブル型定義。
bind point: `SAI_ACL_BIND_POINT_TYPE_PORT` + `SAI_ACL_BIND_POINT_TYPE_LAG`。
match 属性: GRE_KEY / ETHER_TYPE / IP_PROTOCOL / IPV6_NEXT_HEADER / L4_DST_PORT / INNER_ETHER_TYPE の固定 6 属性。
stage: `ACL_STAGE_INGRESS` 固定。これらは CONFIG_DB から変更不可。

### 4. `schema.h` — STATE_DB テーブル名

`STATE_PBH_CAPABILITIES_TABLE_NAME = "PBH_CAPABILITIES"` — STATE_DB への capability 書き込みテーブル名。
