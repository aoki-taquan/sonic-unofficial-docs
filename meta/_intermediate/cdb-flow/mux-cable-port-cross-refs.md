# MUX_CABLE per-port 暗黙参照スキャン (Phase C)

`docs/reference/config-db/mux-cable-port.md` の Phase C (暗黙参照) ブロック裏付け資料。

このページは `MUX_CABLE|<ifname>` エントリのフィールド詳細に特化している。ここでの暗黙参照は、同エントリの処理に携わる `MuxOrch` (orchagent)、`linkmgrd`、`ycabled` の各コンポーネントが参照する入力テーブル・YANG leafref 先・書き出し先 STATE/APP テーブルを指す。

## YANG leafref

`MUX_CABLE_LIST.ifname` は `sonic-port.yang` の `PORT.PORT_LIST.name` への leafref であり、`ifname` の値は必ず `PORT` テーブルに存在するインタフェース名でなければならない (sonic-mux-cable.yang:37-40)。

## orchagent (MuxOrch) が参照するテーブル

### CONFIG_DB 読み取り (subscribe)

`MuxOrch` は `Orch2` フレームワークで `CFG_MUX_CABLE_TABLE_NAME` ("MUX_CABLE") と `CFG_PEER_SWITCH_TABLE_NAME` ("PEER_SWITCH") の 2 テーブルを購読する (muxorch.cpp:2189-2190)。

### PEER_SWITCH (処理前提)

`handleMuxCfg()` 内の `handlePeerSwitch()` チェーンで `PEER_SWITCH` エントリの `address_ipv4` が確定していなければ `MUX_CABLE` 処理を延期する (muxorch.cpp:2271)。

### TUNNEL テーブル (TunnelDecapOrch 経由)

`MuxOrch::handlePeerSwitch()` が `TUNNEL` の `MuxTunnel0` エントリを `decap_orch_->getDstIpAddresses/getDscpMode/getQosMapId` 経由で参照する (muxorch.cpp:2348, 2359, 2367, 2374)。TUNNEL エントリが未存在なら `return false` でリトライ。

### PORT テーブル (PortsOrch 経由)

`MuxCable` コンストラクタおよび状態遷移時に `gPortsOrch->getPort(mux_name_, port)` でポート SAI oid を取得する (muxorch.cpp:468, 493)。ポートが未登録なら即リターン。

### NEIGHBOR_TABLE (NeighOrch 経由)

`handleMuxCfg()` 処理終盤の `addOperation()` (muxorch.cpp:2290) で `gNeighOrch->getMuxNeighborsForPort()` を呼び、既存学習済みネイバーを MUX ネイバーに変換する。

## orchagent (MuxOrch) が書き出すテーブル

| DB | テーブル | キー | 書込みフィールド | タイミング | evidence |
|-----|---------|-----|-----------------|---------|---------|
| STATE_DB | `MUX_CABLE_TABLE` | `<ifname>` | `neighbor_mode` | `handleMuxCfg()` 処理時 1 回 | muxorch.cpp:2283-2285 |
| APP_DB | `HW_MUX_CABLE_TABLE` | `<ifname>` | `state` | mux state 切替時 | muxorch.cpp:2510-2513 |

## linkmgrd が参照するテーブル

linkmgrd は起動時に CONFIG_DB を直接読み (`swss::Table configDbMuxCableTable(...)`) 全ポートの `cable_type`/`prober_type`/`server_ipv4`/`soc_ipv4` を取得する (DbInterface.cpp:801, 843, 898, 956)。

ランタイムは `SubscriberStateTable` で `CFG_MUX_CABLE_TABLE_NAME` を購読し変更通知を受ける (DbInterface.cpp:1824)。

また `APP_PORT_TABLE_NAME` ("PORT_TABLE") を購読してリンク状態変化を受け取り、mux 状態遷移を制御する (DbInterface.cpp:1827)。

linkmgrd が書き出す先:
- `APP_DB:MUX_CABLE_TABLE` ("MUX_CABLE_TABLE") — mux 状態コマンド (DbInterface.cpp:317)
- `APP_DB:MUX_CABLE_COMMAND_TABLE` ("MUX_CABLE_COMMAND_TABLE") — 切替コマンド (DbInterface.cpp:323)
- `APP_DB:FORWARDING_STATE_COMMAND` — フォワーディング状態コマンド (DbInterface.cpp:326)
- `STATE_DB:MUX_LINKMGR_TABLE` — linkmgrd 状態 (DbInterface.cpp:332)
- `STATE_DB:MUX_METRICS_TABLE` — 切替メトリクス (DbInterface.cpp:335)
- `STATE_DB:MUX_SWITCH_CAUSE` — 切替理由 (DbInterface.cpp:341, DbInterface.h:63)
- `STATE_DB:MUX_CABLE_TABLE` ("MUX_CABLE_TABLE") — mux 現在状態 (DbInterface.cpp:346)

## ycabled が参照するテーブル

ycabled は `swsscommon.Table(config_db[asic_id], "MUX_CABLE")` で `MUX_CABLE` テーブルを ASIC ごとに直接読む (y_cable_helper.py:735)。

ycabled が書き出す先:
- `STATE_DB:HW_MUX_CABLE_TABLE_NAME` (`STATE_HW_MUX_CABLE_TABLE_NAME`) — gRPC 経由 HW mux 状態 (y_cable_helper.py:741-742)
- `STATE_DB:"HW_MUX_CABLE_TABLE_PEER"` — peer 側 HW mux 状態 (y_cable_helper.py:743-744)
- `STATE_DB:"MUX_CABLE_INFO"` — ケーブル情報 (y_cable_helper.py:746)

## 依存関係サマリ

```
CONFIG_DB:MUX_CABLE|<ifname>
  ├── orchagent MuxOrch  (subscribe CFG_MUX_CABLE_TABLE_NAME)
  │     ├── 前提: PEER_SWITCH address_ipv4 確定
  │     ├── 前提: TUNNEL MuxTunnel0 存在 (TunnelDecapOrch キャッシュ)
  │     ├── 前提: PORT <ifname> 登録済み (PortsOrch キャッシュ)
  │     ├── 書込: STATE_DB:MUX_CABLE_TABLE  → neighbor_mode
  │     └── 書込: APP_DB:HW_MUX_CABLE_TABLE → state
  ├── linkmgrd  (Table 直読み + SubscriberStateTable)
  │     ├── 参照: APP_DB:PORT_TABLE (リンク状態)
  │     └── 書込: APP_DB:MUX_CABLE_TABLE / COMMAND_TABLE, STATE_DB:MUX_* 系
  └── ycabled  (Table 直読み per ASIC)
        └── 書込: STATE_DB:HW_MUX_CABLE_TABLE, HW_MUX_CABLE_TABLE_PEER, MUX_CABLE_INFO
```
