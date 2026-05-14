# PREFIX_SET — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`frrcfgd` の `PrefixSetMgr` (sonic-mgmt-framework / sonic-routing-policy-sets) が `PREFIX_SET` テーブルを購読し、FRR の `ip prefix-list` / `ipv6 prefix-list` に変換する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| FRR コマンド種別 | `ip_prefix` に `:` 含む | `ipv6 prefix-list` コマンド | `frrcfgd prefix_set manager` |
| FRR コマンド種別 | `ip_prefix` に `.` 含む | `ip prefix-list` コマンド | `frrcfgd prefix_set manager` |

**CONFIG_DB 内フィールド間の自動派生なし**。FRR テキスト生成のみ。

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `frrcfgd` は常時起動 | `PrefixSetMgr` は無条件登録 | `frrcfgd/main.py` |
| sonic-mgmt-framework 非インストール時 | frrcfgd が存在しない → `PREFIX_SET` を消費するプロセスなし | build-time 依存 |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `PrefixSetMgr` | `ip_prefix` の形式 (IPv4/IPv6 判定) | `ip prefix-list` vs `ipv6 prefix-list` の切り替え | `frrcfgd` prefix_set manager |
| `PrefixSetMgr` | エントリ削除 (del_handler) | FRR に `no ip prefix-list` コマンド発行 | `frrcfgd` prefix_set manager |

> **スキャン証跡**: PREFIX_SET は BGP 汎用ルーティングポリシーセット用。frrcfgd 経由で FRR に設定。Config-DB 内フィールド間の自動派生なし。
