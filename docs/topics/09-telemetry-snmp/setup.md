---
title: 設定
description: 設定 — 監視機能の設定は経路ごとに別の CONFIG_DB table と CLI に分かれます。ここではシナリオ別の最小手順、確認用の
  show 出力、よくある設定エラーをまとめます。項目の意味の深掘りは参照ページに任せます。
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
related:
  cli:
  - config sflow
  - config snmp
  - config syslog
  - show techsupport
  - config vrf
  config_db:
  - SNMP
  - VRF
  - SYSLOG_SERVER
  - SNMP_AGENT_ADDRESS_CONFIG
  - SFLOW
  - SFLOW_SESSION
  - SFLOW_COLLECTOR
  yang:
  - sonic-syslog
  - sonic-snmp
  - sonic-vrf
---

# 設定

監視機能の設定は経路ごとに別の [CONFIG_DB](../../reference/glossary.md#term-config_db) table と CLI に分かれます。ここではシナリオ別の最小手順、確認用の `show` 出力、よくある設定エラーをまとめます。項目の意味の深掘りは参照ページに任せます。

## シナリオ 1: SNMP v2c read-only と v3 priv user の併設

社内監視は v2c community で読ませ、外部 SaaS から触らせるアクセスだけ v3 priv で絞る、という典型構成。`snmp.yml` ベースの古い設定は廃止経路にあり、現状は CONFIG_DB の `SNMP` / `SNMP_COMMUNITY` / `SNMP_USER` を CLI 経由で更新します。

```bash
# v2c read-only
config snmp community add public ro

# v3 priv user (auth=SHA, priv=AES)
config snmp user add monitor priv AES 'PrivPass!2026' SHA 'AuthPass!2026' ro

# 監視メタデータ
config snmp location "Tokyo DC1 Rack 5"
config snmp contact admin admin@example.com

# AgentAddress を mgmt VRF 内の管理 IP に限定
config snmp agentaddress add -p 161 -v mgmt 10.0.0.10
```

CONFIG_DB 側はこういう構造になります。

```json
{
  "SNMP_COMMUNITY": {"public": {"TYPE": "RO"}},
  "SNMP_USER": {
    "monitor": {
      "SNMP_USER_TYPE": "Priv",
      "SNMP_USER_PERMISSION": "RO",
      "SNMP_USER_AUTH_TYPE": "SHA",
      "SNMP_USER_AUTH_PASSWORD": "AuthPass!2026",
      "SNMP_USER_ENCRYPTION_TYPE": "AES",
      "SNMP_USER_ENCRYPTION_PASSWORD": "PrivPass!2026"
    }
  },
  "SNMP": {"LOCATION": {"Location": "Tokyo DC1 Rack 5"}, "CONTACT": {"admin": "admin@example.com"}},
  "SNMP_AGENT_ADDRESS_CONFIG": {"10.0.0.10|161|mgmt": {}}
}
```

確認:

```bash
$ show snmp community
Communities:
  Community         Type
  ----------------  ------
  public            RO

$ show snmp user
User              Permission    Type    Auth    Encrypt
monitor           RO            Priv    SHA     AES

$ docker exec snmp snmpwalk -v3 -u monitor -l authPriv -a SHA -A 'AuthPass!2026' \
    -x AES -X 'PrivPass!2026' 127.0.0.1 sysName.0
SNMPv2-MIB::sysName.0 = STRING: sonic-tor-01
```

古い `snmp.yml` から CONFIG_DB への移行は [SNMP](../../reference/glossary.md#term-snmp) migration で扱われ、`config load_minigraph` 時に再生成されます。詳細は [SNMP migration](../../system/snmp-migration-from-snmp-yml-to-configdb.md) を参照。

## シナリオ 2: sFlow を 2 collector に同時に送る

flow ベースの可視化（NDR、Kentik など）と長期 packet sampling の両方を並行運用するパターン。[SONiC](../../reference/glossary.md#term-sonic) の sFlow は global、collector、per-port の 3 段で構成され、collector は最大 2 つまで登録できます。

```bash
config sflow enable
config sflow collector add primary   192.0.2.10 6343
config sflow collector add secondary 192.0.2.11 6343
config sflow polling-interval 20

# 全ポート default で enable、上り回線だけ sample_rate を下げる
config sflow interface enable Ethernet0
config sflow interface sample-rate Ethernet0 1024
```

CONFIG_DB:

```json
{
  "SFLOW": {"global": {"admin_state":"up", "polling_interval":"20", "sample_direction":"both"}},
  "SFLOW_COLLECTOR": {
    "primary":   {"collector_ip":"192.0.2.10","collector_port":"6343"},
    "secondary": {"collector_ip":"192.0.2.11","collector_port":"6343"}
  },
  "SFLOW_SESSION": {"Ethernet0": {"admin_state":"up","sample_rate":"1024"}}
}
```

確認:

```bash
$ show sflow
sFlow Global Information:
  sFlow Admin State:          up
  sFlow Polling Interval:     20
  sFlow AgentID:              eth0
  2 Collectors configured:
    Name: primary    IP addr: 192.0.2.10  UDP port: 6343  VRF: default
    Name: secondary  IP addr: 192.0.2.11  UDP port: 6343  VRF: default

$ show sflow interface
sFlow interface configurations
  Interface     Admin State    Sampling Rate
  ------------  -------------  ---------------
  Ethernet0     up             1024
  Ethernet1     up             50000
  ...
```

`sample_direction` の `rx` / `tx` / `both` と、interface の `sample_rate` / `admin_state` が動作を決めます。エージェントは hsflowd で、collector 設定が消えると datagram は止まります。

## シナリオ 3: Syslog を mgmt VRF 越しに 2 台へ転送

mgmt [VRF](../../reference/glossary.md#term-vrf) 経由で外部 SIEM に syslog を送る構成。management VRF を有効にしてある box では `--vrf mgmt` 指定が必須で、忘れると default VRF から DNS lookup が走って到達不能になります。

```bash
config syslog add 192.0.2.20 --vrf mgmt
config syslog add 192.0.2.21 --vrf mgmt

# global rate limit (msg/sec)
redis-cli -n 4 HSET 'SYSLOG_CONFIG|GLOBAL' rate_limit_interval 5 rate_limit_burst 100

# container 単位で severity を変える (例: bgp container だけ debug)
redis-cli -n 4 HSET 'SYSLOG_CONFIG_FEATURE|bgp' severity debug
```

確認:

```bash
$ show runningconfiguration syslog
Syslog Servers
  Server IP       Source      Port    VRF
  --------------  ----------  ------  ----
  192.0.2.20      N/A         514     mgmt
  192.0.2.21      N/A         514     mgmt

$ docker exec bgp logger -t test "syslog-egress-check"
$ tcpdump -n -i eth0 -c 4 'udp port 514'
13:24:15.001 IP 10.0.0.10.43210 > 192.0.2.20.514: SYSLOG ...
13:24:15.001 IP 10.0.0.10.43211 > 192.0.2.21.514: SYSLOG ...
```

[YANG](../../reference/glossary.md#term-yang) model は `sonic-syslog.yang`、CONFIG_DB は [`SYSLOG_SERVER`](../../reference/config-db/syslog-server.md)。

## シナリオ 4: Telemetry (gNMI server) を有効化する

dial-in / dial-out 両方をサポートする [gNMI](../../reference/glossary.md#term-gnmi) server を立ち上げます。証明書は通常 `/etc/sonic/telemetry/` 配下に置きます。

```bash
# 証明書配置
sudo cp dut.crt dut.key ca.crt /etc/sonic/telemetry/
sudo chmod 600 /etc/sonic/telemetry/dut.key

# CONFIG_DB に server 設定
redis-cli -n 4 HSET 'TELEMETRY|gnmi'  port 50051 client_auth true log_level 2
redis-cli -n 4 HSET 'TELEMETRY|certs' server_crt /etc/sonic/telemetry/dut.crt \
                                       server_key /etc/sonic/telemetry/dut.key \
                                       ca_crt     /etc/sonic/telemetry/ca.crt

sudo systemctl restart telemetry
```

確認:

```bash
$ docker ps | grep telemetry
abcd...   docker-sonic-telemetry:latest   ...   Up 30 seconds   telemetry

$ ss -tlnp | grep 50051
LISTEN 0  128  *:50051  *:*  users:(("telemetry",pid=12345,fd=7))

$ gnmi_capabilities -target_addr localhost:50051 \
    -cert /etc/sonic/telemetry/dut.crt -key /etc/sonic/telemetry/dut.key -ca /etc/sonic/telemetry/ca.crt
supported_models: <name: "openconfig-interfaces" ...>
```

gNMI client 側の使い方は [gNMI / OpenConfig 章](../10-gnmi-openconfig/setup.md) を参照。

## シナリオ 5: Auto-techsupport を coredump トリガで起動する

container の coredump や critical event をトリガに `show techsupport` を自動取得する仕組み。ディスクを食い潰さないように `max-techsupport-limit` をパーセントで制限します。

```bash
config auto-techsupport global state enabled
config auto-techsupport global max-techsupport-limit 10
config auto-techsupport global since "2 days ago"
config auto-techsupport global available-mem-threshold 10.0

# feature 単位の閾値
config auto-techsupport-feature update bgp --rate-limit-interval 600 --state enabled
```

確認:

```bash
$ show auto-techsupport global
State                         enabled
Rate Limit Interval (sec)     180
Max Techsupport Limit (%)     10.0
Min Available Memory (%)      10.0
Available Mem Threshold (%)   10.0
Since                         2 days ago

$ ls -lh /var/dump/
total 24M
-rw-r--r-- 1 root root 12M May 11 02:14 sonic_dump_sonic-tor-01_20260511_021412.tar.gz
```

## 設定が刺さらないときの切り分け

設定は CONFIG_DB に入っているが効いていないとき、確認順は次のとおりです。

1. `redis-cli -n 4 KEYS '<TABLE>|*'` で CONFIG_DB の entry が存在するか。
2. 対応 daemon (`snmpd` / `hsflowd` / `telemetry` / `rsyslogd`) が running か (`systemctl status`、`docker ps`)。
3. [APPL_DB](../../reference/glossary.md#term-appl_db) / [STATE_DB](../../reference/glossary.md#term-state_db) に反映があるか (`show <feature>` か `redis-cli -n 0/6`)。
4. syslog の該当 container に reject や parse error が出ていないか (`docker logs snmp 2>&1 | tail -50`)。

## よくある設定エラーと対処

| 症状 | 典型的な原因 | 対処 |
|---|---|---|
| `config snmp community add` 後も `snmpwalk` が timeout | snmp container が古い `snmp.yml` を読んだまま | `systemctl restart snmp` または `config save -y && config reload -y` |
| v3 user が `Unknown user name` で拒否される | auth/priv passphrase が 8 文字未満 (RFC 制約) | passphrase を 8 文字以上で再作成 |
| sFlow datagram が出ない | `SFLOW.global.admin_state=down` のまま、または collector 0 件 | `config sflow enable`、`show sflow` で collector 確認 |
| `show sflow` で polling は正常だが flow sample が来ない | `sample_rate` が大きすぎ (1 が最頻、10 億は事実上停止) | port の `sample_rate` を 4096 以下に調整 |
| syslog 転送先に届かない | mgmt VRF を使っているのに `--vrf` 未指定 | `config syslog del <ip>` のあと `--vrf mgmt` 付きで再追加 |
| gNMI server が起動するが TLS handshake が失敗 | cert chain が CA 込みでない、または `CN` が DUT FQDN と不一致 | `openssl x509 -in dut.crt -text` で SAN/CN を確認、CA を含めて再発行 |
| auto-techsupport が disk full で停止 | `max-techsupport-limit` が容量に対して大きい | 値を下げ、`/var/dump/` を手で剪定 |

機能ごとの specifics（SNMP MIB、sFlow datagram の中身、telemetry path）は次以降のページで扱います。

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

<!-- glossary-links-injected: 8ba32e5aa69d -->
