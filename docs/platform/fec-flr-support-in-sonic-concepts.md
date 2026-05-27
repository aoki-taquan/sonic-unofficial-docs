---
title: FEC FLR 概念（FLR / CER / interleaving / observed vs predicted）
description: FEC FLR (Frame Loss Ratio) 機能の概念整理。Codeword Error Ratio との関係、interleaving
  factor の役割、observed FLR と predicted FLR の使い分け、FEC counter から FLR を導出する基本式をまとめる。
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
  - ACL_RULE
  - ACL_TABLE
  - CHASSIS_MODULE
  - MID_PLANE_BRIDGE
  cli:
  - show techsupport
  - show platform
  - show version
  - show acl
  - config acl
  yang:
  - sonic-port
  - sonic-crm
  - sonic-system-defaults
---

# FEC FLR 概念（FLR / CER / interleaving / observed vs predicted）

このページは [FEC FLR Support in SONiC（概要ハブ）](fec-flr-support-in-sonic.md) の派生ページで、**概念・指標・公式** に絞って整理する。[CONFIG_DB](../reference/glossary.md#term-config_db) / CLI / 確認手順は [fec-flr-support-in-sonic-operations.md](fec-flr-support-in-sonic-operations.md)、`port_flr.lua` プラグインと FlexCounterOrch の内部実装は [fec-flr-support-in-sonic-internals.md](fec-flr-support-in-sonic-internals.md)、制限事項は [fec-flr-support-in-sonic-limitations.md](fec-flr-support-in-sonic-limitations.md) を参照。

## 1. FLR の定義

`Frame Loss Ratio (FLR)` は **送信フレームに対する欠落フレームの割合** で、リンク品質の代表指標[^1]:

```text
FLR = (Total TX Frames - Total RX Frames) / Total TX Frames
```

実回線で TX と RX 両端を直接突合するのは難しいので、FEC 層の codeword 統計から **推定** するのが [SONiC](../reference/glossary.md#term-sonic) の FEC FLR 機能の本質。

## 2. CER と FLR の関係

物理層で観測可能なのは Codeword Error Ratio (CER):

```text
CER = (uncorrectable codeword 数) / (全 codeword 数)
```

RS-544 系 FEC の場合、1 codeword あたりの最大フレーム数 MFC = 8 と、interleaving factor X から FLR を導出できる[^1]:

```text
FEC_FLR = CER * (1 + X * MFC) / MFC
RS-544: MFC = 8
  X=1 → FLR = 1.125 * CER
  X=2 → FLR = 2.125 * CER
  X=4 → FLR = 4.125 * CER
```

## 3. interleaving factor X

X は **複数 codeword を時間軸で交織し、バーストエラーを 1 codeword に集中させない** ための係数。port speed × lane 数で決まる固定テーブルが [HLD](../reference/glossary.md#term-hld) に示されている[^1]:

| Speed | Lanes | X |
|-------|-------|---|
| 1600G | 8 | 4 |
| 800G  | 8 | 4 |
| 400G  | 8 | 2 |
| 400G  | 4 | 2 |
| 200G  | 4 | 2 |
| 200G  | 2 | 2 |
| 100G  | 2 | 2 |
| 100G  | 1 | 1 or 2 (autoneg) |

理想的には [SAI](../reference/glossary.md#term-sai) 属性で取得したいが新 SAI 属性が無いため、当面は表で代替する設計[^1]。

## 4. Observed FLR と Predicted FLR

- **Observed FLR (`FLR(O)`)**: 直近 interval の CER 実測値から導出。エラーがほぼ無い健全なリンクでは `0` に張り付きやすい。
- **Predicted FLR (`FLR(P)`)**: codeword に含まれる symbol error 分布 (`S0..S15`) の対数線形回帰で **16–20 symbol errors の領域を外挿** した CER から導出。健全なリンクでも低 BER 領域での将来予測ができる。

Predicted は **外挿** に過ぎず、低 BER 域での実測 FLR と乖離する可能性はあるが、劣化傾向の早期検知に有効[^1]。

## 5. 計算周期の考え方

`port_flr.lua` は既存 `PORT_STAT_COUNTER_FLEX_COUNTER_GROUP` のプラグインとして動作し、計算周期は HLD 上は次式で決まる[^1]:

```text
interval = port_stat POLL_INTERVAL * FLR_INTERVAL_FACTOR
```

デフォルト `FLR_INTERVAL_FACTOR = 120`。port_stat の poll を 1 秒で回している場合、FLR は 120 秒ごとに更新される。

> 実装では `FLR_INTERVAL_FACTOR` は lua 内ハードコードで動的変更できない（詳細は [limitations](fec-flr-support-in-sonic-limitations.md) 参照）。

## 関連ページ

- [FEC FLR Support in SONiC（概要ハブ）](fec-flr-support-in-sonic.md) — 元 HLD ページ
- [fec-flr-support-in-sonic-operations.md](fec-flr-support-in-sonic-operations.md) — 設定 / CLI / 確認手順
- [fec-flr-support-in-sonic-internals.md](fec-flr-support-in-sonic-internals.md) — `port_flr.lua` / FlexCounterOrch の内部
- [fec-flr-support-in-sonic-limitations.md](fec-flr-support-in-sonic-limitations.md) — 制限事項と HLD との乖離

## 制限事項

概念レベルでの読み手向け前提条件。実装側の詳細制限は [limitations](fec-flr-support-in-sonic-limitations.md) を参照。

- **FLR は確率指標であって実観測ではない**: Predicted FLR は CER (Codeword Error Rate) と interleaving factor `X` から外挿される値。実トラフィックに直接観測される frame loss とは値域が一致しない。
- **CER → FLR 変換は [ASIC](../reference/glossary.md#term-asic) ベンダ依存**: interleaving factor `X` はポート速度・レーン数で決まり、HLD 定義では 1〜4 の範囲（100G×1lane が 1 or 2、400G 以上が 2 or 4）。ベンダ仕様を取らずに公開値だけで他機種と比較しない。
- **計算周期は秒オーダ**: 短時間バースト (ms オーダ) の劣化は `FLR(O)` には反映されにくく、`FLR(P)` の経時変化として遅れて見える。リアルタイム障害検知用ではなく、劣化傾向検知用と理解する。
- **低 BER 領域の `Accuracy` 低下**: errored codeword サンプル数が少ない健全リンクでは R² (Accuracy 列) が下がり、`FLR(P)` の絶対値の信頼性が落ちる。健全時の値はベースラインとしてのみ扱う。
- **`FLR(P)` ≪ `FLR(O)` の領域は外挿が破綻**: Observed が立った時点で外挿モデルの仮定 (低 BER) を超えており、Predicted を運用判断に使うべきではない。

## 確認コマンド

概念ページの値が master 上の実数値と整合しているかを確認するための最小コマンド
セット。`FLR(O)` / `FLR(P)` / interleaving factor `X` のいずれが NA か / 0 か /
高い値かを切り分けるのに使う。

```bash
# 1. portstat で FLR(O) / FLR(P) / Accuracy 列を観測（-f で raw / 通常で human）
show interfaces counters -f | awk 'NR<=2 || /FLR/'
show interfaces counters | head -3

# 2. SAI レベル: S0..S16 (symbol error bin) が COUNTER_DB に流れているか
redis-cli -n 2 hkeys 'COUNTERS:oid:0x10000000000XX' | grep -E 'FEC_CODEWORD_ERRORS_S' | head

# 3. lua 計算ロジックの実体（interleaving factor X / BIN_FILTER_VALUE）
docker exec swss head -50 /usr/share/swss/port_flr.lua
```

`N/A` が出る場合は [ASIC SDK](../reference/glossary.md#term-asic-sdk) が `SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_Sn` を
サポートしていない可能性が高い。S0..S16 のうち 1 つでも非ゼロが出ていれば
概念ページの計算式が回っている。

## 実装との乖離

`monitor: evolved_beyond_hld` — `monitor: evolved_beyond_hld` の HLD と実装の差分。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [FEC FLR 概念 親ページ](fec-flr-support-in-sonic.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

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

<!-- glossary-links-injected: ec18b66e3507 -->
