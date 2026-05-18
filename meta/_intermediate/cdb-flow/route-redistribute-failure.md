# ROUTE_REDISTRIBUTE — Phase D 失敗挙動・エラーパス 調査メモ

調査対象:
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

調査日: 2026-05-18

---

## frrcfgd のイベント処理モデル

`frrcfgd` は `ConfigDBConnector.subscribe()` / `listen()` による keyspace 通知モデルを使用する。
ハンドラは `bgp_table_handler_common` → `__update_bgp` キューへ積む → 別スレッドで逐次消化する。

**`__update_bgp` 内でエラーが発生した場合、イベントは `continue` で skip される。再投入機構はない。**
これは `swsscommon.SubscriberStateTable` ベースの bgpcfgd (Manager.set_handler の False リトライ) と異なる点。

---

## SET 失敗マトリクス (frrcfgd.py L3149-3168)

```
elif table == 'ROUTE_REDISTRIBUTE':
    src_proto, dst_proto, af = key.split('|')
    if af == 'ipv6' and src_proto == 'ospf3':
        src_proto = 'ospf6'
    ip_type = 'unicast'
    if dst_proto != 'bgp':
        syslog.syslog(LOG_ERR, 'only bgp could be used as dst protocol')
        continue
    op = CachedDataWithOp.OP_DELETE if del_table else CachedDataWithOp.OP_UPDATE
    data['protocol'] = CachedDataWithOp(src_proto, op)
    cmd_prefix = ['configure terminal',
                  'router bgp {} vrf {}'.format(local_asn, vrf),
                  'address-family {} {}'.format(af, ip_type)]
    ret_val = key_map.run_command(self, table, data, cmd_prefix)
    del(data['protocol'])
    if not ret_val:
        syslog.syslog(LOG_ERR, 'failed running BGP route redistribute config command')
        continue
```

### 各エラー条件

| 条件 | 動作 | リトライ | ログ |
|------|------|---------|------|
| `local_asn is None` (BGP_GLOBALS 未設定) | `continue` (silent drop) | なし (BGP_GLOBALS 設定時に `__apply_dep_vrf_table` で再適用) | `LOG_DEBUG "ignore table ... because local_asn not configured"` |
| `dst_proto != 'bgp'` | `continue` | なし | `LOG_ERR "only bgp could be used as dst protocol"` |
| `key.split('|')` 要素数不足 (キーフォーマット不正) | Python ValueError 例外 → frrcfgd が例外ハンドラでスキップ | なし | スタックトレース |
| `key_map.run_command()` が False (vtysh 実行失敗 / bgpd 未起動) | `continue` | なし | `LOG_ERR "failed running BGP route redistribute config command"` |
| `g_run_command` で `p.returncode != 0` | `g_run_command` が False → `run_command` が False | なし | `LOG_ERR "command execution returned <code>"` |
| `bgpd_client.run_vtysh_command()` が False (bgpd_client ソケット切断) | `g_run_command` が False → `run_command` が False → `continue` | なし (次のイベントまで放置) | `LOG_ERR "command execution failure"` |
| `af` が `ipv4` / `ipv6` 以外の文字列 | FRR vtysh が "address-family <invalid> unicast" を拒否 → returncode != 0 | なし | `LOG_ERR "command execution returned"` + `LOG_ERR "failed running"` |
| `src_proto` が FRR 非認識プロトコル文字列 | vtysh が `no redistribute <unknown>` / `redistribute <unknown>` を拒否 → returncode != 0 → `continue` | なし | 同上 |
| `ospf3` + `ipv4` の組み合わせ | `ospf6` 変換されず `redistribute ospf3` として送出 → bgpd が拒否 → `continue` | なし | 同上 |

---

## DEL 失敗マトリクス

DEL 処理は同一コードパス (del_table=True で OP_DELETE) を使用。

| 条件 | 動作 |
|------|------|
| `local_asn is None` | `continue` (silent drop) — FRR に `no redistribute` 未送出 = FRR 側に redistribute 設定残存 |
| vtysh 実行失敗 | `continue` — FRR に `no redistribute` 未送出 = 設定残存 |

`hdl_route_redist_set` は SET 前に `no redistribute <src>` を必ず先行発行する (L1335)。
DEL 時は `OP_DELETE` を渡すため `get_command_cmn` が `no redistribute <src>` を生成。vtysh が失敗した場合は上記通り `continue` で設定残存。

---

## BgpdClientMgr の再接続

`bgpd_client.run_vtysh_command()` が False を返すケースは:
1. ソケット切断 (bgpd が再起動された場合)
2. コマンド応答のタイムアウト (120 秒、L201)
3. 応答が空 (FRR デーモン無応答)

`BgpdClientMgr.__create_frr_client` は起動時に最大 100 回 (間隔 2 秒) 接続を試みる (L186-199)。
ただし runtime 中の再接続は自動では行われない。bgpd が再起動した場合は frrcfgd の再起動が必要。

---

## `__apply_dep_vrf_table` — BGP_GLOBALS 設定後の自動再適用

`local_asn` の SET 成功後、`__apply_dep_vrf_table(vrf, 'ROUTE_REDISTRIBUTE')` が呼ばれる (L2703-2704)。
これは `bgp_message` キューに保留中の ROUTE_REDISTRIBUTE エントリを再送するもの。

ただし **キューに積まれているのは ConfigDBConnector.subscribe() が受信した時点の最新スナップショット**。
`local_asn` 未設定で drop されたイベントはキューに残らない場合がある。
この自動再適用は BGP_GLOBALS 設定前に ROUTE_REDISTRIBUTE を書き込んだケースのリカバーとして機能するが、
信頼性は保証されないため正順 (BGP_GLOBALS → ROUTE_REDISTRIBUTE) が推奨。

---

## サマリ

- frrcfgd はリトライ機構を持たない。エラー時は `continue` でそのイベントを廃棄する
- bgpd 未起動 / vtysh 失敗は LOG_ERR のみ出力し、CONFIG_DB 側にエラーステータスは残らない
- DEL 失敗時は FRR に `no redistribute` が送出されず redistribute 設定が残存するリスクがある
- `local_asn` 未設定 drop は BGP_GLOBALS SET 後の `__apply_dep_vrf_table` でリカバーが試みられる

evidence:
- frrcfgd.py L2658-2662 (local_asn gate)
- frrcfgd.py L3149-3168 (ROUTE_REDISTRIBUTE handler)
- frrcfgd.py L3156-3158 (dst_proto validation)
- frrcfgd.py L3164-3168 (vtysh fail → continue)
- frrcfgd.py L47-63 (g_run_command return False)
- frrcfgd.py L1330-1340 (hdl_route_redist_set, no-prefix先行)
- frrcfgd.py L186-199 (BgpdClientMgr retry on connect)
- frrcfgd.py L2703-2704 (__apply_dep_vrf_table)
