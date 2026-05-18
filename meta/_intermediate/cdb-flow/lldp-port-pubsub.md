# lldp-port — pubsub 調査メモ (Phase G)

調査日: 2026-05-18  
ソース: `sonic-buildimage/dockers/docker-lldp/lldpmgrd`, `supervisord.conf.j2`

## 結論

`LLDP_PORT` テーブルは **lldpmgrd に直接購読されていない**。lldpmgrd が使う通信メカニズムは以下の通り。

## lldpmgrd の購読メカニズム

```python
# lldpmgrd:298-325
sel = swsscommon.Select()

# APPL_DB PORT_TABLE — PortInitDone / PortConfigDone + oper_status
sst_appdb = swsscommon.SubscriberStateTable(self.appl_db, swsscommon.APP_PORT_TABLE_NAME)
sel.addSelectable(sst_appdb)

# CONFIG_DB MGMT_INTERFACE — 管理 IP 変化
sst_mgmt_ip_confdb = swsscommon.SubscriberStateTable(self.config_db, swsscommon.CFG_MGMT_INTERFACE_TABLE_NAME)
sel.addSelectable(sst_mgmt_ip_confdb)

# CONFIG_DB DEVICE_METADATA — hostname / chassis_hostname 変化
sst_device_confdb = swsscommon.SubscriberStateTable(self.config_db, swsscommon.CFG_DEVICE_METADATA_TABLE_NAME)
sel.addSelectable(sst_device_confdb)
```

- `LLDP_PORT` テーブルは `SubscriberStateTable` に登録されていない
- `lldpmgrd` は Redis keyspace notification を一切使わない
- CONFIG_DB への `LLDP_PORT` 書込みは lldpmgrd に届かない（構造的 no-op）

## 起動時読み取り (one-shot)

- `lldpd.conf.j2` テンプレート: `DEVICE_METADATA`, `MGMT_INTERFACE`, `MGMT_PORT` を `sonic-cfggen -d` で一括読み取り
- コンテナ起動時のみ。以後は lldpmgrd SubscriberStateTable で追従

## ポート設定の実際の経路

`LLDP_PORT` の enabled/mode フィールドは lldpd に届かない。ポートの LLDP 動作は以下の経路で間接制御される:

1. `APPL_DB PORT_TABLE oper_status=up` イベント → lldpmgrd がポート設定 lldpcli コマンドを発行
2. lldpcli コマンドは `CONFIG_DB PORT.alias` / `PORT.description` を参照（`LLDP_PORT` フィールドは不使用）

## Redis Pub/Sub の使用状況

- lldpmgrd: `swsscommon.Select` + `SubscriberStateTable`（APPL_DB PORT, CONFIG_DB DEVICE_METADATA, MGMT_INTERFACE）
- Redis native `keyspace notification` / `psubscribe`: 不使用
- `LLDP_PORT` への keyspace notification 購読: なし
