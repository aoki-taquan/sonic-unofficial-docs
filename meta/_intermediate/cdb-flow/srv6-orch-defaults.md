# srv6orch APP_DB テーブル — Phase A コード由来の暗黙デフォルト (grep 証跡)

## 探索対象テーブル一覧

grep entry コマンド:
```
grep -n "APP_SRV6_SID_LIST_TABLE_NAME\|APP_SRV6_MY_SID_TABLE_NAME\|APP_PIC_CONTEXT_TABLE_NAME" \
  sonic-swss/orchagent/srv6orch.cpp
```

ヒット: `sonic-swss/orchagent/srv6orch.cpp` 行 103-105, 2362-2384
ヒット (定義): `sonic-swss-common/common/schema.h`

---

## テーブル 1: SRV6_SID_LIST_TABLE (APP_DB)

### フィールド: path

**探索コマンド**:
```
grep -n '"path"\|sid_list\|SID_LIST_DELIMITER' sonic-swss/orchagent/srv6orch.cpp
```

**結果** (`srv6orch.cpp:1155-1158`):
```cpp
if (fvField(i) == "path")
{
    sid_list = fvValue(i);
}
```
- 未指定時は `sid_list = ""` (空文字列)。
- `createUpdateSidList` で `sid_ips = tokenize(sid_list, SID_LIST_DELIMITER)`。
- `segment_list.count == 0` の場合 `SWSS_LOG_ERROR` 出力後 `return true` (スキップ)。
- `SID_LIST_DELIMITER = ','` — カンマ区切り IPv6 リスト。

**code fallback**: なし — `path` 省略時は空 → `count == 0` でスキップ。事実上必須。

---

### フィールド: type (sidlist_type)

**探索コマンド**:
```
grep -n '"type"\|sidlist_type\|SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED\|Use default' sonic-swss/orchagent/srv6orch.cpp
```

**結果** (`srv6orch.cpp:1159-1162`):
```cpp
if (fvField(i) == "type")
{
    sidlist_type = fvValue(i);
}
```

`createUpdateSidList` 内 (`srv6orch.cpp:1079-1089`):
```cpp
attr.id = SAI_SRV6_SIDLIST_ATTR_TYPE;
if (sidlist_type_map.find(sidlist_type) == sidlist_type_map.end())
{
    SWSS_LOG_INFO("Use default sidlist type: ENCAPS_RED");
    attr.value.s32 = SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED;
}
else
{
    attr.value.s32 = sidlist_type_map.at(sidlist_type);
}
```

有効値 (`srv6orch.cpp:73-79`):
```cpp
const map<string, sai_srv6_sidlist_type_t> sidlist_type_map =
{
    {"insert",             SAI_SRV6_SIDLIST_TYPE_INSERT},
    {"insert.red",         SAI_SRV6_SIDLIST_TYPE_INSERT_RED},
    {"encaps",             SAI_SRV6_SIDLIST_TYPE_ENCAPS},
    {"encaps.red",         SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED}
};
```

**code fallback**: 未指定または不正値時 → `SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED` (`"encaps.red"` 相当)。

---

## テーブル 2: SRV6_MY_SID_TABLE (APP_DB)

### フィールド: action

**探索コマンド**:
```
grep -n '"action"\|end_action\|end_behavior_map' sonic-swss/orchagent/srv6orch.cpp
```

**結果** (`srv6orch.cpp:2215-2217`):
```cpp
if (fvField(i) == "action")
{
    end_action = fvValue(i);
}
```

`srv6orch.cpp:1473-1475`:
```cpp
if (sidEntryEndpointBehavior(end_action, end_behavior, end_flavor) != true)
{
    SWSS_LOG_ERROR("Invalid my_sid action %s", end_action.c_str());
    return false;
}
```

有効値 (`srv6orch.cpp:41-62`): `end`, `end.x`, `end.t`, `end.dx6`, `end.dx4`, `end.dt4`, `end.dt6`, `end.dt46`,
`end.b6.encaps`, `end.b6.encaps.red`, `end.b6.insert`, `end.b6.insert.red`, `udx6`, `udx4`, `udt6`, `udt4`,
`udt46`, `un`, `ua`

**code fallback**: なし — 省略または不正値はエラーで処理中断。**事実上必須**。

---

### フィールド: vrf

**探索コマンド**:
```
grep -n '"vrf"\|dt_vrf\|mySidVrfRequired\|gVirtualRouterId' sonic-swss/orchagent/srv6orch.cpp
```

**結果** (`srv6orch.cpp:2219-2222`):
```cpp
if(fvField(i) == "vrf")
{
    dt_vrf = fvValue(i);
}
```

`srv6orch.cpp:1480-1507` の `mySidVrfRequired(end_behavior)`:
- `SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_T`, `DT4`, `DT6`, `DT46`, `UDT4`, `UDT6`, `UDT46` の場合のみ VRF を設定。
- `dt_vrf == "default"` → `gVirtualRouterId` (global VRF) に解決 (`srv6orch.cpp:1484`)。
- custom VRF の場合は `m_vrfOrch->isVRFexists(dt_vrf)` で存在確認。
- VRF 不要な `action` (例: `end`, `end.x`, `un`) の場合、`vrf` フィールドは無視される。

**code fallback**: VRF 必要な action で未指定時は `dt_vrf = ""` → `isVRFexists("")` が失敗してエラー return。
VRF 不要な action の場合は無関係。`"default"` を明示指定すれば global VRF を使用。

---

### フィールド: adj

**探索コマンド**:
```
grep -n '"adj"\|mySidNextHopRequired\|endAdjString\|adj.*delimiter\|ADJ_DELIMITER' sonic-swss/orchagent/srv6orch.cpp
```

**結果** (`srv6orch.cpp:2223-2226`):
```cpp
if(fvField(i) == "adj")
{
    adj = fvValue(i);
}
```

`srv6orch.cpp:1511-1547` の `mySidNextHopRequired(end_behavior)`:
- `X`, `DX4`, `DX6`, `UDX4`, `UDX6`, `B6_ENCAPS`, `B6_ENCAPS_RED`, `B6_INSERT`, `B6_INSERT_RED`, `UA`
  の場合に nexthop が必要。
- `srv6orch.cpp:1517`: ECMP adjacency (`adjv.size() > 1`) は未サポート。
- nexthop が未解決の場合、`m_pendingSRv6MySIDEntries` に保留してネイバー解決を待つ。

`ADJ_DELIMITER = ','` (`srv6orch.cpp:19`)

**code fallback**: adj 不要な action の場合は無視。必要な action で未指定時は `adj = ""` → `NextHopKey("")`
で nexthop 検索失敗 → pending 状態。事実上必須 (nexthop 要 action 時)。

---

## テーブル 3: PIC_CONTEXT_TABLE (APP_DB)

### フィールド: nexthop

**探索コマンド**:
```
grep -n '"nexthop"\|pci.nexthops\|Srv6PicContextInfo' sonic-swss/orchagent/srv6orch.cpp
```

**結果** (`srv6orch.cpp:2289-2292`):
```cpp
if (fvField(i) == "nexthop" && fvValue(i) != "")
{
    pci.nexthops = tokenize(fvValue(i), ',');
}
```

**code fallback**: 省略または空文字列の場合、`pci.nexthops` は空ベクタ。
`pci.nexthops.size() != pci.sids.size()` チェックで矛盾があればエラー。

---

### フィールド: vpn_sid

**探索コマンド**:
```
grep -n '"vpn_sid"\|pci.sids\|srv6_vpn_sid' sonic-swss/orchagent/srv6orch.cpp
```

**結果** (`srv6orch.cpp:2293-2296`):
```cpp
else if (fvField(i) == "vpn_sid" && fvValue(i) != "")
{
    pci.sids = tokenize(fvValue(i), ',');
}
```

**code fallback**: 省略または空文字列の場合、`pci.sids` は空ベクタ。
`nexthop` と `vpn_sid` のエントリ数が一致しない場合エラー (`srv6orch.cpp:2298-2303`)。

---

## コード定数サマリ

| 定数名 | 値 | 場所 |
|--------|-----|------|
| `ADJ_DELIMITER` | `','` | `srv6orch.cpp:19` |
| `SID_LIST_DELIMITER` | `','` | `srv6orch.h:151` |
| `OVERLAY_RIF_DEFAULT_MTU` | `9100` | `srv6orch.cpp:20` |
| `LOCATOR_DEFAULT_BLOCK_LEN` | `"32"` | `srv6orch.cpp:21` |
| `LOCATOR_DEFAULT_NODE_LEN` | `"16"` | `srv6orch.cpp:22` |
| `LOCATOR_DEFAULT_FUNC_LEN` | `"16"` | `srv6orch.cpp:23` |
| `LOCATOR_DEFAULT_ARG_LEN` | `"0"` | `srv6orch.cpp:24` |
| `SRV6_STAT_COUNTER_POLLING_INTERVAL_MS` | `10000` | `srv6orch.cpp:27` |
| `SRV6_FLEX_COUNTER_UPDATE_TIMER` | `1` (秒) | `srv6orch.cpp:26` |

---

## YANG-コード 乖離サマリ

### SRV6_SID_LIST_TABLE

| フィールド | YANG | コード fallback | 乖離 |
|-----------|------|----------------|------|
| `path` | N/A (APP_DB, YANG 管理外) | 省略時 count=0 でスキップ | N/A |
| `type` | N/A | `SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED` | N/A |

### SRV6_MY_SID_TABLE

| フィールド | YANG | コード fallback | 乖離 |
|-----------|------|----------------|------|
| `action` | N/A (APP_DB) | 省略不可 (エラー) | N/A |
| `vrf` | N/A | action 依存 (不要 action は無視) | N/A |
| `adj` | N/A | action 依存 (不要 action は無視) | N/A |

### PIC_CONTEXT_TABLE

| フィールド | YANG | コード fallback | 乖離 |
|-----------|------|----------------|------|
| `nexthop` | N/A (APP_DB) | 省略時は空ベクタ | N/A |
| `vpn_sid` | N/A | 省略時は空ベクタ | N/A |

---

## 参照ファイル

- `sonic-swss/orchagent/srv6orch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/srv6orch.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss-common/common/schema.h` (APP_DB テーブル名定義)
