# Phase A 中間ファイル — STATE_DB COPP 関連テーブルのコード由来デフォルト

作成日: 2026-05-15  
対象ページ: `docs/reference/config-db/copp-state.md`

## 調査対象テーブル

STATE_DB に存在する COPP 関連テーブル（`schema.h` 定義）:

| 定数名 | テーブル名 | 書き手 |
|---|---|---|
| `STATE_COPP_GROUP_TABLE_NAME` | `COPP_GROUP_TABLE` | `coppmgr` (`CoppMgr::setCoppGroupStateOk`) |
| `STATE_COPP_TRAP_TABLE_NAME` | `COPP_TRAP_TABLE` | `coppmgr` (`CoppMgr::setCoppTrapStateOk`) + `CoppOrch::updateTrapOperStatus` |
| `STATE_COPP_TRAP_CAPABILITY_TABLE_NAME` | `COPP_TRAP_CAPABILITY_TABLE` | `CoppOrch::publishTrapIdsCapability` |

## COPP_GROUP_TABLE フィールド

### `state`
- 型: `string`
- 値: `"ok"` (固定)
- 設定箇所: `coppmgr.cpp` L426-431 `setCoppGroupStateOk()`
- 削除条件: トラップグループが pending 状態になった場合 (`delCoppGroupStateOk()`)
- デフォルト: なし（エントリ自体が存在しない = pending / 未登録）
- コード:
  ```cpp
  FieldValueTuple tuple("state", "ok");
  vector<FieldValueTuple> fvs;
  fvs.push_back(tuple);
  m_stateCoppGroupTable.set(alias, fvs);
  ```

## COPP_TRAP_TABLE フィールド

### `state` (coppmgr 由来)
- 型: `string`
- 値: `"ok"` (固定)
- 設定箇所: `coppmgr.cpp` L439-446 `setCoppTrapStateOk()`
- 削除条件: `delCoppTrapStateOk()` (trap 削除 / feature 無効化時)
- デフォルト: なし（エントリ自体が存在しない = 未登録または feature 無効）
- コード:
  ```cpp
  FieldValueTuple tuple("state", "ok");
  vector<FieldValueTuple> fvs;
  fvs.push_back(tuple);
  m_stateCoppTrapTable.set(alias, fvs);
  ```

### `hw_status` (copporch 由来)
- 型: `string`
- 値:
  - `"installed"`: SAI `sai_hostif_api->create_hostif_trap()` 成功後 (`copporch.cpp` L526)
  - `"not-installed"`: SAI `sai_hostif_api->remove_hostif_trap()` 成功後 (`copporch.cpp` L1413)
- 設定箇所: `copporch.cpp` L222-236 `updateTrapOperStatus()`
- key: trap の名前文字列 (`get_trap_name_by_type()` で sai_hostif_trap_type_t → string 変換)
- デフォルト: エントリが存在しない（trap がまだ SAI で操作されていない状態）
- コード:
  ```cpp
  vector<FieldValueTuple> hwStatusFvs;
  hwStatusFvs.emplace_back("hw_status", hw_status);
  m_trapTable->set(trap_name, hwStatusFvs);
  ```
- 注意: `state` (coppmgr) と `hw_status` (copporch) は **同一テーブル・同一 key** に異なるプロセスが書き込む。それぞれ独立フィールドとして共存する。

## COPP_TRAP_CAPABILITY_TABLE フィールド

### key: `traps`
- フィールド: `trap_ids`
- 型: `string` (comma-separated list)
- 値: SAI capability query で返ったトラップ ID 名をカンマ区切りで連結
- 設定箇所: `copporch.cpp` L240-299 `publishTrapIdsCapability()`
- フォールバック: SAI query 失敗時は `default_supported_trap_ids` の静的リスト（42 種）を使用
- デフォルト: SAI query 結果（プラットフォーム依存）またはフォールバックリスト
- `neighbor_miss` は `default_supported_trap_ids` に意図的に含まれない（コメント: "This list is intended to remain static"）
- コード:
  ```cpp
  trapCapabilityFvs.push_back(FieldValueTuple("trap_ids", trap_id_list_str));
  m_trapCapabilityTable->set("traps", trapCapabilityFvs);
  ```

## 暗黙デフォルトのまとめ

| テーブル | キー | フィールド | デフォルト値 | 出所 |
|---|---|---|---|---|
| `COPP_GROUP_TABLE` | `<group-name>` | `state` | `"ok"` (存在=ok) | `coppmgr.cpp:426-431` |
| `COPP_TRAP_TABLE` | `<trap-name>` | `state` | `"ok"` (存在=ok) | `coppmgr.cpp:439-446` |
| `COPP_TRAP_TABLE` | `<trap-name>` | `hw_status` | `"installed"` または `"not-installed"` | `copporch.cpp:526,1413` |
| `COPP_TRAP_CAPABILITY_TABLE` | `traps` | `trap_ids` | SAI query 結果またはフォールバックリスト | `copporch.cpp:240-299` |

## エントリ不在の意味

- `COPP_GROUP_TABLE|<name>` が不在 → グループが pending 状態（feature 未有効）またはまだ処理前
- `COPP_TRAP_TABLE|<name>` が不在 → trap が pending 状態または DEL 後
- `hw_status` フィールドが不在 → CoppOrch がまだそのトラップを SAI に登録/削除操作していない

## 証跡

- `sonic-swss/cfgmgr/coppmgr.cpp` L424-451 全行読了（setCoppGroupStateOk / setCoppTrapStateOk）
- `sonic-swss/orchagent/copporch.cpp` L222-236, L526, L1413 読了（updateTrapOperStatus）
- `sonic-swss/orchagent/copporch.cpp` L240-299 読了（publishTrapIdsCapability）
- `sonic-swss-common/common/schema.h` L448-450 読了（テーブル名定数）
- `sonic-utilities/tests/dump_input/copp/state_db.json` 読了（実データ確認）
- `sonic-utilities/dump/plugins/copp.py` L108-115 読了（STATE_DB 読み取りパス確認）
