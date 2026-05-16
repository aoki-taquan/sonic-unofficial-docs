# static-route — Phase B 順序依存関係 調査メモ

対象: `docs/reference/config-db/static-route.md`
調査ソース: `bgpcfgd` (`managers_static_rt.py`), `fpmsyncd` (`routesync.cpp`)
作成日: 2026-05-16

---

## 1. NEXTHOP 解決順序 (bgpcfgd / StaticRouteMgr)

### 参照コード

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`

### 処理フロー

```
set_handler(key, data)
  ├─ 1. split_key(key)  →  (vrf, ip_prefix)
  ├─ 2. bfd チェック  →  bfd==true なら即 return (staticroutebfd 委譲)
  ├─ 3. IpNextHopSet 構築
  │     ├─ nexthop / ifname / distance / nexthop-vrf / blackhole をカンマ展開
  │     └─ サイズ不一致 → ValueError → log_crit → return False
  ├─ 4. static_route_commands(ip_nh_set, cur_nh_set, ...)
  │     ├─ route_tag 変更時: 全削除 → 全追加 (OP_DELETE リスト先行)
  │     └─ route_tag 同一時: symmetric_difference → DELETE 先 → ADD
  └─ 5. 初回 VRF 静的経路 → enable_redistribution_command を末尾追加
         bgp_asn 未設定 → vrf_pending_redistribution に積む
```

### 重要な順序制約

| 順序 | 内容 | コード参照 |
|------|------|-----------|
| BFD 判定が最優先 | `bfd==true` なら nexthop 解析すら行わない | L49–55 |
| DELETE が ADD より先 | `cmd_list = OP_DELETE + OP_ADD` | L206–207 |
| advertise タグ変更は全置換 | 差分ではなく全 nexthop を削除→追加 | L187–193 |
| redistribute は最後 | nexthop コマンド群の後に append | L68, L207 |
| BGP ASN 未設定は defer | `vrf_pending_redistribution` → `on_bgp_asn_change` で後適用 | L70, L255–258 |

---

## 2. VRF 先行原則 (fpmsyncd / RouteSync)

### 参照コード

- `sonic-swss/fpmsyncd/routesync.cpp`

### 処理フロー

```
RouteSync::onMsg(nlmsg_type, obj)
  ├─ RTM_NEWLINK / RTM_DELLINK → nl_cache_refill (経路処理なし)
  ├─ AF_MPLS → onLabelRouteMsg
  ├─ AF_INET / AF_INET6 →
  │   ├─ master_index = rtnl_route_get_table()
  │   ├─ master_index != 0 → getIfName() → master_name
  │   │   ├─ master_name starts "Vnet" → onVnetRouteMsg
  │   │   └─ else → onRouteMsg(nlmsg_type, obj, master_name)  ← VRF あり
  │   └─ master_index == 0 → onRouteMsg(nlmsg_type, obj, NULL) ← default VRF

RouteSync::onRouteMsg(nlmsg_type, obj, vrf)
  ├─ vrf != NULL:
  │   ├─ VRF_PREFIX ("Vrf") 検証 → 不合格なら mgmt 確認してスキップ or ERROR
  │   └─ destipprefix = "<vrf>:<prefix>"
  └─ vrf == NULL: destipprefix = "<prefix>" のみ
```

### VRF 先行の意味

- VRF デバイスが存在しない (ifindex 未解決) 場合、`getIfName` が失敗してルートをドロップ。
- よって VRF 側インターフェースが kernel に登録される前に経路が来ると、その経路は処理されない。
- mgmt VRF は明示的にスキップ（APPL_DB に書き込まない）。

---

## 3. kernel FIB 反映順序 (fpmsyncd)

### RTM メッセージ処理順

| 優先度 | 条件 | 処理 |
|--------|------|------|
| 1 (高) | `RTM_DELROUTE` | `delWithWarmRestart` で即削除 |
| 2 | `RTN_BLACKHOLE` | nexthop 解決省略、`blackhole=true` で SET |
| 3 | NHG ID 非ゼロ | `m_nh_groups` 参照。未登録ならドロップ |
| 4 | 単一 nexthop | route テーブルに直接展開 |
| 5 | 複数 nexthop | `nexthop_group` フィールドで参照 |
| 6 (低) | eth0/docker0/eth1-midplane | DEL を発行してスキップ |

### warm-reboot 考慮

- ADD/DEL ともに `setRouteWithWarmRestart` / `delWithWarmRestart` を経由する。
- warm-reboot 中は書き込みを defer し、reconciliation 完了後に一括適用。

### kernel → APPL_DB の最終順序

```
FRR zebra
  └─ Netlink RTM_NEWROUTE/RTM_DELROUTE
        └─ fpmsyncd RouteSync::onMsg
              └─ onRouteMsg → setRouteWithWarmRestart
                    └─ ProducerStateTable → APP_ROUTE_TABLE_NAME (APPL_DB)
                          └─ orchagent RouteOrch → SAI route_entry
```

---

## 証跡サマリ

| 項目 | ファイル | 行 |
|------|---------|-----|
| BFD 優先スキップ | managers_static_rt.py | L49–55 |
| DELETE 先行生成 | managers_static_rt.py | L206–207 |
| BGP ASN defer | managers_static_rt.py | L66–70, L254–258 |
| VRF index 解決 | routesync.cpp | L2082–2097 |
| VRF 名検証 | routesync.cpp | L2117–2136 |
| RTM_DELROUTE 優先 | routesync.cpp | L2149–2154 |
| NHG 先行参照 | routesync.cpp | L2201–2230 |
| eth0 フィルタ | routesync.cpp | L2250–2258 |
