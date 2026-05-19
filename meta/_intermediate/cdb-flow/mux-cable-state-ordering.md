# mux-cable-state — Phase B 書込み順依存 調査ノート

調査日: 2026-05-19  
ソース: sonic-swss/orchagent/muxorch.cpp, sonic-linkmgrd/src/DbInterface.cpp, sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py

## 検出した順序依存

### 1. PEER_SWITCH 先行必須 (muxorch.cpp:2271-2275)

MuxOrch::handleMuxCfg() の SET 処理内で:

```cpp
if (mux_peer_switch_.isZero())
{
    SWSS_LOG_INFO("Mux Peer switch addr not yet configured, port '%s'", port_name.c_str());
    return false;
}
```

PEER_SWITCH テーブルが先に CONFIG_DB に存在しなければ MuxCable オブジェクトは生成されない。
→ MUX_CABLE_TABLE.neighbor_mode は書き込まれない。
→ MUX_CABLE_TABLE.state も書き込まれない（stateStandby() が呼ばれるのはオブジェクト生成後）。

### 2. MuxCable 生成 → neighbor_mode 書込み (muxorch.cpp:2279-2285)

```cpp
mux_cable_tb_[port_name] = std::make_unique<MuxCable>(...);
// Set neighbor_mode in state DB MUX_CABLE_TABLE
state_mux_cable_table_->hset(port_name, "neighbor_mode", neighbor_mode_str);
```

MuxCable コンストラクタ内で stateStandby() が呼ばれ updateMuxState("standby") が実行される。
その直後に neighbor_mode が書かれる。

### 3. MuxStateOrch は MuxOrch 登録チェック (muxorch.cpp:2650-2654)

```cpp
MuxOrch* mux_orch = gDirectory.get<MuxOrch*>();
if (!mux_orch->isMuxExists(port_name))
{
    SWSS_LOG_WARN("Mux entry for port '%s' doesn't exist", port_name.c_str());
    return false;
}
```

APP_DB HW_MUX_CABLE_TABLE の SET が MuxStateOrch に届いても、MuxOrch が該当ポートを登録していなければ MUX_CABLE_TABLE.state は更新されない。再キューされる。

### 4. HW_MUX_CABLE_TABLE は独立経路

ycabled が gRPC 経由でハードウェアを直接クエリして STATE_DB HW_MUX_CABLE_TABLE に書く。
orchagent パイプラインに依存しない。ただし APP_DB HW_MUX_CABLE_TABLE は orchagent 経由で MuxStateOrch が処理する。

### 5. linkmgrd の MUX_CABLE_TABLE 購読

DbInterface.cpp:1833:
swss::SubscriberStateTable stateDbPortTable(stateDbPtr.get(), STATE_MUX_CABLE_TABLE_NAME);

purchase ベースで MUX_CABLE_TABLE の変更を受け取り handleGetMuxState() → processGetMuxState() に渡す。

## CREATE 順序まとめ

CONFIG_DB PEER_SWITCH SET
  ↓
CONFIG_DB MUX_CABLE|<port> SET
  ↓
MuxOrch::handleMuxCfg()
  ↓ MuxCable 生成
  ↓ stateStandby() → updateMuxState("standby") → MUX_CABLE_TABLE.state = "standby"
  ↓ hset neighbor_mode → MUX_CABLE_TABLE.neighbor_mode
  ↓
ycabled (独立): HW_MUX_CABLE_TABLE.state 書込み
  ↓ APP_DB HW_MUX_CABLE_TABLE
MuxStateOrch::addOperation() [MuxOrch 登録チェック後]
  ↓
MUX_CABLE_TABLE.state 更新 (hw_state == mux_state → hw_state, 不一致 → unknown/error)
