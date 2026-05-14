# NAT — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_3)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples.py / db_migrator.py / init_cfg.json.j2 に NAT 系テーブルへの代入なし。NAT は CLI (`config nat`) で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### orchdaemon.cpp — NatOrch 登録

```cpp
// orchdaemon.cpp:465
gNatOrch = new NatOrch(m_applDb, m_stateDb, nat_tables, gRouteOrch, gNeighOrch);
```

NatOrch は **常時** 生成。NAT 設定がない場合は実質無動作。条件付き登録なし。

`nat` feature が有効なプラットフォームのみコンテナ起動 (featuremgrd 経由で間接制御)。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### natmgr.cpp — doTask 分岐 (SET/DEL dispatch)

```
natmgr.cpp:5870  if (op == SET_COMMAND) → addStaticNatEntry()
natmgr.cpp:6107  else if (op == DEL_COMMAND) → removeStaticNatEntry()
natmgr.cpp:6224  if (op == SET_COMMAND) → addStaticNaptEntry()
natmgr.cpp:6511  if (op == SET_COMMAND) → addDynamicNatRule()
natmgr.cpp:6906  if (op == SET_COMMAND) → addNatPool()
natmgr.cpp:7141  if (op == SET_COMMAND) → addNatBinding()
```

早期 return: ip_range 不正 / interface 未解決 → `continue` / `return`。

### natorch.cpp — nexthop 未解決時 early return

nexthop 未解決 (L192-L244) → `return false` で再試行待機。

<!-- /handler-branching -->
