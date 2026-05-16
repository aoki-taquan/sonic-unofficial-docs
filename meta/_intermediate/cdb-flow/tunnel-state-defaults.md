# tunnel-state Phase A — STATE_DB TUNNEL デフォルト調査メモ

調査日: 2026-05-15
対象: `docs/reference/config-db/tunnel-state.md`

## 調査対象ソース

| ファイル | コミット |
|---------|---------|
| `orchagent/tunneldecaporch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `orchagent/vxlanorch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `cfgmgr/vxlanmgr.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |

## TUNNEL_DECAP_TABLE — `setDecapTunnelStatus()` L1521-1531

```cpp
inline void TunnelDecapOrch::setDecapTunnelStatus(const std::string &tunnel_name)
{
    auto &tunnel = tunnelTable.at(tunnel_name);
    vector<FieldValueTuple> fv;
    APPEND_IF_NOT_EMPTY(fv, tunnel, tunnel_type);
    APPEND_IF_NOT_EMPTY(fv, tunnel, dscp_mode);
    APPEND_IF_NOT_EMPTY(fv, tunnel, ecn_mode);
    APPEND_IF_NOT_EMPTY(fv, tunnel, encap_ecn_mode);
    APPEND_IF_NOT_EMPTY(fv, tunnel, ttl_mode);
    stateTunnelDecapTable->set(tunnel_name, fv);
}
```

`APPEND_IF_NOT_EMPTY` マクロ (L15): フィールド値が空の場合は `fv` に追加しない。
→ 内部キャッシュに空のフィールドは STATE_DB に書かれない。

## TUNNEL_DECAP_TERM_TABLE — `doDecapTunnelTermTask()` L355-365 + `setDecapTunnelTermStatus()` L1539-1558

```cpp
// L361: term_type デフォルト値
TunnelTermType term_type = TUNNEL_TERM_TYPE_P2MP;
```

```cpp
// L1539-1558: setDecapTunnelTermStatus() の実装
string term_type_str = DecapTermTypeStrLookupTable.at(term_type);
vector<FieldValueTuple> fv = {{ "term_type", term_type_str }};
if (!src_ip_str.empty())
{
    fv.emplace_back("src_ip", src_ip_str);
}
if (!subnet_type.empty())
{
    fv.emplace_back("subnet_type", subnet_type);
}
```

- `term_type`: 常に STATE_DB に書かれる。省略時デフォルト = `P2MP` (変数初期値)
- `src_ip`: 空の場合は STATE_DB に書かれない
- `subnet_type`: 空の場合は STATE_DB に書かれない

## VXLAN_TUNNEL_TABLE — `addRemoveStateTableEntry()` L1913-1953

```cpp
fvVector.emplace_back("src_ip", (sip.to_string()).c_str());
fvVector.emplace_back("dst_ip", (dip.to_string()).c_str());
if (src == TNL_CREATION_SRC_CLI)
{
    fvVector.emplace_back("tnl_src", "CLI");
}
else
{
    fvVector.emplace_back("tnl_src", "EVPN");
}
fvVector.emplace_back("operstatus", "down");
```

- `operstatus` 初期値: `"down"` (ハードコード)
- `tnl_src`: `"CLI"` または `"EVPN"` (作成元によって分岐)
- Warm reboot 時 (state == INITIALIZED かつ既存エントリあり): 書き込みスキップ

## VXLAN_TABLE — `createVxlan()` L807-892 (vxlanmgr.cpp)

```cpp
// L891
fvVector.emplace_back("state", "ok");
```

- `state` = `"ok"` のみ。成功時のみ書き込み。値はハードコード固定。

## ref count 依存の残存

`tunneldecaporch.cpp`: `TUNNEL_DECAP_TABLE` の削除は `removeDecapTunnel()` で行われるが、
MUX orch 等から参照カウントが残っている間は `del()` が呼ばれない実装になっている。

## YANG discrepancy

STATE_DB テーブル (`TUNNEL_DECAP_TABLE`, `TUNNEL_DECAP_TERM_TABLE`, `VXLAN_TUNNEL_TABLE`) に
対応する YANG モジュールは `sonic-yang-models` に存在しない。
すべてコードのみで定義されており、YANG validation の対象外。
