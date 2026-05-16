# FDB — Phase E ハードコード定数 (grep 証跡)

生成日: 2026-05-16
ソース: `sonic-swss/orchagent/fdborch.cpp` / `orchagent/fdborch.h`

---

## 対象テーブル

CONFIG_DB `FDB` テーブル

キー形式: `FDB|<VlanName>|<MAC>` (例: `FDB|Vlan100|00:01:02:03:04:05`)

---

## 1. FDB type 文字列定数

**探索コマンド**:
```
grep -n "\"static\"\|\"dynamic\"\|\"dynamic_local\"\|assert.*type" fdborch.cpp
```

**結果**:
- `fdborch.cpp:770`: `string type = "dynamic";` — デフォルト初期値
- `fdborch.cpp:830`: `assert(type == "dynamic" || type == "dynamic_local" || type == "static");` — 有効値の網羅
- `fdborch.cpp:288`, `389`, `407-408`: `update.type = "dynamic";` — 自動学習時に DYNAMIC がセット
- `fdborch.cpp:446-448`: `if (existing_entry->second.type == "static") { update.type = "static"; }`

**定数一覧**:

| 文字列値 | 説明 |
|---------|------|
| `"static"` | 静的エントリ（エージングなし） |
| `"dynamic"` | 動的エントリ（エージング対象） |
| `"dynamic_local"` | MCLAG ローカル扱い（SAI 上は DYNAMIC） |

---

## 2. SAI FDB エントリ属性 (`sai_fdb_entry_attr_t`)

**探索コマンド**:
```
grep -n "SAI_FDB_ENTRY_ATTR" fdborch.cpp
```

**結果**:
- `fdborch.cpp:1424`: `attr.id = SAI_FDB_ENTRY_ATTR_TYPE;`
  - 値: `SAI_FDB_ENTRY_TYPE_STATIC` または `SAI_FDB_ENTRY_TYPE_DYNAMIC` (L1427–L1435)
- `fdborch.cpp:1444`: `attr.id = SAI_FDB_ENTRY_ATTR_ALLOW_MAC_MOVE;`
  - static かつ MCLAG 連携時に設定
- `fdborch.cpp:1449`: `attr.id = SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID;`
  - ポートの bridge port OID
- `fdborch.cpp:1467`, `1481`: `attr.id = SAI_FDB_ENTRY_ATTR_ENDPOINT_IP;`
  - VxLAN リモート VTEP IP
- `fdborch.cpp:1496`: `attr.id = SAI_FDB_ENTRY_ATTR_PACKET_ACTION;`
  - `fdborch.cpp:1497`: `attr.value.s32 = (fdbData.discard == "true") ? SAI_PACKET_ACTION_DROP : SAI_PACKET_ACTION_FORWARD;`

**SAI 型マッピング**:

| `type` 文字列 | SAI 型 |
|-------------|--------|
| `"static"` | `SAI_FDB_ENTRY_TYPE_STATIC` |
| `"dynamic"` | `SAI_FDB_ENTRY_TYPE_DYNAMIC` |
| `"dynamic_local"` | `SAI_FDB_ENTRY_TYPE_DYNAMIC`（MCLAG ローカル扱い） |

---

## 3. SAI FDB フラッシュ属性 (`sai_fdb_flush_attr_t`)

**探索コマンド**:
```
grep -n "SAI_FDB_FLUSH_ATTR" fdborch.cpp
```

**結果**:
- `fdborch.cpp:949`: `attr.id = SAI_FDB_FLUSH_ATTR_ENTRY_TYPE; attr.value.s32 = SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC;`
  - フラッシュ対象は DYNAMIC のみ（static はフラッシュしない）
- `fdborch.cpp:1109`: `attr.id = SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID;`
- `fdborch.cpp:1116`: `attr.id = SAI_FDB_FLUSH_ATTR_BV_ID;`
- `fdborch.cpp:1122`: `attr.id = SAI_FDB_FLUSH_ATTR_ENTRY_TYPE; attr.value.s32 = SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC;`
- `fdborch.cpp:1159`: `vlan_attr[0].id = SAI_FDB_FLUSH_ATTR_BV_ID;`
- `fdborch.cpp:1161`: `vlan_attr[1].id = SAI_FDB_FLUSH_ATTR_ENTRY_TYPE; vlan_attr[1].value.s32 = SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC;`

**コメント** (`fdborch.cpp:1121`): `/* do not flush static mac */`

---

## 4. FdbOrigin 列挙値

**探索コマンド**:
```
grep -n "FDB_ORIGIN\|enum FdbOrigin" fdborch.h
```

**結果** (`fdborch.h:8–14`):
```cpp
enum FdbOrigin
{
    FDB_ORIGIN_INVALID = 0,
    FDB_ORIGIN_LEARN = 1,
    FDB_ORIGIN_PROVISIONED = 2,
    FDB_ORIGIN_VXLAN_ADVERTIZED = 4,
    FDB_ORIGIN_MCLAG_ADVERTIZED = 8
};
```

`removeFdbEntry()` デフォルト引数: `FDB_ORIGIN_PROVISIONED` (`fdborch.h:101`)

**有効な (type, origin) 組み合わせ** (`fdborch.h:54–59`):
| type | origin | 意味 |
|------|--------|------|
| `"dynamic"` | `FDB_ORIGIN_LEARN` | カーネル自動学習 |
| `"dynamic"` | `FDB_ORIGIN_PROVISIONED` | swssconfig による動的投入 |
| `"dynamic"` | `FDB_ORIGIN_VXLAN_ADVERTIZED` | BGP MAC route 広報 |
| `"static"` | `FDB_ORIGIN_PROVISIONED` | ユーザー静的プロビジョニング |
| `"static"` | `FDB_ORIGIN_VXLAN_ADVERTIZED` | sticky BGP MAC route |
| `"static"` | `FDB_ORIGIN_LEARN` | 無効 (Invalid) |

---

## 5. `discard` フィールドのデフォルト

**探索コマンド**:
```
grep -n "discard" fdborch.cpp
```

**結果**:
- `fdborch.cpp:775`: `string discard = "false";` — フィールド省略時のデフォルト
- `fdborch.cpp:788-790`: `if (fvField(i) == "discard") { discard = fvValue(i); }`
- `fdborch.cpp:1497`: `(fdbData.discard == "true") ? SAI_PACKET_ACTION_DROP : SAI_PACKET_ACTION_FORWARD`

**デフォルト値**: `"false"` (コード由来, fdborch.cpp:775)

---

## 6. MAC アドレス形式

`fdborch.cpp:734` コメント: `/* format: <VLAN_name>:<MAC_address> */`

KEY 形式は `FDB|<VlanName>|<MAC>` で、MAC は `XX:XX:XX:XX:XX:XX` 形式（コロン区切り 16 進数）。
実装内では `MacAddress` クラスで管理 (`fdborch.cpp:752`: `deleteFdbEntryFromSavedFDB(MacAddress(keys[1]), ...)`）。

---

## YANG-コード 乖離サマリ（定数観点）

| 定数 / 制約 | YANG 定義 | コード実装 | 備考 |
|-----------|----------|----------|------|
| `type` 有効値 | 未確認 | `"static"`, `"dynamic"`, `"dynamic_local"` の 3 値のみ | assert で強制 |
| `discard` デフォルト | 未確認 | `"false"` | SAI FORWARD にマップ |
| static flush 除外 | 未確認 | `SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC` のみ | コメントで明示 |
