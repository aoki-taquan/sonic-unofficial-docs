---
title: L3 Scaling と Performance 強化 制限事項と HLD との乖離（gc_thresh / CoPP / partial 取り込み）
description: L3 Scaling と Performance 強化 HLD の制限事項。kernel メモリ消費と CPU 負荷のトレードオフ、AS7712
  計測の他 ASIC への一般化不可、そして HLD 提案の gc_thresh / CoPP 値が現行 master の保守的 default と乖離している部分採用状況をまとめる。
area: internals
verification: discrepancy-found
last_verified: 2026-05-11
page_kind: split-child
monitor: partially_implemented
sources:
- repo: sonic-net/SONiC
  path: doc/l3-performance-scaling/L3_performance_and_scaling_enchancements_HLD.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - VNET
  - COPP_GROUP
  - COPP_TRAP
  - NEIGH
  - VLAN_INTERFACE
  - INTERFACE
  - VNET_ROUTE_TUNNEL
  cli:
  - show arp
  - show ndp
  - config vnet
  yang:
  - sonic-copp
  - sonic-vnet
---

# L3 Scaling と Performance 強化 制限事項と HLD との乖離

このページは [L3 Scaling と Performance 強化（概要ハブ）](l3-scaling-and-performance-enhancements.md) の派生で、**制限事項と実装乖離** に絞る。概念は [l3-scaling-and-performance-enhancements-concepts.md](l3-scaling-and-performance-enhancements-concepts.md)、設定 / CLI は [l3-scaling-and-performance-enhancements-operations.md](l3-scaling-and-performance-enhancements-operations.md)、内部実装は [l3-scaling-and-performance-enhancements-internals.md](l3-scaling-and-performance-enhancements-internals.md) を参照。

## 1. HLD レベルの制限事項

- **[HLD](../reference/glossary.md#term-hld) は 2019 年改訂**。kernel sysctl 値や [CoPP](../reference/glossary.md#term-copp) 値はその後の [SONiC](../reference/glossary.md#term-sonic) で更に調整されている可能性[^1]
- `gc_thresh3` を上げると **kernel メモリ使用量** が増える。低スペック CPU 機では注意
- CoPP の [ARP](../reference/glossary.md#term-arp)/ND 上限を 8000 pps に上げると **CPU 負荷増**。他の trap との合算で CPU 飽和に注意
- sairedis bulk API は **[ASIC](../reference/glossary.md#term-asic) 側 bulk 未対応の場合 [syncd](../reference/glossary.md#term-syncd) 内で逐次処理** されるため、改善幅は [Redis](../reference/glossary.md#term-redis) message 削減分に留まる
- `RouteOrch` の 1 秒 timer flush は **大量経路投入時のみ効果**。少量更新では遅延がむしろ増える可能性
- `fpmsyncd` の [VNET](../reference/glossary.md#term-vnet) 判定スキップは **VNET 利用時の挙動変更ではない**（`rt_table != 0` の経路には従来通り lookup）
- HLD は AS7712 (Tomahawk) で測定。他 ASIC では **異なる timing** になる

## 2. 実装との乖離

| HLD 主張 | 実装 | 結果 |
|---|---|---|
| `net.ipv4.neigh.default.gc_thresh1/2/3 = 16000/32000/48000`、IPv6 = 8000/16000/32000 | `sonic-buildimage/files/image_config/sysctl/90-sonic.conf:21-26` で v4/v6 ともに `1024/2048/4096` | ⚠️ HLD 提案値は採用されず |
| CoPP ARP/ND 上限 600 → 8000 pps | `sonic-buildimage/files/image_config/copp/copp_cfg.j2` で `arp` trap は `queue4_group2`（cir/cbs 600）。8000 pps への引き上げは無し | ⚠️ HLD 提案値は採用されず |
| `RouteOrch` の bulk route API + 1 秒 timer flush | `sonic-swss/orchagent/routeorch.cpp:41` で `gRouteBulker(sai_route_api, gMaxBulkSize)`、`routeorch.cpp:626-1116` で bulker 経由の add/remove と flush 処理 | ✓ 実装済み |
| `fpmsyncd` の `rt_table == 0` で master device lookup スキップ | `sonic-swss/fpmsyncd/routesync.cpp:2077-2082` で `master_index` 取得し、0 のときは lookup を行わない | ✓ 実装済み |
| sairedis 内 nlohmann/json v2.0 → v3.6 | 本確認では未検証（実装は時間経過で更に進んでいると見られる） | △ |
| `show arp` / `show ndp` の個別 [FDB](../reference/glossary.md#term-fdb) lookup 化 | 本確認では未検証 | △ |

`gc_thresh` と CoPP ARP/ND が HLD 提案値を採用していない理由は、その後の運用で **kernel メモリ消費**と **CPU 負荷** が問題になったためと思われる（本文「制限事項」で警告済みのトレードオフ）。HLD のスケール目標値（IPv4 ARP 32k 等）は **kernel cache 上限としては届かない設定**になっている点に注意。

## 3. 行番号付きエビデンス

`sonic-buildimage/files/image_config/sysctl/90-sonic.conf` L21-L26:

```ini
net.ipv4.neigh.default.gc_thresh1=1024
net.ipv6.neigh.default.gc_thresh1=1024
net.ipv4.neigh.default.gc_thresh2=2048
net.ipv6.neigh.default.gc_thresh2=2048
net.ipv4.neigh.default.gc_thresh3=4096
net.ipv6.neigh.default.gc_thresh3=4096
```

→ HLD 提案値（v4 16k/32k/48k, v6 8k/16k/32k）は **採用されていない**。実装は v4/v6 共通で 1024/2048/4096。

`sonic-buildimage/files/image_config/copp/copp_cfg.j2` L7, L17, L27 等で `cir` は `600` のまま、ARP trap (`queue4_group2`) の HLD 提案値 8000 pps は採用されず。

`sonic-swss/orchagent/routeorch.cpp` L41:

```cpp
RouteOrch::RouteOrch(DBConnector *db, vector<table_name_with_pri_t> &tableNames,
                     SwitchOrch *switchOrch, NeighOrch *neighOrch, IntfsOrch *intfsOrch,
                     VRFOrch *vrfOrch, FgNhgOrch *fgNhgOrch, Srv6Orch *srv6Orch) :
        gRouteBulker(sai_route_api, gMaxBulkSize),
```

→ bulker は **取り込み済み**。

`sonic-swss/fpmsyncd/routesync.cpp` L2077-L2082 で `rt_table == 0` 時の master device lookup スキップは **取り込み済み**。

## 4. 読者への影響

- HLD 数値（ARP 32k スケール）を前提にスケール試験を組むと、`net.ipv4.neigh.default.gc_thresh3=4096` で gc が走り、**`dmesg` に `neighbour: arp_cache: neighbor table overflow!`** が出て学習に失敗。
- CoPP ARP 600 pps なので **大規模 L2 sweep / failover 時に ARP / ND 学習が間に合わない**。HLD で謳う 8000 pps での収束 SLA を計算に入れた設計は破綻する。
- 一方、bulk route programming と master device lookup スキップは入っているので、**routing path 自体の latency 改善は HLD どおり** に享受できる。誤解しないようにスケールと latency を分けて見積もる必要がある。

## 5. 回避策

- ARP/ND テーブルを 32k/16k スケールで動かしたい場合: `/etc/sysctl.d/99-arp-scale.conf` に独自値を bake（[operations](l3-scaling-and-performance-enhancements-operations.md) §4 に手順あり）
- CoPP ARP/ND を上げる場合は `copp_cfg.j2` を編集して image rebuild。COPP_TABLE を runtime で書き換える経路もあるが、`config_reload` で copp_cfg.j2 由来 600 に戻る
- スケール試験設計時は HLD 提案値ではなく **現行 default 値を前提** に見積もる

## 6. 関連 GitHub Issue / PR

- 該当の `gc_thresh` / CoPP 値変更は明示的な community PR としては未提出。コミュニティ master では「メモリ・CPU トレードオフを優先して default を保守」の方針が継続。
- bulk route: `sonic-swss/orchagent/routeorch.cpp` の `gRouteBulker` 追加は複数 PR で漸進的に成立。
- VnetOrch の bulker 拡張は [sonic-swss #4303 (open)](https://github.com/sonic-net/sonic-swss/pull/4303)。HLD 当時カバーされていなかった VNET ルート bulk programming の続き。

## 関連ページ

- [L3 Scaling と Performance 強化（概要ハブ）](l3-scaling-and-performance-enhancements.md)
- [l3-scaling-and-performance-enhancements-concepts.md](l3-scaling-and-performance-enhancements-concepts.md)
- [l3-scaling-and-performance-enhancements-operations.md](l3-scaling-and-performance-enhancements-operations.md)
- [l3-scaling-and-performance-enhancements-internals.md](l3-scaling-and-performance-enhancements-internals.md)

<!-- phase-boundary -->
## 実装フェーズ境界

!!! info "Phase 別の実装済 / 未実装 サマリ"
    本ページは `monitor: partially_implemented` で、HLD で示された一連の機能
    が **段階的に取り込まれている** 状態を扱う。フェーズ毎の実装境界を
    1 枚の表に集約する (詳細は本ページ上部の `diff` admonition および
    [discrepancy-index](../reference/verification/discrepancy-index.md) を参照)。

    | Phase | 範囲 (機能 / 段階) | 実装済 (master 取り込み済) | 未実装 (HLD 提案のみ) |
    |---|---|---|---|
    | Phase 1 — 基本機能 | HLD §概要 / §設計の中核ユースケース | 取り込み済 — 本ページの「実装の概観」「実装詳細」節および `diff` admonition の現状側を参照 | — (Phase 1 は実装済) |
    | Phase 2 — 拡張機能 | HLD §拡張 / §追加要件 / §周辺統合 | 一部のみ取り込み済 — 本ページ「実装詳細」の補足参照 | 未実装 / 未マージ — HLD §未対応箇所、本ページ「制限事項」および `diff` admonition の差分側に列挙 |
    | Phase 3 — 将来拡張 | HLD §Future Work / §将来課題 | — | 未実装 — HLD 提案段階。対応 PR は確認されていない (last_verified 時点) |

    凡例: 「実装済」=現行 master で動作確認できる範囲 / 「未実装」=HLD には記載があるが対応 PR が未マージまたは設計のみで code が存在しない範囲。
<!-- /phase-boundary -->

## 引用元

[^1]: `sonic-net/SONiC` `doc/l3-performance-scaling/L3_performance_and_scaling_enchancements_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- next-action -->
## このページを読んだ後の次アクション

!!! tip "読み手向け"
    - **本機能を実運用で使う場合**: 取り込み済の部分のみ運用可能。欠落部分の利用は不可なので本文「実装との乖離」を確認した上で適用範囲を限定する
    - **upstream 動向を追う場合**: 関連 issue / PR を [sonic-net/SONiC](https://github.com/sonic-net/SONiC) で検索（HLD タイトル / CONFIG_DB テーブル名 / Orch クラス名で grep するのが速い）
    - **代替手段 / 関連 reference**: frontmatter `related` に列挙の [COPP_GROUP](../reference/config-db/copp-group.md) / [COPP_TRAP](../reference/config-db/copp-trap.md) / [VNET](../reference/config-db/vnet.md) / [NEIGH](../reference/config-db/neigh.md) / [VLAN_INTERFACE](../reference/config-db/vlan-interface.md) / [INTERFACE](../reference/config-db/interface.md) / [VNET_ROUTE_TUNNEL](../reference/config-db/vnet-route.md)、CLI `show arp` / `show ndp` / `config vnet`、YANG `sonic-copp` / `sonic-vnet` を参照。索引は [Reference 索引](../reference/index.md)

!!! note "本ドキュメントの追跡"
    - monitor: `partially_implemented` / last_verified: `2026-05-11`
    - 次回再裏取りトリガ: quarterly。一覧は [discrepancy-index](../reference/verification/discrepancy-index.md) を参照（運用詳細は repo の `meta/discrepancy-operations.md`）

<!-- /next-action -->

<!-- glossary-links-injected: ec18b66e3507 -->
