---
title: SONiC Port Mirroring（SPAN / ERSPAN）
description: SONiC Port Mirroring（SPAN / ERSPAN） — Port / Port-Channel 単位の ingress
  / egress / both SPAN、および ERSPAN（IP encapsulation）に対応する port mirroring 機能の HLD と現行
  master 実装の対応関係をまとめる。
area: acl-qos
verification: code-verified
last_verified: 2026-06-06
sources:
- repo: sonic-net/SONiC
  path: doc/port-mirroring/SONiC_Port_Mirroring_HLD.md
  ref: fcf0848bcc6282434e6a3e0b86dd3ee7043db291
- repo: sonic-net/sonic-swss
  path: orchagent/switchorch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-utilities
  path: config/main.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
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

!!! success "裏取りステータス: code-verified"
    現行 master の `sonic-swss/orchagent/mirrororch.cpp` に `MirrorOrch` クラス、SAI Mirror セッションの object availability query (`SAI_OBJECT_TYPE_MIRROR_SESSION`) を確認。`sonic-utilities/config/main.py` の `mirror_session` グループと `validate_mirror_session_config`、`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mirror-session.yang` も存在。Capability Discovery は当初 v0.2 HLD で示された `MIRROR_CAPABILITIES` ではなく、現行実装では `SwitchOrch::querySwitchPortMirrorCapability()` が `STATE_DB SWITCH_CAPABILITY|switch` テーブルに `PORT_INGRESS_MIRROR_CAPABLE` / `PORT_EGRESS_MIRROR_CAPABLE` フィールドとして書き込む形に集約されている[^2][^3]。本ページはこの実装側の名称を採用する（verified at: 2026-06-06）。

# SONiC Port Mirroring（SPAN / ERSPAN）

## 概要

[SONiC](../reference/glossary.md#term-sonic) の port mirroring 拡張。Port / Port-Channel 単位の **ingress / egress / both** SPAN、および ERSPAN（IP encapsulation）に対応する[^1]。複数ソース・単一宛先の動的セッション管理、Port-Channel に対するセッションは少なくとも 1 メンバが UP のとき有効、を要件とする。

v0.2 では **Mirror Capability Discovery and Validation** が追加された（プラットフォームが対応する mirror モード・属性を [STATE_DB](../reference/glossary.md#term-state_db) に公開して上位が事前検証できるようにする仕組み）[^1]。現行 master では HLD 当初案の `MIRROR_CAPABILITIES` 単独テーブルではなく、`SwitchOrch` が一元管理する `SWITCH_CAPABILITY|switch` テーブルにフィールドとして書き込む形で実装されている[^2]。

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
    SO[SwitchOrch\n sai_query_attribute_capability] --> SDB2[(STATE_DB SWITCH_CAPABILITY\|switch)]
    SDB2 -.参照.-> CFG[config mirror_session\n is_port_mirror_capability_supported]
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

HLD v0.2 当初案では `MIRROR_CAPABILITIES` という独立テーブルが提案されていたが、現行 master 実装は `SwitchOrch` が一元管理する `STATE_DB SWITCH_CAPABILITY|switch` テーブルにフィールドとして格納する[^2]。

| STATE_DB エントリ | フィールド | 値 | 書き込み元 |
|------------------|-----------|----|----------|
| `SWITCH_CAPABILITY\|switch` | `PORT_INGRESS_MIRROR_CAPABLE` | `"true"` / `"false"` | `SwitchOrch::querySwitchPortMirrorCapability()` |
| `SWITCH_CAPABILITY\|switch` | `PORT_EGRESS_MIRROR_CAPABLE` | `"true"` / `"false"` | 同上 |

`SwitchOrch` は [orchagent](../reference/glossary.md#term-orchagent) 起動時に `sai_query_attribute_capability(SAI_OBJECT_TYPE_PORT, SAI_PORT_ATTR_INGRESS_MIRROR_SESSION / SAI_PORT_ATTR_EGRESS_MIRROR_SESSION)` を呼び、`set_implemented` の結果を `"true"` / `"false"` の文字列として書き込む。SAI query 自体が失敗した場合は後方互換のためデフォルト `"true"` を入れる[^2]。

`config mirror_session add` 側（CLI）は SPAN セッション作成時に `is_port_mirror_capability_supported(direction)` でこのテーブルを参照し、`direction` が `rx` / `tx` / `both` のいずれかに応じて対応するフィールドを check する。キー欠落（None）は「未公開プラットフォーム」として **supported とみなす**（後方互換）、明示 `"false"` のみ拒否する[^3]。ERSPAN セッションには本 capability check は適用されない。

<!-- evidence:
source: sonic-swss/orchagent/switchorch.cpp#L1903-L1957 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
excerpt: |
  void SwitchOrch::querySwitchPortMirrorCapability() {
    status = sai_query_attribute_capability(gSwitchId, SAI_OBJECT_TYPE_PORT,
                            SAI_PORT_ATTR_INGRESS_MIRROR_SESSION, &capability);
    ...
    fvVector.emplace_back(SWITCH_CAPABILITY_TABLE_PORT_INGRESS_MIRROR_CAPABLE, "true");
    ...
    set_switch_capability(fvVector);
  }
reasoning: 現行 master は MIRROR_CAPABILITIES ではなく SWITCH_CAPABILITY|switch テーブルにフィールド形式で capability を書く。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-swss/orchagent/switchorch.cpp#L1903-L1957 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)"

    **出典**:

    `sonic-swss/orchagent/switchorch.cpp#L1903-L1957 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)`

    **抜粋**:

    ```text
    void SwitchOrch::querySwitchPortMirrorCapability() {
      status = sai_query_attribute_capability(gSwitchId, SAI_OBJECT_TYPE_PORT,
                              SAI_PORT_ATTR_INGRESS_MIRROR_SESSION, &capability);
      ...
      fvVector.emplace_back(SWITCH_CAPABILITY_TABLE_PORT_INGRESS_MIRROR_CAPABLE, "true");
      ...
      set_switch_capability(fvVector);
    }
    ```

    **判断根拠**: 現行 master は MIRROR_CAPABILITIES ではなく SWITCH_CAPABILITY|switch テーブルにフィールド形式で capability を書く。

<!-- evidence-rendered:end -->

<!-- evidence:
source: sonic-utilities/config/main.py#L1290-L1316 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  def is_port_mirror_capability_supported(direction, namespace=None):
      entry_name = "SWITCH_CAPABILITY|switch"
      directions_to_check = []
      if not direction or direction in ['rx', 'both']:
          directions_to_check.append("PORT_INGRESS_MIRROR_CAPABLE")
      if not direction or direction in ['tx', 'both']:
          directions_to_check.append("PORT_EGRESS_MIRROR_CAPABLE")
      for capability_key in directions_to_check:
          value = state_db.get(state_db.STATE_DB, entry_name, capability_key)
          if value is not None and value != "true":
              return False
      return True
reasoning: CLI 側は同じ SWITCH_CAPABILITY|switch を読み、SPAN direction に応じて事前検証する。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-utilities/config/main.py#L1290-L1316 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)"

    **出典**:

    `sonic-utilities/config/main.py#L1290-L1316 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)`

    **抜粋**:

    ```text
    def is_port_mirror_capability_supported(direction, namespace=None):
        entry_name = "SWITCH_CAPABILITY|switch"
        directions_to_check = []
        if not direction or direction in ['rx', 'both']:
            directions_to_check.append("PORT_INGRESS_MIRROR_CAPABLE")
        if not direction or direction in ['tx', 'both']:
            directions_to_check.append("PORT_EGRESS_MIRROR_CAPABLE")
        for capability_key in directions_to_check:
            value = state_db.get(state_db.STATE_DB, entry_name, capability_key)
            if value is not None and value != "true":
                return False
        return True
    ```

    **判断根拠**: CLI 側は同じ SWITCH_CAPABILITY|switch を読み、SPAN direction に応じて事前検証する。

<!-- evidence-rendered:end -->

なお `MirrorOrch` 自体は SAI Mirror セッションの **数量** capability を `SAI_OBJECT_TYPE_MIRROR_SESSION` の object availability query で取得しており、port 属性 capability とは別経路で扱われる。

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
# Mirror session の状態と CONFIG_DB / APPL_DB を確認
show mirror_session
redis-cli -n 4 keys 'MIRROR_SESSION|*'
redis-cli -n 0 hgetall 'MIRROR_SESSION_TABLE|everflow0'

# プラットフォームの port mirror capability を STATE_DB で確認
redis-cli -n 6 hgetall 'SWITCH_CAPABILITY|switch' | grep -i mirror
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/port-mirroring/SONiC_Port_Mirroring_HLD.md` @ `fcf0848bcc6282434e6a3e0b86dd3ee7043db291`
[^2]: `sonic-net/sonic-swss` `orchagent/switchorch.cpp` `querySwitchPortMirrorCapability()` L1903-L1957 @ `4305596156d70e9797e8a881b3d19b46de0bce0d`、定数定義は `orchagent/switchorch.h` L34-L35
[^3]: `sonic-net/sonic-utilities` `config/main.py` `is_port_mirror_capability_supported()` L1290-L1316 @ `39732bceb8bdefe706518ab40623bbbba6ff33b9`

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: ACL / CoPP / Mirror / Packet Action](../topics/07-acl-copp-mirror/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: e2892b76fd9a -->
