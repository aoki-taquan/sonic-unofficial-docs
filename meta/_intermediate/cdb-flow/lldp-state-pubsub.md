# lldp-state Phase G (pubsub) 調査証跡

## 対象ページ

`docs/reference/config-db/lldp-state.md`

## 調査ソース

- `sonic-snmpagent/src/sonic_ax_impl/mibs/ieee802_1ab.py` — LocPortUpdater, LLDPRemManAddrUpdater, LLDPRemTableUpdater, LLDPLocalSystemDataUpdater
- `sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py` — get_redis_pubsub(), poll_lldp_entry_updates()
- `sonic-mgmt-common/translib/lldp_app.go` — translateSubscribe(), processSubscribe()
- `sonic-buildimage/dockers/docker-lldp/lldpmgrd` — LldpManager.run(), SubscriberStateTable usage

## 主要な知見

### sonic-snmpagent の keyspace 購読

LocPortUpdater (L252-254) と LLDPRemManAddrUpdater (L570-572) は `get_redis_pubsub()` を使って
`__keyspace@{APPL_DB}__:LLDP_ENTRY_TABLE:*` を `psubscribe` でパターン購読する。

poll_lldp_entry_updates() (L75-97) でメッセージを消費し:
- `msg["channel"].split(":")[-1]` でインタフェース名を取得
- `msg["data"]` に "set" / "del" が含まれるかで操作種別を判別

### LLDPRemTableUpdater はポーリング

SNMP walk のたびに `update_data()` が呼ばれ `hgetall` で全エントリを再取得する。keyspace 通知は使わない。

### LLDPLocalSystemDataUpdater はポーリング

`reinit_data()` で LLDP_LOC_CHASSIS を dbs_get_all で取得。`update_data()` は pass 実装（no-op）。
MIBUpdater の reinit サイクル（デフォルト 1 分）で更新される。

### lldp_app.go は gNMI Subscribe 非対応

translateSubscribe() → emptySubscribeResponse()
processSubscribe() → tlerr.New("not implemented")

REST/gNMI での LLDP 情報取得は GET のみ対応。Subscribe には非対応。

### lldpmgrd の間接購読

lldpmgrd は LLDP_ENTRY_TABLE を直接購読しない。以下を SubscriberStateTable + Select (timeout=10000ms) で購読:
- APP_PORT_TABLE (APPL_DB): PortInitDone / PortConfigDone
- CFG_MGMT_INTERFACE_TABLE (CONFIG_DB): 管理 IP 変更
- CFG_DEVICE_METADATA_TABLE (CONFIG_DB): hostname / chassis_hostname 変更

変化を検知すると lldpcli コマンドを発行し lldpd を更新 → lldp-syncd が差分を APPL_DB に書き込む（間接パス）。
