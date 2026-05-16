# ACL_TABLE — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/acl-table.md`
解析日: 2026-05-15
根拠ソース: `sonic-swss/orchagent/aclorch.cpp` (sha `4305596`)

---

## 目的

`ACL_TABLE` エントリが CONFIG_DB に書かれたとき、`AclOrch` が **暗黙的に** 参照・依存する
他テーブルのキー / フィールドを網羅する。スキーマ定義 (YANG / schema.h) に明示されない
「leafref 相当」の依存を列挙し、`<!-- cross-refs -->` ブロックに変換する。

---

## 1. PORT テーブル (暗黙 leafref)

### 参照箇所

`processAclTablePorts(string portList, AclTable &aclTable)` — `aclorch.cpp:5776-5807`

```cpp
if (!gPortsOrch->getPort(alias, port))
{
    aclTable.pendingPortSet.emplace(alias);   // 未解決はペンディング
    continue;
}
```

`getAclBindPortId(Port &port, sai_object_id_t &port_id)` — `aclorch.cpp:6056-6083`

```cpp
case Port::PHY:
    port_id = port.m_port_id;
    break;
```

### 依存内容

| `ACL_TABLE.ports` の値 | 参照先テーブル | 参照先フィールド | 参照タイミング |
|---|---|---|---|
| `EthernetN` (物理ポート) | `PORT` | `name` (キー) | SET 処理時 `processAclTablePorts()` |

### 特記事項

- PortsOrch が当該ポートを未登録の場合は `pendingPortSet` に積み、PortsOrch からの
  `SUBJECT_TYPE_PORT_CHANGE` 通知受信後に再バインドを試みる (`aclorch.cpp:2866-2901`)。
- LAG メンバポートを直接指定すると `m_lag_member_id != SAI_NULL_OBJECT_ID` 判定で reject。

---

## 2. PORTCHANNEL テーブル (LAG) (暗黙 leafref)

### 参照箇所

`getAclBindPortId()` — `aclorch.cpp:6073`

```cpp
case Port::LAG:
    port_id = port.m_lag_id;
    break;
```

`aclBindPointTypeLookup` — `aclorch.cpp:103-107`

```cpp
{ BIND_POINT_TYPE_PORTCHANNEL, SAI_ACL_BIND_POINT_TYPE_LAG }
```

### 依存内容

| `ACL_TABLE.ports` の値 | 参照先テーブル | 参照先フィールド | 参照タイミング |
|---|---|---|---|
| `PortChannelN` (LAG) | `PORTCHANNEL` | `name` (キー) | SET 処理時 `processAclTablePorts()` |

### 特記事項

- `gPortsOrch->getPort("PortChannelN", port)` で `Port::LAG` として解決され、
  SAI の `SAI_ACL_BIND_POINT_TYPE_LAG` にマップされる。
- LAG に紐づいた物理ポートへの ACL バインドは PortsOrch 内部で管理。

---

## 3. VLAN テーブル (暗黙 leafref)

### 参照箇所

`getAclBindPortId()` — `aclorch.cpp:6076`

```cpp
case Port::VLAN:
    port_id = port.m_vlan_info.vlan_oid;
    break;
```

### 依存内容

| `ACL_TABLE.ports` の値 | 参照先テーブル | 参照先フィールド | 参照タイミング |
|---|---|---|---|
| `VlanN` | `VLAN` | `name` (キー、`VlanN` 形式) | SET 処理時 `processAclTablePorts()` |

### 特記事項

- VLAN バインドには ASIC が `SAI_ACL_BIND_POINT_TYPE_VLAN` を持つことが前提。
- `ACL_TABLE_TYPE.BPOINT_TYPES` に `VLAN` を含まないと SAI レベルで reject される可能性あり。

---

## 4. ACL_TABLE_TYPE テーブル (ユーザ定義型参照)

### 参照箇所

`doAclTableTask()` — `aclorch.cpp:5380-5388`

```cpp
else if (attr_name == ACL_TABLE_TYPE)
{
    ...
    processAclTableType(attr_value, newTable);
}
```

`m_AclTableTypeMap` — ユーザ定義型は `ACL_TABLE_TYPE|<name>` から読み込まれたもの

### 依存内容

| `ACL_TABLE.type` の値 | 参照先テーブル | 参照先フィールド | 参照タイミング |
|---|---|---|---|
| 事前定義型以外の任意文字列 | `ACL_TABLE_TYPE` | `name` (キー)、`MATCHES`、`ACTIONS`、`BPOINT_TYPES` | `processAclTableType()` + `AclTableType` lookup |

### 特記事項

- 事前定義型 (`L3`/`MIRROR`/`CTRLPLANE` 等) は `m_AclTableTypeMap` に初期登録済みのため
  `ACL_TABLE_TYPE` テーブルへの問い合わせなし。
- ユーザ定義型 (`type` が事前定義リスト外の値) の場合は `ACL_TABLE_TYPE|<type>` が存在しないと
  `AclTableType` が空のまま → SAI テーブル属性設定で失敗するおそれあり。

---

## 5. MIRROR_SESSION テーブル (間接参照: ACL_RULE 経由)

### 参照箇所

`ACL_TABLE` の `type=MIRROR`/`MIRRORV6` は ACL_RULE 側の
`AclRuleMirror::validateAddMatch()` — `aclorch.cpp:2301-2349` で `MIRROR_SESSION` を参照する。
`ACL_TABLE` 自体は `MIRROR_SESSION` を直接参照しない。

### 依存内容

| 依存元 | 参照先テーブル | 参照先フィールド | 参照タイミング |
|---|---|---|---|
| ACL_RULE (type=MIRROR テーブルに属するルール) | `MIRROR_SESSION` | `name` (キー)、セッション状態 | ACL_RULE SET 処理時 |

### 特記事項

- `ACL_TABLE` → `ACL_RULE` → `MIRROR_SESSION` の連鎖は ACL_RULE ページで扱うべき依存。
- `ACL_TABLE` への cross-refs としては「間接参照」として記載する。

---

## 6. STATE_DB / CRM 側依存 (書き込み先)

| 書き込み先 | 目的 | 証跡 |
|---|---|---|
| `STATE_DB / ACL_TABLE` | 作成/削除時の status 書き込み | `aclorch.cpp:6092,6098` |
| `CRM_ACL_TABLE` カウンタ | ASIC リソース残量管理 | `aclorch.cpp:2855,4877` |

これらは ACL_TABLE が**参照する**のではなく ACL_TABLE 処理が**書き込む**先のため、
cross-refs ではなく runtime-trace の扱い。

---

## 7. cross-refs ブロック (最終形)

以下を `docs/reference/config-db/acl-table.md` の `<!-- glossary-links-injected -->` 直前に挿入する。

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`ACL_TABLE.ports` フィールドに記載されたインターフェース名は CONFIG_DB 上では文字列だが、
`AclOrch` が `gPortsOrch->getPort()` と `getAclBindPortId()` を通じて以下のテーブルの
エントリを**暗黙的に leafref 参照**する。YANG 定義がないため制約はコードのみで表現されている。

| 参照元フィールド | 参照先テーブル | 参照先キー形式 | SAI バインド種別 | 参照箇所 |
|---|---|---|---|---|
| `ports` | `PORT` | `PORT\|EthernetN` | `SAI_ACL_BIND_POINT_TYPE_PORT` | `aclorch.cpp:6062-6069` |
| `ports` | `PORTCHANNEL` | `PORTCHANNEL\|PortChannelN` | `SAI_ACL_BIND_POINT_TYPE_LAG` | `aclorch.cpp:6073-6075` |
| `ports` | `VLAN` | `VLAN\|VlanN` | `SAI_ACL_BIND_POINT_TYPE_VLAN` | `aclorch.cpp:6076-6078` |
| `type` | `ACL_TABLE_TYPE` | `ACL_TABLE_TYPE\|<name>` | N/A (テーブル定義参照) | `aclorch.cpp:5380-5388` |

### 解決タイミング

- `ports` に指定したポートが PortsOrch 未登録の場合、`pendingPortSet` に保留され
  PortsOrch の `SUBJECT_TYPE_PORT_CHANGE` 通知で再バインドを試みる (`aclorch.cpp:2866-2901`)。
- `type` にユーザ定義型を指定する場合は `ACL_TABLE_TYPE|<type>` が先に存在している必要がある。

### 間接参照

- `type=MIRROR`/`MIRRORV6` テーブルに紐づく `ACL_RULE` は `MIRROR_SESSION` テーブルを参照する
  (`AclRuleMirror::validateAddMatch()`)。`ACL_TABLE` 自体は直接参照しない。
<!-- /cross-refs -->
```
