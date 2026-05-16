# CHASSIS_APP_DB テーブル群 暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象 DB: `CHASSIS_APP_DB` (Redis DB id=12, instance=redis_chassis)

## 調査対象ファイル

- `sonic-swss-common/common/schema.h` — テーブル名定数定義
- `sonic-swss/orchagent/intfsorch.cpp` — `SYSTEM_INTERFACE` テーブル書き込み
- `sonic-swss/orchagent/neighorch.cpp` — `SYSTEM_NEIGH` テーブル書き込み
- `sonic-swss/orchagent/portsorch.cpp` — `SYSTEM_LAG_TABLE` / `SYSTEM_LAG_MEMBER_TABLE` 書き込み
- `sonic-swss/orchagent/lagids.lua` — `SYSTEM_LAG_ID_TABLE` / `SYSTEM_LAG_ID_SET` / `SYSTEM_LAG_IDS_FREE_LIST` Lua スクリプト
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_chassis_app_db.py` — `BGP_DEVICE_GLOBAL|STATE` 購読
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py` — `BGP_DEVICE_GLOBAL|STATE.tsa_enabled` 読み取り
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` — chassisd DB 接続・cleanup

---

## CHASSIS_APP_DB とは

`CHASSIS_APP_DB` は VoQ (Virtual Output Queue) チャシスシステム専用の Redis DB（DB id=12, instance=`redis_chassis`）。チャシス内の全ラインカードが **中央スーパーバイザーの redis_chassis** を共有し、ラインカード間でシステムポート・インタフェース・ネイバー・LAG の情報を同期するために使用する。非 VoQ 環境では存在しない（`isChassisDbInUse()` が false）。

---

## テーブル別 フィールドとデフォルト

### テーブル: `SYSTEM_INTERFACE`

**定数**: `CHASSIS_APP_SYSTEM_INTERFACE_TABLE_NAME = "SYSTEM_INTERFACE"` (`schema.h:411`)

**書き込み元**: `intfsorch.cpp::voqSyncAddIntf()` / `voqSyncDelIntf()`  
**条件**: `isChassisDbInUse()` かつローカル PORT/LAG のインタフェース追加・削除時

| フィールド | 型 | デフォルト / fallback | コード根拠 |
|-----------|-----|----------------------|-----------|
| `oper_status` | string | インタフェース追加時に `port.m_oper_status == SAI_PORT_OPER_STATUS_UP ? "up" : "down"` で決定 | `intfsorch.cpp:1708` |

**キー構造**: `SYSTEM_INTERFACE|<system_port_alias>` (LAG の場合は `m_system_lag_info.alias`)

**挙動の注意点**:
- 非ローカルポート（`SAI_SYSTEM_PORT_TYPE_REMOTE`）は書き込みをスキップ (`intfsorch.cpp:1689-1692`)
- LAG の場合、`m_system_lag_info.switch_id != gVoqMySwitchId` なら書き込みをスキップ (`intfsorch.cpp:1681-1683`)
- `oper_status` は SAI の `m_oper_status` から直接変換。SAI 初期化前に値がない場合は `"down"` 相当

---

### テーブル: `SYSTEM_NEIGH`

**定数**: `CHASSIS_APP_SYSTEM_NEIGH_TABLE_NAME = "SYSTEM_NEIGH"` (`schema.h:412`)

**書き込み元**: `neighorch.cpp::voqSyncAddNeigh()`  
**条件**: `isChassisDbInUse()` かつローカルネイバー追加時

| フィールド | 型 | デフォルト / fallback | コード根拠 |
|-----------|-----|----------------------|-----------|
| `encap_index` | uint32 | SAI API `get_neighbor_entry_attribute(SAI_NEIGHBOR_ENTRY_ATTR_ENCAP_INDEX)` で取得。`0` の場合はエラーとして書き込みをスキップ | `neighorch.cpp:2595-2611` |
| `neigh` | string (MAC) | ネイバーの MAC アドレス (`mac.to_string()`) | `neighorch.cpp:2650` |

**キー構造**: `SYSTEM_NEIGH|<system_port_alias>|<ip_address>`

**挙動の注意点**:
- `encap_index == 0` は無効値として扱われ、書き込み自体がキャンセルされる (`neighorch.cpp:2608-2612`)
- 非ローカルポートは書き込みをスキップ（`SAI_SYSTEM_PORT_TYPE_REMOTE` 確認）
- LAG メンバーの場合は `m_system_lag_info.switch_id == gVoqMySwitchId` のみ許可

---

### テーブル: `SYSTEM_LAG_TABLE`

**定数**: `CHASSIS_APP_LAG_TABLE_NAME = "SYSTEM_LAG_TABLE"` (`schema.h:413`)

**書き込み元**: `portsorch.cpp::voqSyncAddLag()` / `voqSyncDelLag()`  
**条件**: `gMultiAsicVoq` が true かつ `switch_id == gVoqMySwitchId` のローカル LAG

| フィールド | 型 | デフォルト / fallback | コード根拠 |
|-----------|-----|----------------------|-----------|
| `lag_id` | string (uint32) | `to_string(lag.m_system_lag_info.spa_id)` — LAG 追加時に `LagIdAllocator::lagIdAdd()` が払い出す値 | `portsorch.cpp:11155` |
| `switch_id` | string (int32) | `to_string(lag.m_system_lag_info.switch_id)` — VoQ スイッチ ID | `portsorch.cpp:11158` |

**キー構造**: `SYSTEM_LAG_TABLE|<system_lag_alias>`

**挙動の注意点**:
- `switch_id != gVoqMySwitchId` または `!gMultiAsicVoq` の場合はスキップ (`portsorch.cpp:11145-11149`)
- `lag_id` は `SYSTEM_LAG_ID_TABLE` (ハッシュ) + `SYSTEM_LAG_ID_SET` (セット) + `SYSTEM_LAG_IDS_FREE_LIST` (リスト) で管理される Lua スクリプトによる集中割り当て

---

### テーブル: `SYSTEM_LAG_MEMBER_TABLE`

**定数**: `CHASSIS_APP_LAG_MEMBER_TABLE_NAME = "SYSTEM_LAG_MEMBER_TABLE"` (`schema.h:414`)

**書き込み元**: `portsorch.cpp::voqSyncAddLagMember()` / `voqSyncDelLagMember()`  
**条件**: ローカル LAG メンバー追加・削除時

| フィールド | 型 | デフォルト / fallback | コード根拠 |
|-----------|-----|----------------------|-----------|
| `status` | string | LAG メンバー追加時の `status` 文字列（caller から渡される） | `portsorch.cpp:11188` |

**キー構造**: `SYSTEM_LAG_MEMBER_TABLE|<system_lag_alias>:<system_port_alias>`

**挙動の注意点**:
- `lag.m_system_lag_info.switch_id != gVoqMySwitchId` の場合はスキップ (`portsorch.cpp:11182-11184`)
- `status` の具体値は caller の渡し方による。LAG メンバーの動的ステータス更新時は再呼び出しで上書き

---

### テーブル: `BGP_DEVICE_GLOBAL` (key=`STATE`)

**書き込み元**: `bgpcfgd` の `ChassisAppDbMgr` が スーパーバイザー上で購読・更新  
**読み取り先**: ラインカードの `managers_device_global.py::get_chassis_tsa_status()`

| フィールド | 型 | デフォルト / fallback | コード根拠 |
|-----------|-----|----------------------|-----------|
| `tsa_enabled` | string (`"true"` / `"false"`) | キー不在時は `"false"` (get 失敗扱い) | `managers_device_global.py:239` |

**キー構造**: `BGP_DEVICE_GLOBAL|STATE`

**挙動の注意点**:
- `device_info.is_chassis()` が `False` の場合、`get_chassis_tsa_status()` は即座に `"false"` を返す (`managers_device_global.py:241-242`)
- `SonicV2Connector.get()` が例外を投げた場合も `"false"` を返す (`managers_device_global.py:248-250`)
- `ChassisAppDbMgr.set_handler()` は `lc_tsa == "false"` の場合のみ `isolate_unisolate_device()` を呼び出す。LC の TSA 状態がスーパーバイザー TSA に優先する (`managers_chassis_app_db.py:41-44`)

---

### LAG ID 管理用エントリ群 (Redis 生 KEY)

`CHASSIS_APP_DB` には標準テーブル形式でない Redis key が直接書き込まれる:

| Redis Key | 型 | 説明 | コード根拠 |
|-----------|-----|------|-----------|
| `SYSTEM_LAG_ID_START` | string (int) | LAG ID 割り当て範囲下限 | `lagids.lua:15` — GET のみ、chassisd/init が書き込み |
| `SYSTEM_LAG_ID_END` | string (int) | LAG ID 割り当て範囲上限 | `lagids.lua:16` — GET のみ |
| `SYSTEM_LAG_ID_TABLE` | hash | `pcname → lag_id` マッピング | `lagids.lua:22,78,90` |
| `SYSTEM_LAG_ID_SET` | set | 現在割り当て済み lag_id のセット（重複防止） | `lagids.lua:43,46,68` |
| `SYSTEM_LAG_IDS_FREE_LIST` | list | 未割り当て lag_id のフリーリスト | `lagids.lua:41,44,60,63` |

**デフォルト値**: `SYSTEM_LAG_ID_START` / `SYSTEM_LAG_ID_END` は初期化スクリプトが書き込む（lua スクリプト自体は GET のみ）。テスト環境では `1`/`2` が使用される (`test_virtual_chassis.py:28-29`)。本番値はプラットフォーム設定による。

---

### chassisd クリーンアップ (モジュール down 時)

**対象テーブル（Lua スクリプト `_cleanup_chassis_app_db` による一括削除）**:
- `SYSTEM_NEIGH*` (パターン一致)
- `SYSTEM_INTERFACE*` (パターン一致)
- `SYSTEM_LAG_MEMBER_TABLE*` (パターン一致)
- `SYSTEM_LAG_TABLE*` (host/asic パターン一致)
- `SYSTEM_LAG_ID_TABLE` のエントリ削除 + `SYSTEM_LAG_ID_SET` / `SYSTEM_LAG_IDS_FREE_LIST` の再整理

**条件**: モジュール down 検知から **30 分** (`CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30` 分, chassisd:?) 後に実行

---

## 要約表

| テーブル | フィールド | デフォルト/fallback | 条件 |
|---------|-----------|-------------------|------|
| `SYSTEM_INTERFACE` | `oper_status` | `"up"` または `"down"` (SAI から直接) | ローカルポート/LAG にのみ書き込み |
| `SYSTEM_NEIGH` | `encap_index` | なし (0 の場合は書き込みスキップ) | `intfsorch.cpp:2608` |
| `SYSTEM_NEIGH` | `neigh` | MAC アドレス文字列 | 必須。スキップ条件なし |
| `SYSTEM_LAG_TABLE` | `lag_id` | LagIdAllocator 払い出し値 (プラットフォーム依存) | `gMultiAsicVoq && local LAG` |
| `SYSTEM_LAG_TABLE` | `switch_id` | `gVoqMySwitchId` | ローカル LAG のみ |
| `SYSTEM_LAG_MEMBER_TABLE` | `status` | caller 渡し | ローカル LAG メンバーのみ |
| `BGP_DEVICE_GLOBAL\|STATE` | `tsa_enabled` | `"false"` (キー不在/例外時) | is_chassis() == True かつ CHASSIS_APP_DB 接続可能時のみ意味を持つ |

---

## 証拠リンク

- `sonic-swss-common/common/schema.h:411-414` — テーブル名定数
- `sonic-swss/orchagent/intfsorch.cpp:1672-1714` — `voqSyncAddIntf()` / `oper_status` 書き込み
- `sonic-swss/orchagent/neighorch.cpp:2587-2655` — `voqSyncAddNeigh()` / `encap_index` + `neigh` 書き込み
- `sonic-swss/orchagent/portsorch.cpp:11139-11205` — `voqSyncAddLag()` / `voqSyncAddLagMember()`
- `sonic-swss/orchagent/lagids.lua` — LAG ID 割り当て Lua スクリプト
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_chassis_app_db.py:7-50` — `ChassisAppDbMgr`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py:238-251` — `get_chassis_tsa_status()`
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:593-658` — `_cleanup_chassis_app_db()`
