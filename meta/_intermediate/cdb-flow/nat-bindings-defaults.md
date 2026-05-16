# NAT_BINDINGS フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `NAT_BINDINGS`

## 調査対象ファイル

- `sonic-swss/cfgmgr/natmgr.cpp` (`doNatBindingTask` / `addDynamicNatRule`)
- `sonic-swss/cfgmgr/natmgr.h` (定数定義)
- `sonic-utilities/config/nat.py` (`add_binding` CLI コマンド)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-nat.yang` (YANG スキーマ)

---

## フィールド別 暗黙デフォルト

### `nat_pool`

**必須フィールド**。YANG では `mandatory true` かつ `leafref` で既存 `NAT_POOL.name` への参照が必須。  
CLI (`config nat add binding`) では positional argument として required=True。  
省略不可。デフォルト値なし。

```
# natmgr.h:56
#define NAT_POOL  "nat_pool"
```

---

### `access_list`

**省略可能。コード由来デフォルト: `""` (空文字列)**

YANG モジュール (`sonic-nat.yang`) には `access_list` フィールドが定義されていない。  
`natmgr.h` で `#define NAT_ACLS "access_list"` として定義され、`natmgr.cpp` の `doNatBindingTask` が直接読む。

CLI (`config nat add binding`):
```python
# sonic-utilities/config/nat.py:782,796-797
@click.argument('acl_name', metavar='<acl_name>', required=False)
...
if acl_name is None:
    acl_name = ""
```
ACL 名を省略した場合、`""` を DB に書き込む。

`natmgr.cpp` 初期化:
```cpp
// natmgr.cpp:6879
string nat_pool = EMPTY_STRING, nat_acl = EMPTY_STRING;
```
DB に `access_list` キーが存在しない場合 `nat_acl = ""` のまま処理。

`addDynamicNatRule` での利用:
```cpp
// natmgr.cpp:4629
string acls_name = m_natBindingInfo[key].acl_name;
```
`acls_name` が空文字列の場合、`setDynamicAllForwardOrAclbasedRules` は ACL なし (全トラフィック対象) でルールを設定する。

**結論**: `access_list` 省略時は全送信元トラフィックが NAT 対象となる。

---

### `nat_type`

**省略可能。コード由来デフォルト: `"snat"`**

YANG:
```yang
# sonic-nat.yang:276-281
leaf nat_type {
    description "Nat type for the binding - snat or dnat";
    type nat-type;
    default snat;
}
```
YANG レベルでは `default snat`。

CLI:
```python
# sonic-utilities/config/nat.py:816-821
if nat_type is not None:
    if nat_type == "dnat":
        click.echo("Ignored, DNAT is not yet supported for Binding ")
        entryFound = True
else:
    nat_type = "snat"
```
省略時は `"snat"` を設定。`dnat` を指定した場合は **未サポートとして拒否**される (CLI レベル)。

`natmgr.cpp` での読み込み:
```cpp
// natmgr.cpp:7056-7063
if (nat_type.empty())
{
    m_natBindingInfo[key].nat_type = SNAT_NAT_TYPE;  // "snat"
}
else
{
    m_natBindingInfo[key].nat_type = nat_type;
}
```
DB に `nat_type` フィールドが存在しない場合、`SNAT_NAT_TYPE = "snat"` がデフォルトとして適用される。

**結論**: `nat_type` 省略時は `"snat"` が適用される (YANG / CLI / natmgr 全て一致)。

---

### `twice_nat_id`

**省略可能。コード由来デフォルト: `""` (空文字列 / 未設定)**

YANG では `twice_nat_id` に `default` 指定なし。省略可能リーフ。

CLI:
```python
# sonic-utilities/config/nat.py:823-824
if twice_nat_id is None:
    twice_nat_id = "NULL"
```
省略時は `"NULL"` を DB に書き込む。

`natmgr.cpp` での `"NULL"` 処理:
```cpp
// natmgr.cpp:6993-6996
if (twice_nat_id == "NULL")
{
    twiceNatFound = false;
    twice_nat_id = EMPTY_STRING;
}
```
`"NULL"` は空文字列 (`""`) に変換され、`twiceNatFound = false` となる。

キャッシュへの格納:
```cpp
// natmgr.cpp:7054
m_natBindingInfo[key].twice_nat_id = twice_nat_id;  // ""
m_natBindingInfo[key].twice_nat_added = false;
```

動作分岐:
```cpp
// natmgr.cpp:4663
if (m_natBindingInfo[key].twice_nat_id.empty())
{
    /* Add Dynamic rules for Single NAT */
    setDynamicAllForwardOrAclbasedRules(ADD, ...);
}
else
{
    /* Add Dynamic rules for Twice NAT */
    addDynamicTwiceNatRule(key);
}
```
`twice_nat_id` が空 → Single NAT として処理。非空 → Twice NAT として処理。

有効範囲: 1..9999 (YANG: `range "1..9999"`, natmgr.h: `TWICE_NAT_ID_MIN=1, TWICE_NAT_ID_MAX=9999`)。

**結論**: `twice_nat_id` 省略時は `""` 相当となり Single NAT モード。DB には `"NULL"` が書き込まれ natmgrd が空文字列に変換する。

---

## 上限・制約

- **バインディング名**: 最大 32 文字、`[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})` パターン。
- **エントリ数上限**: max-elements=16 (YANG) / コード側でも `len(binding_dict) == 16` チェック (nat.py:812)。
- **nat_type=dnat は CLI で拒否**: natmgr 側では `SNAT_NAT_TYPE` のみ許容 (natmgr.cpp:6986-6991)。

---

## 要約表

| フィールド | 省略可否 | コード由来デフォルト | 根拠 |
|-----------|---------|-------------------|------|
| `nat_pool` | 必須 | なし (mandatory) | YANG mandatory + CLI required |
| `access_list` | 省略可 | `""` (空文字列) | cli nat.py:797 / natmgr.cpp:6879 |
| `nat_type` | 省略可 | `"snat"` | YANG default / cli nat.py:821 / natmgr.cpp:7058 |
| `twice_nat_id` | 省略可 | `""` → Single NAT | cli `"NULL"` → natmgr.cpp:6993-6996 変換 |

---

## 証拠リンク

- `sonic-swss/cfgmgr/natmgr.cpp:6869-7071` — `doNatBindingTask` (フィールド解析・デフォルト適用)
- `sonic-swss/cfgmgr/natmgr.cpp:4621-4679` — `addDynamicNatRule` (twice_nat_id 分岐)
- `sonic-swss/cfgmgr/natmgr.h:36-57` — 定数定義 (`NAT_POOL`, `NAT_ACLS`, `SNAT_NAT_TYPE`, 範囲定数)
- `sonic-utilities/config/nat.py:776-838` — `add_binding` CLI コマンド
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-nat.yang:245-296` — `NAT_BINDINGS` YANG 定義
