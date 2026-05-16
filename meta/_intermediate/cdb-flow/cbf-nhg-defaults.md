# cbf-nhg Phase A — CLASS_BASED_NEXT_HOP_GROUP フィールドデフォルト調査

## 調査対象

- テーブル: `CLASS_BASED_NEXT_HOP_GROUP` (APPL_DB)
- ソースコード: `sonic-swss/orchagent/cbf/cbfnhgorch.cpp` (HEAD)
- HLD: `SONiC/doc/cbf/cbf_hld.md`

## フィールド一覧

HLD `cbf_hld.md:109-114` より:

```
key           = CLASS_BASED_NEXT_HOP_GROUP_TABLE:string
members       = NEXT_HOP_GROUP_TABLE.key,...   ; カンマ区切り
selection_map = FC_TO_NHG_INDEX_MAP_TABLE.key
```

## 各フィールドのデフォルト分析

### `members` (string, カンマ区切り)

- 必須フィールド。省略するとデフォルト空文字列 `""` となる
- `cbfnhgorch.cpp:69-73`: `string members;` → 初期値空文字列
- `cbfnhgorch.cpp:82-90`: `getMembers(members)` が空文字列を受け取ると `members_set.empty()` → `SWSS_LOG_ERROR` + エラー返却 → エントリを consumer からも除去 (erase) される
- **コード由来デフォルト: なし（必須、省略時はエラー破棄）**
- 重複メンバーも検証: `members_set.size() != members_vec.size()` → エラー

### `selection_map` (string)

- 必須フィールド。省略するとデフォルト空文字列 `""` となる
- `cbfnhgorch.cpp:75-77`: `string selection_map;` → 初期値空文字列
- `cbfnhgorch.cpp:318-325`: `gNhgMapOrch->getMapId(m_selection_map)` が `SAI_NULL_OBJECT_ID` を返すとエラーログ + `false` 返却 → sync 失敗
- 空文字列のマップは存在しないため、結果として必須扱い
- **コード由来デフォルト: なし（必須、省略時は sync 失敗）**

## SAI 属性マッピング

| CONFIG/APPL フィールド | SAI 属性 | ソース |
|---|---|---|
| グループ型 (固定) | `SAI_NEXT_HOP_GROUP_TYPE_CLASS_BASED` | `cbfnhgorch.cpp:301-303` |
| `members` の数 | `SAI_NEXT_HOP_GROUP_ATTR_CONFIGURED_SIZE` | `cbfnhgorch.cpp:306-309` |
| `selection_map` → OID | `SAI_NEXT_HOP_GROUP_ATTR_SELECTION_MAP` | `cbfnhgorch.cpp:318-333` |
| 各 member の index (0-based) | `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_INDEX` | `cbfnhgorch.cpp:738-739; CbfNhg::CbfNhg:257-260` |

## インデックス割り当て

- `CbfNhg::CbfNhg()` コンストラクタ: `uint8_t idx = 0; for (member) { m_members.emplace(member, CbfNhgMember(member, idx++)); }` — `cbfnhgorch.cpp:257-261`
- member の index は宣言順に 0 から自動付与
- `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_INDEX` は `CREATE_ONLY` 属性 (更新不可)
- member 変更時は全 member を一旦 remove → 再 sync: `cbfnhgorch.cpp:516-553`

## 制約まとめ

| 制約 | コード箇所 |
|---|---|
| `members` は空不可 | `cbfnhgorch.cpp:223-227` |
| `members` の各エントリは一意 | `cbfnhgorch.cpp:231-235` |
| `selection_map` は既存の FC_TO_NHG_INDEX_MAP_TABLE エントリを参照必須 | `cbfnhgorch.cpp:321-325` |
| selection_map の最大 NH index < members.size() | `cbfnhgorch.cpp:327-331, 540-544` |
| グループ数上限: `gRouteOrch->getMaxNhgCount()` | `cbfnhgorch.cpp:100` |
| members 数が FC 最大数超過 → 警告ログのみ (エラーではない) | `cbfnhgorch.cpp:311-314` |

## Phase A 結論

`CLASS_BASED_NEXT_HOP_GROUP` には「省略時に fallback するデフォルト値」を持つフィールドは存在しない。両フィールドとも実質必須であり、コードが初期化する空文字列はエラーパスに入るだけ。ドキュメントには「必須フィールド / デフォルトなし」として記載する。
