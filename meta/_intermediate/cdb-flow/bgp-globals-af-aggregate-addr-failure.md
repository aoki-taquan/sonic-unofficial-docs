# BGP_GLOBALS_AF_AGGREGATE_ADDR Phase D 失敗挙動 中間調査

対象ハンドラ: `frrcfgd.py` (`sonic-frr-mgmt-framework`)
対象テーブル: `BGP_GLOBALS_AF_AGGREGATE_ADDR`
スコープ: コミュニティ master / `frr_mgmt_framework_config=true` 経路のみ
（bgpcfgd テンプレ経路 = `BGP_AGGREGATE_ADDRESS` は別ページ `bgp-aggregate-address.md` で扱う）

## 1. 失敗経路スキャン結果

`frrcfgd.py` 中、`BGP_GLOBALS_AF_AGGREGATE_ADDR` の到達するコードパスを起点に、`continue` / `syslog.LOG_ERR` / `raise` / `return False` を列挙。

### 1.1 `bgp_table_handler_common()` 内 `BGP_GLOBALS_AF_AGGREGATE_ADDR` 分岐 (L3169-L3197)

| # | 行 | トリガ | 動作 | retry |
|---|----|--------|------|-------|
| F1 | L3172-3175 | `MatchPrefix.normalize_ip_prefix()` が `None` (prefix 形式不正、AF と IP family の不一致) | `syslog ERR 'invalid IP prefix format %s for af %s'` → `continue`。FRR コマンド非投入、`af_aggr_list` 未更新 | なし |
| F2 | L3170 | `af_type.lower().split('_')` の `ValueError` (`afi_safi` キーが `_` を含まない / 3 要素以上) | 上位 try ガード外。例外が `bgp_table_handler_common` を抜ける | なし (再 SET で再評価) |
| F3 | L3184-3186 | `key_map.run_command()` が `False` (vtysh 投入失敗 — bgpd vty socket 不通、bgpd 構文エラー、`router bgp` 未生成) | `syslog ERR 'failed running BGP IP prefix AF config command'` → `continue`。`af_aggr_list` 更新も skip | なし |
| F4 | L3176 (cmd_prefix 組み立て直前) | `local_asn = self.bgp_asn[vrf]` (L3144 付近で取得) — `BGP_GLOBALS` が未到着で `self.bgp_asn` に該当 vrf 未登録 | `KeyError` が上位に伝播。当該 SET 後に `BGP_GLOBALS` が来ても aggregate は自動再投入されない | なし |
| F5 | L3195-3197 | DEL で `vrf in self.af_aggr_list` が False | 何もせず skip。冪等扱い | — |
| F6 | L3196 | DEL で prefix が `af_aggr_list[vrf]` に不在 | `pop(norm_ip_prefix, None)` により `KeyError` を出さず skip | — |

### 1.2 `hdl_af_aggregate()` (L1313-L1328)

| # | 行 | トリガ | 動作 | retry |
|---|----|--------|------|-------|
| F7 | L1314-1315 | `len(args) < 5` (key 要素不足。通常 frrcfgd 内部で発生せず保険) | `return None` → 上位で no-op | なし |
| F8 | L1322 | `get_command_cmn()` が `None` を返す (フィールド書式不正) | `return None` → 上位は当該 key を skip | なし |
| F9 | L1320 | UPDATE 時、`no aggregate-address <prefix>` を先発行する間に bgpd vty が瞬断 | F3 と同じ経路で `key_map.run_command` False、`af_aggr_list` キャッシュは前回値のまま (更新されない) | なし |

### 1.3 `aggr-policy` format / ROUTE_MAP 未準備 (L928-930)

`CommandArgument.__format__(aggr-policy)`:

```python
elif format == 'aggr-policy':
    if len(self.value) > 0:
        self.value = 'route-map %s' % self.to_str()
```

- `policy` フィールド未設定 → 空文字列のまま展開され、FRR コマンドに `route-map` キーワードが付かない (正常パス)。
- `policy=<name>` だが `ROUTE_MAP_SET` に該当 name が未登録 → frrcfgd は **`ROUTE_MAP_SET` 存在検証を行わない**。FRR (`bgpd`) へ `aggregate-address <prefix> route-map <name>` をそのまま流す。bgpd 側で route-map 未定義の場合、bgpd はコマンド自体を受理する (route-map は後追い定義可) が、route-map が解決されないまま aggregate-address が作成され、attribute 加工は no-op となる (= silent ineffective)。`F10` として記録。

| # | 行 | トリガ | 動作 | retry |
|---|----|--------|------|-------|
| F10 | L928-930, L1313-1328 | `policy=<name>` を `ROUTE_MAP_SET` 未登録のまま SET | bgpd は aggregate-address を生成するが route-map は未解決。後から `ROUTE_MAP_SET` を SET しても aggregate-address は**自動で再投入されない** (frrcfgd は ROUTE_MAP 変更を aggregate 再投入トリガにしない) | なし。ユーザが aggregate-address を SET し直す必要 |

### 1.4 FRR 接続レイヤ (`FrrClient.__create_frr_client` L181-200, `__proc_command` L255-275)

| # | 行 | トリガ | 動作 | retry |
|---|----|--------|------|-------|
| F11 | L186-200 | 起動時 `/run/frr/bgpd.vty` 接続失敗 | 2 秒間隔で 100 回 retry、超過で `return False` → frrcfgd 起動失敗、aggregate-address 含む全 BGP テーブル未反映 | 100 回 / 2 秒 |
| F12 | L259-264 | 運用中 vtysh 送信時 `socket.error` | `syslog ERR 'failed to send command to frr daemon'` → `return (False, None)` → 上位は当該コマンド失敗扱い、CONFIG_DB 側は残存、再接続なし | なし。frrcfgd プロセス再起動が必要 |
| F13 | L267-269 | bgpd から `ret_code != 0` (構文エラー、router bgp 未生成 等) | `syslog DEBUG` のみ。aggregate 側からは「成功」扱いで `af_aggr_list` キャッシュは更新される | なし |

### 1.5 `BGP_GLOBALS_LIST.vrf_name` 未存在 (依存待機)

`router bgp <as> vrf <vrf>` の `<as>` は `self.bgp_asn[vrf]` から取得。`BGP_GLOBALS` 未到着で `vrf` が `bgp_asn` に存在しない場合 = F4。

frrcfgd は依存待機キューを持たない (`bgpcfgd` の `Directory` 機構に相当する仕組みは無い)。順序逆転時の救済は `frrcfg.sh restart` か CONFIG_DB 再 SET のみ。

## 2. retry サマリ

| retry 種別 | あり / なし | 根拠 |
|---|---|---|
| 周期 retry | なし | `bgp_table_handler_common` 内に timer / queue 機構なし |
| 自動再投入トリガ | なし (bgpcfgd の `on_bbr_change` のような hook は frrcfgd では未実装) | `frrcfgd.py` 全体に `BGP_GLOBALS_AF_AGGREGATE_ADDR` 専用の再投入経路なし |
| bgpd 接続 retry | あり (起動時のみ 100 回 / 2 秒) | F11 |
| 運用中 socket 切断回復 | なし | F12 |
| ROUTE_MAP 後追い定義による再投入 | なし | F10 |

## 3. 状態記録

- `STATE_DB` には記録しない (frr-mgmt-framework 経路は `BGP_AGGREGATE_ADDRESS|*` のような STATE_DB ミラーを持たない)。
- syslog のみが失敗観測手段:
  - `'invalid IP prefix format ...'` (F1)
  - `'failed running BGP IP prefix AF config command'` (F3)
  - `'failed to connect to frr daemon ...'` (F11)
  - `'failed to send command to frr daemon: ...'` (F12)
  - `[bgpd] command return code: <N>` (F13, DEBUG)
- `ERROR_TABLE` への記録はなし。

## 4. bgpcfgd 系 (BGP_AGGREGATE_ADDRESS) との対比

| 観点 | frr-mgmt-framework (本テーブル) | bgpcfgd (BGP_AGGREGATE_ADDRESS) |
|---|---|---|
| STATE_DB | なし | `BGP_AGGREGATE_ADDRESS|<prefix>` に state |
| BBR retry hook | なし | `on_bbr_change()` (enabled 遷移で再投入) |
| ROUTE_MAP 順序救済 | なし | あり (`ConfigMgr` レベル) |
| vtysh 失敗検出 | `key_map.run_command` False / DEBUG ログ | `ConfigMgr.commit()` の rc 確認 |

実装が薄いため、aggregate-address (frr-mgmt-framework 経路) は**実質「投げっぱなし」**であることが要点。

## 5. evidence 行

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:3169-3197` (BGP_GLOBALS_AF_AGGREGATE_ADDR 分岐)
- `frrcfgd.py:1313-1328` (`hdl_af_aggregate`)
- `frrcfgd.py:928-930` (`aggr-policy` format)
- `frrcfgd.py:181-200` (FRR 接続 retry)
- `frrcfgd.py:255-275` (`__proc_command`)
- `frrcfgd.py:1982-1983` (`af_aggregate_key_map`)
