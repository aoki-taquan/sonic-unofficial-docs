# BGP_GLOBALS_AF_NETWORK テーブル — consumer 例外条件分析

## Consumer: frrcfgd (sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py)

### 処理関数
- `bgp_table_handler_common` → BGP_GLOBALS_AF_NETWORK 分岐 (L3169) (AGGREGATE_ADDR と同一コードパス)

### 例外条件・特殊挙動

#### 1. 不正 IP prefix → syslog ERR & continue
`normalize_ip_prefix()` が None を返した場合はスキップ。AGGREGATE_ADDR と同一の検証ロジック。

#### 2. AF_TYPE パース失敗 → ValueError 伝播
`af_type.lower().split('_')` の分割失敗は例外。

#### 3. FRR コマンド失敗 → syslog ERR & continue
`run_command` が False を返した場合 → syslog ERR & continue。再試行なし。

#### 4. NETWORK 固有: policy / backdoor フィールド
`af_network_key_map` は `['ip_prefix', '++policy', '+backdoor']` を扱う。
`policy` / `backdoor` フィールドが欠如している場合は空文字列/デフォルトで FRR コマンドが生成される (Jinja2 テンプレートの `{3:network-policy}` / `{4:network-backdoor}` 形式で省略)。

#### 5. AGGREGATE_ADDR との差異: af_aggr_list キャッシュなし
AGGREGATE_ADDR は内部キャッシュ (`af_aggr_list`) を持つが、NETWORK はキャッシュ管理なし。
DEL 操作は FRR への `no network <prefix>` コマンドのみで完結する。

#### 6. 重複 network 登録
FRR は同一 prefix を複数回 `network` コマンドで投入されても冪等に扱う。
frrcfgd 側での重複チェックはない。

#### 7. bgp_asn / vrf 依存 (AGGREGATE_ADDR と同様)
BGP_GLOBALS の設定が必須前提。
