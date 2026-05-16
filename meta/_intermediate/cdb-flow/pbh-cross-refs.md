# PBH_TABLE / PBH_RULE 暗黙参照スキャン (Phase C)

`docs/reference/config-db/pbh.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/orchagent/pbh/` および `orchagent/aclorch.cpp`。

## スキャン手順

```
grep -n "PORT\|PORTCHANNEL\|validateAddPorts\|gPortsOrch\|AclOrch" \
    .cache/sonic-sources/sonic-swss/orchagent/pbh/pbhorch.cpp

grep -n "validateAddPorts\|getPort\|PORTCHANNEL" \
    .cache/sonic-sources/sonic-swss/orchagent/aclorch.cpp
```

## 検出された暗黙参照

### PBH_TABLE.interface_list → PORT / PORTCHANNEL

`pbhorch.cpp:266-268` および `pbhorch.cpp:345-347` で `pbhTable.validateAddPorts(table.interface_list.value)` を呼び出す。
`validateAddPorts` の実装は `aclorch.cpp:2691-2721` で `gPortsOrch->getPort(itAlias, port)` を使用してインターフェース名を解決する。

- `PORT` (`PORT|EthernetN`) — 物理ポートの場合 `AclOrch::getAclBindPortId()` で `SAI_ACL_BIND_POINT_TYPE_PORT` を取得
- `PORTCHANNEL` (`PORTCHANNEL|PortChannelN`) — LAG の場合 `SAI_ACL_BIND_POINT_TYPE_LAG` を取得 (`aclorch.cpp:106`)

YANG では `interface_list` は `leafref` で `PORT` および `PORTCHANNEL` への参照として定義されているが、実装側の解決は YANG leafref チェックではなく `gPortsOrch->getPort()` による動的解決。

**ポート未登録時の挙動**: `getPort()` が false を返した場合、`pendingPortSet` にエントリを追加して保留し (`aclorch.cpp:2698-2703`)、`SUBJECT_TYPE_PORT_CHANGE` 通知で再試行する。

### PBH_RULE → PBH_TABLE (テーブル存在依存)

`pbhrule.cpp` の `validateDependencies()` が `PBH_RULE.table_name` フィールドに対応する `PBH_TABLE` エントリの存在を確認する。`PBH_TABLE` 未作成の場合 RULE はペンディングキューに入り retry loop に入る (`pbhmgr.cpp` の `deployPbhTasks()` より)。

### PBH_RULE.hash → PBH_HASH (ハッシュ依存)

`PBH_RULE.hash` フィールドは `PBH_HASH.hash_name` への leafref。YANG で定義されているが、実装側でも `validateDependencies(rule)` が `PBH_HASH` エントリの存在を確認し、未作成の場合は `task_need_retry` となる。

### PbhOrch → AclOrch / PortsOrch コンストラクタ依存

`pbhorch.cpp:90-91` の `PbhOrch` コンストラクタは `AclOrch *aclOrch` および `PortsOrch *portsOrch` を引数に受け取り、これらが初期化済みであることを前提とする (`orchdaemon.cpp:565` で AclOrch 作成後に PbhOrch を生成)。

## まとめ — `pbh.md` Phase C 記載対象

| カテゴリ | 参照元フィールド | 参照先テーブル | evidence |
|---|---|---|---|
| 暗黙 leafref (runtime 解決) | `PBH_TABLE.interface_list` | `PORT` | `pbhorch.cpp:266-268`, `aclorch.cpp:2698` |
| 暗黙 leafref (runtime 解決) | `PBH_TABLE.interface_list` | `PORTCHANNEL` | `pbhorch.cpp:266-268`, `aclorch.cpp:106` |
| 依存エントリ存在チェック | `PBH_RULE.table_name` | `PBH_TABLE` | `pbhmgr.cpp` `deployPbhTasks()` |
| 依存エントリ存在チェック | `PBH_RULE.hash` | `PBH_HASH` | `pbhmgr.cpp` `validateDependencies()` |

## 検証コマンド

```bash
grep -n "validateAddPorts\|gPortsOrch\|AclOrch\|PortsOrch" \
    .cache/sonic-sources/sonic-swss/orchagent/pbh/pbhorch.cpp

grep -n "validateAddPorts" \
    .cache/sonic-sources/sonic-swss/orchagent/aclorch.cpp

grep -n "pendingPortSet\|task_need_retry\|validateDependencies" \
    .cache/sonic-sources/sonic-swss/orchagent/pbh/pbhmgr.cpp
```
