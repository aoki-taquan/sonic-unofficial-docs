# ACL_RULE — 書き込み入り口 (Direction A)

## 探索サマリー

| ソース種別 | 有無 | 概要 |
|---|---|---|
| CLI (sonic-utilities) | あり | `acl-loader update full/incremental/delete` |
| config CLI | なし | ACL_RULE はコマンド単体の直接操作なし（acl_loader 経由） |
| minigraph | なし | ACL_RULE は minigraph で生成しない（ACL_TABLE のみ） |
| REST/gNMI | あり | `sonic-mgmt-common/translib/acl_app.go` (`/openconfig-acl:acl/acl-sets/acl-set/acl-entries`) |
| db_migrator | なし | ACL_RULE の migration ステップなし |
| build-time (j2) | なし | qos_config.j2 / init_cfg.json.j2 に ACL_RULE なし |
| hard-coded defaults | なし | |
| runtime injection | なし | orchagent は読み取り側 |

---

## CLI — acl_loader

ソース: `sonic-utilities/acl_loader/main.py`

### `acl-loader update full <filename>`

`full_update()` (L850):

1. 既存 ACL_RULE を全削除: `configdb.mod_entry(ACL_RULE, key, None)` (L859-863)
2. 新規ルールを一括書き込み: `configdb.mod_config({ACL_RULE: rules_info})` (L866)

入力: JSON ファイル（OpenConfig ACL 形式）

### `acl-loader update incremental <filename>`

`incremental_update()` (L871):

- dataplane ACL: full update 方式（L890-916）
- controlplane ACL: 差分更新
  - 追加: `configdb.mod_entry(ACL_RULE, key, value)`
  - 削除: `configdb.mod_entry(ACL_RULE, key, None)`
  - 更新（内容変更あり）: `configdb.set_entry(ACL_RULE, key, value)` (L940,944)

### `acl-loader delete [table] [rule]`

`delete()` (L946):

```python
configdb.set_entry(ACL_RULE, key, None)
```

フィルタリングして対象のみ削除。

### Multi-ASIC 対応

各 namespace ごとの `namespace_configdb` にも同じ操作を適用。per-asic namespace に対して `namespace_configdb.set_entry(ACL_RULE, ...)` を実行 (L944, L955-958)。

**対象 DB**: CONFIG_DB（+ per-namespace CONFIG_DB）

---

## REST / gNMI

ソース: `sonic-mgmt-common/translib/acl_app.go`

- REST/gNMI path: `/openconfig-acl:acl/acl-sets/acl-set{}{}/acl-entries/acl-entry{}`
- `processCreate()` / `processUpdate()` → `convertOCAclRulesToInternal()` (L1062) でルール変換
- → `d.SetEntry(app.ruleTs, db.Key{Comp: []string{aclKey, ruleKey}}, ...)` で ACL_RULE に書き込み (L266, L1418)
- ルール削除: `SetEntry(app.ruleTs, key, db.Value{})` で空 value を set

---

## db_migrator

なし。ACL_RULE の migration ステップは db_migrator.py に存在しない。

---

## build-time デフォルト

なし。

---

## hard-coded デフォルト

`acl_loader` の `deny_rule()` (L802):

デフォルト deny ルールを末尾に自動追加する内部メソッド。`full_update()` の最後に `createDefaultDenyAclRule()` (L1138) 経由で呼び出し。priority=0 の DROP ルールを ACL_RULE に書き込む。

```python
rules_info[key] = {
    "PRIORITY": "0",
    "PACKET_ACTION": "DROP",
}
configdb.set_entry(ACL_RULE, key, rules_info[key])
```

ソース: `acl_loader/main.py:1138-1149`

---

## 死活 (runtime injection)

`orchagent` の `AclOrch` は ACL_RULE を購読するのみ（読み取り側）。orchagent 自身が ACL_RULE へ書き込むケースはない。

---

## エビデンス grep カバレッジ

| ソース | パス | hit |
|---|---|---|
| acl_loader/main.py | `set_entry(ACL_RULE, ...)` | 4 |
| acl_loader/main.py | `mod_entry(ACL_RULE, ...)` / `mod_config({ACL_RULE...})` | 8 |
| acl_app.go | `SetEntry(app.ruleTs, ...)` | 3 |
| db_migrator.py | ACL_RULE | 0 |
| init_cfg.json.j2 | ACL_RULE | 0 |
| qos_config.j2 | ACL_RULE | 0 |
| minigraph.py | ACL_RULE | 0 |
