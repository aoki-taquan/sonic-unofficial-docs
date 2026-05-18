# STATE_DB PORT_TABLE — 暗黙テーブル参照調査 (Phase C)

## 調査対象

- `sonic-swss/portsyncd/linksync.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

## linksync.cpp の暗黙参照

### APP_DB `PORT_TABLE` (APP_PORT_TABLE_NAME)

`LinkSync::onMsg()` は RTM_NEWLINK / RTM_DELLINK 受信時に `m_portTable.get(key, temp)` を呼び出し、APPL_DB `PORT_TABLE` に該当キーが存在するかを確認する (linksync.cpp:193)。
- 存在する → STATE_DB `PORT_TABLE` に `state / admin_status / mtu / netdev_oper_status` を書き込む
- 存在しない → `"Cannot find %s in port table"` ログを出してスキップ

つまり `portsyncd` の STATE_DB 書き込みは、orchagent が APPL_DB に PORT エントリを書き込んでいることを前提とする。

## portsorch.cpp の暗黙参照

### APPL_DB `PORT_TABLE` (APP_PORT_TABLE_NAME)

`PortsOrch` 自身が `m_portTable` (`Table(db, APP_PORT_TABLE_NAME)`) として保持し、PortConfigDone / PortInitDone の確認や warm start 状態の読み出しに使用する (portsorch.cpp:770, 4342-4403)。

### STATE_DB `TRANSCEIVER_INFO` (STATE_TRANSCEIVER_INFO_TABLE_NAME)

`m_cmisModuleAsicSyncSupported` が true の環境では、`PortsOrch` が `SubscriberStateTable(stateDb, STATE_TRANSCEIVER_INFO_TABLE_NAME)` を購読する (portsorch.cpp:984)。
- `TRANSCEIVER_INFO` の SET/DEL イベントを受けて `doTransceiverPresenceCheck()` を呼び出す
- このコールバックが `host_tx_ready` フィールドの書き込みを制御する (portsorch.cpp:2274, on_port_host_tx_ready コールバック経由)

### APPL_DB `_GEARBOX_TABLE`

Gearbox が有効 (`m_gearboxEnabled = true`) な場合、portsorch は `_GEARBOX_TABLE` に oper speed を書き込み (portsorch.cpp:3422) かつ `GearboxUtils::isGearboxEnabled()` で設定の有無を確認する (portsorch.cpp:10375-10376)。Gearbox 有効時は `setPortAdminStatus()` の Gearbox 側ステータスも待つ (portsorch.cpp:2246)。

### WarmStart (CONFIG_DB `WARM_RESTART` テーブル)

`PortsOrch` コンストラクタで `WarmStart::isWarmStart()` を呼び出し (portsorch.cpp:753)、warm start モードかどうかに応じて初期化フローを分岐させる。warm start 時は既存 APPL_DB エントリから oper_status を読み出してポートを復元する (portsorch.cpp:6610-6618)。
