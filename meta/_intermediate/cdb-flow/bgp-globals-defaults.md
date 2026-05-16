# BGP_GLOBALS — Phase A: コード由来の暗黙デフォルト調査

対象: `docs/reference/config-db/bgp-globals.md`
調査日: 2026-05-14
調査者: Claude (agent)

## 調査手順

1. `grep -rln "BGP_GLOBALS" .cache/sonic-sources/` — 1 回のみ実行（エントリポイント特定）
2. 主要ファイル全行精読:
   - `frrcfgd/frrcfgd.py` (global_key_map L1784, bgp_global_handler L3935, get_command_cmn L374, __init__ L2156)
   - `templates/bgpd/bgpd.conf.db.j2` (全行)
   - `yang-models/sonic-bgp-global.yang` (全行)
3. データフロー追跡: CONFIG_DB → frrcfgd → FRR vtysh コマンド

## 発見事項: field ごとの暗黙デフォルト

### キー: `{no:no-prefix}` パターンの解釈

`global_key_map` の各エントリの `['true', 'false']` は bool_values 引数。`get_command_cmn()` の処理:
- 値 == `'true'`  → コマンド発行 (`cmd_enable=True`)
- 値 == `'false'` → `no <command>` 発行 (`cmd_enable=False`)
- フィールドが CONFIG_DB に **存在しない** → frrcfgd は何もしない → FRR の組み込みデフォルトが維持される

第3要素 `True` (Python bool) の意味:
- `['true', 'false', True]` → DELETE 時に「フィールドを FRR 組み込みデフォルト（= 有効状態）に戻す」ため `cmd_enable=True` でコマンド発行 (L377-379)
- 対象: `fast_external_failover`, `rr_clnt_to_clnt_reflection` の 2 フィールド

### YANG デフォルト

YANG `sonic-bgp-global.yang` に `default` 文を持つフィールド:

| フィールド | YANG default | YANG 所在 |
|-----------|-------------|---------|
| `BGP_GLOBALS_AF.max_ebgp_paths` | 1 | L345 |
| `BGP_GLOBALS_AF.max_ibgp_paths` | 1 | L354 |

**`BGP_GLOBALS` 本体 (BGP_GLOBALS_LIST) には YANG `default` 文なし** — 全フィールドが optional。

### コード由来の暗黙デフォルト (FRR 組み込みデフォルトとの対応)

以下はフィールドが CONFIG_DB に**存在しない**場合に FRR が持つ組み込みデフォルト（frrcfgd は何も送らないため FRR の初期値が有効）:

| フィールド | FRR 組み込みデフォルト | 根拠 / evidence |
|-----------|---------------------|----------------|
| `fast_external_failover` | **有効 (true)** | J2 テンプレート L33: `== 'false'` 時のみ `no bgp fast-external-failover` を発行。存在しない場合は FRR の "on" 状態維持。global_key_map `['true','false',True]` の第3要素 `True` もこれを示す。frrcfgd.py L1798 |
| `rr_clnt_to_clnt_reflection` | **有効 (true)** | J2 テンプレート L64: `== 'false'` 時のみ `no bgp client-to-client reflection` を発行。global_key_map `['true','false',True]` L1801 |
| `default_ipv4_unicast` | **有効 (true)** | J2 テンプレート L46-50: `!= 'true'` の else 節で `no bgp default ipv4-unicast` を発行する。つまり**フィールドが存在しない場合も `no bgp default ipv4-unicast` が発行される** ← これは書き込みデフォルト(false相当)であり FRR の組み込みデフォルト(true)と**乖離** |
| `keepalive` + `holdtime` | 両方存在しない場合は FRR デフォルト (60s / 180s) | comb_attr_list `{'keepalive','holdtime'}` により片方だけでは FRR コマンド未送出。両方揃った時のみ `timers bgp {} {}` 発行。frrcfgd.py L3936, L1820 |

### 書き込み時デフォルト vs 実行時 fallback の乖離

| フィールド | CONFIG_DB 未設定時の frrcfgd 動作 | FRR 組み込みデフォルト | 乖離 |
|-----------|----------------------------------|---------------------|------|
| `default_ipv4_unicast` | J2: else 節で `no bgp default ipv4-unicast` を常に発行 | true (有効) | **あり**: 未設定でも `no` が発行されるため FRR は無効化される |
| `fast_external_failover` | frrcfgd: 未設定時は何も送出しない | true (有効) | なし: FRR デフォルト維持 |
| `rr_clnt_to_clnt_reflection` | frrcfgd: 未設定時は何も送出しない | true (有効) | なし: FRR デフォルト維持 |
| `keepalive` / `holdtime` | 片方のみ → コマンド未送出 | 60 / 180 s | なし: FRR デフォルト維持。両方セット必須 |

### 複合制約フィールド (comb_attr_list)

bgp_global_handler は `comb_attr_list=[{'keepalive', 'holdtime'}]` を渡す (frrcfgd.py L3936)。
`__add_op_to_data()` の処理: 集合内のいずれかが欠如している場合、集合全体のエントリを data から除去 → FRR コマンド未生成。
**効果**: `keepalive` と `holdtime` はセットでのみ有効。片方だけ書いても FRR タイマーは更新されない。

### max_delay / establish_wait の複合

`global_key_map` L1817: `(['max_delay', '+establish_wait'], '{no:no-prefix}update-delay {} {}')` — `+` prefix は optional 扱い。
J2 テンプレート L76-83 も同様: `max_delay` が存在すれば `establish_wait` を追記（存在すれば）。
**効果**: `max_delay` なしで `establish_wait` 単独は無意味。

### max_med_time / max_med_val の複合

`global_key_map` L1816: `(['max_med_time', '+max_med_val'], ...)` — `max_med_val` は optional。
`max_med_time` が必須トリガー。値なしでは startup max-med は設定されない。

### max_med_admin / max_med_admin_val の複合

`global_key_map` L1821: `(['max_med_admin', '+max_med_admin_val'], ...)` — `max_med_admin_val` は optional。
`max_med_admin == 'true'` が必須トリガー。

## frrcfgd __init__ で読み取るフィールド

- `local_asn`: `self.bgp_asn[vrf]` に格納 (L2177-2178)
- `confed_peers`: `self.bgp_confed_peers[vrf]` に格納 (L2180-2181)
- これらは起動時に CONFIG_DB 全量読み込みでキャッシュ

## J2 テンプレート (bgpd.conf.db.j2) との対応

bgpcfgd 側（bgpd.conf.db.j2）と frrcfgd 側（global_key_map）で両方 BGP_GLOBALS を処理する。
通常は **どちらか一方のみ稼働**（main.py L87 で docker_routing_config_mode に依存）。
J2 テンプレートの `default_ipv4_unicast` の `else` 節は frrcfgd の key_map にはなく動作が異なる点に注意。

## 結論: `<!-- defaults -->` ブロックに記載すべき内容

1. `fast_external_failover` — 未設定時は FRR の "on" を維持（FRR デフォルト: 有効）
2. `rr_clnt_to_clnt_reflection` — 未設定時は FRR の "on" を維持（FRR デフォルト: 有効）  
3. `default_ipv4_unicast` — **乖離あり**: J2 テンプレート経由 (bgpcfgd) では未設定でも `no bgp default ipv4-unicast` が発行される（実質 false 扱い）
4. `keepalive` + `holdtime` — 両方必須セット; 片方のみでは FRR タイマー未変更
5. YANG `default` は BGP_GLOBALS 本体フィールドには存在しない（BGP_GLOBALS_AF の max_ebgp_paths / max_ibgp_paths のみ default 1）
