# PREFIX_LIST — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`bgpcfgd` の `PrefixListMgr` は CONFIG_DB から `PREFIX_LIST` エントリを読み、FRR の `ip prefix-list` / `ipv6 prefix-list` コマンドに変換して `vtysh` 経由で送信する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| FRR コマンド種別 | `family==IPv6` または `ip-prefix` に `:` 含む | `ipv6 prefix-list` コマンド生成 | `managers_prefix_list.py` |
| FRR コマンド種別 | `family==IPv4` または `ip-prefix` に `.` 含む | `ip prefix-list` コマンド生成 | `managers_prefix_list.py` |
| `ipv4_name` / `ipv6_name` | constants に `bgp.prefix_list.<type>.ipv4_name` あり | constants 値でリスト名を上書き | `managers_prefix_list.py` |

**自動派生なし (CONFIG_DB 内フィールド間)**: `PREFIX_LIST` テーブル内で他フィールドへの自動付与はない。FRR 向けテキスト生成のみ。

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `bgpcfgd` は常時起動 (platform 非依存) | `PrefixListMgr` は無条件登録 | `bgpcfgd/main.py` |
| `DEVICE_METADATA|localhost` 未存在 | `bgp_asn` / `type` キーが取得できずリトライ待ちになる | `managers_prefix_list.py` |
| `prefix_type` が `ANCHOR_PREFIX` + デバイスタイプが SpineRouter/UpperSpineRouter 以外 | `log_warn` してスキップ (FRR 設定せず) | `managers_prefix_list.py` |

## Phase 8: Handler メソッド内分岐

`PrefixListMgr` の `set_handler` 内で以下の分岐がある。

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `PrefixListMgr` | `prefix_type` が `ANCHOR_PREFIX`/`SUPPRESS_PREFIX` 以外 | `log_warn` + return (FRR 設定スキップ) | `managers_prefix_list.py` |
| `PrefixListMgr` | `family==IPv6` | `ipv6 prefix-list` コマンド生成 | `managers_prefix_list.py` |
| `PrefixListMgr` | `family==IPv4` | `ip prefix-list` コマンド生成 | `managers_prefix_list.py` |
| `PrefixListMgr` | `netaddr.IPNetwork()` 解析失敗 | `log_warn` + return True (エントリスキップ) | `managers_prefix_list.py` |
| `PrefixListMgr` | `ANCHOR_PREFIX` + SpineRouter/UpperSpineRouter 以外 | `log_warn` + skip | `managers_prefix_list.py` |

> **スキャン証跡**: `managers_prefix_list.py` 全体読了。CONFIG_DB 内フィールド間の自動派生なし（Phase 6 は FRR テキスト変換のみ）。Phase 7 は DEVICE_METADATA 依存のみ。
