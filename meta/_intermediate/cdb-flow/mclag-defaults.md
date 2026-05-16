# Phase A — MCLAG_DOMAIN / MCLAG_INTERFACE デフォルト調査

## 対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mclag.yang`
- `sonic-swss/mclagsyncd/mclaglink.cpp`
- `sonic-swss/orchagent/mlagorch.cpp`

## MCLAG_DOMAIN フィールド別デフォルト

| フィールド | YANG default 文 | コード由来デフォルト | 出典 |
|-----------|----------------|---------------------|------|
| `domain_id` (key) | なし (必須) | — | sonic-mclag.yang L45-51 |
| `source_ip` | なし (必須) | — | sonic-mclag.yang L54-57 |
| `peer_ip` | なし (必須) | — | sonic-mclag.yang L58-61 |
| `peer_link` | なし (必須) | — | sonic-mclag.yang L62-72; mlagorch.cpp L85-91 で空文字列チェックあり(エラー) |
| `keepalive_interval` | **`default 1;`** | 省略時 = 1 秒; 空文字列時 = -1 (mclagsyncd 内部で iccpd への送信をスキップ) | sonic-mclag.yang L81; mclaglink.cpp L710-722 |
| `session_timeout` | **`default 30;`** | 省略時 = 30 秒; 空文字列時 = -1 (mclagsyncd 内部で iccpd への送信をスキップ) | sonic-mclag.yang L91; mclaglink.cpp L726-738 |

## MCLAG_INTERFACE フィールド別デフォルト

| フィールド | YANG default 文 | 備考 |
|-----------|----------------|------|
| `domain_id` (key) | なし (必須) | leafref → MCLAG_DOMAIN_LIST |
| `if_name` (key) | なし (必須) | leafref → PORTCHANNEL_LIST |
| `if_type` | なし | YANG type string; プレースホルダ用途。コード側で参照なし (mlagorch.cpp 全体) |

## MCLAG_UNIQUE_IP フィールド別デフォルト

| フィールド | YANG default 文 | 備考 |
|-----------|----------------|------|
| `if_name` (key) | なし (必須) | Vlan パターン制約 |
| `unique_ip` | なし | enum `enable` のみ。YANG コメント「by default disable」= エントリ不在が無効 |

## 結論

- `keepalive_interval` = **1** (YANG `default 1`) — YANG バリデーション段階で適用
- `session_timeout` = **30** (YANG `default 30`) — YANG バリデーション段階で適用
- `source_ip` / `peer_ip` / `peer_link` は必須フィールド（デフォルトなし）
- `if_type` はプレースホルダ; デフォルトなし・コード参照なし
- `unique_ip` のデフォルトは「エントリ削除 = 無効」; `enable` のみが有効値

## hard フラグ評価

`<!-- defaults -->` ブロックの `hard` は **0**（推奨値はすべて YANG `default` 文由来、ハードコード定数は iccpd デーモン内部値のみ）。
