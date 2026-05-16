# VXLAN_TUNNEL 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/vxlan-tunnel.md` Phase D block.

## 調査対象ソース

- `sonic-swss/orchagent/vxlanorch.cpp` (全行スキャン)

スキャン範囲:
- `VxlanTunnelOrch::addOperation()` L1590-1650
- `VxlanTunnelOrch::delOperation()` L1652-1680
- `VxlanTunnel::createTunnelHw()` L892-950
- `VxlanTunnel::deleteTunnelHw()` L855-876
- `VxlanVrfMapOrch::addOperation()` L2250-2365
- `VxlanVrfMapOrch::delOperation()` L2367-2445
- `create_tunnel()` L293-412
- `create_tunnel_termination()` L435-516

---

## 失敗パス一覧

### 1. VRF 未解決 → `return false` (retry)

`vxlanorch.cpp:2320-2323` (`VxlanVrfMapOrch::addOperation()`):

```cpp
else
{
    SWSS_LOG_WARN("Vrf '%s' hasn't been created yet", vrf_name.c_str());
    return false;
}
```

VNI→VRF マッピング SET 時に参照先 VRF が VRFOrch にまだ登録されていない場合、`addOperation()` が `false` を返す。orchagent の `OrchDaemon` は `false` 戻りのエントリを同一キューに残し、次回 `doTask()` 呼び出し時に再試行する（無制限 retry）。**VRF が後から作成されれば自動的に適用される。rollback なし。エントリは消費されない。**

---

### 2. SAI tunnel 作成失敗 → `SAI_NULL_OBJECT_ID` 返却 → `active_ = false` で停止

`vxlanorch.cpp:912-921` (`VxlanTunnel::createTunnelHw()`):

```cpp
ids_.tunnel_id = create_tunnel(&ids_, &ips, ip, gUnderlayIfId, p2p, decap_ttl_mode_, encap_ttl);

if (ids_.tunnel_id != SAI_NULL_OBJECT_ID)
{
    tunnel_orch->addTunnelToFlexCounter(ids_.tunnel_id, tunnel_name_);
}
else
{
    // Undo changes in createMapperHw if create_tunnel fails.
    deleteMapperHw(mapper_list, map_src);
    ids_.tunnel_id = SAI_NULL_OBJECT_ID;
    ids_.tunnel_term_id = SAI_NULL_OBJECT_ID;
    active_ = false;
    return false;
}
```

`create_tunnel()` 内部で `sai_tunnel_api->create_tunnel()` が失敗すると `SAI_NULL_OBJECT_ID` を返し、`createTunnelHw()` は mapper ロールバック後に `false` を返す。**`tunnel_obj->isActive()` が false のまま固定され、後続の VXLAN_TUNNEL_MAP / VXLAN_EVPN_NVO 処理がすべてサスペンドされる。自動 retry なし。再起動または DEL + 再 SET でリカバリ。**

`vxlanorch.cpp:403-411` (`create_tunnel()` 内):

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_TUNNEL, status);
    if (handle_status != task_process_status::task_success)
    {
        return SAI_NULL_OBJECT_ID;
    }
}
```

---

### 3. 不正 `src_ip` / `dst_ip` アドレスファミリ不一致 → `return true` (drop)

`vxlanorch.cpp:1610-1614` (`VxlanTunnelOrch::addOperation()`):

```cpp
if ((src_ip.isV4() && !dst_ip.isV4()) ||
       (!src_ip.isV4() && dst_ip.isV4())) {
    SWSS_LOG_ERROR("Format mismatch: 'src_ip' and 'dst_ip' must be of the same family");
    return true;
}
```

`src_ip` が IPv4 で `dst_ip` が IPv6（またはその逆）の場合、エラーログを出力してエントリをキューから除去する（`return true` = 処理済み扱い）。**retry なし。トンネルオブジェクトは作成されない。CONFIG_DB のエントリは残存。直接 Redis 書き込みで YANG バリデーションを回避した場合のみ発生しうる。**

`ttl_mode` の不正値 (`vxlanorch.cpp:1631`) も同様：

```cpp
SWSS_LOG_ERROR("Invalid ttl_mode '%s' for the VxLAN tunnel '%s'", ttl_mode_str.c_str(), tunnel_name.c_str());
return true;
```

---

### 4. DEL 時に依存オブジェクト（EVPN_NVO / TUNNEL_MAP）が残存 → retry

`vxlanorch.cpp` `VxlanTunnel::deleteTunnelHw()` の呼び出し元 (cfgmgr/vxlanmgr.cpp 側の WARN ログとの連携):

- NVO エントリ残留: `SWSS_LOG_WARN("Tunnel %s deletion failed. Need to delete NVO")` → リトライ待ち
- TUNNEL_MAP 残留: `SWSS_LOG_WARN("Need to delete mapping entries")` → リトライ待ち
- State テーブル未クリア: `SWSS_LOG_WARN("State VXLAN tunnel table not yet empty.")` → リトライ

orchagent 側では `delOperation()` が呼ばれても依存オブジェクトが残存する場合は `false` を返し、キューに残す。**削除順序: VXLAN_TUNNEL_MAP → VXLAN_EVPN_NVO → VXLAN_TUNNEL の順で DEL しないと SAI 依存違反が発生する。**

`vxlanorch.cpp:874`:

```cpp
catch (const std::runtime_error& error)
{
    SWSS_LOG_ERROR("Error deleting tunnel %s: %s", tunnel_name_.c_str(), error.what());
    return false;
}
```

---

### 5. SAI tunnel term table 作成失敗 → rollback して `false`

`vxlanorch.cpp:926-937` (`VxlanTunnel::createTunnelHw()` 続き):

```cpp
ids_.tunnel_term_id = create_tunnel_termination(ids_.tunnel_id, ips, ip, gVirtualRouterId);
if (ids_.tunnel_term_id == SAI_NULL_OBJECT_ID)
{
    // Undo changes if create_tunnel_termination fails
    tunnel_orch->removeTunnelFromFlexCounter(ids_.tunnel_id, tunnel_name_);
    remove_tunnel(ids_.tunnel_id);
    deleteMapperHw(mapper_list, map_src);
    ids_.tunnel_id = SAI_NULL_OBJECT_ID;
    active_ = false;
    return false;
}
```

tunnel term table entry 作成失敗時は tunnel オブジェクトおよび mapper を全ロールバックし `active_ = false` で戻る。**部分的な SAI オブジェクト残留を防ぐ明示的 rollback あり。**

---

## retry パターンサマリ

| パターン | ケース | 挙動 | 影響範囲 |
|---|---|---|---|
| `return false` (retry) | VRF 未解決 | キューに残し次回再試行 | VRF 登録後に自動復旧 |
| `return false` (no auto retry) | SAI tunnel 作成失敗 | `active_=false` で停止 | 後続 MAP/NVO 処理がすべて停止 |
| `return true` (drop) | src/dst_ip ファミリ不一致・不正 ttl_mode | エントリ破棄・ログのみ | CONFIG_DB エントリは残存 |
| `return false` (retry) | DEL 時依存オブジェクト残存 | キューに残し再試行 | 削除順序不正で発生 |
| rollback + `return false` | SAI term table 作成失敗 | tunnel/mapper を全 rollback | 部分状態なし |

---

## config rollback 挙動

- CONFIG_DB のエントリは失敗後も残存（orchagent は CONFIG_DB を書き戻さない）
- `active_ = false` 状態では `show vxlan tunnel` でトンネルが表示されないか inactive となる
- VRF 未解決は VRF 作成後に自動復旧するが、SAI 失敗は手動で DEL + 再 SET が必要
- STATE_DB / ERROR_TABLE への書き込みなし（syslog のみ）
