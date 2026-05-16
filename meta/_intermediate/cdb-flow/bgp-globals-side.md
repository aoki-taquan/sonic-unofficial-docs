# BGP_GLOBALS — Phase F: 副次 DB 書込スキャン結果

## スキャン対象

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/` (全 .py)
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 結論: STATE_DB / COUNTERS_DB への副次書込なし

`BGP_GLOBALS` テーブルの変更を直接ハンドルするコードパス（`frrcfgd.BGPConfigDaemon.bgp_global_handler()` および `bgpcfgd` の managers_bgp.py 内 BGP_GLOBALS 相当処理）は、**STATE_DB / COUNTERS_DB への書込を一切行わない**。

### grep 証跡

| 検索対象ファイル | キーワード | ヒット数 (STATE_DB write) |
|-----------------|-----------|--------------------------|
| `frrcfgd.py` | `STATE_DB`, `state_db`, `COUNTERS_DB`, `hset`, `hmset`, `.set(` | 0 |
| `managers_bgp.py` | `BGP_GLOBALS` | 0 (BGP_GLOBALS 固有の state 書込なし) |
| `managers_bgp.py` | `STATE_DB` / `update_state_db` | 存在するが BGP_NEIGHBOR ハンドラのみ |

### STATE_DB 書込が存在するが BGP_GLOBALS とは無関係なパス

| モジュール | STATE_DB テーブル | トリガー CONFIG_DB テーブル |
|-----------|------------------|-----------------------------|
| `managers_bgp.py:BGPPeerMgrBase.update_state_db()` | `BGP_PEER_CONFIGURED_TABLE` | `BGP_NEIGHBOR` / `BGP_NEIGHBOR_AF` |
| `managers_aggregate_address.py:AggregateAddressMgr` | `BGP_AGGREGATE_ADDRESS` | `BGP_AGGREGATE_ADDRESS`（CONFIG_DB） |
| `main.py:ZebraSetSrc` | `STATE_INTERFACE_TABLE_NAME` | `BGP_INTERFACE` |
| `main.py:AdvertiseRouteMgr` | `STATE_ADVERTISE_NETWORK_TABLE_NAME` | `BGP_ADVERTISE_NETWORK` |
| `main.py:BfdMgr` | `STATE_BFD_SOFTWARE_SESSION_TABLE_NAME` | `BFD_SESSION` |

これらはすべて `BGP_GLOBALS` ではなく別テーブルのハンドラが書き込む。

## 間接効果（副次書込ではない実行時挙動）

`BGP_GLOBALS` の変更が FRR vtysh に届いた後、FRR 自体が BGP session を reset / renegotiate することで、**FRR 内部の BGP session 状態が変わる**。ただしこれは SONiC DB への書込ではなく FRR プロセス内部の状態変化である。  
`bgpd` が session 状態変化を `bgpmon` 経由で通知するケースがあるが、これは BGP_GLOBALS handler から直接トリガされる DB 書込ではない。

## 出力先サマリ

```
BGP_GLOBALS (CONFIG_DB)
  ↓ bgpcfgd / frrcfgd
  FRR vtysh (プロセス内設定のみ)
  → STATE_DB 書込: なし
  → COUNTERS_DB 書込: なし
  → APPL_DB 書込: なし
```

## evidence

- `frrcfgd.py:3935` `def bgp_global_handler()` — vtysh コマンド発行のみ、DB write なし
- `managers_bgp.py:271-300` `update_state_db()` — `BGP_NEIGHBOR` ハンドラからのみ呼ばれる（BGP_GLOBALS ハンドラから呼び出しなし）
- `main.py:71-120` — BGP_GLOBALS に対応する Manager 登録なし（bgpcfgd は BGP_GLOBALS テーブルを直接購読しない）
- `frrcfgd.py` 全体: `STATE_DB` / `COUNTERS_DB` の `DBConnector` 生成ゼロ
