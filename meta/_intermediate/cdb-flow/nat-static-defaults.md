# STATIC_NAT フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: CONFIG_DB `STATIC_NAT`

## 調査対象ファイル

- `sonic-swss/cfgmgr/natmgr.cpp` (`doStaticNatTask` L5810-6136)
- `sonic-utilities/config/nat.py` (`add_basic` CLI コマンド L240-329)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-nat.yang` (STATIC_NAT_LIST L117-155)

---

## フィールド別 暗黙デフォルト

### key: `global_ip`

YANG key。`STATIC_NAT|<global_ip>` 形式。`inet:ipv4-address` 型。  
Zero / Broadcast / Loopback / Multicast / Reserved アドレスは natmgr が拒否する (L5855-5861)。  
**必須 (key)。デフォルト値なし。**

---

### `local_ip`

**必須フィールド**。YANG `mandatory true`、`inet:ipv4-address` 型。  
CLI (`config nat add static basic`) では positional argument で required=True。  
省略不可。`natmgr.cpp:5904` で `ipFound == false` の場合 SWSS_LOG_ERROR + erase。

---

### `nat_type`

**省略可能。コード由来デフォルト: `"dnat"`**

YANG:
```yang
# sonic-nat.yang:137-142
leaf nat_type {
    description "Nat type for the static nat entry - snat or dnat";
    type nat-type;
    default dnat;
}
```

CLI (`nat.py:246`): `-nat_type` オプションは `required=False`。省略時は DB に `nat_type` フィールドを書かない (L326-328 で `local_ip` のみ `set_entry`)。

`natmgr.cpp` での読み込み:
```cpp
// natmgr.cpp:6088-6095
if (nat_type.empty())
{
    m_staticNatEntry[key].nat_type = DNAT_NAT_TYPE;  // "dnat"
}
else
{
    m_staticNatEntry[key].nat_type = nat_type;
}
```
DB に `nat_type` フィールドが存在しない (または空) 場合、`DNAT_NAT_TYPE = "dnat"` がデフォルトとして適用される。

**注意**: `NAT_BINDINGS.nat_type` のデフォルトが `"snat"` であるのと逆。

**結論**: `nat_type` 省略時は `"dnat"` が適用 (YANG default / natmgr コード 両方一致)。

---

### `twice_nat_id`

**省略可能。コード由来デフォルト: `""` (空文字列 / 未設定 = Single NAT)**

YANG: `twice_nat_id` に `default` 指定なし。省略可能リーフ。有効範囲 `1..9999`。

CLI:
```python
# sonic-utilities/config/nat.py:247,320-328
@click.option('-twice_nat_id', metavar='<twice_nat_id>', required=False, ...)
...
elif twice_nat_id is not None:
    config_db.set_entry(table, key, {dataKey1: local_ip, dataKey3: twice_nat_id})
else:
    config_db.set_entry(table, key, {dataKey1: local_ip})
```
省略時は `twice_nat_id` フィールドを DB に書かない。

`natmgr.cpp` 初期化:
```cpp
// natmgr.cpp:5825
string twice_nat_id = EMPTY_STRING;
```
DB に `twice_nat_id` がなければ `""` のまま。

キャッシュ格納:
```cpp
// natmgr.cpp:6096-6098
m_staticNatEntry[key].twice_nat_id = twice_nat_id;  // "" if omitted
m_staticNatEntry[key].twice_nat_added = false;
m_staticNatEntry[key].binding_key = EMPTY_STRING;
```

動作分岐:
```cpp
// natmgr.cpp:1579
if (m_staticNatEntry[key].twice_nat_id.empty())
{
    // Single NAT: addStaticSingleNatEntry
}
else
{
    // Twice NAT: addStaticTwiceNatEntry
}
```
`twice_nat_id` が空 → Single NAT として処理。非空 → Twice NAT として処理。

**結論**: `twice_nat_id` 省略時は `""` = Single NAT モード。DB には書き込まれない。

---

## 上限・制約

- **key (global_ip)**: unicast IPv4 のみ (Zero/Broadcast/Loopback/Multicast/Reserved は拒否)
- **key size**: `STATIC_NAT_KEY_SIZE = 1` (delimiter `|` で分割したセグメント数) — 超過は ERROR + erase (`natmgr.cpp:5846`)
- **local_ip**: unicast IPv4 のみ (同様のアドレスクラス制限)
- **nat_type**: `"snat"` or `"dnat"` のみ。それ以外は ERROR + erase (`natmgr.cpp:5954-5958`)
- **twice_nat_id**: 1..9999。範囲外は YANG / natmgr 両方で拒否
- **エントリ数**: CLI では COUNTERS_DB `SNAT_ENTRIES >= MAX_NAT_ENTRIES` でスキップ (`nat.py:298-300`)
- **IP 重複禁止**: global_ip が他の STATIC_NAPT エントリや NAT_POOL と重複する場合は ERROR + erase

---

## silent drop / discrepancy まとめ

| フィールド / 条件 | 検出種別 | 挙動 | ソース |
|---|---|---|---|
| `local_ip` 欠落 | silent drop | `SWSS_LOG_ERROR("Invalid local_ip values, skipping %s")` + erase | `natmgr.cpp:5906` |
| `nat_type` 欠落 | 暗黙デフォルト | `DNAT_NAT_TYPE = "dnat"` にフォールバック | `natmgr.cpp:6088-6090` |
| `twice_nat_id` 欠落 | 暗黙デフォルト | `""` = Single NAT モード | `natmgr.cpp:5825, 6096` |
| `nat_type` が `snat`/`dnat` 以外 | silent drop | ERROR + erase | `natmgr.cpp:5954-5958` |
| `global_ip` が特殊アドレス | silent drop | ERROR + erase | `natmgr.cpp:5855-5861` |
| `local_ip` が特殊アドレス | silent drop | ERROR + erase | `natmgr.cpp:5944-5950` |
| global_ip が STATIC_NAPT と重複 | silent drop | ERROR + erase | `natmgr.cpp:6007-6011` |
| global_ip が NAT_POOL IP と重複 | silent drop | ERROR + erase | `natmgr.cpp:6052-6056` |
| 重複エントリ (同 key + 同 local_ip) | silent drop | `"Duplicate Static NAT and it's values"` + erase | `natmgr.cpp:6067` |
| 未知フィールド (local_ip/nat_type/twice_nat_id 以外) | silent drop | `nonValueFound=true` → ERROR + erase | `natmgr.cpp:5898-5933` |
| NAT_BINDINGS.nat_type default vs STATIC_NAT.nat_type default | YANG-実装一致 discrepancy (テーブル間) | BINDINGS は `"snat"` デフォルト、STATIC_NAT は `"dnat"` デフォルト — 逆方向 | YANG `sonic-nat.yang:141,280` |

---

## 要約表

| フィールド | 省略可否 | コード由来デフォルト | 根拠 |
|-----------|---------|-------------------|------|
| `global_ip` (key) | 必須 | なし (key) | YANG key |
| `local_ip` | 必須 | なし (mandatory) | YANG mandatory + CLI required |
| `nat_type` | 省略可 | `"dnat"` | YANG `default dnat` / `natmgr.cpp:6088-6090` |
| `twice_nat_id` | 省略可 | `""` → Single NAT | DB に書かれない / `natmgr.cpp:5825,6096` |

---

## 証拠リンク

- `sonic-swss/cfgmgr/natmgr.cpp:5810-6136` — `doStaticNatTask` (フィールド解析・デフォルト適用)
- `sonic-swss/cfgmgr/natmgr.cpp:1544-1690` — `addStaticNatEntry` / `removeStaticNatEntry` (twice_nat_id 分岐)
- `sonic-utilities/config/nat.py:240-329` — `add_basic` CLI コマンド
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-nat.yang:117-155` — `STATIC_NAT_LIST` YANG 定義
