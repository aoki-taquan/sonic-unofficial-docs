---
title: Egress Outer DSCP 書換 ACL（UNDERLAY_SET_DSCP / METADATA + EGR_SET_DSCP）
area: acl-qos
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/acl/egress_outer_dscp_change_table.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - ACL_TABLE
    - ACL_RULE
  cli:
    - config acl add table
  yang: []
---

!!! warning "裏取りステータス: HLD-only"
    `UNDERLAY_SET_DSCP` / `MARK_META` / `EGR_SET_DSCP` の AclOrch 内部展開、SAI metadata 属性の community SAI 取り込み、CLI の sonic-utilities 取り込みは未確認。

# Egress Outer DSCP 書換 ACL（UNDERLAY_SET_DSCP / METADATA + EGR_SET_DSCP）

## 概要

encapsulated 後の **outer header の DSCP を、inner header（元パケット L3 フィールド）の値に基づいて egress 段階で書き換える** ための ACL table type[^1]。Microsoft 提案、2024-07 初版。

既存の手段の限界:

- Ingress L3 ACL で DSCP を書き換えると **inner DSCP 自体が変わってしまう**（後段で復元できない）
- Tunnel encap 設定で inner→outer DSCP コピーは可能だが、書き換えの自由度が無い
- Egress L3 ACL は outer の DSCP を書けるが、**inner L3 フィールドにマッチできるかは ASIC 依存**

本 HLD は ASIC ハードウェア要件として `SAI_ACL_ENTRY_ATTR_ACTION_SET_ACL_META_DATA` と `SAI_ACL_ENTRY_ATTR_FIELD_ACL_USER_META` を使うことで、platform 中立な解を出す[^1]。

## 動作仕様

### 採用案: Option-C（dummy table → 内部展開）

3 案検討した上で、**Option-C** を推奨[^1]:

- ユーザは `UNDERLAY_SET_DSCP` / `UNDERLAY_SET_DSCPV6` という新 table type に rule を書くだけ
- AclOrch が内部で **`MARK_META` / `MARK_METAV6`（ingress, metadata 設定）** と **`EGR_SET_DSCP`（egress, metadata→DSCP）** に展開
- metadata 値の管理（衝突回避）は AclOrch が握る

```mermaid
flowchart LR
    USER[ユーザ ACL\nUNDERLAY_SET_DSCP rule\n(SRC_IP, ..., DSCP=v)] --> AO[AclOrch]
    AO -->|内部展開| ING[(MARK_META rule\nfield: SRC_IP\naction: SET_METADATA=N)]
    AO -->|内部展開| EGR[(EGR_SET_DSCP rule\nfield: ACL_USER_META=N\naction: SET_DSCP=v)]
    PKT[ingress pkt] --> ING
    ING -. metadata=N をパケットに付与 .-> EGR
    EGR --> ENC[encap 後の outer header DSCP=v]
```

### SAI 要件

- `SAI_ACL_ENTRY_ATTR_ACTION_SET_ACL_META_DATA`: ingress 段で metadata を打つ
- `SAI_ACL_ENTRY_ATTR_FIELD_ACL_USER_META`: egress 段で metadata でマッチする
- platform が両方サポートしていない場合、本 ACL table type は **作成不可**[^1]

### Capability の公開

`STATE_DB.ACL_ACTIONS` に `metadata range`（platform がサポートする値範囲）と capability を出す[^1]。CLI / orchagent が事前 check に使う。

### Match field

ユーザ ACL は標準 L3 IPv4 / IPv6 と同じ match セット（`MATCH_SRC_IP` / `DST_IP` / `IP_PROTOCOL` / `L4_SRC_PORT` / `L4_DST_PORT` / `TCP_FLAGS` / `DSCP`）。出力は `SET_DSCP`（outer に効く）[^1]。

### bind point

`PORT` / `LAG`。VLAN bind は HLD の表に無い[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/acl/egress_outer_dscp_change_table.md#L92-L102 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  Option-C: Create a dummy table type which translates into MARK_META/V6 and EGR_SET_DSCP as in the approach mentioned above. Manage the metadata internally
  ... requires ASICs to support the SAI_ACL_ENTRY_ATTR_ACTION_SET_ACL_META_DATA and SAI_ACL_ENTRY_ATTR_FIELD_ACL_USER_META fields.
reasoning: 採用案 Option-C と SAI 要件の根拠。
-->

## 設定

### 関連する CLI

| Command | 用途 |
|---------|------|
| `config acl add table <name> --stage egress --type UNDERLAY_SET_DSCP --ports ...` | テーブル作成（IPv4 用） |
| `config acl add table <name> --stage egress --type UNDERLAY_SET_DSCPV6 --ports ...` | IPv6 用 |

CLI 文法は HLD 例示。実装側で `--stage` の解釈差異がある可能性あり。

### 設定例

```json
{
  "ACL_TABLE": {
    "OUTER_DSCP_TBL": {
      "type": "UNDERLAY_SET_DSCP",
      "stage": "egress",
      "ports": ["Ethernet0", "Ethernet4"]
    }
  },
  "ACL_RULE": {
    "OUTER_DSCP_TBL|RULE_1": {
      "PRIORITY": "100",
      "SRC_IP": "10.0.0.0/24",
      "SET_DSCP": "46"
    }
  }
}
```

## 制限事項

- **SAI metadata 属性が必須**[^1]。未対応 platform では作成不可
- inner / outer の対象は encapsulated パケット限定。一般的な egress L3 ACL のように non-encap には掛けない設計
- metadata range は platform 依存。多数 rule が同 metadata 値で衝突しないよう AclOrch が管理する

## 干渉する機能

- **Tunnel encap orch**: encap で outer header を作るのは Tunnel 機能。本 ACL は encap 後に outer DSCP を上書きする位置づけ
- **既存 L3 ingress ACL の SET_DSCP**: inner DSCP を書き換える挙動なので併用注意
- **MARK_META / EGR_SET_DSCP table（内部）**: AclOrch が暗黙生成するため、ユーザは直接触らない

## トラブルシューティング

- table 作成失敗 → `STATE_DB.ACL_ACTIONS` で `SET_ACL_META_DATA` / `ACL_USER_META` capability を確認
- DSCP が変わらない → encap が egress の本 ACL より前に走っているか確認、ingress 側の MARK_META rule が hit しているか aclshow で確認

## 引用元

[^1]: `sonic-net/SONiC` `doc/acl/egress_outer_dscp_change_table.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- AclOrch 内部での UNDERLAY_SET_DSCP -> MARK_META + EGR_SET_DSCP 展開実装存在確認
- SAI_ACL_ENTRY_ATTR_ACTION_SET_ACL_META_DATA / FIELD_ACL_USER_META の community SAI 取り込み確認
- STATE_DB.ACL_ACTIONS の metadata capability 公開実装確認
- config acl add table CLI で type=UNDERLAY_SET_DSCP* を受け入れる sonic-utilities 取り込み確認
- sonic-yang-models 側の ACL_TABLE_TYPE への追加確認
- 提案 HLD（2024-07 初版）であり master 取り込み状況の確認
-->
