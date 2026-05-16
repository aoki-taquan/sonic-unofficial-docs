# mux-linkmgr — Phase G: 通信メカニズム調査メモ

## 調査対象

- ソース: `sonic-linkmgrd/src/DbInterface.cpp`
- 対象テーブル: `MUX_LINKMGR` (CONFIG_DB)

## CONFIG_DB Subscribe 経路

### SubscriberStateTable 登録

`DbInterface::handleSwssNotification()` (`DbInterface.cpp:1811-`) が専用スレッドで以下の SubscriberStateTable を作成し `swss::Select` に登録する。

```cpp
// DbInterface.cpp:1820
swss::SubscriberStateTable configDbMuxLinkmgrTable(configDbPtr.get(), CFG_MUX_LINKMGR_TABLE_NAME);
```

Select ループ内の dispatch:
```cpp
// DbInterface.cpp:1887-1888
if (selectable == static_cast<swss::Selectable *> (&configDbMuxLinkmgrTable)) {
    handleMuxLinkmgrConfigNotifiction(configDbMuxLinkmgrTable);
```

### Handler チェーン

```
handleMuxLinkmgrConfigNotifiction()  → DbInterface.cpp:1222
  └─ configMuxLinkmgrTable.pops(entries)
  └─ processMuxLinkmgrConfigNotifiction(entries)  → DbInterface.cpp:1120

processMuxLinkmgrConfigNotifiction():
  key == "LINK_PROBER":
    interval_v4            → MuxManager::setTimeoutIpv4_msec()
    interval_v6            → MuxManager::setTimeoutIpv6_msec()
    positive_signal_count  → MuxManager::setPositiveStateChangeRetryCount()
    negative_signal_count  → MuxManager::setNegativeStateChangeRetryCount()
    suspend_timer          → MuxManager::setSuspendTimeout_msec()
    use_well_known_mac     → MuxManager::setUseWellKnownMacActiveActive(v == "enable")
    src_mac                → MuxManager::processSrcMac(v == "ToRMac")
    interval_pck_loss_count_update → MuxManager::setLinkProberStatUpdateIntervalCount()
    reset_suspend_timer    → MuxManager::processResetSuspendTimer(ports)

  key == "MUXLOGGER":
    log_verbosity          → MuxManager::updateLogVerbosity() (SwSS logger 非使用時のみ)

  key == "TIMED_OSCILLATION":
    oscillation_enabled    → MuxManager::setOscillationEnabled(true/false)
    interval_sec           → MuxManager::setOscillationInterval_sec()
```

**注意**: `SERVICE_MGMT` キー (`kill_radv`) は `processMuxLinkmgrConfigNotifiction()` に分岐なし。Runtime での動的反映不可。

## xcvrd 経路

### MUX 状態確認 (I2C)

linkmgrd → xcvrd のコマンド送出:
```cpp
// DbInterface.cpp:439-443  handleProbeMuxState()
mAppDbMuxCommandTablePtr->hset(portName, "command", "probe");
// テーブル: APPL_DB::APP_MUX_CABLE_COMMAND_TABLE_NAME
```

xcvrd → linkmgrd の応答受信:
```cpp
// DbInterface.cpp:1829
swss::SubscriberStateTable appDbMuxResponseTable(appDbPtr.get(), APP_MUX_CABLE_RESPONSE_TABLE_NAME);
// dispatch: handleMuxResponseNotifiction() → processMuxResponseNotifiction()
// → MuxManager::processProbeMuxState(port, response_value)
```

### 転送状態確認 (gRPC, Active-Active)

linkmgrd → xcvrd:
```cpp
// DbInterface.cpp:449-455  handleProbeForwardingState()
mAppDbForwardingCommandTablePtr->hset(portName, "command", "probe");
// テーブル: APPL_DB::APP_FORWARDING_STATE_COMMAND_TABLE_NAME
```

xcvrd → linkmgrd:
```cpp
// DbInterface.cpp:1831
swss::SubscriberStateTable appDbForwardingResponseTable(appDbPtr.get(), APP_FORWARDING_STATE_RESPONSE_TABLE_NAME);
// dispatch: handleForwardingResponseNotification() → processForwardingResponseNotification()
// → MuxManager::processProbeMuxState(port, response) / processPeerMuxState(port, response_peer)
```

## その他の Subscribe テーブル (handleSwssNotification)

| テーブル | DB | 用途 |
|---|---|---|
| `CFG_MUX_CABLE_TABLE_NAME` | CONFIG_DB | MUX ポートごとの設定変更通知 |
| `CFG_BGP_DEVICE_GLOBAL_TABLE_NAME` | CONFIG_DB | TSA 制御 |
| `APP_PORT_TABLE_NAME` | APPL_DB | リンク UP/DOWN 通知 |
| `APP_MUX_CABLE_RESPONSE_TABLE_NAME` | APPL_DB | xcvrd MUX 状態確認応答 |
| `APP_FORWARDING_STATE_RESPONSE_TABLE_NAME` | APPL_DB | xcvrd gRPC 転送状態応答 |
| `STATE_MUX_CABLE_TABLE_NAME` | STATE_DB | orchagent による MUX 状態更新 |
| `STATE_ROUTE_TABLE_NAME` | STATE_DB | デフォルトルート状態 |
| `MUX_CABLE_INFO_TABLE` | STATE_DB | peer の link status |
| `STATE_PEER_HW_FORWARDING_STATE_TABLE_NAME` | STATE_DB | peer の admin forwarding state |
| `STATE_ICMP_ECHO_SESSION_TABLE_NAME` | STATE_DB | ICMP echo セッション状態 |

## MUX_LINKMGR と直接関係のある Subscribe

MUX_LINKMGR テーブル自体は `CFG_MUX_LINKMGR_TABLE_NAME` のみ。xcvrd 経路は MUX_LINKMGR の内容（プローブ間隔等）が linkmgrd 内部で適用された結果として発火するが、xcvrd とのやり取りのテーブル (MUX_CABLE_COMMAND / RESPONSE 等) は MUX_LINKMGR テーブルに直接対応しない。
