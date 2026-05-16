# PORTCHANNEL_MEMBER ハードコード定数調査 (Phase E)

## 調査ソース

- `sonic-swss/orchagent/portsorch.cpp:8138-8172`
- `sonic-swss/orchagent/portsorch.cpp:8304-8338`
- `sonic-swss/orchagent/portsorch.cpp:6320-6350`

## ハードコード定数一覧

### SAI lag_member_attr — 作成時

| 定数名 | 値 | 定義箇所 | 用途 |
|---|---|---|---|
| `SAI_LAG_MEMBER_ATTR_LAG_ID` | SAI enum | `portsorch.cpp:8152` | `create_lag_member()` 呼び出し時に LAG OID を渡す必須属性 |
| `SAI_LAG_MEMBER_ATTR_PORT_ID` | SAI enum | `portsorch.cpp:8156` | `create_lag_member()` 呼び出し時に物理ポート OID を渡す必須属性 |
| `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` | `true` (ハードコード) | `portsorch.cpp:8162-8163` | `status != "enabled"` かつポートが SYSTEM 型でない場合、egress を無効化した状態で追加 |
| `SAI_LAG_MEMBER_ATTR_INGRESS_DISABLE` | `true` (ハードコード) | `portsorch.cpp:8166-8167` | 同上、ingress も無効化した状態で追加 |

### SAI lag_member_attr — 状態変更時

| 定数名 | 値 | 定義箇所 | 用途 |
|---|---|---|---|
| `SAI_LAG_MEMBER_ATTR_INGRESS_DISABLE` | `true` / `false` | `portsorch.cpp:8304` | `setCollectionOnLagMember()` / `setDistributionOnLagMember()` 経由で ingress 制御 |
| `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` | `true` / `false` | `portsorch.cpp:8335` | 同上、egress 制御 |

### status フィールド文字列定数 (APP_DB → SAI 変換)

| 文字列 | ハードコード判定 | 定義箇所 | 挙動 |
|---|---|---|---|
| `"enabled"` | `member_status == "enabled"` | `portsorch.cpp:8141` | `true` の場合、EGRESS_DISABLE / INGRESS_DISABLE を attrs に**追加しない**（forwarding 有効） |
| `"enabled"` 以外 | `member_status != "enabled"` | `portsorch.cpp:8160` | EGRESS_DISABLE=true + INGRESS_DISABLE=true を attrs に追加してメンバを無効状態で生成 |

## 補足

- `PORTCHANNEL_MEMBER` は CONFIG_DB では key-only テーブル（付加フィールドなし）。
  `status` フィールドは APP_DB の `LAG_MEMBER_TABLE` に存在し、orchagent がここを読んで SAI 属性を決定する。
- CONFIG_DB の PORTCHANNEL_MEMBER テーブル自体にはハードコード数値定数は存在しない。
  定数は orchagent が APP_DB → SAI 変換時に使用する SAI 属性 enum と、forwarding 制御の "enabled" 比較文字列のみ。
- `min_links` 等の LAG 全体に関わる定数は PORTCHANNEL テーブル (`portchannel-constants.md`) 参照。

## 結論

- `SAI_LAG_MEMBER_ATTR_LAG_ID` / `SAI_LAG_MEMBER_ATTR_PORT_ID` は LAG member 作成の必須 SAI 属性。
- `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` / `INGRESS_DISABLE` は、LACP ネゴシエーション前の forwarding 制御に使用。
  `"enabled"` 文字列との比較でハードコード分岐し、LACP が有効化するまでトラフィックをブロックする設計。
- PORTCHANNEL_MEMBER は key-only テーブルのため、CONFIG_DB レベルの数値定数・デフォルト値は存在しない。
