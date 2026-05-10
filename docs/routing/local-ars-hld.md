---
title: Local ARS（Adaptive Routing & Switching の local 完結版）
area: routing
verification: discrepancy-found
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/ARS/Local_ARS_HLD.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - ARS
    - ARS_PROFILE
    - ARS_INTERFACE
  cli:
    - config ars
    - show ars
  yang:
    - sonic-ars
---

!!! warning "裏取りステータス: discrepancy-found"
    Local ARS は AI/HPC 向けの adaptive routing 機能。

!!! note "Verifier 注記（2026-05-10）"
    実コード裏取り: 現行 master の `sonic-swss/orchagent/` には **`ArsOrch` 等の ARS 関連 orch 実装は確認できず**、`sonic-yang-models` にも `sonic-ars.yang` / `ARS_PROFILE` 等のスキーマは存在しない。`sonic-utilities` にも `config ars` / `show ars` は未取り込み。SAI 側は `sonic-sairedis/unittest/meta/TestMeta.cpp` に `SAI_OBJECT_TYPE_ARS` / `SAI_ARS_ATTR_*` の参照があり SAI API 自体は community SAI に取り込まれていることが確認できる。**HLD は提案段階で、SONiC SWSS / yang / utilities への取り込みは未完了**。本ページの記述は仕様意図の理解には有用だが、現行 master では機能として利用できない可能性が高い。

# Local ARS（Adaptive Routing & Switching の local 完結版）

## design 意図

Local ARS は ECMP の next-hop 選択を **静的ハッシュではなく、出力キューの瞬時負荷や link 利用率に応じて動的に変える** 機能[^1]。AI / HPC 向けに RDMA 通信の hot-spot を抑え、tail latency を低減することを狙う。

「Local」とは、**自スイッチ内の ASIC 観測値だけで判断** することを示す。複数ホップ協調の Global ARS は別テーマ。

## 動作仕様

```mermaid
flowchart LR
    PKT[ingress packet] --> HASH[既定 ECMP hash]
    HASH --> CHK{ARS profile\n適用 nexthop?}
    CHK -- no --> NORM[既定 next-hop]
    CHK -- yes --> ARS[ARS engine\n(出力 queue depth /\nport utilization 観測)]
    ARS --> SEL[next-hop 選択 reconsider]
    SEL --> EGR[egress port]
```

主要な構成要素[^1]:

- **ARS profile**: idle window / sample interval / quantization band / threshold 等のパラメータ束
- **ARS object（SAI）**: nexthop group や ECMP に紐づける ASIC 機能 object。SAI 側で `SAI_OBJECT_TYPE_ARS` 系拡張に対応
- **ARS interface**: per-egress-port の有効化と max load
- **flowlet 風挙動**: 同一フローでも idle window 後は別 path に切り替え可（ARS の本質）

### 主な CONFIG_DB

| Table | 説明 |
|-------|------|
| `ARS` | グローバル admin / モード（mode=`PER_FLOWLET_QUALITY` / `PER_PACKET_QUALITY` 等） |
| `ARS_PROFILE` | profile 名 ↔ パラメータ群 |
| `ARS_INTERFACE` | per-port enable / max_load |
| `ARS_NEXTHOP_GROUP_MAP` | nexthop group に profile を紐づけ（HLD 表現上） |

### 主な CLI

| Command | 用途 |
|---------|------|
| `config ars enable` | グローバル on |
| `config ars profile add <name> ...` | profile 定義 |
| `config ars interface enable <if>` | port で有効化 |
| `show ars` / `show ars profile` | 状態表示 |

## 制限事項

- **対応 ASIC のみ**: SAI ARS 拡張をサポートする NPU でのみ動く
- **Local 観測のみ**: 自スイッチを越えた congestion は見えないため、fabric の global view が必要なケースはカバー外
- **profile チューニング**: idle window / quantization の設定が不適切だと flapping や順序逆転を招く
- **ECMP との組み合わせ**: 既存 ECMP（policy-based hashing 等）と評価順序が衝突しないか注意

## 干渉する機能

- **inner packet hashing in ECMP**: ECMP ハッシュキー設定との組み合わせ
- **policy-based hashing**: フィールド指定ハッシュと ARS の動的選択の競合
- **fine-grained ECMP / weighted ECMP**: 重みづけ next-hop と ARS の relative priority
- **congestion control（PFC / ECN）**: ARS の判断材料となる出力 queue 観測

## トラブルシューティング

- 効果が出ない → `ARS_INTERFACE` の enable、profile 紐づけ、ARS 対応 ASIC かを確認
- 順序逆転 → idle window が小さすぎないか
- カウンタが進まない → `show ars` の active flowlet 数を確認、SAI debug counter で ARS reroute 統計を確認

## 引用元

[^1]: `sonic-net/SONiC` `doc/ARS/Local_ARS_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- SAI ARS 拡張 API（SAI_OBJECT_TYPE_ARS / SAI_ARS_ATTR_*）の community SAI 取り込み確認
- ARSOrch（または NextHopOrch 拡張）の現行実装存在確認
- CONFIG_DB ARS / ARS_PROFILE / ARS_INTERFACE スキーマの現行 sonic-yang-models 取り込み確認
- config ars / show ars CLI の sonic-utilities 取り込み確認
- 対応 ASIC platform リスト（特に AI cluster 向け NPU）の現行確認
- inner packet hashing / policy-based hashing / fine-grained ECMP との同居挙動確認
-->
