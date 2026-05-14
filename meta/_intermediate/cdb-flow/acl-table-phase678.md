# ACL_TABLE — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_0)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### minigraph.py — `filter_acl_table_bindings()` (L1827)

```python
# sonic-buildimage/src/sonic-config-engine/minigraph.py:2671
results['ACL_TABLE'] = filter_acl_table_bindings(
    acls, neighbors, pcs, pc_members, sub_role,
    current_device['type'], is_storage_device, vlan_members
)
```

minigraph.py は ACL_TABLE を自動生成する。`type` フィールドは `MIRROR` / `MIRRORV6` / `MIRROR_DSCP` / `DATAPLANE` などがミニグラフの ACL 設定から派生する。

**派生条件**:
- `sub_role == BACKEND_ASIC_SUB_ROLE` の場合: ACL_TABLE は空（全スキップ）
- `device_type == 'BackEndToRRouter' and is_storage_device`: `filter_acl_table_for_backend()` でフィルタ
- MIRROR 系 type: backplane ポートを ports リストから除外して代入

### init_cfg.json.j2

ACL_TABLE の記述なし（minigraph 生成のみ）。

### db_migrator.py

ACL_TABLE の migration ステップなし。

**結論**: minigraph が ACL_TABLE を自動生成。`type` / `ports` フィールドは device_type / sub_role / ネイバー情報から条件付きで派生代入される。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### orchagent — AclOrch

```cpp
// sonic-swss/orchagent/orchdaemon.cpp:533
gAclOrch = new AclOrch(acl_table_connectors, m_stateDb, ...);
```

AclOrch は **常時** 登録。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### AclOrch — type フィールド別 dispatch

ACL_TABLE の `type` フィールド（14 値）により SAI テーブル属性が分岐する:

| type 値 | 処理 |
|---------|------|
| `L3` / `L3V6` | L3 match fields を SAI ACL テーブルに設定 |
| `MIRROR` / `MIRRORV6` / `MIRROR_DSCP` | mirror アクション属性を追加 |
| `MCLAG` | MCLAG 専用テーブルタイプ |
| `PFCWD` | PFC watchdog テーブル |
| `L3_CUSTOM` | カスタム match fields |
| その他 | ACL_TABLE_TYPE から動的解決 |

### stage フィールド分岐

`stage` フィールド（`ingress` / `egress`）により SAI の `SAI_ACL_TABLE_ATTR_ACL_STAGE` が切り替わる:

- `ingress` → `SAI_ACL_STAGE_INGRESS`
- `egress` → `SAI_ACL_STAGE_EGRESS`

### BackEnd ASIC early return

Multi-NPU 環境で `sub_role == BackEnd` の場合、ACL バインディングをスキップ（minigraph 段で空になるため orchagent は処理対象なし）。

<!-- /handler-branching -->
