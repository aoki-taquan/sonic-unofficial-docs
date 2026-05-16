# VXLAN_TUNNEL_MAP — Phase D: 失敗・リトライ挙動

調査対象: `sonic-swss/orchagent/vxlanorch.cpp`

## addOperation() の失敗分類

### 永続破棄（return true）― リトライなし

| 条件 | ログ | コードロケーション |
|------|------|------------------|
| マップキーが既にキャッシュに存在 | `SWSS_LOG_ERROR("Vxlan tunnel map '%s' already exist")` | `vxlanorch.cpp:2025-2027` |
| `vni` >= `MAX_VNI_ID` (16777215) | `SWSS_LOG_ERROR("Vxlan tunnel map vni id is too big: %d")` | `vxlanorch.cpp:2037-2040` |

### リトライ待ち（return false）― 依存オブジェクト待機

| 条件 | ログ | コードロケーション |
|------|------|------------------|
| VLAN が PortsOrch に未登録 | `SWSS_LOG_WARN("Vxlan tunnel map vlan id doesn't exist: %d")` | `vxlanorch.cpp:2030-2033` |
| 親 VXLAN_TUNNEL が未存在 | `SWSS_LOG_WARN("Vxlan tunnel '%s' doesn't exist")` | `vxlanorch.cpp:2047-2050` |
| `del_tnl_hw_pending` フラグが立っている | `SWSS_LOG_WARN("Tunnel Mapper deletion is pending")` | `vxlanorch.cpp:2057-2060` |
| `createTunnelHw()` が失敗 | （内部エラーログ） | `vxlanorch.cpp:2069-2074` |

### SAI 失敗（`std::runtime_error` catch → return false）

| 操作 | SAI API | ログ | コードロケーション |
|------|---------|------|------------------|
| SAI トンネルマップオブジェクト作成失敗 | `sai_tunnel_api->create_tunnel_map()` | `SWSS_LOG_ERROR("Can't create tunnel map object")` + `SAI_NULL_OBJECT_ID` 返却 | `vxlanorch.cpp:147-154` |
| SAI トンネルマップエントリ作成失敗 | `sai_tunnel_api->create_tunnel_map_entry()` | `SWSS_LOG_ERROR("Can't create a tunnel map entry object")` + `SAI_NULL_OBJECT_ID` 返却 | `vxlanorch.cpp:215-221` |
| `create_tunnel_map_entry()` が例外送出 | — | `SWSS_LOG_WARN("Error adding tunnel map entry. Tunnel: %s. Entry: %s. Error: %s")` | `vxlanorch.cpp:2113-2117` |
| `createTunnelHw()` 内のトンネル作成失敗 | `sai_tunnel_api->create_tunnel()` | `SWSS_LOG_ERROR("Can't create a tunnel object")` + `return false` | `vxlanorch.cpp:403-409` |
| tunnel-term 作成失敗 | `sai_tunnel_api->create_tunnel_term_table_entry()` | `SWSS_LOG_ERROR("Can't create a tunnel term table object")` + `return false` | `vxlanorch.cpp:488-494` |

## delOperation() の失敗分類

### 永続破棄（return true）― 警告のみ・処理継続

| 条件 | ログ | コードロケーション |
|------|------|------------------|
| 削除対象マップキーが存在しない | `SWSS_LOG_WARN("Vxlan tunnel map '%s' doesn't exist")` | `vxlanorch.cpp:2138-2141` |
| 削除時に VLAN が消えていた | `SWSS_LOG_ERROR("Delete VLAN-VNI map.vlan id doesn't exist: %d")` | `vxlanorch.cpp:2145-2148` |
| ブリッジポート取得失敗（vlan_vrf_vni_count==0 時）| `SWSS_LOG_ERROR("Get port failed for source vtep %s")` | `vxlanorch.cpp:2196-2197` |
| ブリッジポート削除失敗 | `SWSS_LOG_ERROR("Remove Bridge port failed for source vtep = %s fdbcount = %d")` | `vxlanorch.cpp:2202-2204` |

### SAI 失敗（`std::runtime_error` catch → return false）

| 操作 | SAI API | ログ | コードロケーション |
|------|---------|------|------------------|
| SAI マップエントリ削除失敗 | `sai_tunnel_api->remove_tunnel_map_entry()` | `SWSS_LOG_ERROR("Can't delete a tunnel map entry object")` | `vxlanorch.cpp:237-242` |
| `remove_tunnel_map_entry()` が例外送出 | — | `SWSS_LOG_ERROR("Error removing tunnel map %s: %s")` + `return false` | `vxlanorch.cpp:2158-2161` |

## del_tnl_hw_pending による連鎖ブロック

最後の MAP エントリ削除時（`vlan_vrf_vni_count == 0`）に DIP トンネルが残存していると、
`del_tnl_hw_pending = true` が設定され（`vxlanorch.cpp:2215`）、以降の MAP 追加は
`Tunnel Mapper deletion is pending` で永続ブロックされる。
DIP トンネルが解放されて `del_tnl_hw_pending` が `false` に戻るまで MAP は追加不可。

## SAI 失敗後の状態不整合リスク

`create_tunnel_map_entry()` が `SAI_NULL_OBJECT_ID` を返した場合、上位の
`addOperation()` は `vxlan_tunnel_map_table_` にエントリを追加するが
`map_entry_id` が `SAI_NULL_OBJECT_ID` のまま記録される (`vxlanorch.cpp:2108`)。
これは L3VNI の場合の意図的 no-op と同じコードパスに落ち、
後続の `delOperation()` で `remove_tunnel_map_entry(SAI_NULL_OBJECT_ID)` が呼ばれても
`if (obj_id != SAI_NULL_OBJECT_ID)` ガードにより SAI 呼び出しはスキップされる（`vxlanorch.cpp:232-235`）。
ただし、キャッシュ上は存在するが HW に実体がない状態となるため、
実際のパケット転送に影響するがログ上は正常に見える点に注意。
