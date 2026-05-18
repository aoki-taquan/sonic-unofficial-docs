# srv6-applb — Phase B 書込み順依存 調査ノート

## 調査対象

- `sonic-net/sonic-swss` `orchagent/srv6orch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- APPL_DB テーブル: `SRV6_MY_SID_TABLE`, `SRV6_SID_LIST_TABLE`

## 検出された順序依存

### 依存 #1: SRV6_SID_LIST_TABLE → SRV6 nexthop 作成 (間接参照)

`Srv6Orch::createSrv6NextHop()` (srv6orch.cpp:826-831):
nexthop 作成時に SID リストが `sid_table_` に存在しない場合は即時 false を返す。
→ SID リストは nexthop より先に SET されている必要がある。

### 依存 #2: VRF (VrfOrch) → SRV6_MY_SID_TABLE.vrf (DT 系行動)

`srv6orch.cpp:1488-1502`:
`end.dt4/dt6/dt46/udt4/udt6/udt46` 行動は VRF が VrfOrch に登録されていないと false を返す（リトライなし）。

### 依存 #3: NeighborOrch → SRV6_MY_SID_TABLE.adj (X 系・UA 系行動)

`srv6orch.cpp:1524-1542`:
`end.x/end.dx4/end.dx6/ua/udx4/udx6` 行動で `adj` が未解決の場合、エントリを `m_pendingSRv6MySIDEntries` にパーク。
`updateNeighbor()` が NeighborOrch から ADD 通知を受け取ると自動的に再インストール。

### 依存 #4: SRV6_SID_LIST_TABLE 削除ブロック

`srv6orch.cpp:1129-1133`:
SID リストを参照している nexthop が残っている間、DEL は `task_need_retry` を返してブロックされる。

## 方向性サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `SRV6_SID_LIST_TABLE` SET → SRV6 nexthop 作成 | 強制先行 | SID リスト未存在時は nexthop 作成失敗 |
| 2 | `VRF` (VrfOrch) 登録 → `SRV6_MY_SID_TABLE` DT 行動 SET | 強制先行 | VRF 未存在時は false 即時返却（リトライなし） |
| 3 | NeighborOrch 解決 → `SRV6_MY_SID_TABLE` X/UA 行動 | 自動再試行（pending パーク） | neighbor ADD 通知で自動インストール |
| 4 | SRV6 nexthop 削除 → `SRV6_SID_LIST_TABLE` DEL | 強制先行（参照カウント） | nexthop 削除後に DEL が自動再試行 |
