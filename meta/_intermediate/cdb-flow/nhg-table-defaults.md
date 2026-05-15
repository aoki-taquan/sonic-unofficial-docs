# NEXTHOP_GROUP_TABLE / CLASS_BASED_NEXT_HOP_GROUP_TABLE フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: APPL_DB `NEXTHOP_GROUP_TABLE` / `CLASS_BASED_NEXT_HOP_GROUP_TABLE`

## 調査対象ファイル

- `sonic-swss/orchagent/nhgorch.cpp` (`NhgOrch::doTask`, `NextHopGroup::createNhgmAttrs`)
- `sonic-swss/orchagent/nhgorch.h` (`NhgOrch` / `NextHopGroup` / `NextHopGroupMember`)
- `sonic-swss/orchagent/nexthopkey.h` (`NextHopKey` — weight フィールドの初期値)
- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp` (`CbfNhgOrch::doTask`, `CbfNhg::sync`)
- `sonic-swss/orchagent/cbf/cbfnhgorch.h` (`CbfNhg` / `CbfNhgMember` / `CbfNhgOrch`)
- `sonic-swss/fpmsyncd/routesync.cpp` (`NextHopGroupTableFieldValueTupleWrapper::fieldValueTupleVector`)
- `sonic-swss-common/common/schema.h` (テーブル名定数)

---

## テーブル名定数（schema.h）

```c
#define APP_NEXTHOP_GROUP_TABLE_NAME                "NEXTHOP_GROUP_TABLE"
#define APP_CLASS_BASED_NEXT_HOP_GROUP_TABLE_NAME   "CLASS_BASED_NEXT_HOP_GROUP_TABLE"
```

---

## NEXTHOP_GROUP_TABLE フィールド別 暗黙デフォルト

### `nexthop` (comma-separated IP list)

**コード由来デフォルト**: キー不在 → 空文字列 `""` → ips 変数は空のまま

```cpp
// nhgorch.cpp:60-74
string ips;
for (auto i : kfvFieldsValues(t)) {
    if (fvField(i) == "nexthop" && fvValue(i) != "")
        ips = fvValue(i);
}
```

`nexthop` が空または不在の場合、`nexthop_group`（再帰 NHG）フィールドの有無で分岐。
どちらも空の場合は `nhg_key` が空 → `NextHopGroupKey` の空キーが渡され、NHG 生成はスキップされる。

---

### `ifname` (comma-separated interface name list)

**コード由来デフォルト**: キー不在 → 空文字列 `""` → aliases 変数は空のまま

```cpp
// nhgorch.cpp:76-77
if (fvField(i) == "ifname" && fvValue(i) != "")
    aliases = fvValue(i);
```

fpmsyncd の `NextHopGroupTableFieldValueTupleWrapper` では `ifname != string()` のときのみ書き込む（空文字列はフィールドなし）。

---

### `weight` (comma-separated uint32 list)

**コード由来デフォルト**: キー不在 → 空文字列 → 各 NH の weight = `0`

```cpp
// nhgorch.cpp:79-80
if (fvField(i) == "weight" && fvValue(i) != "")
    weights = fvValue(i);
```

`NextHopGroupKey` に渡される `weights` が空の場合、内部で各 NH の `weight` フィールドは初期値 `0` のまま。

```cpp
// nexthopkey.h:37
NextHopKey() : weight(0) {}
```

`createNhgmAttrs()` では weight == 0 のとき `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_WEIGHT` を送出しない:

```cpp
// nhgorch.cpp:1113-1118
auto weight = nhgm.getWeight();
if (weight != 0) {
    nhgm_attr.id = SAI_NEXT_HOP_GROUP_MEMBER_ATTR_WEIGHT;
    nhgm_attr.value.s32 = weight;
    nhgm_attrs.push_back(nhgm_attr);
}
```

→ weight = 0 は「SAI デフォルト（等コスト）」として扱われる。ECMP は weight 不在時に等分配。

**fpmsyncd 側のデフォルト**: `weight != string()` のときのみ書き込み (routesync.cpp:1154-1155)。
weight 指定なしルートは weight フィールドを書かない → orchagent は weight=0 (等コスト) と解釈。

---

### `nexthop_group` (再帰 NHG 用: comma-separated NHG index list)

**コード由来デフォルト**: キー不在 → `is_recursive = false`

```cpp
// nhgorch.cpp:91-95
if (fvField(i) == "nexthop_group" && fvValue(i) != "") {
    nhgs = fvValue(i);
    is_recursive = true;
}
```

`nexthop_group` が存在する場合、`nexthop`/`ifname` との排他チェックあり:

```cpp
// nhgorch.cpp:98-103
if (is_recursive && (!ips.empty() || !aliases.empty())) {
    SWSS_LOG_ERROR("Nexthop group %s has both regular(ip/alias) and recursive fields", index.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

`nexthop_group` で参照先 NHG が未存在の場合: `return false` → Consumer キューに残り再試行。
参照先が recursive または temporary の場合: `SWSS_LOG_ERROR` → エントリ破棄。

---

### `mpls_nh` (comma-separated MPLS nexthop list)

**コード由来デフォルト**: キー不在 → 空文字列 → MPLS ラベルなし (IP-only NH として処理)

```cpp
// nhgorch.cpp:82-83
if (fvField(i) == "mpls_nh" && fvValue(i) != "")
    mpls_nhs = fvValue(i);
```

`mpls_nhv[i] == "na"` のエントリは MPLS ラベルなし (nhgorch.cpp:230)。

---

### `seg_src` (SRv6 source address)

**コード由来デフォルト**: キー不在 → `srv6_nh = false` → 通常 IP NH として処理

```cpp
// nhgorch.cpp:85-89
if (fvField(i) == "seg_src" && fvValue(i) != "") {
    srv6_source = fvValue(i);
    srv6_nh = true;
}
```

---

## CLASS_BASED_NEXT_HOP_GROUP_TABLE フィールド別 暗黙デフォルト

### `members` (comma-separated NEXTHOP_GROUP_TABLE key list)

**コード由来デフォルト**: 必須フィールド。空またはキー不在 → `SWSS_LOG_ERROR` → エントリ破棄

```cpp
// cbfnhgorch.cpp:69-71
if (fvField(i) == "members") {
    members = fvValue(i);
}
```

`getMembers()` (cbfnhgorch.cpp:212-238) でバリデーション:
- 空リストは `SWSS_LOG_ERROR("CBF next hop group members list is empty.")` → `{false, {}}` を返す
- 重複あり は `SWSS_LOG_ERROR("CBF next hop group members are not unique.")` → `{false, {}}` を返す
- 親の `doTask()` で `p.first == false` → `consumer.m_toSync.erase(it)` → 破棄 (再試行なし)

各メンバーの index は追加順に 0, 1, 2, ... と自動採番 (cbfnhgorch.cpp:257-261, 534-537):

```cpp
uint8_t idx = 0;
for (const auto &member : members) {
    m_members.emplace(member, CbfNhgMember(member, idx++));
}
```

---

### `selection_map` (FC_TO_NHG_INDEX_MAP_TABLE key)

**コード由来デフォルト**: 空文字列許容。ただし sync() 時に `SAI_NULL_OBJECT_ID` チェックあり。

```cpp
// cbfnhgorch.cpp:72-74
else if (fvField(i) == "selection_map") {
    selection_map = fvValue(i);
}
```

`CbfNhg::sync()` (cbfnhgorch.cpp:318-325):

```cpp
nhg_attr.id = SAI_NEXT_HOP_GROUP_ATTR_SELECTION_MAP;
nhg_attr.value.oid = gNhgMapOrch->getMapId(m_selection_map);

if (nhg_attr.value.oid == SAI_NULL_OBJECT_ID) {
    SWSS_LOG_ERROR("FC to NHG map index %s does not exist", m_selection_map.c_str());
    return false;
}
```

`selection_map` が空または未存在の MAP の場合 → `return false` → Consumer キューに残り再試行。

SAI に渡す属性: `SAI_NEXT_HOP_GROUP_ATTR_TYPE = SAI_NEXT_HOP_GROUP_TYPE_CLASS_BASED` (固定、オーバーライド不可)。

`SAI_NEXT_HOP_GROUP_ATTR_CONFIGURED_SIZE` = `m_members.size()` (メンバー数)。

---

## 要約表

### NEXTHOP_GROUP_TABLE

| フィールド | コード由来デフォルト | デフォルト源 |
|-----------|-------------------|------------|
| `nexthop` | なし (フィールド不在 → ips 空) | nhgorch.cpp:73-74 条件分岐 |
| `ifname` | なし (フィールド不在 → aliases 空) | nhgorch.cpp:76-77 条件分岐 |
| `weight` | `0` (等コスト ECMP) | nexthopkey.h:37 `NextHopKey()` コンストラクタ |
| `nexthop_group` | なし → `is_recursive=false` | nhgorch.cpp:91-95 条件分岐 |
| `mpls_nh` | なし (フィールド不在 → MPLS 無効) | nhgorch.cpp:82-83 条件分岐 |
| `seg_src` | なし → `srv6_nh=false` | nhgorch.cpp:85-89 条件分岐 |

### CLASS_BASED_NEXT_HOP_GROUP_TABLE

| フィールド | コード由来デフォルト | デフォルト源 |
|-----------|-------------------|------------|
| `members` | なし (必須; 空は SWSS_LOG_ERROR+破棄) | cbfnhgorch.cpp:223-226 getMembers() |
| `selection_map` | なし (必須; 未存在は return false+再試行) | cbfnhgorch.cpp:321-324 sync() |

---

## 証拠リンク

- `sonic-swss/orchagent/nhgorch.cpp:58-103` — `NhgOrch::doTask()` フィールド読み取り
- `sonic-swss/orchagent/nhgorch.cpp:1112-1119` — `NextHopGroup::createNhgmAttrs()` weight==0 時 SAI 非送出
- `sonic-swss/orchagent/nexthopkey.h:37` — `NextHopKey()` コンストラクタ (weight=0)
- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp:38-200` — `CbfNhgOrch::doTask()`
- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp:212-238` — `CbfNhgOrch::getMembers()` バリデーション
- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp:287-376` — `CbfNhg::sync()` SAI 属性
- `sonic-swss/fpmsyncd/routesync.cpp:1138-1158` — `NextHopGroupTableFieldValueTupleWrapper::fieldValueTupleVector()`
- `sonic-swss-common/common/schema.h:55-56` — テーブル名定数
