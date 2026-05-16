# 順序依存分析: MUX_CABLE (Phase B)

ソース: `sonic-swss/orchagent/muxorch.cpp`

## 1. NEIGHBOR / PORT 先行依存

### PORT テーブル先行
- `MuxCable::stateActive()` (muxorch.cpp:463) および `MuxCable::stateStandby()` (muxorch.cpp:488) は冒頭で
  `gPortsOrch->getPort(mux_name_, port)` を呼ぶ。
  ポートが未登録の場合 `return false` でリトライキューに戻る。
  → **PORT エントリが存在しないと active/standby 切替は一切進まない。**

### NEIGHBOR 先行 / 後続学習キャッシュ
- `MuxOrch::handleMuxCfg()` (muxorch.cpp:2288-2315) の SET 処理終盤で
  `gNeighOrch->getMuxNeighborsForPort()` を呼び、MUX_CABLE 設定**前**に学習済みのネイバーを
  `updateNeighbor()` / `convertNeighborToMux()` で取り込む。
  → **MUX_CABLE より先に NEIGHBOR が存在してもよい**（後付け取り込み済）。
- 逆に MUX_CABLE 設定後に NEIGHBOR が追加された場合は通常の `updateNeighbor()` フローで処理される。

## 2. Tunnel encap 先行依存

### PEER_SWITCH → Tunnel encap → MUX_CABLE の順序が必須
`MuxOrch::handleMuxCfg()` (muxorch.cpp:2271-2275):
```
if (mux_peer_switch_.isZero())
{
    SWSS_LOG_INFO("Mux Peer switch addr not yet configured, port '%s'", port_name.c_str());
    return false;
}
```
MUX_CABLE エントリを処理しようとした時点で `mux_peer_switch_` が 0.0.0.0 のままだと
`return false` でリトライ待機に入る。`mux_peer_switch_` は `handlePeerSwitch()` が
PEER_SWITCH テーブルを処理した際に設定される。

### MuxTunnel0 (TUNNEL テーブル) 先行
`MuxOrch::handlePeerSwitch()` (muxorch.cpp:2348-2353):
```
IpAddresses dst_ips = decap_orch_->getDstIpAddresses(MUX_TUNNEL);
if (!dst_ips.getSize())
{
    SWSS_LOG_INFO("Mux tunnel not yet created for '%s' peer ip '%s'", ...);
    return false;
}
```
PEER_SWITCH を処理する際に `MuxTunnel0` の dst IP が `decap_orch_` から取得できなければ
`return false` でリトライ待機。Tunnel encap SAI オブジェクトも `handlePeerSwitch()` 内の
`create_tunnel()` (muxorch.cpp:2380) で生成される。

### Tunnel NH (nexthop) 先行
`MuxOrch::createStandaloneTunnelRoute()` (muxorch.cpp:2445-2447):
```
sai_object_id_t tunnel_nexthop = getNextHopTunnelId(MUX_TUNNEL, mux_peer_switch_);
if (tunnel_nexthop == SAI_NULL_OBJECT_ID) {
    SWSS_LOG_NOTICE("... nexthop not created yet, ignoring tunnel route creation ...");
    return;
}
```
スタンドアロン tunnel route 作成は Tunnel NH が存在しないと silent skip される。

## 3. active / standby 状態遷移の順序制約

### 初期状態: standby
`MuxCable::MuxCable()` コンストラクタ (muxorch.cpp:445-448):
- 通常起動時: `stateStandby()` を呼んで MUX_STATE_STANDBY で開始。
  → **エントリ追加時は必ず standby が先に実行される。**
- Warm restart 時: `MUX_STATE_INIT` で開始し、APP_DB sync 後に前回状態に復元。

### state 遷移マトリクス (state_machine_handlers_)
muxorch.cpp:432-435 に登録された遷移のみが合法:
| トリガー (from→to) | ハンドラ |
|---|---|
| INIT → ACTIVE | `stateInitActive()` |
| STANDBY → ACTIVE | `stateActive()` |
| INIT → STANDBY | `stateStandby()` |
| ACTIVE → STANDBY | `stateStandby()` |

ACTIVE→ACTIVE や STANDBY→STANDBY の遷移エントリは登録されていない
（同状態への再設定は `setState()` の冒頭ログ後に handler_map lookup が失敗してエラー出力される）。

### stateActive() での ACL 操作順序
muxorch.cpp:474-483:
1. `aclHandler(port_id, mux_name_, false)` — **ACL drop rule を削除**してからトラフィックを受け入れる
2. `nbrHandler(true)` — neighbor を active (local) nexthop に切替

### stateStandby() での ACL 操作順序
muxorch.cpp:499-508:
1. `nbrHandler(false)` — **neighbor を tunnel nexthop に切替**してトラフィックをピア ToR へ迂回
2. `aclHandler(port_id, mux_name_)` — **ACL drop rule を追加**して直接受信をブロック

neighbor 操作が ACL 操作より**先**に行われる（standby 時は逆順で neighbor→ACL）。

### neighbor_mode の変更不可制約
muxorch.cpp:2256-2266:
既存 MuxCable オブジェクトへの `neighbor_mode` 変更は `SWSS_LOG_ERROR` を出して `return false`。
MUX_CABLE の DELETE + 再 SET が必要（ポート削除+再登録が前提）。

## 4. 順序依存まとめ

```
TUNNEL (MuxTunnel0) の decap dst IP 登録
       ↓
PEER_SWITCH テーブル SET → create_tunnel() → mux_peer_switch_ 確定
       ↓
PORT テーブルに ifname が登録済み
       ↓  （NEIGHBOR は先行しても後続でもよい、後付け取り込みあり）
MUX_CABLE テーブル SET → MuxCable オブジェクト生成 (初期状態: standby)
       ↓
state: standby → active 遷移要求
  1. PORT 取得確認
  2. ACL drop rule 削除
  3. neighbor を local nexthop に切替
```
