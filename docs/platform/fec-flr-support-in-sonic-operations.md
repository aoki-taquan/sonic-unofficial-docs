---
title: FEC FLR 設定・運用（counterpoll / show interfaces counters fec-stats / portstat -f）
description: FEC FLR 機能の設定・CLI・確認手順。`counterpoll port flr-interval-factor` での周期調整（HLD
  提案）、`show interfaces counters fec-stats` / `portstat -f` での FLR(O) / FLR(P) 表示、COUNTER_DB:RATES
  に書かれる entry の確認方法をまとめる。
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
  - FLEX_COUNTER_TABLE
  - PORT
  - TRANSCEIVER_INFO
  - PORTCHANNEL
  - BREAKOUT_CFG
  cli:
  - show interfaces counters fec-stats
  - counterpoll port flr-interval-factor
  - portstat -f
  - show interfaces
  - clear counters
  yang:
  - sonic-port
---

# FEC FLR 設定・運用

このページは [FEC FLR Support in SONiC（概要ハブ）](fec-flr-support-in-sonic.md) の派生で、**[CONFIG_DB](../reference/glossary.md#term-config_db) / CLI / 確認手順** に絞る。概念・公式は [fec-flr-support-in-sonic-concepts.md](fec-flr-support-in-sonic-concepts.md)、内部実装は [fec-flr-support-in-sonic-internals.md](fec-flr-support-in-sonic-internals.md)、制限事項は [fec-flr-support-in-sonic-limitations.md](fec-flr-support-in-sonic-limitations.md) を参照。

## 1. 関連する CONFIG_DB

| Table | Key | フィールド |
|-------|-----|-----------|
| `FLEX_COUNTER_TABLE` | `PORT` | `FLR_INTERVAL_FACTOR`（[HLD](../reference/glossary.md#term-hld) 提案。FlexCounterOrch が CONFIG_DB → [FLEX_COUNTER_DB](../reference/glossary.md#term-flex_counter_db) に伝搬する想定）[^1] |

> 実装では `FLR_INTERVAL_FACTOR` は CLI / CONFIG_DB 経由で動的に変更できない（[limitations](fec-flr-support-in-sonic-limitations.md) 参照）。lua 側のハードコード値 `120` が使われる。

## 2. CLI

| Command | 用途 |
|---------|------|
| `counterpoll port flr-interval-factor <factor>` | 計算周期（デフォルト 120）の設定[^1]（HLD 提案、未実装） |
| `show interfaces counters fec-stats` | `FLR(O)` / `FLR(P)` カラム追加[^1] |
| `portstat -f` | 上記の内部呼び出し（CLI が叩く形）[^1] |

## 3. 設定例（HLD 提案ベース）

```bash
# 60 秒に 1 回計算（port_stat poll 1s 前提なら 60 倍）
counterpoll port flr-interval-factor 60

# 表示
show interfaces counters fec-stats
```

期待表示[^1]:

```text
IFACE         STATE FEC_CORR FEC_UNCORR FEC_SYMBOL_ERR ... FLR(O)  FLR(P) (Accuracy)
Ethernet72    U     28,531   0          31                 0       2.68e-09 (79%)
Ethernet80    U     25,890   0          25                 0       6.03e-09 (79%)
Ethernet104   U     21,141   0          7                  0       7.08e-09 (79%)
```

`FLR(P)` は predicted FLR、Accuracy は線形回帰の決定係数 R² から派生する精度指標。

## 4. COUNTER_DB の確認

`port_flr.lua` は `COUNTER_DB:RATES` に以下を書く[^1]。`redis-cli` で直接確認できる:

| Entry | 説明 |
|-------|------|
| `FEC_FLR` | observed FEC FLR（float） |
| `FEC_FLR_PREDICTED` | predicted FEC FLR（float） |
| `FEC_FLR_R_SQUARED` | predicted の決定係数 |
| `SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last` | 直前値（次回 Δ 計算用） |
| `SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES_last` | 直前値 |
| `SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_Si_last` | 直前値（i=0..15） |

```bash
# port の OID から RATES エントリを引く（例）
redis-cli -n 2 hgetall 'RATES:oid:0x1000000000123'
```

## 5. 運用フロー

1. 健全リンクでは `FLR(O)` がほぼ 0、`FLR(P)` が低 BER 領域の外挿値を出す。
2. `FLR(P)` の経時的な上昇が **劣化傾向の早期サイン**。例: 1e-12 → 1e-9 へ 3 桁悪化したら点検対象。
3. `FLR(O)` が `0` でなくなった時点で **すでに観測レベルの欠落** が発生。`FEC_UNCORR` の増加と組み合わせて即時対応。
4. `Accuracy` 列が極端に低い場合は外挿の信頼度が低いので `FLR(P)` の値を厳密には使わない。

## 関連ページ

- [FEC FLR Support in SONiC（概要ハブ）](fec-flr-support-in-sonic.md)
- [fec-flr-support-in-sonic-concepts.md](fec-flr-support-in-sonic-concepts.md)
- [fec-flr-support-in-sonic-internals.md](fec-flr-support-in-sonic-internals.md)
- [fec-flr-support-in-sonic-limitations.md](fec-flr-support-in-sonic-limitations.md)

## 制限事項

- **poll 周期は固定 120 秒**: `FLR_INTERVAL_FACTOR` が `port_flr.lua` 内のハードコードで、CONFIG_DB / CLI からの動的変更は不可。短周期化には image リビルドが必要 ([limitations](fec-flr-support-in-sonic-limitations.md))。
- **`counterpoll port flr-interval-factor` CLI は未取り込み**: HLD で提案された CLI フラグは現行 master の `sonic-utilities` に存在しない。設定の見える化は `show counterpoll` ではなく `port_flr.lua` 内の定数値の grep で行う。
- **`Accuracy` 列が低い区間で `FLR(P)` を信用しない**: 外挿の信頼度が低いとき Predicted FLR の絶対値を運用閾値に使うと誤警報の原因になる。傾きの相対変化を見るのが安全。
- **[SAI](../reference/glossary.md#term-sai) counter 依存**: [ASIC](../reference/glossary.md#term-asic) が `SAI_PORT_STAT_IF_IN_FEC_*` を返さないと FLR(O) / FLR(P) ともに値が出ない。プラットフォーム SAI の対応状況により利用可否が変わる。
- **`FLR(O) > 0` は既に欠落発生済み**: Observed は事後指標。早期検知は Predicted の経時変化を主軸にする。

## 確認コマンド

運用フロー (`5. 運用フロー`) で示した手順を master 上で実走するための具体的な
コマンド列。HLD で提案された動的設定 CLI が未実装である点も併せて再確認できる。

```bash
# 1. portstat で FLR(O) / FLR(P) / Accuracy を観測（運用での主要 view）
show interfaces counters | head -3
show interfaces counters fec-stats | grep -iE 'FLR|FEC'

# 2. COUNTER_DB:RATES に FEC_FLR / FEC_FLR_PREDICTED / FEC_FLR_R_SQUARED が
#    書かれていることを直接確認
for oid in $(redis-cli -n 2 hvals 'COUNTERS_PORT_NAME_MAP' | head); do
  echo "--- $oid ---"
  redis-cli -n 2 hgetall "RATES:$oid" | grep -A1 -iE 'FEC_FLR'
done

# 3. lua 内のハードコード値（POLL_INTERVAL/BIN_FILTER/MFC）と
#    sonic-utilities 側に flr-interval-factor サブコマンドが無いことを確認
docker exec swss grep -nE 'FEC_FLR_POLL_INTERVAL|BIN_FILTER_VALUE|MFC' /usr/share/swss/port_flr.lua
counterpoll --help 2>&1 | grep -iE 'flr|fec' || echo 'flr-interval-factor: 未取り込み'
```

これらを実行すると、HLD で記述された `counterpoll port flr-interval-factor`
が実機の counterpoll CLI に存在しないことが具体的に確認できる。

## 実装との乖離

`monitor: evolved_beyond_hld` の HLD と実装の差分。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [FEC FLR 設定・運用 親ページ](fec-flr-support-in-sonic.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

## 引用元

[^1]: `sonic-net/SONiC` `doc/port_fec_flr/port_fec_flr.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- next-action -->
## このページを読んだ後の次アクション

!!! tip "読み手向け"
    - **本機能を実運用で使う場合**: 実装は存在するが本 HLD の記述と乖離。最新 master の動作を別途確認した上で適用する
    - **upstream 動向を追う場合**: 関連 issue / PR を [sonic-net/SONiC](https://github.com/sonic-net/SONiC) で検索（HLD タイトル / CONFIG_DB テーブル名 / Orch クラス名で grep するのが速い）
    - **代替手段 / 関連 reference**:
        - [CONFIG_DB: FLEX_COUNTER_TABLE](../reference/config-db/flex-counter-table.md)

!!! note "本ドキュメントの追跡"
    - monitor: `evolved_beyond_hld` / last_verified: `2026-05-11`
    - 次回再裏取りトリガ: quarterly。一覧は [discrepancy-index](../reference/verification/discrepancy-index.md) を参照（運用詳細は repo の `meta/discrepancy-operations.md`）

<!-- /next-action -->

<!-- glossary-links-injected: c006405759d8 -->
