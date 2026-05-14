# ACL_TABLE — Phase A: コード由来の暗黙デフォルト

調査日: 2026-05-14  
対象ファイル:
- `sonic-swss/orchagent/aclorch.h` (sha 43055961)
- `sonic-swss/orchagent/aclorch.cpp` (sha 43055961)
- `sonic-utilities/config/main.py`

## フィールド別デフォルト一覧

### `stage`

**C++ struct default (aclorch.h:543)**:
```cpp
acl_stage_type_t stage = ACL_STAGE_INGRESS;
```
`AclTable` オブジェクト生成時点で `ACL_STAGE_INGRESS` が初期値。`processAclTableStage()` が呼ばれなければ（= `stage` フィールドが CONFIG_DB に存在しない場合）INGRESS がそのまま使われる。

**CLI Python default (config/main.py:8081)**:
```python
@click.option("-s", "--stage", type=click.Choice(["ingress", "egress"]), default="ingress")
```
`-s` オプション省略時に `"ingress"` をセット。`parse_acl_table_info()` の L8067 で `table_info["stage"] = stage` として CONFIG_DB に書き込む。

**結論**: `stage` 未指定時 → `INGRESS` (C++ struct default + CLI default 両方で担保)。

### `policy_desc`

**CLI Python fallback (config/main.py:8044-8047)**:
```python
if description:
    table_info["policy_desc"] = description
else:
    table_info["policy_desc"] = table_name
```
`-d` オプション省略時、`policy_desc` に `table_name` (テーブル名文字列) を設定する。YANG / C++ 側にデフォルト値定義なし。

**C++ 側**: `description` フィールドは `AclTable::description` (string, 空文字列が C++ デフォルト)。CONFIG_DB に `policy_desc` がない場合、orchagent は空文字列のまま保持し SAI 属性には渡さない (ログ・表示のみに使用)。

**結論**: CLI 経由なら `policy_desc = table_name`。直接 CONFIG_DB 書き込み（REST/minigraph）では `policy_desc` はオプション、C++ では空文字列デフォルト。

### `type`

YANG / CLI ともに **必須** 扱い。`processAclTableType()` (aclorch.cpp:5819-5831):
```cpp
if (type.empty()) { return false; }
```
空文字のみ reject。省略した場合は `bAllAttributesOk=false` となりエントリが erase される。**暗黙デフォルトなし**。

### `ports`

**CLI Python fallback (config/main.py:8054-8059)**:
```python
if ports:
    for port in ports.split(","):
        port_list += expand_vlan_ports(port, namespace)
else:
    port_list = valid_acl_ports
```
`-p` オプション省略時 → `get_acl_bound_ports()` で取得した全有効 ACL ポートをデフォルトとして設定。

**C++ 側**: `portSet` / `pendingPortSet` は空 set がデフォルト。CONFIG_DB に `ports` がない場合は `processAclTablePorts()` が呼ばれず、空のまま `validate()` を通過（エラーにはならない — ただし hardware には ACL_RULE が降りない）。

**結論**: CLI 経由で `-p` 省略 → 全有効ポートにバインド。直接書き込みで `ports` 省略 → 空（ポートバインドなし）。

### `services`

**C++ 側 (aclorch.cpp:5410-5413)**:
```cpp
else if (attr_name == ACL_TABLE_SERVICES)
{
    // TODO: validate control plane ACL table has this attribute
    continue;
}
```
`services` フィールドは `doAclTableTask()` 内で `continue` されるため完全に無視。内部状態への影響なし。**デフォルト値の概念が存在しない** (読み捨て)。

## 内部自動付与デフォルト (暗黙的派生)

### mandatory action list (aclorch.cpp:2563-2605)

`addMandatoryActions()` は `stage != ACL_STAGE_UNKNOWN` かつ `isAclActionListMandatoryOnTableCreation(stage)` が true のとき、`type.getActions()` が空なら `SAI_ACL_ACTION_TYPE_COUNTER` を自動付与する。

さらに `defaultAclActionList` テーブル (aclorch.cpp:196-) から type/stage 組み合わせで追加:

| type | INGRESS 自動付与 action | EGRESS 自動付与 action |
|---|---|---|
| `L3` | `PACKET_ACTION`, `REDIRECT` | `PACKET_ACTION`, `REDIRECT` |
| `L3V6` | `PACKET_ACTION`, `REDIRECT` | `PACKET_ACTION`, `REDIRECT` |
| `L3V4V6` | `PACKET_ACTION`, `REDIRECT` | `PACKET_ACTION`, `REDIRECT` |
| `MIRROR` | `MIRROR_INGRESS`, `MIRROR_EGRESS` | `MIRROR_EGRESS` |

これらはユーザが `ACL_TABLE_TYPE` エントリで actions を指定しなかった場合に `AclTable` 内部に自動追加される。CONFIG_DB フィールドではなく SAI 属性 `SAI_ACL_TABLE_ATTR_ACL_ACTION_TYPE_LIST` として SAI に渡される。

### mandatory match fields (aclorch.cpp:2632-2665)

`addStageMandatoryMatchFields()` は `stageMandatoryMatchFields` テーブルから type/stage に応じて SAI match 属性を自動付与。`SAI_ACL_TABLE_ATTR_FIELD_ACL_RANGE_TYPE` (L4 port range) は BRCM プラットフォームの EGRESS stage では省略される (`addStageMandatoryRangeFields()` が false を返す)。

## まとめ

| フィールド | YANG default | コード default | 発生源 |
|---|---|---|---|
| `stage` | なし | `INGRESS` | C++ struct 初期化 (`aclorch.h:543`) + CLI `default="ingress"` (`main.py:8081`) |
| `policy_desc` | なし | `table_name` (CLI) / `""` (C++) | `parse_acl_table_info()` else branch (`main.py:8047`) / C++ string default |
| `type` | なし | **なし** (必須、空文字 reject) | `processAclTableType()` (`aclorch.cpp:5823`) |
| `ports` | なし | 全有効ポート (CLI) / `[]` (C++) | `get_acl_bound_ports()` fallback (`main.py:8059`) / C++ empty set |
| `services` | なし | **なし** (読み捨て) | `continue` (`aclorch.cpp:5413`) |
