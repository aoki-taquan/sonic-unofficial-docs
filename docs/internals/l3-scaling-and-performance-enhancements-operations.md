---
title: L3 Scaling と Performance 強化 設定・運用（sysctl / COPP_TABLE / show arp）
description: L3 Scaling と Performance 強化 HLD の設定・確認手順。kernel ARP/ND gc_thresh の sysctl
  適用方法、COPP_TABLE での ARP/ND CoPP 上限の見直し、show arp / show ndp の応答短縮確認、bulk route programming
  の動作確認方法をまとめる。
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
  - COPP_GROUP
  - COPP_TRAP
  - VLAN
  - VLAN_INTERFACE
  - VLAN_MEMBER
  - VLAN_SUB_INTERFACE
  cli:
  - show arp
  - show ndp
  - config vlan
  - show vlan
  yang:
  - sonic-vlan
  - sonic-copp
  - sonic-vlan-sub-interface
  - sonic-port
---

# L3 Scaling と Performance 強化 設定・運用

このページは [L3 Scaling と Performance 強化（概要ハブ）](l3-scaling-and-performance-enhancements.md) の派生で、**設定 / CLI / 確認手順** に絞る。概念は [l3-scaling-and-performance-enhancements-concepts.md](l3-scaling-and-performance-enhancements-concepts.md)、内部実装は [l3-scaling-and-performance-enhancements-internals.md](l3-scaling-and-performance-enhancements-internals.md)、制限事項と乖離は [l3-scaling-and-performance-enhancements-limitations.md](l3-scaling-and-performance-enhancements-limitations.md) を参照。

## 1. CLI / CONFIG_DB / YANG

新規 CLI / [CONFIG_DB](../reference/glossary.md#term-config_db) / [YANG](../reference/glossary.md#term-yang) なし[^1]。設定は **kernel sysctl** と **`COPP_TABLE`** 値、CLI 改修（`show arp` 高速化）に閉じる。

## 2. 関連する CONFIG_DB

| Table | フィールド | 用途 |
|-------|----------|------|
| `COPP_TABLE`（CONFIG_DB スキーマ上は [`COPP_GROUP`](../reference/config-db/copp-group.md) + [`COPP_TRAP`](../reference/config-db/copp-trap.md)、`COPP_TABLE` は runtime での APPL_DB 反映名）| [ARP](../reference/glossary.md#term-arp)/ND group の `cir` / `cbs` | 600 → 8000 pps（[HLD](../reference/glossary.md#term-hld) 提案。現行 master は 600 のまま）|
| (`/etc/sysctl.d/...`) | `net.ipv4.neigh.default.gc_thresh1/2/3` 等 | kernel ARP cache（HLD 提案値と現行 default は乖離）|

## 3. HLD 提案 vs 現行 default

| パラメータ | 提案 (IPv4) | 提案 (IPv6) | 現行 default (v4/v6 共通) |
|-----------|------------|------------|--------|
| `gc_thresh1` | 16000 | 8000 | 1024 |
| `gc_thresh2` | 32000 | 16000 | 2048 |
| `gc_thresh3` | 48000 | 32000 | 4096 |
| [CoPP](../reference/glossary.md#term-copp) ARP/ND `cir` | 8000 pps | 8000 pps | 600 pps |

HLD 値で運用したい場合は **自前で sysctl 上書きと CoPP 上書き** が必要（後述）。

## 4. ARP/ND スケールを上げる sysctl 上書き

恒久化（image rebuild 不要）:

```bash
sudo tee /etc/sysctl.d/99-arp-scale.conf <<EOF
net.ipv4.neigh.default.gc_thresh1=8192
net.ipv4.neigh.default.gc_thresh2=16384
net.ipv4.neigh.default.gc_thresh3=32768
net.ipv6.neigh.default.gc_thresh1=4096
net.ipv6.neigh.default.gc_thresh2=8192
net.ipv6.neigh.default.gc_thresh3=16384
EOF
sudo sysctl --system
```

確認:

```bash
cat /proc/sys/net/ipv4/neigh/default/gc_thresh3
cat /proc/sys/net/ipv6/neigh/default/gc_thresh3
dmesg | grep -i "neighbour\|arp_cache" | tail
```

## 5. CoPP ARP/ND 上限の上書き

runtime（再起動で揮発、`config_reload` でも copp_cfg.j2 由来の 600 に戻る）:

```bash
sonic-db-cli CONFIG_DB hset 'COPP_GROUP|queue4_group2' cir 8000 cbs 8000
```

恒久化するには `sonic-buildimage/files/image_config/copp/copp_cfg.j2` の `queue4_group2` の `cir`/`cbs` を編集してリビルド。

## 6. show 系応答短縮の確認

```bash
time show arp
time show ndp
```

旧版（[VLAN](../reference/glossary.md#term-vlan) L3 上 ARP の outgoing IF 解決で [FDB](../reference/glossary.md#term-fdb) 全件 fetch）では entry が大量だと秒〜分単位。新版は個別 FDB lookup でほぼ即時に近い応答[^1]。

## 7. bulk route programming の動作確認

```bash
# RouteOrch のログ詳細化
swssloglevel -l INFO -c routeorch

# sairedis.rec で bulk を確認
sudo grep -i "bulk" /var/log/swss/sairedis.rec | tail
```

`gRouteBulker(sai_route_api, gMaxBulkSize)` 経由で 64 件単位の bulk が走る[^1]。1 秒 timer flush で蓄積を吐き出す。

## 関連ページ

- [L3 Scaling と Performance 強化（概要ハブ）](l3-scaling-and-performance-enhancements.md)
- [l3-scaling-and-performance-enhancements-concepts.md](l3-scaling-and-performance-enhancements-concepts.md)
- [l3-scaling-and-performance-enhancements-internals.md](l3-scaling-and-performance-enhancements-internals.md)
- [l3-scaling-and-performance-enhancements-limitations.md](l3-scaling-and-performance-enhancements-limitations.md)

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
    - **代替手段 / 関連 reference**:
        - [CLI: `show arp`](../reference/cli/show-arp.md)
        - [CLI: `show ndp`](../reference/cli/show-ndp.md)

!!! note "本ドキュメントの追跡"
    - monitor: `partially_implemented` / last_verified: `2026-05-11`
    - 次回再裏取りトリガ: quarterly。一覧は [discrepancy-index](../reference/verification/discrepancy-index.md) を参照（運用詳細は repo の `meta/discrepancy-operations.md`）

<!-- /next-action -->

<!-- glossary-links-injected: f0f6af0a12c5 -->
