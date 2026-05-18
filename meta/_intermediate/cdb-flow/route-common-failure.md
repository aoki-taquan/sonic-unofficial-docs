# ROUTE_REDISTRIBUTE — Phase D 失敗挙動スキャンノート

対象テーブル: `ROUTE_REDISTRIBUTE`
Consumer: `frrcfgd.BGPConfigDaemon` (`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`)
スキャン範囲: L3149-3180 (ROUTE_REDISTRIBUTE イベント処理), L47-278 (__run_command / __proc_command), L255-306 (run_vtysh_command), L2658-2665 (local_asn ゲート), L1330-1358 (hdl_route_redist_set)

---

## 検出した失敗パターン

### 1. BGP_GLOBALS.local_asn 未設定 → silent drop (ゲート失敗)

`frrcfgd.py` L2658-2661:

```python
local_asn = self.__get_vrf_asn(vrf)
if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
    syslog.syslog(LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured')
    continue
```

`ROUTE_REDISTRIBUTE` イベント処理は `bgp_table_handler_common` を経由する。先頭で `__get_vrf_asn(vrf)` を呼び、VRF に対応する `BGP_GLOBALS.local_asn` が未設定の場合は DEBUG ログのみで `continue`（silent drop）。CONFIG_DB へのロールバックなし・リトライなし。BGP_GLOBALS.local_asn が後から設定されると `__apply_dep_vrf_table` で自動再適用される（緩和策あり）。

evidence: `frrcfgd.py:2658-2661`, `frrcfgd.py:2442-2447`

### 2. dst_protocol != 'bgp' → LOG_ERR + drop (恒久スキップ)

`frrcfgd.py` L3156-3158:

```python
if dst_proto != 'bgp':
    syslog.syslog(syslog.LOG_ERR, 'only bgp could be used as dst protocol, but {} was given'.format(dst_proto))
    continue
```

`dst_protocol` が `bgp` 以外の場合、LOG_ERR レベルで記録し `continue`。リトライなし・自動回復なし。YANG で `dst_protocol` の値は制約されておらず、ランタイムでのみ検証される。CONFIG_DB に不正エントリが存在し続けても frrcfgd は同エントリを毎回 drop し続ける（イベント再発行のたびに同エラーが出力される）。

evidence: `frrcfgd.py:3156-3158`

### 3. vtysh コマンド送出失敗 → LOG_ERR + continue (FRR 未反映)

`frrcfgd.py` L3165-3168:

```python
ret_val = key_map.run_command(self, table, data, cmd_prefix)
del(data['protocol'])
if not ret_val:
    syslog.syslog(syslog.LOG_ERR, 'failed running BGP route redistribute config command')
    continue
```

`key_map.run_command()` が `False` を返した場合（FRR bgpd への vtysh コマンド失敗）、LOG_ERR で記録し `continue`。FRR への `redistribute` コマンドは発行されず、CONFIG_DB の設定と FRR running-config が乖離した状態になる。自動リトライなし。orchagent 等のコンポーネントへの通知もなし。

内部的には `run_vtysh_command` → `__proc_command` → FRR daemon socket が処理する。以下の場合に失敗する:
- FRR bgpd プロセスが未起動または socket 切断 → `daemon %s is not connected` ログ
- socket `send()` 失敗 → `failed to send command to frr daemon: %s`
- FRR からの返信取得失敗 → `failed to get reply from frr daemon`

evidence: `frrcfgd.py:3165-3168`, `frrcfgd.py:255-278`

### 4. hdl_route_redist_set が None を返す → run_command False → LOG_ERR

`hdl_route_redist_set` (`frrcfgd.py:1330-1350`):

```python
def hdl_route_redist_set(daemon, cmd_str, op, st_idx, args, data):
    cmd_list = []
    if op != CachedDataWithOp.OP_DELETE:
        # blindly run no command first (reset前の no redistribute)
        cmd_list.append(...)
    upd_cmd_list = get_command_cmn(daemon, cmd_str, op, st_idx, args, data)
    if upd_cmd_list is None:
        return None   # → run_command が False を返す → LOG_ERR
    return cmd_list + upd_cmd_list
```

`get_command_cmn` が `None` を返した場合（引数構築失敗など）、`hdl_route_redist_set` も `None` を返し、`run_command` は `False` となる。上記パターン #3 のエラーパスに落ちる。

evidence: `frrcfgd.py:1330-1350`

---

## 失敗時の状態まとめ

| 失敗シナリオ | FRR 状態 | CONFIG_DB | ログレベル | 自動回復 |
|---|---|---|---|---|
| `BGP_GLOBALS.local_asn` 未設定 (local_asn is None) | 未反映 | 変更なし（エントリ残存） | DEBUG | あり（BGP_GLOBALS.local_asn SET 後に自動再適用） |
| `dst_protocol != 'bgp'` | 未反映 | エントリ残存 (invalid) | ERR | なし（不正エントリを修正するまで繰り返し drop） |
| vtysh コマンド送出失敗 (FRR 未接続等) | 未反映 | エントリ残存 | ERR | なし（frrcfgd 再起動・FRR 再接続後に手動 re-trigger 必要） |
| `hdl_route_redist_set` が None 返却 | 未反映 | エントリ残存 | ERR | なし |

## 補足: SET と DEL の非対称性

SET 失敗後に DEL を送ると、FRR 側には `redistribute <src>` が存在しないため `no redistribute <src>` は副作用なく実行される（FRR は存在しない設定への `no` コマンドをエラーなく処理する）。逆に DEL が失敗した場合は FRR 側に `redistribute` 設定が残存し、CONFIG_DB からエントリが削除されても FRR は経路再配布を継続する。
