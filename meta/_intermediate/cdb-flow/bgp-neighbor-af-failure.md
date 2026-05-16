# bgp-neighbor-af — Phase D 失敗挙動スキャンノート

調査対象: `frrcfgd.py` (`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`)

## 検出した失敗・リトライ分岐

### 1. local_asn 未設定によるサイレントスキップ (L2658-2662)

`BGP_NEIGHBOR_AF` は `__vrf_based_table()` → `True` のため `__update_bgp` 冒頭で VRF の
`local_asn` 存在チェックが必ず実施される。`__get_vrf_asn()` が `None` を返した場合:

```python
if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
    syslog.syslog(syslog.LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured')
    continue
```

- 挙動: `continue` でサイレントスキップ。再試行なし。
- 回復: `BGP_GLOBALS.local_asn` 書き込み後に `__apply_dep_vrf_table` チェーン (L2851-2853) で再投入。

### 2. vtysh コマンド失敗 (L2872-2874)

```python
if not key_map.run_command(self, table, data, cmd_prefix, nbr):
    syslog.syslog(syslog.LOG_ERR, 'failed running BGP neighbor AF config command')
    continue
```

- 挙動: `LOG_ERR` + `continue`。リトライなし。
- 回復: 次回 CONFIG_DB 変更イベント待ち。

### 3. vtysh/bgpd ソケット接続リトライ (L186-200)

`BgpdClientMgr.__create_frr_client` での初期接続失敗時のみリトライあり。

- 挙動: 2s インターバル × 最大 100 回（= 最大 200 秒）。超過時 `RuntimeError` → 起動失敗。
- 対象: frrcfgd 起動時のみ。運用中のソケット断には適用されない。

### 4. g_run_command 非ゼロ終了 (L47-63)

`__run_command` は `ignore_fail=False` で呼び出すため、失敗時 `False` を返す。
呼び出し元 (`BGP_NEIGHBOR_AF` ブロック) が `continue` で処理。

### 5. ROUTE_MAP 未準備 (暗黙失敗)

`nbr_af_key_map` (L1903-1904) の `route_map_in` / `route_map_out` エントリは
vtysh `neighbor <addr> route-map <name> in|out` として送信される。
frrcfgd は bgpd 内での名前解決結果を確認しない。
FRR で未定義の route-map 名を参照した場合、frrcfgd 側は `STAT_SUCC` 扱いとなり
エラーは検出されない。bgpd 内部ログにのみ記録される可能性がある。

## 参照箇所まとめ

| 箇所 | L 番号 | 種別 |
|------|--------|------|
| `__update_bgp` local_asn チェック | 2656-2662 | silent skip |
| `BGP_NEIGHBOR_AF` ハンドラブロック | 2865-2874 | LOG_ERR + continue |
| `BgpdClientMgr.__create_frr_client` | 186-200 | retry (起動時のみ) |
| `g_run_command` | 47-63 | LOG_ERR + False |
| `nbr_af_key_map` route_map エントリ | 1903-1904 | 暗黙失敗 (bgpd 側) |

成果物: `docs/reference/config-db/bgp-neighbor-af.md` の `<!-- failure -->` ブロック。
