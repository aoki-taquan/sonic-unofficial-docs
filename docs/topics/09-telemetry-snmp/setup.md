---
title: 設定
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/config-snmp.md
  - docs/reference/cli/config-sflow.md
  - docs/reference/cli/config-syslog.md
  - docs/reference/config-db/sflow.md
  - docs/reference/config-db/syslog-server.md
  - docs/reference/config-db/telemetry.md
  - docs/reference/config-db/auto-techsupport.md
  - docs/reference/yang/sonic-syslog.md
  - docs/system/snmp-migration-from-snmp-yml-to-configdb.md
---

# 設定

監視機能の設定は経路ごとに別の CONFIG_DB table と CLI に分かれます。ここでは最小限の入口だけを示し、項目の意味は参照ページに任せます。

## SNMP

SNMP は historically `snmp.yml` で設定していましたが、現在は CONFIG_DB の `SNMP` / `SNMP_COMMUNITY` / `SNMP_USER` table に移行しています。CLI は `config snmp ...` で操作します。

```bash
config snmp community add public ro
config snmp user add monitor priv aes 'A!' auth sha 'S!' ro
config snmp location "Tokyo DC1 Rack 5"
```

community / user / contact / location の追加削除と AgentAddress の制御が CLI 入口です。古い `snmp.yml` から CONFIG_DB への移行は SNMP migration で扱われており、`config load_minigraph` 時に再生成されます。

## sFlow

sFlow は `SFLOW` global、`SFLOW_SESSION` per-port、`SFLOW_COLLECTOR` の 3 系統で設定します。

```bash
config sflow enable
config sflow collector add c0 192.0.2.10 6343
config sflow interface enable Ethernet0
config sflow polling-interval 20
```

`SFLOW.global.sample_direction` の `rx` / `tx` / `both` と、interface の `sample_rate` / `admin_state` が動作を決めます。エージェントは hsflowd で、collector 設定が消えると datagram は止まります。

## Syslog

`SYSLOG_SERVER` に外部 syslog 転送先を登録します。VRF（management VRF など）を選べる点が特徴です。

```bash
config syslog add 192.0.2.20 --vrf mgmt
```

`SYSLOG_CONFIG` で global rate limit や severity を制御し、`SYSLOG_CONFIG_FEATURE` で container 単位の severity を切り替えられます。YANG model は `sonic-syslog.yang` で定義されます。

## Telemetry (gNMI server)

gNMI server の設定は `TELEMETRY` / `GNMI` table が持ちます。デフォルトでは port 8080 で起動し、`certs` 配下の証明書を読みます。`TELEMETRY|gnmi.port`、`TELEMETRY|certs.*` の値を変更し、`systemctl restart telemetry` または `systemctl restart gnmi` で反映します。

gNMI 側の運用（OpenConfig path、subscribe mode、authentication）は管理プレーン側の章（gNMI / gNOI / OpenConfig / YANG）で扱う想定です。ここでは server を起動するための最小設定として参照します。

## Auto-techsupport

`AUTO_TECHSUPPORT|global` で機能の有効化、coredump や critical event をトリガにした `show techsupport` の自動実行を設定します。`AUTO_TECHSUPPORT_FEATURE|<feature>` で機能単位の閾値や rate limit を分離できます。

```bash
config auto-techsupport global state enabled
config auto-techsupport global max-techsupport-limit 10
config auto-techsupport global since "2 days ago"
```

ディスクの圧迫を避けるため、`max-techsupport-limit` と `available-mem-threshold` を実機の容量に合わせます。

## 設定が刺さらないとき

設定は CONFIG_DB に入っているが効いていないとき、確認順は次のとおりです。

1. `redis-cli -n 4 KEYS '<TABLE>|*'` で CONFIG_DB の entry が存在するか。
2. 対応 daemon (`snmpd` / `hsflowd` / `telemetry` / `rsyslogd`) が running か（`systemctl status`、`docker ps`）。
3. APPL_DB / STATE_DB に反映があるか（`show <feature>` か `redis-cli -n 0/6`）。
4. syslog の該当 container に reject や parse error が出ていないか。

機能ごとの specifics（SNMP MIB、sFlow datagram、telemetry path）は次以降のページで扱います。

## 関連ページ

- [config snmp CLI](../../reference/cli/config-snmp.md)
- [config sflow CLI](../../reference/cli/config-sflow.md)
- [config syslog CLI](../../reference/cli/config-syslog.md)
- [SFLOW table](../../reference/config-db/sflow.md)
- [SYSLOG_SERVER table](../../reference/config-db/syslog-server.md)
- [TELEMETRY table](../../reference/config-db/telemetry.md)
- [AUTO_TECHSUPPORT table](../../reference/config-db/auto-techsupport.md)
- [sonic-syslog YANG](../../reference/yang/sonic-syslog.md)
- [SNMP yml から CONFIG_DB への移行](../../system/snmp-migration-from-snmp-yml-to-configdb.md)
