# state-bgp Phase G — 通信メカニズム調査

調査日: 2026-05-19
対象: `docs/reference/config-db/state-bgp.md`

## BGP_PEER_CONFIGURED_TABLE — bgpcfgd の購読方式

`bgpcfgd` (`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/`) は Runner クラス (`runner.py`) が
`swsscommon.SubscriberStateTable` + `swsscommon.Select` でイベントループを構成する。

`SELECT_TIMEOUT = 1000` ms (runner.py:21) でブロッキング `select()` を繰り返す。

購読テーブル一覧 (main.py:75–136):

| 購読元 DB | テーブル名 (swsscommon 定数) | Manager クラス |
|---------|--------------------------|--------------|
| CONFIG_DB | `CFG_BGP_NEIGHBOR_TABLE_NAME` (`BGP_NEIGHBOR`) | `BGPPeerMgrBase` |
| CONFIG_DB | `CFG_BGP_INTERNAL_NEIGHBOR_TABLE_NAME` (`BGP_INTERNAL_NEIGHBOR`) | `BGPPeerMgrBase` |
| CONFIG_DB | `BGP_MONITORS` | `BGPPeerMgrBase` |
| CONFIG_DB | `BGP_PEER_RANGE` | `BGPPeerMgrBase` |
| CONFIG_DB | `BGP_VOQ_CHASSIS_NEIGHBOR` | `BGPPeerMgrBase` |
| CONFIG_DB | `BGP_SENTINELS` | `BGPPeerMgrBase` |
| CONFIG_DB | `CFG_DEVICE_METADATA_TABLE_NAME` | `BGPDataBaseMgr` |
| CONFIG_DB | `CFG_DEVICE_NEIGHBOR_METADATA_TABLE_NAME` | `BGPDataBaseMgr` |
| CONFIG_DB | `CFG_INTF_TABLE_NAME` / `CFG_LOOPBACK_INTERFACE_TABLE_NAME` / その他 | `InterfaceMgr` |
| STATE_DB | `STATE_INTERFACE_TABLE_NAME` | `ZebraSetSrc` |
| STATE_DB | `STATE_BFD_SOFTWARE_SESSION_TABLE_NAME` | `BfdMgr` (条件付き) |
| APPL_DB | `STATIC_ROUTE` | `StaticRouteMgr` |
| APPL_DB | `APP_BGP_PROFILE_TABLE_NAME` | `RouteMapMgr` |

SET イベント受信後 → `BGPPeerMgrBase.set_handler()` → FRR vtysh に設定注入
→ 成功時 `update_state_db()` → `swsscommon.Table(state_db, STATE_BGP_PEER_CONFIGURED_TABLE_NAME).set()` で STATE_DB に書き込み (managers_bgp.py:286–290)

DEL イベント受信後 → `BGPPeerMgrBase.del_handler()` → FRR vtysh で設定削除
→ `state_peer_table.delete(key)` (managers_bgp.py:294)

## BGP_STATE_TABLE — fpmsyncd のポーリング方式

`fpmsyncd` は `BGP_STATE_TABLE` を `swsscommon.Table` で直接 `hget()` するポーリング方式を使う
(fpmsyncd.cpp:91, 58-70)。Subscribe / keyspace 通知は**使用しない**。

Warm Restart モードでのみポーリングが有効化:
- 初回確認: 5 秒後から開始 (`eoiuCheckTimer.setInterval({5, 0})`, L176)
- 以降: 1 秒ごとに再確認 (`eoiuCheckTimer.setInterval({1, 0})`, L242)
- EOIU 検出後: hold timer (デフォルト 3 秒) 満了後に reconciliation を実行

select タイムアウト: 通常 `gSelectTimeout = INFINITE(-1)` / フラッシュ中は `500ms` (FLUSH_TIMEOUT, fpmsyncd.cpp:25)

## BMP_STATE_DB テーブル — openbmpd による直接書込み

`BGP_NEIGHBOR_TABLE` / `BGP_RIB_IN_TABLE` / `BGP_RIB_OUT_TABLE` は `openbmpd`
(OpeNBMP プロセス) が FRR と BMP (RFC 7854) セッションを直接確立し、
BGP OPEN / UPDATE メッセージを解析して `BMP_STATE_DB` に書き込む。

`bmpcfgd` は CONFIG_DB `BMP` テーブルを `ConfigDBConnector.subscribe()` + `listen()` (keyspace notification)
で購読し、`bgp_neighbor_table` / `bgp_rib_in_table` / `bgp_rib_out_table` フィールド変更時に
`openbmpd` を停止 → BMP_STATE_DB のテーブルを `delete_all_by_pattern` でクリア → `openbmpd` を再起動する
(bmpcfgd.py:58–70)。

Evidence:
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py` L21, L27-52, L57-69
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py` L75-136
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` L276-295
- `sonic-swss/fpmsyncd/fpmsyncd.cpp` L22-26, L82-91, L128-243
- `sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py` L58-89
