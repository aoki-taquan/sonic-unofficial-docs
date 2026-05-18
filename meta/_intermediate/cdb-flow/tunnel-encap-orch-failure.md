# tunnel-encap-orch — Phase: failure-behavior

## 調査対象

slug: tunnel-encap-orch
phase: failure-behavior (失敗・ロールバック挙動)
調査日: 2026-05-18

## ソース

- `orchagent/vxlanorch.cpp` (4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/vxlanorch.h` (4305596156d70e9797e8a881b3d19b46de0bce0d)

## 調査結果

### create_tunnel SAI 失敗時

`create_tunnel()` が `SAI_NULL_OBJECT_ID` を返した場合 (vxlanorch.cpp:908-920):
1. `deleteMapperHw(mapper_list, map_src)` を呼んで直前の mapper 作成をロールバック
2. `ids_.tunnel_id = SAI_NULL_OBJECT_ID`, `ids_.tunnel_term_id = SAI_NULL_OBJECT_ID` にリセット
3. `active_ = false` にセット
4. `createTunnelHw()` が `false` を返す

`VxlanTunnelMapOrch::addOperation` では `createTunnelHw()` が `false` を返すと `return false` し、
Consumer キューに留まって次サイクルで再試行する。

### create_tunnel_termination SAI 失敗時

`with_term=true` の場合で `create_tunnel_termination()` が `SAI_NULL_OBJECT_ID` を返した場合 (vxlanorch.cpp:925-934):
1. `removeTunnelFromFlexCounter(ids_.tunnel_id, ...)` でフレックスカウンタ登録を取り消し
2. `remove_tunnel(ids_.tunnel_id)` で直前の SAI tunnel を削除（ロールバック）
3. `deleteMapperHw(mapper_list, map_src)` で mapper も削除
4. `ids_.tunnel_id = SAI_NULL_OBJECT_ID`, `active_ = false` にリセット
5. `createTunnelHw()` が `false` を返す

### VLAN 未存在時 (VxlanTunnelMapOrch::addOperation)

`VXLAN_TUNNEL_MAP` 追加時に対象 VLAN が存在しない場合 (vxlanorch.cpp:2032):
- `gPortsOrch->getVlanByVlanId(vlan_id, tempPort)` が false
- `SWSS_LOG_WARN("Vxlan tunnel map vlan id doesn't exist: %d", ...)` を記録
- `return false` → Consumer キューに保留して再試行。VLAN 作成後に自動収束する

### VXLAN_TUNNEL 未存在時

`VXLAN_TUNNEL_MAP` 追加時に対応する `VXLAN_TUNNEL` エントリが存在しない場合 (vxlanorch.cpp:2049):
- `SWSS_LOG_WARN("Vxlan tunnel '%s' doesn't exist", ...)` を記録
- `return false` → Consumer キューに保留して再試行

### del_tnl_hw_pending ガード

削除前の HW 操作が完了していない場合 (vxlanorch.cpp:2057):
- `SWSS_LOG_WARN("Tunnel Mapper deletion is pending")` を記録
- `return false` → 保留。HW 削除完了後に自動収束

### SAI エラーの handleSaiCreateStatus

`sai_tunnel_api->create_tunnel()` が `SAI_STATUS_SUCCESS` 以外を返した場合は
`handleSaiCreateStatus(SAI_API_TUNNEL, status)` で処理される (vxlanorch.cpp:403-413)。
`task_success` 以外の場合は `SWSS_LOG_ERROR("Can't create a tunnel object")` を記録し
`SAI_NULL_OBJECT_ID` を返す → 上述の tunnel SAI 失敗フローに乗る。

## ブロック案

```markdown
<!-- failure -->
## 失敗時の挙動 (Phase D)

| 失敗ケース | 挙動 | リトライ | evidence |
|-----------|------|---------|----------|
| `sai_tunnel_api->create_tunnel()` 失敗 | `deleteMapperHw()` で mapper をロールバック後 `active_=false`、`createTunnelHw()` が `false` 返却 → `VxlanTunnelMapOrch::addOperation` が `return false` してキュー保留 | 自動リトライ | `vxlanorch.cpp:908-920` |
| `create_tunnel_termination()` 失敗 (`with_term=true`) | `remove_tunnel()` + `deleteMapperHw()` で完全ロールバック後 `active_=false` | 自動リトライ | `vxlanorch.cpp:925-934` |
| `VXLAN_TUNNEL_MAP` 追加時に対象 VLAN が未存在 | `SWSS_LOG_WARN` + `return false` → キュー保留。VLAN 作成後に自動収束 | 自動リトライ | `vxlanorch.cpp:2030-2033` |
| `VXLAN_TUNNEL_MAP` 追加時に `VXLAN_TUNNEL` 未存在 | `SWSS_LOG_WARN` + `return false` → キュー保留。`VXLAN_TUNNEL` 投入後に自動収束 | 自動リトライ | `vxlanorch.cpp:2047-2050` |
| `del_tnl_hw_pending` フラグが立っている間の操作 | `SWSS_LOG_WARN` + `return false` → 保留。HW 削除完了後に自動収束 | 自動リトライ | `vxlanorch.cpp:2057-2060` |

!!! warning "SAI 失敗時のロールバック"
    `create_tunnel()` が失敗した場合、直前に作成した mapper オブジェクト (`createMapperHw`) が
    自動的にロールバックされる。部分的な SAI オブジェクトが残存しないよう設計されている
    (`vxlanorch.cpp:913-920`)。

!!! note "return false = リトライ"
    swss の Consumer フレームワークでは `addOperation` / `delOperation` が `false` を返すと
    エントリがキューに残り、次の doTask() サイクルで再処理される。依存リソース（VLAN / TUNNEL）が
    後から投入されれば自動的に収束する。

<!-- /failure -->
```

## 引用

[^fail1]: VxlanTunnel::createTunnelHw() ロールバック: `vxlanorch.cpp:895-940`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/vxlanorch.cpp#L895-L940>
[^fail2]: VxlanTunnelMapOrch::addOperation() VLAN/TUNNEL 依存: `vxlanorch.cpp:2012-2090`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/vxlanorch.cpp#L2012-L2090>
