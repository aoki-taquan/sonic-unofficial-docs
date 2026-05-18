# STATE_DB PORT_TABLE — Phase D 失敗挙動調査

調査日: 2026-05-18
ソース: sonic-swss portsyncd/linksync.cpp, orchagent/portsorch.cpp

## portsyncd (linksync.cpp) の失敗パターン

### RTM_NEWLINK 到着時の書き込みスキップ

linksync.cpp:193 で `m_portTable.get(key, temp)` が false を返す場合（APP_DB に該当ポートが未登録）、STATE_DB への書き込み全体がスキップされる。このとき SWSS_LOG_NOTICE("Cannot find %s in port table") が出力されるだけで、retry 機構はない。次の RTM_NEWLINK イベントまで STATE_DB エントリは不在のまま。

### 旧インタフェースの RTM は完全無視

linksync.cpp:172-177 の m_ifindexOldNameMap チェックで旧 ifindex の RTM_NEWLINK が弾かれる。この場合 STATE_DB への書き込みも更新も発生しない。エラーログすら出ない。

## PortsOrch (portsorch.cpp) の失敗パターン

### SAI get_port_attribute 失敗 → supported_speeds 書き込みスキップ

portsorch.cpp:3145-3156 の getPortSupportedSpeeds で SAI が NOT_SUPPORTED / NOT_IMPLEMENTED を返すと supported_speeds は clear() 後に空文字列セット。フィールド不在とは異なる（空文字列として存在）。

### allPortsReady() false → refreshPortStatus 早期 return

portsorch.cpp:9617-9621 の doTask(NotificationConsumer&) で allPortsReady() が false の場合、port_state_change 通知全体がドロップ。STATE_DB の speed / fec / link_training_status が更新されないまま。この通知はキューに残らないため、起動完了前に届いた oper 変化は**永続的に失われる**（再ポーリングで補完される場合あり）。

### getPortOperStatus 失敗 → runtime_error

portsorch.cpp:9898-9901 の refreshPortStatus で SAI get_port_attribute が失敗すると `throw runtime_error("PortsOrch get port oper status failure")` でプロセスが abort する。orchagent 全体が落ちるため他テーブルへの書き込みも全停止。

### host_tx_ready 更新失敗 → "false" 残留

initHostTxReadyState (portsorch.cpp:2181) が SAI / Gearbox 失敗ケースで "false" を書いた後、setPortAdminStatus が続けて失敗した場合、"false" が残留する。"true" への更新は発生しない。

### updateDbPortOperFec 変換失敗 → "N/A"

portsorch.cpp:9920-9928 の fecToStr が false を返した場合（SAI FEC モード値が未知）、SWSS_LOG_ERROR が出力され fec_str = "N/A" でフォールバック書き込みされる。フィールドが不在になることはない。

### setPortSerdesAttribute 失敗 → phy_ctrl_unreliable_los 書き込み

portsorch.cpp:5191-5200 で setPortSerdesAttribute が失敗した場合、m_unreliable_los = false のまま STATE_DB に "false" を書く。serdes 設定失敗自体はエラーログのみで、retry なし。

## ERROR_TABLE への書き込み

linksync.cpp / portsorch.cpp のいずれも STATE_DB PORT_TABLE 関連の処理失敗時に ERROR_TABLE には書き込まない。失敗は syslog (SWSS_LOG_ERROR) のみ。
