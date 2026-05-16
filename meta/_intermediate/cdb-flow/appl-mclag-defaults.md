# APPL_DB MCLAG/ICCP 関連テーブル — Phase A デフォルト調査メモ

## 調査対象ソース

- `sonic-swss/mclagsyncd/mclaglink.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/mclagsyncd/mclaglink.h`
- `sonic-swss/mclagsyncd/mclag.h`
- `sonic-swss-common/common/schema.h` (SHA: 158de8d3463ff4b841653f6d57190bb142b80d9c)
- `sonic-buildimage/src/iccpd/include/scheduler.h` (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-buildimage/src/iccpd/src/iccp_csm.c`
- `sonic-buildimage/src/iccpd/src/mlacp_link_handler.c`

---

## APPL_DB 書き込みテーブル一覧 (mclagsyncd)

`mclaglink.cpp` コンストラクタ (L1810–1816) で以下の `ProducerStateTable` が初期化される:

| ProducerStateTable 変数 | APPL_DB テーブル名 | 定数 |
|------------------------|------------------|------|
| `p_intf_tbl`     | `INTF_TABLE`           | `APP_INTF_TABLE_NAME` |
| `p_iso_grp_tbl`  | `ISOLATION_GROUP_TABLE`| `APP_ISOLATION_GROUP_TABLE_NAME` |
| `p_fdb_tbl`      | `MCLAG_FDB_TABLE`      | `APP_MCLAG_FDB_TABLE_NAME` |
| `p_acl_table_tbl`| `ACL_TABLE_TABLE`      | `APP_ACL_TABLE_TABLE_NAME` |
| `p_acl_rule_tbl` | `ACL_RULE_TABLE`       | `APP_ACL_RULE_TABLE_NAME` |
| `p_lag_tbl`      | `LAG_TABLE`            | `APP_LAG_TABLE_NAME` |
| `p_port_tbl`     | `PORT_TABLE`           | `APP_PORT_TABLE_NAME` |

STATE_DB 書き込みは別テーブル（`p_mclag_tbl` → `MCLAG_TABLE`, `p_mclag_local_intf_tbl`, `p_mclag_remote_intf_tbl`）で、APPL_DB には含まない。

---

## テーブル別フィールドとデフォルト

### 1. MCLAG_FDB_TABLE (APPL_DB)

`setFdbEntry()` L465–521:

| フィールド | 型 | コード由来デフォルト | 備考 |
|-----------|----|--------------------|------|
| `port`    | string | なし（必須） | `fdb_info->port_name` をそのまま |
| `type`    | string | なし（必須） | `"static"` / `"dynamic"` / `"dynamic_local"` |

- キー形式: `Vlan<vid>:<mac>` (例: `Vlan100:00:01:02:03:04:05`)
- `MCLAG_FDB_TYPE_STATIC = 1` → `"static"`
- `MCLAG_FDB_TYPE_DYNAMIC = 2` → `"dynamic"`
- `MCLAG_FDB_TYPE_DYNAMIC_LOCAL = 3` → `"dynamic_local"` (aging 有効でローカル書き込み時)

### 2. ISOLATION_GROUP_TABLE (APPL_DB)

`setPortIsolate()` — プラットフォームが `broadcom` / `barefoot` / `centec` / `clounix` / `marvell-prestera` / `marvell-teralynx` のいずれかの場合 (L192–281):

| フィールド    | 型 | コード由来デフォルト | 備考 |
|--------------|----|--------------------|------|
| `DESCRIPTION`| string | `"Isolation group for MCLAG"` | ハードコード |
| `TYPE`       | string | `"bridge-port"` | ハードコード |
| `PORTS`      | string | なし（必須） | MCLAG インタフェース名 (isolate_src_port) |
| `MEMBERS`    | string | `""` (空文字列) | 全リモートインタフェースが down 時は空 |

- キー: `"MCLAG_ISO_GRP"` (ハードコード)
- ICCP セッションが down のとき (`is_iccp_up == false`) はエントリを DEL する
- `MEMBERS` 内の `Ethernet` 始まりのポートはフィルタして除外する

非対応プラットフォームの場合 ACL フォールバック (L283–375):

| APPL_DB テーブル | キー | フィールド | 値 |
|----------------|------|-----------|---|
| `ACL_TABLE_TABLE` | `"mclag"` | `policy_desc` | `"Mclag egress port isolate acl"` |
| | | `type` | `"L3"` |
| | | `ports` | isolate_src_port |
| `ACL_RULE_TABLE` | `"mclag:mclag"` | `IP_TYPE` | `"ANY"` |
| | | `OUT_PORTS` | isolate_dst_port (Ethernet 除外後) |
| | | `PACKET_ACTION` | `"DROP"` |

### 3. PORT_TABLE / LAG_TABLE (APPL_DB) — learn_mode

`setPortMacLearnMode()` L380–418:

| フィールド    | 型 | 値 | 備考 |
|--------------|----|----|------|
| `learn_mode` | string | `"hardware"` または `"disable"` | MCLAG_SUB_OPTION_TYPE_MAC_LEARN_ENABLE → `"hardware"`, DISABLE → `"disable"` |

- PortChannel の場合 (`PortChannel` プレフィクス) は `p_lag_tbl` (LAG_TABLE)
- それ以外は `p_port_tbl` (PORT_TABLE)

### 4. LAG_TABLE (APPL_DB) — traffic_disable

`mclagsyncdSetTrafficDisable()` L1289–1317:

| フィールド        | 型 | 値 | 備考 |
|-----------------|----|----|------|
| `traffic_disable` | string | `"true"` または `"false"` | DISABLE メッセージ → `"true"`, ENABLE → `"false"` |

### 5. INTF_TABLE (APPL_DB) — mac_addr

`setIntfMac()` L435–463:

| フィールド  | 型 | コード由来デフォルト | 備考 |
|------------|----|--------------------|------|
| `mac_addr` | string | なし（必須） | ICCP ロール確定後に ICCP デーモンがセット |

---

## CONFIG_DB 由来フィールドのデフォルト (iccpd 側)

mclagsyncd が CONFIG_DB から読む `MCLAG_DOMAIN` フィールドと、iccpd 内部でのデフォルト:

| フィールド          | CONFIG_DB 名       | iccpd 内部デフォルト | コード箇所 |
|--------------------|-------------------|-------------------|----------|
| `keepalive_interval`| `keepalive_interval`| `1` 秒 (`CONNECT_INTERVAL_SEC`) | `scheduler.h:40`, `iccp_csm.c:125` |
| `session_timeout`   | `session_timeout`  | `15` 秒 (`HEARTBEAT_TIMEOUT_SEC`) | `scheduler.h:42`, `iccp_csm.c:126` |
| `source_ip`         | `source_ip`        | 省略時は必須エラー | `mandatoryFieldsPresent()` check |
| `peer_ip`           | `peer_ip`          | 省略時は必須エラー | `mandatoryFieldsPresent()` check |
| `peer_link`         | `peer_link`        | 省略時は空文字列 | オプション |

- `keepalive_interval = -1` (空文字列) の場合、iccpd は `CONNECT_INTERVAL_SEC = 1` にフォールバック (L3108)
- `session_timeout = -1` (空文字列) の場合、iccpd は `HEARTBEAT_TIMEOUT_SEC = 15` にフォールバック (L3120)

---

## まとめ: hard=0 ページへの追記内容

`docs/reference/config-db/appl-mclag.md` に以下を追加:

1. `<!-- defaults -->` ブロック: 上記テーブル別フィールドのコード由来デフォルト
2. `MCLAG_FDB_TABLE` / `ISOLATION_GROUP_TABLE` / `PORT_TABLE` / `LAG_TABLE` / `INTF_TABLE` の書き込みロジック
3. iccpd の keepalive/timeout デフォルト値参照
