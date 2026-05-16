# BGP_AGGREGATE_ADDRESS — Phase E: ハードコード定数調査

## 調査対象ファイル

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_aggregate_address.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-aggregate-address.yang`

---

## ハードコード定数一覧

### CONFIG_DB / STATE_DB キー文字列リテラル（bgpcfgd）

`managers_aggregate_address.py:9-20` で module-level の定数として定義。CONFIG_DB のフィールド名・STATE_DB 状態値はここに集約され、ハンドラ全体で参照される。

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `CONFIG_DB_NAME` | `"CONFIG_DB"` | directory subscribe 対象 DB 名 | `managers_aggregate_address.py:9` |
| `BGP_AGGREGATE_ADDRESS_TABLE_NAME` | `"BGP_AGGREGATE_ADDRESS"` | CONFIG_DB / STATE_DB テーブル名 | `managers_aggregate_address.py:10` |
| `BBR_REQUIRED_KEY` | `"bbr-required"` | フィールド名 | `managers_aggregate_address.py:11` |
| `AS_SET_KEY` | `"as-set"` | フィールド名 / FRR キーワード | `managers_aggregate_address.py:12` |
| `SUMMARY_ONLY_KEY` | `"summary-only"` | フィールド名 / FRR キーワード | `managers_aggregate_address.py:13` |
| `AGGREGATE_ADDRESS_PREFIX_LIST_KEY` | `"aggregate-address-prefix-list"` | フィールド名 | `managers_aggregate_address.py:14` |
| `CONTRIBUTING_ADDRESS_PREFIX_LIST_KEY` | `"contributing-address-prefix-list"` | フィールド名 | `managers_aggregate_address.py:15` |
| `COMMON_TRUE_STRING` | `"true"` | bool 真値リテラル | `managers_aggregate_address.py:16` |
| `COMMON_FALSE_STRING` | `"false"` | bool 偽値リテラル / 全フィールドの暗黙デフォルト | `managers_aggregate_address.py:17` |
| `ADDRESS_STATE_KEY` | `"state"` | STATE_DB の state フィールド名 | `managers_aggregate_address.py:18` |
| `ADDRESS_ACTIVE_STATE` | `"active"` | STATE_DB state 値（FRR 投入成功時） | `managers_aggregate_address.py:19` |
| `ADDRESS_INACTIVE_STATE` | `"inactive"` | STATE_DB state 値（バリデーション失敗・BBR 不整合・FRR push 失敗） | `managers_aggregate_address.py:20` |

### FRR vtysh コマンドリテラル（bgpcfgd 生成）

`generate_aggregate_address_commands()` (`managers_aggregate_address.py:239-252`) と `generate_prefix_list_commands()` (`managers_aggregate_address.py:255-264`) が FRR vtysh コマンド文字列をハードコード生成する。

| コマンド断片 | 値 | 出現コンテキスト | ソース |
|---|---|---|---|
| BGP インスタンス入り口 | `"router bgp %s"` (asn 埋め込み) | aggregate コマンド前段 | `managers_aggregate_address.py:241` |
| IPv4 address-family | `"address-family ipv4"` | `net.version == 4` 時 | `managers_aggregate_address.py:242` |
| IPv6 address-family | `"address-family ipv6"` | それ以外 | `managers_aggregate_address.py:242` |
| 集約コマンド本体 | `"aggregate-address %s"` (prefix 埋め込み) | set / del 共通（del 時は `"no "` プレフィクス） | `managers_aggregate_address.py:243-244` |
| `summary-only` 接尾辞 | `" summary-only"` | `summary_only == "true"` かつ非削除時 | `managers_aggregate_address.py:245-246` |
| `as-set` 接尾辞 | `" as-set"` | `as_set == "true"` かつ非削除時 | `managers_aggregate_address.py:247-248` |
| address-family 退出 | `"exit-address-family"` | aggregate コマンド後 | `managers_aggregate_address.py:250` |
| router-bgp 退出 | `"exit"` | 末尾 | `managers_aggregate_address.py:251` |
| 削除プレフィクス | `"no "` | `is_remove=True` 時の全 vtysh コマンド先頭 | `managers_aggregate_address.py:243, 257` |
| prefix-list IPv4 前置詞 | `"ip"` | `is_v4=True` 時 | `managers_aggregate_address.py:258` |
| prefix-list IPv6 前置詞 | `"ipv6"` | `is_v4=False` 時 | `managers_aggregate_address.py:258` |
| prefix-list 本体 | `" prefix-list %s permit %s"` (名前 + prefix) | aggregate / contributing 共通 | `managers_aggregate_address.py:259-260` |
| contributing prefix-list IPv4 suffix | `" le 32"` | `is_con=True` かつ IPv4 | `managers_aggregate_address.py:262` |
| contributing prefix-list IPv6 suffix | `" le 128"` | `is_con=True` かつ IPv6 | `managers_aggregate_address.py:262` |

### prefix 長制約値（CIDR 上限）

`generate_prefix_list_commands()` が contributing prefix-list 構築時に **IPv4=32 / IPv6=128** をハードコードで `le` 句に付与する。YANG / CONFIG_DB から構成不能。

| 用途 | 値 | ソース |
|---|---|---|
| IPv4 最大プレフィクス長（`le` 値） | `32` | `managers_aggregate_address.py:262` |
| IPv6 最大プレフィクス長（`le` 値） | `128` | `managers_aggregate_address.py:262` |

### prefix-list 名のバリデーション範囲（YANG 由来）

YANG schema が aggregate-address / contributing-address それぞれの prefix-list 名に同一制約を課す。

| 用途 | 値 | ソース |
|---|---|---|
| prefix-list 名 pattern | `[0-9a-zA-Z_-]*` | `sonic-bgp-aggregate-address.yang:63, 72` |
| prefix-list 名 length | `0..128` 文字 | `sonic-bgp-aggregate-address.yang:64, 73` |

### frrcfgd（frr-mgmt-framework）経路の FRR コマンドテンプレート

frrcfgd は YANG-driven の代替経路。`af_aggregate_key_map` に FRR コマンドのフォーマット文字列をハードコード保持し、`hdl_af_aggregate()` で適用する。

| 定数 / フォーマット | 値 | ソース |
|---|---|---|
| FRR コマンドテンプレート | `"{no:no-prefix}aggregate-address {2} {3:aggr-as-set} {4:aggr-summary-only} {5:aggr-policy}"` | `frrcfgd.py:1983` |
| `aggr-as-set` → FRR キーワードマッピング | `as-set` | `frrcfgd.py:815` |
| `aggr-summary-only` → FRR キーワードマッピング | `summary-only` | `frrcfgd.py:816` |
| `aggr-policy` プレフィクス（非空時） | `"route-map "` | `frrcfgd.py:928-930` |
| 購読対象テーブル daemon | `'bgpd'` (only) | `frrcfgd.py:98` |
| 引数最小数ガード | `len(args) < 5` で `return None` | `frrcfgd.py:1314` |
| AggregateAddr 初期値 `as_set` | `False` | `frrcfgd.py:1704` |
| AggregateAddr 初期値 `summary_only` | `False` | `frrcfgd.py:1705` |

### 暗黙デフォルト値（コード fallback）

`set_address_state()` (`managers_aggregate_address.py:209-216`) と `set_handler()` で `data.get(KEY, default)` のフォールバック値として与えられるリテラル。

| フィールド | コード fallback | ソース |
|---|---|---|
| `bbr-required` | `"false"` (`COMMON_FALSE_STRING`) | `managers_aggregate_address.py:77, 210` |
| `summary-only` | `"false"` | `managers_aggregate_address.py:109, 211` |
| `as-set` | `"false"` | `managers_aggregate_address.py:110, 212` |
| `aggregate-address-prefix-list` | `""` (空文字列) | `managers_aggregate_address.py:213` |
| `contributing-address-prefix-list` | `""` (空文字列) | `managers_aggregate_address.py:214` |
| `bbr_status` BGP_BBR 不在時 | `""` (空文字列) | `managers_aggregate_address.py:76` |

### directory subscribe 対象（依存テーブル）

`AggregateAddrMgr.__init__()` (`managers_aggregate_address.py:33-41`) が以下を依存として固定購読する。

| 依存先 | キー | 用途 | ソース |
|---|---|---|---|
| CONFIG_DB `DEVICE_METADATA` | `localhost/bgp_asn` | `address_set_handler()` が `router bgp <asn>` 生成時に参照（未設定だと KeyError 伝播） | `managers_aggregate_address.py:36, 93, 149` |
| CONFIG_DB `BGP_BBR` | `BGP_BBR_STATUS_KEY` (`status`) | `on_bbr_change` / `set_handler` の BBR 状態判定 | `managers_aggregate_address.py:41, 47, 74` |

---

## 特記事項（discrepancy / 注意）

1. **IPv4=32 / IPv6=128 の `le` suffix 固定化** — contributing prefix-list の最大プレフィクス長を CONFIG_DB / YANG から変更する手段は無い。サブネット階層によっては全 contributing 経路にマッチしてしまう。
2. **prefix-list 名 pattern の `_-` のみ許容** — `.` / `:` / 数字始まり制限は無いが、FRR 側の prefix-list 名規約と完全一致するわけではない。FRR 側で reject される文字列が YANG では通る可能性あり（要追加検証）。
3. **bgpcfgd / frrcfgd の二経路並存** — bgpcfgd 経路は `BGP_AGGREGATE_ADDRESS` テーブル（VRF キー無し、default VRF 前提）を購読、frrcfgd 経路は `BGP_GLOBALS_AF_AGGREGATE_ADDR`（VRF/AF キー付き）を購読する。Phase E 観点ではコマンド生成リテラルが二箇所に重複定義されており、片方を変更してももう片方は追従しない。
4. **`router bgp <asn>` 生成で VRF 未指定** — bgpcfgd 経路は `DEVICE_METADATA.localhost.bgp_asn` を直接読むため default VRF のみ対応。VRF 拡張時はここがブロッカ。
5. **`exit-address-family` / `exit` 二段退出** — FRR 8.x 系の vtysh セマンティクスに依存。FRR バージョン更新で `exit-address-family` 廃止が来ると bgpcfgd 経路は壊れる。
6. **空文字列フォールバック (`bbr_status = ""`) の意味** — `BGP_BBR` テーブル未作成時、`bbr-required=true` のエントリは恒久的に `inactive` 落ちする。BGP_BBR 機能を使わない構成でも `BGP_BBR` テーブルに enabled レコードを置く必要がある可能性（仕様矛盾候補）。
