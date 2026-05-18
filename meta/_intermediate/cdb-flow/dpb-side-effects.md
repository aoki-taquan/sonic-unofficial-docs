# DPB (BREAKOUT_CFG) — Phase F 副次 DB 書込調査

調査対象: `BREAKOUT_CFG` テーブルへの書込み（CLI `config interface breakout`）がトリガーする副次的な DB 操作。

## 主要ソース

- `sonic-utilities/config/main.py:5465–5557` (`breakout()` CLI コマンド)
- `sonic-utilities/config/config_mgmt.py:414–465` (`breakOutPort()`)
- `sonic-utilities/config/config_mgmt.py:468–526` (`_deletePorts()`)
- `sonic-utilities/config/config_mgmt.py:530–583` (`_addPorts()`)
- `sonic-utilities/config/config_mgmt.py:598–610` (`_shutdownIntf()`)
- `sonic-utilities/config/config_mgmt.py:377–412` (`_verifyAsicDB()`)
- `sonic-swss/cfgmgr/portmgr.cpp:244,257,264` (`doTask()` DEL/SET 分岐)

## 副次 DB 操作の詳細

### 1. CONFIG_DB への副次書込み（ポート削除時）

`breakOutPort()` は以下の順序で CONFIG_DB を変更する:

1. **PORT テーブルのシャットダウン書込み** (`_shutdownIntf()`):
   - `config_mgmt.py:602–608`
   - 削除予定の各ポートに `PORT|<port>` の `admin_status=down` を書き込む
   - これは `BREAKOUT_CFG` 自体への書込みではなく、CONFIG_DB `PORT` テーブルへの副次書込み

2. **依存テーブルの一括削除** (`_deletePorts()` with force=True):
   - YANG 依存解析で検出された全テーブルのエントリを CONFIG_DB から削除
   - 対象: `VLAN_MEMBER`, `PORTCHANNEL_MEMBER`, `INTERFACE`, `BUFFER_PG`, `BUFFER_QUEUE`, `PORT_QOS_MAP`, `QUEUE`, `ACL_TABLE`（ports フィールド参照分）など
   - `config_mgmt.py:480–500`

3. **PORT エントリ削除** (`writeConfigDB(delConfigToLoad)`):
   - 旧ポート（例: `Ethernet0`, `Ethernet1`, `Ethernet2`, `Ethernet3`）の `PORT|*` エントリを CONFIG_DB から削除
   - `config_mgmt.py:456`

4. **新ポートエントリ追加** (`writeConfigDB(addConfigtoLoad)`):
   - 新ポート（例: `Ethernet0` at 100G）の `PORT|*` エントリを CONFIG_DB に追加
   - `loadDefConfig=True` の場合、`port_breakout_config_db.json` から `BUFFER_PG`, `BUFFER_QUEUE`, `PORT_QOS_MAP`, `QUEUE` 等のデフォルト設定も同時書込み
   - `config_mgmt.py:460`

5. **BREAKOUT_CFG 自体の更新** (CLI 最終ステップ):
   - `config_db.set_entry("BREAKOUT_CFG", interface_name, {'brkout_mode': target_brkout_mode})`
   - `main.py:5547`

### 2. APPL_DB への伝播（portmgrd 経由）

`PORT` テーブルへの CONFIG_DB 書込みを `portmgrd` が購読し APPL_DB `PORT_TABLE` に伝播する:

- **DEL**: `m_appPortTable.del(alias)` → `APPL_DB PORT_TABLE|<port>` を削除 (`portmgr.cpp:244`)
- **SET**: `writeConfigToAppDb(alias, field_values)` → `APPL_DB PORT_TABLE|<port>` を更新 (`portmgr.cpp:257,264`)

### 3. ASIC_DB への確認ポーリング

`_verifyAsicDB()` は削除ポートの SAI OID が ASIC_DB から消えるまで最大 60 秒ポーリングする:
- `ASIC_DB ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x<oid>` の消滅を確認
- 消えなければ `Exception` を raise して操作を中断
- `config_mgmt.py:343,365,377–412`

### 4. STATE_DB への影響

`portmgrd` はポート削除時に STATE_DB `PORT_TABLE|<port>` を直接削除しない。
STATE_DB の `PORT_TABLE` エントリは `portsyncd` が netlink イベントを受けて管理する。
DPB で物理ポートが削除されると、syncd/orchagent がホストインタフェースを削除し、
`portsyncd` が STATE_DB `PORT_TABLE|<port>` のエントリを削除する（間接副作用）。

## 確認コマンド

```bash
# CONFIG_DB — ポート削除後に残存依存エントリがないか確認
sonic-db-cli CONFIG_DB keys 'VLAN_MEMBER|*' | grep Ethernet0
sonic-db-cli CONFIG_DB keys 'PORT|*'
sonic-db-cli CONFIG_DB hgetall 'BREAKOUT_CFG|Ethernet0'

# APPL_DB — portmgrd 経由での PORT_TABLE 伝播確認
sonic-db-cli APPL_DB keys 'PORT_TABLE|*'

# ASIC_DB — ポート OID の消滅確認（_verifyAsicDB が行う確認と同等）
sonic-db-cli ASIC_DB keys 'ASIC_STATE:SAI_OBJECT_TYPE_PORT:*'
```
