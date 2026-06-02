---
title: SONiC Port Mirroring（SPAN / ERSPAN）
description: SONiC Port Mirroring（SPAN / ERSPAN） — SONiC の port mirroring 拡張。Port
  / Port-Channel 単位の ingress / egress / both SPAN、および ERSPAN（IP encapsulation）に対応する。
area: acl-qos
verification: code-verified
last_verified: 2026-05-11
sources:
- repo: sonic-net/SONiC
  path: doc/port-mirroring/SONiC_Port_Mirroring_HLD.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - MIRROR_SESSION
  - PORT
  - ACL_RULE
  - ACL_TABLE
  - PORT_QOS_MAP
  cli:
  - config mirror_session
  - show mirror_session
  - show interfaces
  - show acl
  - config acl
  yang:
  - sonic-mirror-session
  - sonic-port
  - sonic-port-qos-map
  - sonic-crm
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 07 章: ACL / CoPP / Mirror](../topics/07-acl-copp-mirror/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: code-verified（基本構成のみ）"
    現行 master の `sonic-swss/orchagent/mirrororch.cpp` に `MirrorOrch` クラス、SAI Mirror セッションの利用可能数取得 (`SAI_OBJECT_TYPE_MIRROR_SESSION` の object availability query, mirrororch.cpp:362) を確認。`sonic-utilities/config/main.py` の `mirror_session` グループ (3148-) と `validate_mirror_session_config`、`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mirror-session.yang` も存在。Mirror Capability Discovery 名（`MIRROR_SESSION_CAPABILITY` テーブル）は明示見つからず、object availability query API 経由で代替されている可能性あり。詳細フロー / SAI 属性マッピングは元 HLD 参照（verified at: 2026-05-09）。

# SONiC Port Mirroring（SPAN / ERSPAN）

## 概要

[SONiC](../reference/glossary.md#term-sonic) の port mirroring 拡張。Port / Port-Channel 単位の **ingress / egress / both** SPAN、および ERSPAN（IP encapsulation）に対応する[^1]。複数ソース・単一宛先の動的セッション管理、Port-Channel に対するセッションは少なくとも 1 メンバが UP のとき有効、を要件とする。

v0.2 では **Mirror Capability Discovery and Validation** が追加された（プラットフォームが対応する mirror モード・属性を [STATE_DB](../reference/glossary.md#term-state_db) に公開して上位が事前検証できるようにする仕組み）[^1]。

## 動作仕様

### 主要要件（要約）

- Port / Port-Channel の ingress / egress / both のミラー方向選択。
- **SPAN**: 同一スイッチ内ポートへのコピー。
- **ERSPAN**: 任意の IP 宛先への encapsulation 配送。
- 複数ソース → 単一宛先（many-to-one）。
- Port-Channel ソースは少なくとも 1 メンバ UP で有効化。
- 動的更新（メンバ追加・削除、宛先変更）。
- Capability Discovery: [ASIC](../reference/glossary.md#term-asic) ごとに対応モード/属性を STATE_DB に公開し、未対応モードの設定試行を早期に弾く。

### モジュール

```mermaid
flowchart LR
    CLI[config mirror_session] --> CDB[(CONFIG_DB MIRROR_SESSION)]
    CDB --> MM[MirrorMgr]
    MM --> ADB[(APPL_DB MIRROR_SESSION_TABLE)]
    ADB --> MO[MirrorOrch]
    MO --> ASIC[(ASIC: SAI_OBJECT_TYPE_MIRROR_SESSION)]
    MO --> SDB[(STATE_DB MIRROR_SESSION_TABLE)]
    CAP[Capability\n SAI query] --> SDB2[(STATE_DB MIRROR_CAPABILITIES)]
```

### CONFIG_DB スキーマ

```text
MIRROR_SESSION|<session_name>
    type            = "SPAN" | "ERSPAN"
    src_ip          = ipv4/v6      ; ERSPAN only
    dst_ip          = ipv4/v6      ; ERSPAN only
    gre_type        = uint16       ; ERSPAN only
    dscp            = uint8        ; ERSPAN only
    ttl             = uint8        ; ERSPAN only
    queue           = uint         ; ERSPAN only
    src_port        = comma-list   ; ingress/egress マッピング
    dst_port        = ifname       ; SPAN destination
    direction       = "rx" | "tx" | "both"
```

### Capability Discovery

`MIRROR_CAPABILITIES` テーブル（STATE_DB）に、プラットフォームでサポートされる mirror モードと属性を [syncd](../reference/glossary.md#term-syncd) 起動時に書き込み。`MirrorOrch` は新セッション作成前に capability を参照し、未対応モードを `MirrorMgr` に対してエラー返却する。

## 設定

### 関連する CONFIG_DB

| Table | 説明 |
|-------|------|
| `MIRROR_SESSION` | session 単位の SPAN/ERSPAN 定義 |

### 関連する CLI

```text
config mirror_session add <name> --type SPAN --src-port <p> --dst-port <p> --direction rx
config mirror_session add <name> --type ERSPAN --src-ip <ip> --dst-ip <ip> --gre-type <type> --src-port <p>
config mirror_session remove <name>
show mirror_session
```

### 設定例

```bash
sudo config mirror_session add MIR_SPAN1 \
    --type SPAN --src-port Ethernet0 --dst-port Ethernet48 --direction both
show mirror_session
```

## 制限事項

- Mirror セッション数の上限は ASIC 依存。Capability Discovery で取得する。
- Port-Channel 宛先は [HLD](../reference/glossary.md#term-hld) の主要対象ではない（ソースのみ Port-Channel 対応が明記）。
- Warm boot 影響は HLD 別節を参照。
- 詳細フロー / [SAI](../reference/glossary.md#term-sai) 属性マッピングは HLD `doc/port-mirroring/SONiC_Port_Mirroring_HLD.md` を参照。

## 干渉する機能

- **[ACL](../reference/glossary.md#term-acl) ベース mirror（Everflow）**: 別途 ACL ルールに `MIRROR` アクションを付ける機能があり、本ページの port-based mirror とは独立に動く。
- **Buffer / Egress queue**: ERSPAN は egress queue を消費する。輻輳時のミラー精度に影響。
- **Port-Channel メンバシップ変更**: メンバ全滅でセッションが down する。

## トラブルシューティング

- mirror が走らない → `show mirror_session` で `status: active` を確認、capability 未対応モード指定でないか確認。
- ERSPAN 受信側で抜ける → src_ip / dst_ip / gre_type の組み合わせを受信側 collector と合わせる。
- 一部メンバのみ反映される → Port-Channel メンバの oper-up を `show interfaces status` で確認。

### コマンド例: Port mirroring 確認

下記コマンドを順に実行することで、関連する [CONFIG_DB](../reference/glossary.md#term-config_db) / APP_DB / STATE_DB のエントリと、
CLI 表示・syslog の整合を一通り突き合わせ確認できる。

```bash
# Mirror session の状態と CONFIG_DB / STATE_DB を確認
show mirror_session
redis-cli -n 4 keys 'MIRROR_SESSION|*'
redis-cli -n 0 hgetall 'MIRROR_SESSION_TABLE|everflow0'
```


## 引用元

[^1]: `sonic-net/SONiC` `doc/port-mirroring/SONiC_Port_Mirroring_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: ACL / CoPP / Mirror / Packet Action](../topics/07-acl-copp-mirror/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: ec18b66e3507 -->
