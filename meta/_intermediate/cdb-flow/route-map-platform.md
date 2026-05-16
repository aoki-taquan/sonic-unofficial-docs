# ROUTE_MAP — Phase H プラットフォーム差分 中間ファイル

生成日: 2026-05-16

ソース調査対象:
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_rm.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

---

## 1. FRR バージョン差 (bgpcfgd vs frrcfgd 実装差)

bgpcfgd の `RouteMapMgr` (`managers_rm.py`) は **APPL_DB の BGP_PROFILE_TABLE** を購読し、SDN 専用の固定 2 キー (`FROM_SDN_SLB_ROUTES` / `FROM_SDN_APPLIANCE_ROUTES`) のみを処理する簡易実装。FRR コマンドは `set as-path prepend`, `set community`, `set origin incomplete` の 3 件に限定される。

frrcfgd (`frrcfgd.py`) は **CONFIG_DB の ROUTE_MAP テーブル** を直接購読し、`route_map_key_map` 全フィールド（`match_*` / `set_*` 30+ 項目）を FRR vtysh へ変換する汎用実装。配信先 daemon は `['zebra', 'bgpd', 'ospfd']` の 3 デーモン。

```
bgpcfgd RouteMapMgr  → APPL_DB BGP_PROFILE_TABLE → FRR (SDN専用3コマンド)
frrcfgd              → CONFIG_DB ROUTE_MAP        → FRR vtysh (汎用30+コマンド)
```

### FRR コマンド対応差

| コマンド | bgpcfgd | frrcfgd |
|---------|---------|---------|
| `route-map <name> permit\|deny <seq>` | 固定 permit 100 のみ | 任意 permit/deny/seq |
| `set as-path prepend` | ○ (SDN ASN) | ○ (`set_asn` / `set_asn_list`) |
| `set community` | ○ (SDN community_id) | ○ (`set_community_inline` / `_ref`) |
| `match ip address prefix-list` | ✗ | ○ (`match_prefix_set\|ipv4`) |
| `match ipv6 address prefix-list` | ✗ | ○ (`match_prefix_set\|ipv6`) |
| `match peer` (bgpd only) | ✗ | ○ (`match_neighbor`) |
| `set ipv6 next-hop global` (bgpd only) | ✗ | ○ (`set_ipv6_next_hop_global`) |
| `match source-protocol` (zebra only) | ✗ | ○ (`match_protocol`) |

---

## 2. SmartSwitch DPU 差分

`managers_rm.py` および `frrcfgd.py` に SmartSwitch / DPU 固有の分岐コードなし。
ROUTE_MAP テーブルは SmartSwitch 環境でも同一スキーマ・同一処理経路を使用する。
**プラットフォーム差なし（SmartSwitch DPU）**。

---

## 3. IPv4 / IPv6 ファミリー差

frrcfgd `route_map_key_map` (L1927–1956) において IPv4/IPv6 の取り扱いが異なる:

```python
('match_prefix_set|ipv4',   '{no:no-prefix}match ip address prefix-list {}'),
('match_prefix_set|ipv6',   '{no:no-prefix}match ipv6 address prefix-list {}'),
('match_next_hop_set|ipv4', '{no:no-prefix}match ip next-hop prefix-list {}'),
('match_next_hop_set|ipv6', '{no:no-prefix}match ip next-hop prefix-list {}'),  # コメント: FRR は ipv6 next-hop prefix-list 未サポート
('set_ipv6_next_hop_global',        '[bgpd]{no:no-prefix}set ipv6 next-hop global {}'),
('set_ipv6_next_hop_prefer_global', '[bgpd]{no:no-prefix}set ipv6 next-hop prefer-global', ['true','false']),
```

**重要な非対称性**:
- `match_next_hop_set|ipv6` は IPv6 next-hop prefix-list が FRR 未サポートのため、IPv4 と同じコマンド (`match ip next-hop prefix-list`) へフォールバック (コード内コメント: `#match ipv6 next-hop prefix-list not suppported by frr`)。
- `set_ipv6_next_hop_global` / `set_ipv6_next_hop_prefer_global` は bgpd 限定 (`[bgpd]` プレフィックス)。zebra / ospfd への送信なし。
- `match_origin` / `match_local_pref` / `match_community` / `match_ext_community` / `match_as_path` / `match_src_vrf` はすべて bgpd 限定。
- `match_protocol` (`match source-protocol`) は zebra 限定。

---

## 4. <!-- platform --> ブロック草案

```markdown
<!-- platform -->
## プラットフォーム差・ファミリー差

### bgpcfgd vs frrcfgd 実装差

ROUTE_MAP テーブルは **2 つの独立したデーモン** が異なる経路で処理する:

| 観点 | bgpcfgd RouteMapMgr | frrcfgd |
|------|---------------------|---------|
| 購読元 | APPL_DB `BGP_PROFILE_TABLE` | CONFIG_DB `ROUTE_MAP` |
| 対象キー | `FROM_SDN_SLB_ROUTES` / `FROM_SDN_APPLIANCE_ROUTES` のみ | 任意の route-map 名・seq |
| FRR コマンド範囲 | `set as-path prepend` / `set community` / `set origin incomplete` の 3 件 | `match_*` / `set_*` 全 30+ フィールド |
| ユースケース | SDN SLB / SDN Appliance 専用 | 汎用 BGP ポリシー |

### IPv4 / IPv6 ファミリー差 (frrcfgd)

- `match_prefix_set|ipv4` → FRR `match ip address prefix-list`
- `match_prefix_set|ipv6` → FRR `match ipv6 address prefix-list`
- `match_next_hop_set|ipv6` は **IPv6 next-hop prefix-list が FRR 未サポート** のため `match ip next-hop prefix-list`（IPv4 コマンド）へフォールバック。
- `set_ipv6_next_hop_global` / `set_ipv6_next_hop_prefer_global` は bgpd 限定。zebra・ospfd には送信されない。
- BGP 属性系 match (`match_origin`, `match_local_pref`, `match_community`, `match_as_path` 等) は bgpd 限定。
- `match_protocol` (`match source-protocol`) は zebra 限定。

### SmartSwitch DPU

SmartSwitch / DPU 固有の分岐なし。通常の BGP コンテナと同一処理経路。
<!-- /platform -->
```
