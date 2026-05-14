# ACL_RULE — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_0)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### minigraph.py

ACL_RULE テーブルへの代入なし。minigraph は `ACL_TABLE` のみ生成する（L2671）。ACL_RULE は minigraph 管轄外。

### init_cfg.json.j2

ACL_RULE の記述なし。

### db_migrator.py

ACL_RULE の migration ステップなし（grep: 0 hit）。

### acl_loader — hard-coded デフォルト deny ルール

```python
# sonic-utilities/acl_loader/main.py:1138-1149
def createDefaultDenyAclRule(self, table_name):
    key = (table_name, "DEFAULT_RULE")
    rules_info[key] = {
        "PRIORITY": "0",
        "PACKET_ACTION": "DROP",
    }
    configdb.set_entry(ACL_RULE, key, rules_info[key])
```

`acl-loader update full` の末尾に `createDefaultDenyAclRule()` が自動呼び出しされ、priority=0 の DROP ルールが派生代入される。CLI 経由の操作で自動生成。

**結論**: minigraph / db_migrator / init_cfg による自動派生なし。acl_loader の full update 時に PACKET_ACTION=DROP のデフォルト deny ルールが自動派生代入される。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### orchagent — AclOrch

```cpp
// sonic-swss/orchagent/orchdaemon.cpp:533
gAclOrch = new AclOrch(acl_table_connectors, m_stateDb, ...);
m_orchList.push_back(gAclOrch);
```

`AclOrch` は **常時** 登録される。条件付き登録なし。ACL_TABLE および ACL_RULE を購読するが、orchagent 自身は ACL_RULE への書き込みを行わない（読み取り側）。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### AclOrch — PACKET_ACTION 分岐

`PACKET_ACTION` フィールドの値により SAI 属性マッピングが分岐する:

| PACKET_ACTION 値 | SAI 属性 |
|-----------------|---------|
| `FORWARD` | `SAI_PACKET_ACTION_FORWARD` |
| `DROP` | `SAI_PACKET_ACTION_DROP` |
| `REDIRECT` | redirect 先オブジェクト解決 |
| `DO_NOT_NAT` | NAT バイパス設定 |
| `COPY` | `SAI_PACKET_ACTION_COPY` |
| `COPY_CANCEL` | `SAI_PACKET_ACTION_COPY_CANCEL` |

`REDIRECT` の場合のみ redirect 先ポート/nexthop の解決処理が追加で走る（解決失敗時は early return でルール未適用）。

### IP_TYPE 分岐

`IP_TYPE` フィールドにより SAI の `SAI_ACL_ENTRY_ATTR_FIELD_ACL_IP_TYPE` マッピングが切り替わる。`ANY` / `IP` / `NON_IP` / `IPv4ANY` / `NON_IPv4` / `IPv6ANY` / `NON_IPv6` / `ARP` / `ARP_REQUEST` / `ARP_REPLY` の 9 値。

### dataplane vs controlplane ACL — incremental update 分岐

```python
# acl_loader/main.py:890-916
if acl_table_type in ('DATAPLANE', 'MIRROR', ...):
    # full update 方式
else:
    # 差分更新（追加/削除/更新を個別処理）
```

dataplane ACL は incremental update でも常に full replace。controlplane ACL のみ差分更新。

<!-- /handler-branching -->
