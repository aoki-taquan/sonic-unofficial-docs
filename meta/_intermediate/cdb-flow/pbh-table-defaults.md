# PBH_TABLE フィールド暗黙デフォルト調査 (Phase A)

## 調査ソース

| ファイル | 役割 |
|---|---|
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-pbh.yang` | YANG スキーマ定義 |
| `sonic-swss/orchagent/pbh/pbhmgr.cpp` | フィールド parse + validate (parsePbhTable / validatePbhTable) |
| `sonic-swss/orchagent/pbh/pbhschema.h` | フィールド名定数 |
| `sonic-utilities/config/plugins/pbh.py` | CLI add/update/delete |

## フィールド別解析結果

### 1. `interface_list` (PBH_TABLE_INTERFACE_LIST)

- **YANG**: `leaf-list interface_list; min-elements 1; type union { leafref PORT | leafref PORTCHANNEL }; ordered-by user`
  - YANG は `min-elements 1` のみ。`mandatory` キーワードは使用しない (leaf-list は mandatory 不可)
- **pbhmgr.cpp `parsePbhTableInterfaceList`**:
  ```cpp
  const auto &ifList = tokenize(value, ',');
  if (ifList.empty()) {
      SWSS_LOG_ERROR("Failed to parse field(%s): empty list is prohibited", field.c_str());
      return false;
  }
  table.interface_list.value = std::unordered_set<std::string>(ifList.cbegin(), ifList.cend());
  if (table.interface_list.value.size() != ifList.size()) {
      SWSS_LOG_WARN("Duplicate interfaces in field(%s): unexpected value(%s)", ...);
  }
  ```
- **pbhmgr.cpp `validatePbhTable`**:
  ```cpp
  if (!table.interface_list.is_set) {
      SWSS_LOG_ERROR("Validation error: missing mandatory field(%s)", PBH_TABLE_INTERFACE_LIST);
      return false;
  }
  ```
- **デフォルト**: なし。未指定 (`is_set == false`) → validatePbhTable で SWSS_LOG_ERROR + return false
- **暗黙動作**:
  - 空リスト (`""`) → parsePbhTableInterfaceList で即 error
  - 重複 interface → `unordered_set` により自動的に dedup されるが SWSS_LOG_WARN を出力
  - CONFIG_DB には `,` 区切り文字列として格納、parse 時に tokenize して set へ変換
- **YANG-実装 discrepancy**: なし (YANG min-elements 1 と実装の空リスト禁止は一致)

### 2. `description` (PBH_TABLE_DESCRIPTION)

- **YANG**: `leaf description; mandatory true; type string { length 1..255; }`
- **pbhmgr.cpp `parsePbhTableDescription`**:
  ```cpp
  if (value.empty()) {
      SWSS_LOG_ERROR("Failed to parse field(%s): empty string is prohibited", field.c_str());
      return false;
  }
  table.description.value = value;
  ```
- **pbhmgr.cpp `validatePbhTable`**:
  ```cpp
  if (!table.description.is_set) {
      SWSS_LOG_ERROR("Validation error: missing mandatory field(%s)", PBH_TABLE_DESCRIPTION);
      return false;
  }
  ```
- **デフォルト**: なし。未指定 → SWSS_LOG_ERROR + return false
- **暗黙動作**:
  - 空文字列 (`""`) → parsePbhTableDescription で即 error (YANG length 1..255 と一致)
  - 最大長 255 は YANG 定義。実装側に上限チェックはないが YANG バリデーション段階で拒否される
- **YANG-実装 discrepancy**: なし

## 未知フィールドの扱い

`parsePbhTable` のループで `interface_list` / `description` 以外のフィールドを受け取った場合:

```cpp
else {
    SWSS_LOG_WARN("Unknown field(%s): skipping ...", field.c_str());
}
```

→ 未知フィールドはサイレントにスキップ (error にならない)

## CLI 側動作 (sonic-utilities/config/plugins/pbh.py)

```python
@PBH_TABLE.command(name="add")
@click.option("--interface-list", required=True, ...)
@click.option("--description", required=True, ...)
def PBH_TABLE_add(db, table_name, interface_list, description):
    data[PBH_TABLE_INTERFACE_LIST] = interface_list.split(",")
    data[PBH_TABLE_DESCRIPTION] = description
```

- CLI レベルでも両フィールドは `required=True` — デフォルトなし
- `update` コマンドでは両フィールドとも optional だが、省略時は CONFIG_DB に書き込まれない (既存値を保持)

## SAI マッピング

`PBH_TABLE` は SAI では `sai_acl_api->create_acl_table_group()` および `create_acl_table_group_member()` に相当するオブジェクトへマッピングされる (pbhorch.cpp `createPbhTable`)。`interface_list` の各 interface に対して ACL table group member が生成される。

## 検出まとめ

| 種別 | フィールド | 内容 |
|---|---|---|
| mandatory (デフォルトなし) | `interface_list` | YANG min-elements 1 + 実装 validatePbhTable で強制。空リスト即 error |
| mandatory (デフォルトなし) | `description` | YANG mandatory true + 実装 validatePbhTable で強制。空文字列即 error |
| 暗黙動作 | `interface_list` 重複 | unordered_set で dedup + SWSS_LOG_WARN (error にならない) |
| 未知フィールド | 任意 | SWSS_LOG_WARN でスキップ (error にならない) |

**結論**: `PBH_TABLE` の全フィールドは mandatory で実装デフォルトなし。YANG-実装間の discrepancy なし。
