---
title: FEC FLR 制限事項と HLD との乖離（CLI 未取り込み / ハードコード値）
description: FEC FLR の制限事項。SAI counter 未サポート interface、interleaving factor X の固定テーブル前提、線形回帰の最小データ点数制約、そして
  HLD 提案の `counterpoll port flr-interval-factor` サブコマンドが現行 master に取り込まれず lua ハードコード値で固定されている乖離点をまとめる。
area: platform
verification: discrepancy-found
last_verified: 2026-05-11
page_kind: split-child
monitor: evolved_beyond_hld
sources:
- repo: sonic-net/SONiC
  path: doc/port_fec_flr/port_fec_flr.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - PORT
  - TRANSCEIVER_INFO
  - CRM
  - PORTCHANNEL
  - BREAKOUT_CFG
  cli:
  - show interfaces
  yang:
  - sonic-port
  - sonic-crm
---

# FEC FLR 制限事項と HLD との乖離

このページは [FEC FLR Support in SONiC（概要ハブ）](fec-flr-support-in-sonic.md) の派生で、**制限事項と実装乖離** に絞る。概念は [fec-flr-support-in-sonic-concepts.md](fec-flr-support-in-sonic-concepts.md)、設定 / CLI は [fec-flr-support-in-sonic-operations.md](fec-flr-support-in-sonic-operations.md)、内部実装は [fec-flr-support-in-sonic-internals.md](fec-flr-support-in-sonic-internals.md) を参照。

## 1. HLD レベルの制限事項

- 必要な [SAI](../reference/glossary.md#term-sai) counter（`SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_Si` 等）が **未サポートの interface は `N/A`** 表示[^1]
- 非ゼロ bin が 2 個未満で回帰できない場合は `FLR(P) = 0`[^1]
- interleaving factor X は **port speed × lane 数の固定テーブル** で代替。新 SAI 属性が追加されればそちらに置換予定[^1]
- 100G × 1 lane の場合 X は **autonegotiated**（1 or 2）。誤った X を使うと FLR が 2 倍ずれる[^1]
- 計算は `port_stat POLL_INTERVAL × FLR_INTERVAL_FACTOR` 周期。ASIC counter の更新粒度に依存
- predicted は **線形回帰の外挿** に過ぎず、低 BER 領域での実測 FLR と乖離する可能性

## 2. 実装との乖離（2026-05-09 / 05-11 裏取り）

| 項目 | [HLD](../reference/glossary.md#term-hld) | 現行 master | 結果 |
|------|-----|------|------|
| `port_flr.lua` の swss 取り込み | 必須 | `sonic-swss/orchagent/port_flr.lua` L1-460 に存在。`FEC_FLR` / `FEC_FLR_PREDICTED` / `FEC_FLR_R_SQUARED` を RATES テーブルへ書く実装あり | ✓ 実装済み |
| `SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_S0..S16` の利用 | 必須 | `sonic-swss/crates/countersyncd/src/sai/saiport.rs` L766-782 で S0〜S16 を列挙、L1144- で文字列マッピング | ✓ 実装済み |
| `COUNTER_DB:RATES` への `FEC_FLR` / `FEC_FLR_PREDICTED` 書き込み | 必須 | `port_flr.lua` L443 / L451 / L452 で `FEC_FLR` / `FEC_FLR_PREDICTED` / `FEC_FLR_R_SQUARED` を HSET | ✓ 実装済み |
| `show interfaces counters` (portstat) に FLR カラム追加 | 必須 | `sonic-utilities/utilities_common/portstat.py` L50 のヘッダ列定義に `fec_flr`, `fec_flr_predicted`, `fec_flr_r_squared` が追加済、L271-273 で CHASSIS_STATE_DB から読み出し、L671-673 で format して表示。`sonic-utilities/utilities_common/netstat.py` L144 `format_fec_flr` / L156 `format_fec_flr_predicted` も実装 | ✓ 実装済み |
| `counterpoll port flr-interval-factor` サブコマンド | 提案 | **未実装**。`sonic-utilities/counterpoll/` 配下に `flr` / `flr-interval` サブコマンドは存在しない。`port_flr.lua` L31 で `FEC_FLR_POLL_INTERVAL = 120`（port_stat poll 周期に掛ける倍率 / factor。port_stat poll = 1 秒なら実効 FLR poll = 120 秒）がハードコード | ⚠️ 未取り込み |
| `BIN_FILTER_VALUE` / `MIN_SIGNIFICANT_BINS` / `MFC` のチューニング API | 想定 | `port_flr.lua` L29-32 で `BIN_FILTER_VALUE=10` / `MIN_SIGNIFICANT_BINS=2` / `MFC=8` ハードコード。実行時変更経路無し | ⚠️ 未取り込み |
| portstat `-f` モードでの FLR(O) / FLR(P) サンプル出力フォーマット | 必須 | HLD のサンプル表示と portstat の列名（`fec_flr` / `fec_flr_predicted`）が一致。L156-180 の `format_fec_flr_predicted` で r_squared から accuracy 列を生成 | ✓ 実装済み |

> 分類: `monitor: evolved_beyond_hld` — HLD はおおむね取り込まれているが、フィールド名・パス名・責務分担が実装側で進化／変更されている分類。実装側を正として読み替える必要がある。

## 3. 読者への影響

- 高頻度に FLR を見たい場合（例: 30 秒周期）、[CONFIG_DB](../reference/glossary.md#term-config_db) / CLI で周期を縮められない。
- 計算ロジック（`BIN_FILTER_VALUE` 等）の調整は **lua スクリプトを直接書き換えてビルドし直す** しか手段が無い。
- 一方、コア機能（FLR / FLR_PREDICTED の計算と表示）は最初から使えるので、観測自体には支障なし。

## 4. 回避策

- poll 周期を 120 秒以下にしたい場合: `sonic-swss/orchagent/port_flr.lua` L31 を書き換えて image をリビルド。
- ランタイムでだけ試したい場合: `docker exec swss sed -i 's/FEC_FLR_POLL_INTERVAL = 120/FEC_FLR_POLL_INTERVAL = 60/' /usr/share/swss/port_flr.lua` で in-place 編集後 `docker restart swss`（恒久化には buildimage への patch 必須）。
- 計算閾値の調整も同様に lua スクリプトレベル。動的にはチューニング不可。
- 動的設定を求めるなら、`counterpoll port flr-interval-factor` CLI の上流 PR 追跡が必要。

## 5. 関連 GitHub Issue / PR

- [sonic-utilities #4126: Add secondary poll factor to flex counter infra (open)](https://github.com/sonic-net/sonic-utilities/pull/4126) — `counterpoll port flr-interval-factor` 周辺で必要となる flex counter 二次ポーリング機構の追加 PR。本 HLD の `port_flr.lua` 実装と整合させる前提。
- HLD 本体の FLR 算出ロジック (`port_flr.lua`) の取り込み PR は明示的に紐づく単独 PR が確認できず、断片的な flexcounter / port counter 改修に混在している。

## 関連ページ

- [FEC FLR Support in SONiC（概要ハブ）](fec-flr-support-in-sonic.md)
- [fec-flr-support-in-sonic-concepts.md](fec-flr-support-in-sonic-concepts.md)
- [fec-flr-support-in-sonic-operations.md](fec-flr-support-in-sonic-operations.md)
- [fec-flr-support-in-sonic-internals.md](fec-flr-support-in-sonic-internals.md)

## 確認コマンド

```bash
# 現行 master の FLR_INTERVAL_FACTOR ハードコード値を確認 (動的変更不可の根拠)
docker exec swss grep -n 'FLR_INTERVAL_FACTOR\|FEC_FLR_POLL_INTERVAL' /usr/share/swss/port_flr.lua

# 実効 poll 周期 (= port_stat POLL_INTERVAL × FLR_INTERVAL_FACTOR) を逆算
sonic-db-cli CONFIG_DB hget 'FLEX_COUNTER_TABLE|PORT' POLL_INTERVAL

# in-place で factor を 60 に縮めた場合の検証 (恒久化には buildimage patch 必須)
docker exec swss sed -i 's/FEC_FLR_POLL_INTERVAL = 120/FEC_FLR_POLL_INTERVAL = 60/' /usr/share/swss/port_flr.lua
docker restart swss

# CLI が未取り込みか確認 (取り込まれていれば counterpoll port flr-interval-factor が見える)
show counterpoll | grep -i flr || echo "FLR counterpoll CLI 未取り込み"

# 関連 PR (sonic-utilities #4126) の取り込み状況確認
git -C .cache/sonic-sources/sonic-utilities log --oneline | grep -iE 'flr|flex.*secondary'
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/port_fec_flr/port_fec_flr.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- next-action -->
## このページを読んだ後の次アクション

!!! tip "読み手向け"
    - **本機能を実運用で使う場合**: 実装は存在するが本 HLD の記述と乖離。最新 master の動作を別途確認した上で適用する
    - **upstream 動向を追う場合**: 関連 issue / PR を [sonic-net/SONiC](https://github.com/sonic-net/SONiC) で検索（HLD タイトル / CONFIG_DB テーブル名 / Orch クラス名で grep するのが速い）
    - **代替手段 / 関連 reference**: 関連テーブル / CLI / YANG は frontmatter `related` および [Reference 索引](../reference/index.md) を参照

!!! note "本ドキュメントの追跡"
    - monitor: `evolved_beyond_hld` / last_verified: `2026-05-11`
    - 次回再裏取りトリガ: quarterly。一覧は [discrepancy-index](../reference/verification/discrepancy-index.md) を参照（運用詳細は repo の `meta/discrepancy-operations.md`）

<!-- /next-action -->

<!-- glossary-links-injected: 5440b86e15ed -->
