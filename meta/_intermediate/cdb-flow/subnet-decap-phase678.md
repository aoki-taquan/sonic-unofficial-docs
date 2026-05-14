# SUBNET_DECAP — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`tunnelmgrd` が `SUBNET_DECAP` テーブルを読み、サブネット decapsulation の設定を行う。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| IP-in-IP トンネル設定 | `SUBNET_DECAP` エントリ存在 | tunnelmgrd が対応するトンネルオブジェクトを作成 | `tunnelmgrd` |
| `src_ip` 取得 | `SUBNET_DECAP.key` のサブネット情報 | デカプセル化対象サブネットを設定 | `tunnelmgrd` |

**CONFIG_DB 内フィールド間の自動派生**: 特になし。YANG の `must` 制約による論理チェックのみ。

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `tunnelmgrd` は常時起動 | `SUBNET_DECAP` テーブルは無条件購読 | `tunnelmgrd` |
| `DEVICE_METADATA.subtype==DualToR` | SUBNET_DECAP が典型的に使われる構成 | `tunnelmgrd` |
| `ip_prefix_list` に指定サブネットが含まれない | デカプセル化ルールが適用されない | YANG `must` 制約 |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `tunnelmgrd` | `SUBNET_DECAP` エントリ追加 | IP-in-IP デカプセルトンネル作成 | `tunnelmgrd` |
| `tunnelmgrd` | `SUBNET_DECAP` エントリ削除 | 対応トンネル削除 | `tunnelmgrd` |
| `tunnelmgrd` | `ip_prefix_list` が空 | ログエラー + スキップ | `tunnelmgrd` |

> **スキャン証跡**: `SUBNET_DECAP` は主に DualToR 構成で使われる。tunnelmgrd 経由でサブネット decap トンネルを管理。CONFIG_DB 内の自動付与なし。
