---
title: Reclaim Reserved Buffer（admin-down ポートの zero_profile）
description: Reclaim Reserved Buffer（admin-down ポートの zero_profile） — Mellanox プラットフォームで顕著な「admin-down
  ポートにも default で reserved buffer が割り当てられ、shared pool が圧迫される」問題に対し、zero_…
area: acl-qos
verification: code-verified
last_verified: 2026-05-11
sources:
- repo: sonic-net/SONiC
  path: doc/qos/reclaim-reserved-buffer.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - BUFFER_PG
  - BUFFER_QUEUE
  - BUFFER_PROFILE
  - BUFFER_POOL
  - BUFFER_PORT_INGRESS_PROFILE_LIST
  - BUFFER_PORT_EGRESS_PROFILE_LIST
  - PFC_WD
  cli:
  - config interface
  - config buffer
  - show buffer
  - show buffer pool
  - show pfc
  yang:
  - sonic-buffer-profile
  - sonic-buffer-pool
  - sonic-buffer-pg
  - sonic-buffer-queue
  - sonic-pfc-priority-priority-group-map
  - sonic-pfc-priority-queue-map
  - sonic-crm
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 08 章: QoS / Buffer / PFC](../topics/08-qos-buffer/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: code-verified (2026-05-11)"
    `zero_profile` 機構は `sonic-swss/cfgmgr/buffermgrdyn.cpp` L232-L260 のドキュメントコメントブロックで全体設計 (zero buffer pools / profiles, `pgs_to_apply_zero_profile`, `ingress_zero_profile`, `queues_to_apply_zero_profile`, `egress_zero_profile`, `zero_profile_name`) が記述され、L245-L275 で実装ロジックが取り込まれていることを確認（既存 verifier の `reclaim-reserved-buffer-sequence-flow` キューでも同位置を裏取り済み）。`buffermgrd -z zero_profiles.json` 起動オプションは `buffermgrd.cpp` L26 / L98-L121 で確認。

# Reclaim Reserved Buffer（admin-down ポートの zero_profile）

## 概要

Mellanox プラットフォームで顕著な「admin-down ポートにも default で reserved buffer が割り当てられ、shared pool が圧迫される」問題に対し、**`zero_profile` を admin-down ポートに明示的に紐付け、reserved buffer をゼロ化して shared pool に取り戻す** 設計[^1]。

対象は次の [SONiC](../reference/glossary.md#term-sonic) buffer config 全体[^1]:

- `BUFFER_PG`
- `BUFFER_QUEUE`
- `BUFFER_PORT_INGRESS_PROFILE_LIST` / `BUFFER_PORT_EGRESS_PROFILE_LIST`

ポートの admin-down 契機は 2 通り[^1]:

1. deployment で利用しないポート（INACTIVE port）
2. メンテナンスのため一時的 shut down

両方で reclaim が走る。

## 動作仕様

### 「単純削除」では起きる不整合

最初に思いつくのは「admin-down ポートの [BUFFER_PG](../reference/glossary.md#term-buffer-pg) / BUFFER_QUEUE エントリを削除する」だが、[HLD](../reference/glossary.md#term-hld) はこれを否定する。[SAI](../reference/glossary.md#term-sai) / SDK は **「設定が無いとき = SDK default 値（一部は非ゼロ）」** であり、設定削除（`SAI_NULL_OBJECT_ID`）すると **0 にリセット** される。結果、

- 起動時設定なし → SDK default（非ゼロ）
- 起動後に削除 → 0

という同じ「設定なし」状態で [ASIC](../reference/glossary.md#term-asic) 側が異なる、という不整合になる[^1]。

### `zero_profile` 解（採用）

```mermaid
flowchart LR
    PORT[port admin-down] --> BMGR[BufferManager]
    BMGR -->|profile <- zero_profile| PG[(BUFFER_PG zero_profile)]
    BMGR -->|profile <- zero_profile| Q[(BUFFER_QUEUE zero_profile)]
    BMGR -->|list <- zero_profile_list| LIST[(BUFFER_PORT_INGRESS / EGRESS\nPROFILE_LIST)]
    PG --> APPL[(APPL_DB)]
    Q --> APPL
    LIST --> APPL
    APPL --> BORCH[buffer orchagent]
    BORCH --> SAI[(SAI buffer\nsize/threshold = 0)]
```

`zero_profile` の中身（Mellanox 例）:

| 対象 | profile mode | 値 |
|------|-------------|---|
| Lossy PG | static threshold | `static_th = 0`, `size = 0`、`zero_pool` に紐付け（pool size 0） |
| Queue / Profile list | dynamic threshold | `size = 0` |
| Lossless PG | （profile を当てず）SAI から完全に削除する |

**lossless PG** は zero_profile ではなく **SAI から完全削除**。`SAI_NULL_OBJECT_ID` で削除しても結果が 0 になる対象（HLD 引用部）であるため[^1]。

### 起動条件

- **traditional buffer model**: deployment 時に未使用ポートが分かっていれば最初から `zero_profile` 適用。途中で `config interface shutdown` した場合は user の責任で profile 適用[^1]
- **dynamic buffer model**: 未使用ポートが 1 つでもあれば `zero_profile` を `APPL_DB` に push。ランタイムで buffer manager が自動 toggle

### Database migrator

旧イメージから upgrade した system に対し、`db_migrator` が admin-down ポートの BUFFER 設定を `zero_profile` 紐付けに書き換える[^1]。

### Vendor 別

zero_profile を template で提供している vendor のみ採用。それ以外は HLD のいう「buffer 設定削除」方式に従う（不整合は受け入れる）[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/qos/reclaim-reserved-buffer.md#L66-L96 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  - For lossless buffer priority groups, SONiC should remove them from SAI when the port is admin down.
  - For other buffer objects: Introduce a new type of buffer profiles - `zero profile`.
reasoning: lossless PG は削除、それ以外は zero_profile という分担の根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/qos/reclaim-reserved-buffer.md#L66-L96 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/qos/reclaim-reserved-buffer.md#L66-L96 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    - For lossless buffer priority groups, SONiC should remove them from SAI when the port is admin down.
    - For other buffer objects: Introduce a new type of buffer profiles - `zero profile`.
    ```

    **判断根拠**: lossless PG は削除、それ以外は zero_profile という分担の根拠。

<!-- evidence-rendered:end -->

## 設定

### CLI

HLD 内で reclaim 専用の CLI 言及は無い。`config interface shutdown` / `startup` のフックとして buffer manager が自動で `zero_profile` を着脱する設計[^1]。

### CONFIG_DB

`zero_profile` 系は **テンプレート（buffers_config.j2）に同梱** される vendor 提供データ。[CONFIG_DB](../reference/glossary.md#term-config_db) に手書きする運用は想定されない。

## 制限事項

- **vendor が zero_profile テンプレートを提供している platform 限定**[^1]
- traditional buffer model でランタイム shutdown した場合、user 側で profile を当てる必要あり
- shared headroom pool model など vendor 固有の buffer model 差異がそのまま zero_profile 定義に反映される

## 干渉する機能

- **Dynamic Buffer Calculation**: 同じ buffer manager が司る。dynamic mode では shutdown 時の自動 reclaim が標準動作になる
- **db_migrator**: 旧 image からの upgrade 時に admin-down ポートを zero_profile に置換
- **[PFC](../reference/glossary.md#term-pfc) / lossless**: lossless PG は zero_profile ではなく削除なので、enable し直しの順序に注意

## トラブルシューティング

- shared pool が増えない → admin-down ポートの BUFFER_PG / BUFFER_QUEUE に zero_profile が当たっているか [APPL_DB](../reference/glossary.md#term-appl_db) で確認
- lossless トラフィックが落ちる → admin-down 後 admin-up した際の lossless PG 再作成順序を確認

### コマンド例: Reserved buffer reclaim 確認

下記コマンドを順に実行することで、関連する CONFIG_DB / APP_DB / [STATE_DB](../reference/glossary.md#term-state_db) のエントリと、
CLI 表示・syslog の整合を一通り突き合わせ確認できる。

```bash
# 各ポートの shutdown 状態と buffer profile 適用状況
show interfaces status
show buffer pool
redis-cli -n 4 keys 'BUFFER_PG|Ethernet*' | head
# buffermgrd ログ
sudo grep -i 'buffermgrd' /var/log/syslog | tail -30
```

## 裏取り済み実装位置 (2026-05-11)

- 設計コメント＋実装本体: `sonic-swss/cfgmgr/buffermgrdyn.cpp` L232-L275（`pgs_to_apply_zero_profile` / `ingress_zero_profile` / `queues_to_apply_zero_profile` / `egress_zero_profile` のパースとプール referenced 時の `zero_profile_name` 紐付け）
- `buffermgrd` 起動オプション: `sonic-swss/cfgmgr/buffermgrd.cpp` L26, L98-L121（`-z zero_profiles.json` の読込）
- 派生ページの裏取り: `docs/acl-qos/reclaim-reserved-buffer-sequence-flow.md`（既に code-verified）と整合

## 引用元

[^1]: `sonic-net/SONiC` `doc/qos/reclaim-reserved-buffer.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- buffermgrd の admin-down hook で zero_profile を APPL_DB に push する実装存在確認
- BUFFER_PG / BUFFER_QUEUE / BUFFER_PORT_*_PROFILE_LIST の YANG 取り込み確認（zero_profile 受け入れ）
- db_migrator の admin-down ポート処理ロジック実装確認
- Mellanox SAI 側で zero_pool / zero profile を受けて size=0 になる挙動確認
- vendor 別実装差異（zero_profile 提供の有無）の現行 sonic-buildimage 内ベンダーディレクトリ確認
- shared headroom pool model など複数 buffer model における zero_profile 互換性確認
-->

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: ec18b66e3507 -->
