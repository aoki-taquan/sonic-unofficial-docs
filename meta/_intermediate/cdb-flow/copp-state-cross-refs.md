# STATE_DB COPP 状態テーブル — Phase C 暗黙参照テーブルスキャンノート

対象ページ: `docs/reference/config-db/copp-state.md`
対象テーブル: `STATE_DB`
  - `COPP_GROUP_TABLE`
  - `COPP_TRAP_TABLE`
  - `COPP_TRAP_CAPABILITY_TABLE`
Producer: `CoppMgr` (`sonic-swss/cfgmgr/coppmgr.cpp`) + `CoppOrch` (`sonic-swss/orchagent/copporch.cpp`)
スキャン範囲: coppmgr.cpp L296-411, L531-985 / copporch.cpp L32-36, L191-215, L240-300, L392-420, L880-960, L1370-1492

---

## 検出した暗黙参照

### 1. CONFIG_DB `COPP_TRAP` — キー転写 + SET/DEL トリガ

- `coppmgrd` は `CFG_COPP_TRAP_TABLE_NAME` を subscribe し、`<trap-name>` をそのまま `COPP_TRAP_TABLE` キーに転写する。
- `trap_group` / `trap_ids` / `always_enabled` フィールドを参照して STATE_DB への書込み可否を決定する。
- evidence: `coppmgr.cpp` L298-303, L531-815 (`doCoppTrapTask`)

### 2. CONFIG_DB `COPP_GROUP` — キー転写 + SET/DEL トリガ

- `<group-name>` が `COPP_GROUP_TABLE` キーに転写される。
- evidence: `coppmgr.cpp` L299, L840-927 (`doCoppGroupTask`)

### 3. CONFIG_DB `FEATURE` — feature 有効フラグ参照

- `isFeatureEnabled(feature)` が `FEATURE|<name>.state == "enabled"` を確認し、トラップを有効化するか否かを決定する。
- evidence: `coppmgr.cpp` L300, L323-330, L928-967 (`doFeatureTask`), L157-172 (`isFeatureEnabled`)

### 4. APPL_DB `APP_COPP_TABLE` — 中継テーブル

- `coppmgrd` が `APP_COPP_TABLE|<group>` に SET した後、`CoppOrch` が APPL_DB を consumer として読み出し SAI に反映する。SAI 結果が `hw_status` として STATE_DB に返る。
- evidence: `coppmgr.cpp` L301, `copporch.cpp` L191

### 5. `PortsOrch::allPortsReady()` — 起動順序ガード

- `CoppOrch::doTask()` 冒頭で `gPortsOrch->allPortsReady()` が false なら即 return する。
- 全ポートが Ready でない間は `hw_status` が `COPP_TRAP_TABLE` に書き込まれない。
- evidence: `copporch.cpp` L885-888

### 6. SAI `sai_query_attribute_enum_values_capability()` — COPP_TRAP_CAPABILITY_TABLE 生成源

- 起動時 1 回、SAI クエリで得たトラップ ID リストを `COPP_TRAP_CAPABILITY_TABLE|traps` に書き込む。
- クエリ失敗時は `default_supported_trap_ids`（42 種、`neighbor_miss` 除く）にフォールバック。
- evidence: `copporch.cpp` L240-300 (`publishTrapIdsCapability`)

### 7. SAI `sai_hostif_api` 戻り値 — `hw_status` 値決定

- `create_hostif_trap()` 成功 → `"installed"`、`remove_hostif_trap()` 成功 → `"not-installed"` を書き込む。
- 失敗時は書込みをスキップしエラーログのみ出力。
- evidence: `copporch.cpp` L526, L1413 (`updateTrapOperStatus`)

### 8. `platform` 環境変数 — SAI 操作の分岐

- Mellanox / Marvell プラットフォームでは trap priority 設定が省略される。
- `COPP_TRAP_TABLE.hw_status` の書込みには直接影響しないが、SAI create_hostif_trap の成否に間接影響する。
- evidence: `copporch.cpp` L353-354, L1188-1189

---

## 参照サマリ

| 参照先 | 影響テーブル | 影響フィールド |
|--------|------------|--------------|
| `COPP_TRAP` (CONFIG_DB) | `COPP_TRAP_TABLE` | キー・state |
| `COPP_GROUP` (CONFIG_DB) | `COPP_GROUP_TABLE` | キー・state |
| `FEATURE` (CONFIG_DB) | `COPP_TRAP_TABLE`, `COPP_GROUP_TABLE` | state（追加・削除トリガ） |
| `APP_COPP_TABLE` (APPL_DB) | `COPP_TRAP_TABLE` | hw_status（間接） |
| `PortsOrch::allPortsReady()` | `COPP_TRAP_TABLE` | hw_status（書込みガード） |
| SAI capability query | `COPP_TRAP_CAPABILITY_TABLE` | trap_ids |
| SAI hostif_trap API | `COPP_TRAP_TABLE` | hw_status |
| `platform` 環境変数 | `COPP_TRAP_TABLE` | hw_status（間接） |
