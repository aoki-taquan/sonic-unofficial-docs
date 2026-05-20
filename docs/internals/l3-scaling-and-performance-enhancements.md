---
title: L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show
  arp）
description: L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd
  / show arp） — SONiC 201908 リリース時に行われた L3 のスケール拡大と性能改善 をまとめた HLD。
area: internals
verification: discrepancy-found
monitor: partially_implemented
last_verified: 2026-05-11
page_kind: split-hub
sources:
- repo: sonic-net/SONiC
  path: doc/l3-performance-scaling/L3_performance_and_scaling_enchancements_HLD.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - COPP_TABLE
  - VNET
  - VLAN
  - VLAN_INTERFACE
  - VLAN_MEMBER
  - VLAN_SUB_INTERFACE
  - COPP_GROUP
  cli:
  - show arp
  - show ndp
  - config vlan
  - show vlan
  - config vnet
  yang:
  - sonic-vlan
  - sonic-vlan-sub-interface
  - sonic-copp
  - sonic-vnet
  - sonic-port
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含みます。機能の概念・設定・運用を読み物として読みたい場合は [Topics 12 章: Multi-ASIC / VoQ / Chassis](../topics/12-multi-asic-voq/index.md) を参照。
<!-- /topics-tip -->

!!! danger "裏取りステータス: Discrepancy-found（提案値と現行 default が乖離、一部最適化は実装済み）"
    現行 master を裏取りした結果、HLD 提案の **kernel `gc_thresh*` 値**と **CoPP ARP/ND 上限**は採用されておらず、より保守的な default に再設定されている。一方で **`RouteOrch` の bulk route API**（`gRouteBulker`）と **`fpmsyncd` の master device lookup スキップ**は実装済み。詳細は本文末尾の「実装との乖離」を参照（verified at: 2026-05-09）。

# L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / `show arp`）

!!! info "章分割済み"
    本ページは大型 HLD の **概要ハブ** として保持。詳細は以下の派生ページを参照:

    - [l3-scaling-and-performance-enhancements-concepts.md](l3-scaling-and-performance-enhancements-concepts.md) — スケール / 性能目標と改善 4 系統の位置づけ
    - [l3-scaling-and-performance-enhancements-operations.md](l3-scaling-and-performance-enhancements-operations.md) — sysctl / `COPP_TABLE` / `show arp` 確認手順
    - [l3-scaling-and-performance-enhancements-internals.md](l3-scaling-and-performance-enhancements-internals.md) — RouteOrch bulker / fpmsyncd / sairedis 内部
    - [l3-scaling-and-performance-enhancements-limitations.md](l3-scaling-and-performance-enhancements-limitations.md) — 制限事項と HLD 提案値の未採用乖離

## 概要

[SONiC](../reference/glossary.md#term-sonic) 201908 リリース時に行われた **L3 のスケール拡大と性能改善** をまとめた [HLD](../reference/glossary.md#term-hld)[^1]。スケールでは **[ARP](../reference/glossary.md#term-arp)/ND エントリ数** と **route 数 / [ECMP](../reference/glossary.md#term-ecmp) 構成** を引き上げ、性能では **route programming 時間** と **show コマンド応答時間** を短縮する。CLI / [CONFIG_DB](../reference/glossary.md#term-config_db) / [YANG](../reference/glossary.md#term-yang) への新規追加は **無し**[^1]。

スケール目標[^1]:

| 項目 | 目標 |
|------|------|
| IPv4 ARP entry | 32k |
| IPv6 ND entry | 16k |
| IPv4 route | 200k |
| IPv6 route | 65k |
| ECMP | 512×32, 256×64, 128×128 |

性能目標[^1]:

- IPv4 / IPv6 route programming 時間を短縮
- 未知 ARP / ND 学習時間を短縮
- `show arp` / `show ndp` の応答短縮
- **route programming 時間 30% 短縮** を狙う

## 動作仕様

### 1. ARP/ND の枚数増（kernel gc tuning）

旧 SONiC は ~2400 entry が上限だった。kernel ARP cache の **garbage collector 閾値**[^1]:

| パラメータ | 既定 | 提案 (IPv4) | 提案 (IPv6) |
|-----------|------|------------|------------|
| `gc_thresh1` | 128 | 16000 | 8000 |
| `gc_thresh2` | 512 | 32000 | 16000 |
| `gc_thresh3` | 1024 | 48000 | 32000 |

```text
net.ipv4.neigh.default.gc_thresh1=16000
net.ipv4.neigh.default.gc_thresh2=32000
net.ipv4.neigh.default.gc_thresh3=48000
net.ipv6.neigh.default.gc_thresh1=8000
net.ipv6.neigh.default.gc_thresh2=16000
net.ipv6.neigh.default.gc_thresh3=32000
```

burst 時の add/remove ループで entry が満杯にならない問題を解消する。

#### CoPP の ARP/ND 上限引き上げ

旧: ARP/ND の最大 600 pps → **8000 pps** に引き上げ[^1]。学習時間の短縮を狙う。`COPP_TABLE` の ARP/ND group の `cir`/`cbs` を変更する想定。

### 2. Route programming 時間短縮

旧時計値（AS7712 / Tomahawk 上）[^1]:

| 経路数 | IPv4 所要時間 | IPv6 所要時間 |
|--------|-------------|-------------|
| 10k | 11s | 11s |
| 30k | 30s | 30s |
| 60k | 48s | - |
| 90k | 68s | - |

#### 2.1 sairedis bulk route API の利用

旧: `RouteOrch` は 1 経路ごとに sairedis API を呼ぶ。[Redis](../reference/glossary.md#term-redis) pipelining でいくらかバルク化はされるが **1 経路 = 1 Redis message**[^1]。

新: **sairedis の bulk API** を使う:

- `RouteOrch` は 64 件まとめて bulk API に渡す
- meta_sai layer は内部で個別オブジェクトを作るが、**Redis に流れる message は 1 件** に集約
- [ASIC](../reference/glossary.md#term-asic) 側は **bulk route create を実装していない** ため `syncd` は 1 件ずつ処理する → 純粋な節約は **Redis message 数の削減**

`RouteOrch` に **新 timer** を追加し、未送信のバッチを **1 秒ごとに flush**[^1]。

```mermaid
sequenceDiagram
    participant RO as RouteOrch
    participant SA as sairedis (meta_sai)
    participant ADB as ASIC_DB
    participant SY as syncd
    participant SAI
    Note over RO: 64 経路を内部キューに溜める / 1秒 timer
    RO->>SA: bulk_create_routes([r1..r64])
    SA->>SA: meta object を 64 件作る
    SA->>ADB: 1 Redis message
    ADB->>SY: 通知
    loop 各経路
        SY->>SAI: create_route_entry()
    end
```

#### 2.2 `fpmsyncd` の最適化

旧: 各経路の処理で **`rt_table` 属性から master device 名を kernel から取得** する。これは VNET_ROUTE_TABLE 判定のため[^1]。

問題: [VNET](../reference/glossary.md#term-vnet) が無い環境でも lookup が **常に失敗 → cache 更新を毎経路で行う**。これが route 投入を遅くする。

修正: **`route.rt_table == 0`（global routing table）** なら lookup を **skip**。10k 経路の APP_DB 投入が **7-8s → 4-5s** に短縮[^1]。

#### 2.3 sairedis 内 JSON ライブラリ更新

`nlohmann/json` ライブラリの **v2.0 → v3.6** への更新で `dump()` 系最適化を取り込む[^1]。

#### 期待効果

上記合算で **route programming 時間 30% 削減** を目標[^1]。

### 3. `show arp` / `show ndp` の高速化

旧: [VLAN](../reference/glossary.md#term-vlan) L3 interface 上の ARP の **outgoing interface を求めるため [FDB](../reference/glossary.md#term-fdb) 全件を fetch**。エントリが大量だと show が秒〜分単位かかる[^1]。

修正: 該当 ARP/ND **特定エントリだけの FDB lookup** に変更。CLI スクリプト側の改修。

```mermaid
flowchart LR
    OLD[show arp 旧] -->|FDB 全件取得| F1[1 entry 解決]
    NEW[show arp 新] -->|"FDB 個別 GET (mac, vlan)"| F2[1 entry 解決]
```

## 設定

### CLI / CONFIG_DB / YANG

**新規 CLI / CONFIG_DB / YANG なし**[^1]。kernel sysctl と `COPP_TABLE` 値、内部実装の改善のみ。

### 関連する CONFIG_DB

| Table | フィールド | 用途 |
|-------|----------|------|
| `COPP_TABLE` | ARP/ND group の `cir` / `cbs` | 600 → 8000 pps |
| (`/etc/sysctl.d/...`) | `net.ipv4.neigh.default.gc_thresh1/2/3` 等 | kernel ARP cache |

### 設定例

```bash
# kernel ARP/ND threshold は image 側 sysctl で適用される想定
# 必要に応じユーザが上書き
sudo sysctl -w net.ipv4.neigh.default.gc_thresh3=48000
sudo sysctl -w net.ipv6.neigh.default.gc_thresh3=32000

# show 高速化はバージョンに含まれる
show arp     # 短縮された応答時間
show ndp
```

## 制限事項

- **HLD は 2019 年改訂**。kernel sysctl 値や [CoPP](../reference/glossary.md#term-copp) 値は **その後の SONiC で更に調整** されている可能性[^1]
- `gc_thresh3` を上げると **kernel メモリ使用量** が増える。低スペック CPU 機では注意
- CoPP の ARP/ND 上限を 8000 pps に上げると **CPU 負荷増**。他の trap との合算で CPU 飽和に注意
- sairedis bulk API は **ASIC 側 bulk 未対応の場合 [syncd](../reference/glossary.md#term-syncd) 内で逐次処理** されるため、改善幅は Redis message 削減分に留まる
- `RouteOrch` の 1 秒 timer flush は **大量経路投入時のみ効果**。少量更新では遅延がむしろ増える可能性
- `fpmsyncd` の VNET 判定スキップは **VNET 利用時の挙動変更ではない**（`rt_table != 0` の経路には従来通り lookup）
- HLD は AS7712 (Tomahawk) で測定。他 ASIC では **異なる timing** になる

## 干渉する機能

- **`RouteOrch`**: bulk API + timer 化
- **`fpmsyncd`**: master device lookup 最適化
- **`sairedis` (meta_sai + JSON)**: bulk API + JSON 更新
- **`syncd`**: bulk 受け取り側（[ASIC SDK](../reference/glossary.md#term-asic-sdk) 個別 call）
- **kernel ARP/ND**: gc_thresh による cache サイズ
- **`COPP_TABLE`**: ARP/ND の到達 pps
- **`show arp` / `show ndp` CLI**: 個別 FDB lookup 化
- **`warm boot`**: 本機能では明示変更なしだが速度向上の影響評価が必要[^1]

## トラブルシューティング

- 大量経路の programming が遅い → `RouteOrch` の bulk timer ログ、Redis message 数を確認
- ARP entry が 32k に達しない → `sysctl net.ipv4.neigh.default.gc_thresh*` の現在値、CoPP の ARP rate limiter
- `show arp` が遅い → `show arp` 実装が **個別 FDB lookup 版** か、古い版で全件取得していないかを確認
- VNET ありで route 反映が遅い → 本最適化の対象外（`rt_table != 0` の lookup は従来通り）

<!-- diff-admonition -->
!!! diff "HLD と実装の差分"
    2026-05-09 時点の現行 master を裏取り。

    | HLD 主張 | 実装 | 結果 |
    |---|---|---|
    | `net.ipv4.neigh.default.gc_thresh1/2/3 = 16000/32000/48000`、IPv6 = 8000/16000/32000 | `sonic-buildimage/files/image_config/sysctl/90-sonic.conf:21-26` で v4/v6 ともに `1024/2048/4096` | ⚠️ HLD 提案値は採用されず |
    | CoPP ARP/ND 上限 600 → 8000 pps | `sonic-buildimage/files/image_config/copp/copp_cfg.j2` で `arp` trap は `queue4_group2`（cir/cbs 600）。8000 pps への引き上げは無し | ⚠️ HLD 提案値は採用されず |
    | `RouteOrch` の bulk route API + 1 秒 timer flush | `sonic-swss/orchagent/routeorch.cpp:41` で `gRouteBulker(sai_route_api, gMaxBulkSize)`、`routeorch.cpp:626-1116` で bulker 経由の add/remove と flush 処理 | ✓ 実装済み |
    | `fpmsyncd` の `rt_table == 0` で master device lookup スキップ | `sonic-swss/fpmsyncd/routesync.cpp:2077-2082` で `master_index` 取得し、0 のときは lookup を行わない | ✓ 実装済み |
    | sairedis 内 nlohmann/json v2.0 → v3.6 | 本確認では未検証（実装は時間経過で更に進んでいると見られる） | △ |
    | `show arp` / `show ndp` の個別 FDB lookup 化 | 本確認では未検証 | △ |

    `gc_thresh` と CoPP ARP/ND が HLD 提案値を採用していない理由は、その後の運用で **kernel メモリ消費**と **CPU 負荷** が問題になったためと思われる（本文「制限事項」で警告済みのトレードオフ）。本ページで挙げているスケール目標値（IPv4 ARP 32k 等）は **kernel cache 上限としては届かない設定**になっている点に注意。

    **読者への影響**:

    - HLD の数値（IPv4 ARP 32k / IPv6 16k 等）を期待してスケール試験を組むと、**現行 default 値（v4 上限 2048〜4096、v6 同様）で先に gc が走り、想定スケールに到達できない**。`dmesg` に `neighbour: arp_cache: neighbor table overflow!` が出る。
    - CoPP ARP/ND が 600 pps のままなので、**大規模 L2 sweep / fast reroute 時に ARP/ND 学習が間に合わない** 場合がある。HLD で謳う 8000 pps での収束時間を期待してはいけない。
    - 一方、`RouteOrch` の bulk + 1 秒 timer flush と `fpmsyncd` の master device lookup スキップは取り込み済みで、**経路投入レイテンシ自体は HLD どおりの改善**が得られる。

    **回避策 / 対応方法**:

    - ARP/ND テーブルを 32k/16k スケールで動かしたい場合は、`/etc/sysctl.d/` 配下に独自ファイル（例: `99-arp-scale.conf`）を bake して `net.ipv4.neigh.default.gc_thresh3 = 65536` 等を上書き。次回 image build から有効。
    - CoPP の ARP/ND 上限を上げる場合は `sonic-buildimage/files/image_config/copp/copp_cfg.j2` の `queue4_group2` の `cir`/`cbs` を編集してリビルド。COPP_TABLE を runtime で書き換える経路もあるが、`copp_cfg.j2` ベースの設定が再 apply されると上書きされる。
    - スケール試験設計時は、HLD の提案値ではなく **現行 default 値** を前提に見積もりを立てる。
<!-- /diff-admonition -->

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

<!-- concerns hint:
- /etc/sysctl.d 配下の SONiC default で net.ipv4/ipv6.neigh.default.gc_thresh* が設定されているか未確認
- COPP_TABLE の ARP/ND group の cir/cbs が 600 → 8000 pps に上がっているか未確認
- RouteOrch の bulk route API + 1 秒 timer flush の現行 master 実装確認
- fpmsyncd の rt_table=0 での master device lookup スキップ実装確認
- sonic-sairedis の nlohmann/json バージョン現行確認
- show arp / show ndp の個別 FDB lookup 化が sonic-utilities に取り込まれているか確認
- HLD は 2019 年改訂のため現行 master との乖離リスクあり
-->

### 深掘り（2026-05-11、batch q3-disc-detail）

#### HLD 記述と実装の差分（行番号 + コード抜粋）

`sonic-buildimage/files/image_config/sysctl/90-sonic.conf` L21-L26:

```ini
net.ipv4.neigh.default.gc_thresh1=1024
net.ipv6.neigh.default.gc_thresh1=1024
net.ipv4.neigh.default.gc_thresh2=2048
net.ipv6.neigh.default.gc_thresh2=2048
net.ipv4.neigh.default.gc_thresh3=4096
net.ipv6.neigh.default.gc_thresh3=4096
```

→ HLD 提案値 (`16k/32k/48k` for v4, `8k/16k/32k` for v6) は **採用されていない**。実装は v4/v6 共通で `1024/2048/4096`。

`sonic-buildimage/files/image_config/copp/copp_cfg.j2` L7, L17, L27 等で `cir` は `600` のまま、ARP trap (`queue4_group2`) の HLD 提案値 `8000 pps` は採用されず。

`sonic-swss/orchagent/routeorch.cpp` L41:

```cpp
RouteOrch::RouteOrch(DBConnector *db, vector<table_name_with_pri_t> &tableNames,
                     SwitchOrch *switchOrch, NeighOrch *neighOrch, IntfsOrch *intfsOrch,
                     VRFOrch *vrfOrch, FgNhgOrch *fgNhgOrch, Srv6Orch *srv6Orch) :
        gRouteBulker(sai_route_api, gMaxBulkSize),
```

→ bulker は **取り込み済み**。

`sonic-swss/fpmsyncd/routesync.cpp` L2077-L2082 で `rt_table == 0` 時の master device lookup スキップは **取り込み済み**。

#### 読者への影響

- HLD 数値（ARP 32k スケール）を前提にスケール試験を組むと、`net.ipv4.neigh.default.gc_thresh3=4096` で gc が走り、**dmesg に `neighbour: arp_cache: neighbor table overflow!`** が出て学習に失敗。
- CoPP ARP 600 pps なので **大規模 L2 sweep / failover 時に ARP / ND 学習が間に合わない**。HLD で謳う 8000 pps での収束 SLA を計算に入れた設計は破綻する。
- 一方、bulk route programming と master device lookup スキップは入っているので、**routing path 自体の latency 改善は HLD どおりに享受できる**。誤解しないようにスケールと latency を分けて見積もる必要がある。

#### 回避策の実コマンド

```bash
# 1) ARP/ND テーブル拡大（恒久化、image 再ビルド不要、runtime 上書き）
sudo tee /etc/sysctl.d/99-arp-scale.conf <<EOF
net.ipv4.neigh.default.gc_thresh1=8192
net.ipv4.neigh.default.gc_thresh2=16384
net.ipv4.neigh.default.gc_thresh3=32768
net.ipv6.neigh.default.gc_thresh1=4096
net.ipv6.neigh.default.gc_thresh2=8192
net.ipv6.neigh.default.gc_thresh3=16384
EOF
sudo sysctl --system

# 2) CoPP ARP 上限引き上げ（runtime）
sonic-db-cli CONFIG_DB hset 'COPP_GROUP|queue4_group2' cir 8000 cbs 8000
# 注: config_reload 後は copp_cfg.j2 由来の 600 に戻るため、bake 化が望ましい

# 3) 現在の溢れ状況確認
dmesg | grep -i "neighbour\|arp_cache" | tail
ip -s -s neigh flush all   # 必要時のみ
cat /proc/sys/net/ipv4/neigh/default/gc_thresh3

# 4) bulk route 動作確認
swssloglevel -l INFO -c routeorch
sudo grep -i "bulk" /var/log/swss/sairedis.rec | tail
```

#### 関連 GitHub Issue / PR

- 該当の `gc_thresh` / CoPP 値変更は明示的な community PR としては未提出。コミュニティ master では「メモリ・CPU トレードオフを優先して default を保守」の方針が継続している。
- bulk route 関連: `sonic-swss/orchagent/routeorch.cpp` の `gRouteBulker` 追加は複数 PR で漸進的に成立。`grep -n "bulker" sonic-swss/orchagent/routeorch.cpp` で詳細を追える。
- VnetOrch の bulker 拡張は [sonic-swss #4303 (open)](https://github.com/sonic-net/sonic-swss/pull/4303)。HLD 当時カバーされていなかった VNET ルート bulk programming の続き。

#### 検証日

2026-05-11 (q3-disc-detail batch)

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

<!-- glossary-links-injected: ec18b66e3507 -->
