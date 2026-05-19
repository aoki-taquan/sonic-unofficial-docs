# state-db-port Phase H — プラットフォーム差異調査メモ

調査対象:
- sonic-swss/orchagent/portsorch.cpp
- sonic-swss/portsyncd/linksync.cpp

調査日: 2026-05-19

## linksync.cpp の結論

switch_type / voq / chassis / platform 参照なし。
STATE_DB PORT_TABLE への書き込みは全プラットフォームで同一コードパス。

## portsorch.cpp のプラットフォーム分岐

### 1. CMIS 対応 ASIC — host_tx_ready の制御方式が変わる

gMySwitchType != "dpu" かつ SAI が以下の両属性をサポートする場合に
m_cmisModuleAsicSyncSupported = true が成立 (portsorch.cpp:969-972):
- SAI_SWITCH_ATTR_PORT_HOST_TX_READY_NOTIFY (create_implemented == true)
- SAI_PORT_ATTR_HOST_TX_SIGNAL_ENABLE (set_implemented == true)

この場合:
- setPortAdminStatus() 内で host_tx_ready を直接書かない (portsorch.cpp:2220)
- SAI コールバック on_port_host_tx_ready (portsorch.cpp:977) 経由でのみ書く
- STATE_DB TRANSCEIVER_INFO を購読して CMIS モジュール存在を確認 (portsorch.cpp:984)

非 CMIS 環境:
- admin UP + SAI set 成功 + Gearbox OK で host_tx_ready = "true" を直接書く (portsorch.cpp:2254)

### 2. Gearbox (外付け PHY) — host_tx_ready に条件追加

isGearboxEnabled() が true の環境では、setPortAdminStatus() での host_tx_ready = "true"
セットに Gearbox の成功確認 (gbstatus == true) が追加条件になる (portsorch.cpp:2246)。
Gearbox なし環境ではこの条件はスキップされる。

### 3. switch_type == "dpu" — バッファ/キュー初期化スキップ

DPU 構成では以下がスキップされる:
- initializePortBufferMaximumParameters() (portsorch.cpp:6449-6452)
- initializePriorityGroupsBulk() / initializeQueuesBulk() / initializeSchedulerGroupsBulk() (portsorch.cpp:6589-6594)
- SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID / DEFAULT_VLAN_ID 取得 (portsorch.cpp:987-1035)
- getSystemPorts() / removeDefaultVlanMembers() / removeDefaultBridgePorts() (portsorch.cpp:1043-1051)
- FDB イベント通知 (portsorch.cpp:1056-1082)
- autoneg FEC モード override / oper FEC mode SAI capability クエリ (portsorch.cpp:987-1011)

これらはいずれも STATE_DB PORT_TABLE への書き込みとは間接的な関係であり、
DPU では supported_speeds / fec / supported_fecs / rmt_adv_speeds などが
書き込まれない可能性がある。ただし portsyncd 側の 4 フィールド
(state / admin_status / netdev_oper_status / mtu) は全プラットフォームで書かれる。

### 4. switch_type == "voq" — システムポートとの連携

VOQ 構成では addSystemPorts() が追加呼び出しされ、リモートシステムポート向けの
port エントリも portsorch 内で管理される。ただしシステムポートは CHASSIS_APP_DB 由来であり、
STATE_DB PORT_TABLE には物理ポート (Port::PHY) のみ書き込まれる (portsorch.cpp:11033)。
updateSystemPort() は VOQ かつ Port::PHY の場合のみシステムポート属性を更新する。

### 5. Mellanox (MLNX) プラットフォーム — PORT_TABLE への影響なし

isMlnxPlatform() が true の場合、FLEX_COUNTER_DB の trim stat プラグインが
異なる設定になる (portsorch.cpp:858-863)。
これは STATE_DB PORT_TABLE フィールドには影響しない。

### 6. phy_ctrl_unreliable_los — serdes 設定がある環境のみ書き込まれる

phy_ctrl_unreliable_los フィールドは pCfg.serdes.unreliable_los.is_set が true の場合のみ
setPortSerdesAttribute() 経由で書き込まれる (portsorch.cpp:5182-5200)。
この設定は主に Mellanox serdes 設定ファイルが存在するプラットフォームで現れる。
is_set が false のプラットフォームではフィールドが書き込まれない（不在のまま）。

## 結論

| フィールド | プラットフォーム差 | 詳細 |
|-----------|-----------------|------|
| state / admin_status / netdev_oper_status / mtu | なし | linksync.cpp は全プラットフォーム共通 |
| speed / fec / supported_fecs / rmt_adv_speeds / link_training_status | DPU で不在になりうる | autoneg / oper_fec SAI capability クエリが DPU でスキップされるため |
| host_tx_ready | CMIS / Gearbox 依存 | m_cmisModuleAsicSyncSupported が true かどうかで書き込みパスが変わる |
| phy_ctrl_unreliable_los | serdes 設定依存 | is_set フラグが true のプラットフォームでのみ書き込まれる |
| supported_speeds | SAI 実装依存 | SAI NOT_SUPPORTED 時は空文字 / フィールド不在 |
