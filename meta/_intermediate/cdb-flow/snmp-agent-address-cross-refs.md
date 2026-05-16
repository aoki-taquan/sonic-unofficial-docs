# snmp-agent-address-config — Phase C: Cross-Refs スキャン記録

## スキャン対象

- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` (template)
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` (L2308-2324)
- `sonic-utilities/config/main.py` (L4130-4210)
- `sonic-host-services/scripts/hostcfgd` (grep: SNMP_AGENT_ADDRESS)

## 発見した暗黙参照

### 1. snmpd.conf.j2 が CONFIG_DB から直接読む関連テーブル

テンプレートは `SNMP_AGENT_ADDRESS_CONFIG` の他に以下も読む:

- `SNMP_COMMUNITY` — `rocommunity` / `rwcommunity` 行生成 (L48-64)
- `SNMP_USER` — `rouser` / `rwuser` / `CreateUser` 行生成 (L66-77)
- `SNMP` — `sysLocation` / `sysContact` 行生成 (L88-97)
- `SNMP_TRAP_CONFIG` — `trapsink` / `trap2sink` / `informsink` 行生成 (L145-173)

### 2. CLI (config/main.py) の暗黙読み出し

`config snmp agentaddress add` 実行時:
- `MGMT_VRF_CONFIG|vrf_global` を読み `mgmtVrfEnabled` を確認 (L4153-4157)
  - `true` のとき `-v` 省略を CLI で拒否
- `netifaces.interfaces()` でホスト NIC の IP 一覧を取得 (L4160-4171)
  - 指定 IP が NIC に存在しない場合は書き込みを拒否

### 3. minigraph.py の暗黙依存 (L2308-2322)

`sonic-cfggen -m <minigraph>` による自動生成時:
- `MGMT_INTERFACE` のキー一覧 (管理 IP/prefix) を解析して `SNMP_AGENT_ADDRESS_CONFIG` を生成
- `LOOPBACK_INTERFACE` のキー一覧 (Loopback0 IP) を同様に解析
- `is_multi_asic()` が True の場合は空辞書になり自動生成されない
- `MGMT_VRF_CONFIG` (`mvrf`) は同一 results dict に入るが SNMP_AGENT_ADDRESS_CONFIG の key 生成には直接使わない

### 4. hostcfgd は SNMP_AGENT_ADDRESS_CONFIG を購読しない (確認済み)

```
grep -n "SNMP_AGENT_ADDRESS" sonic-host-services/scripts/hostcfgd
→ 0 件
```

`docker-snmp` コンテナの `snmpd.conf.j2` テンプレートが CONFIG_DB を直接読む設計であり、
hostcfgd 経由のフローは存在しない。

## 結論

| 参照元 | 参照先テーブル | 参照タイミング | 用途 |
|---|---|---|---|
| `snmpd.conf.j2` | `SNMP` | 起動時テンプレート生成 | sysLocation / sysContact |
| `snmpd.conf.j2` | `SNMP_COMMUNITY` | 起動時テンプレート生成 | rocommunity / rwcommunity |
| `snmpd.conf.j2` | `SNMP_USER` | 起動時テンプレート生成 | rouser / rwuser / CreateUser |
| `snmpd.conf.j2` | `SNMP_TRAP_CONFIG` | 起動時テンプレート生成 | trapsink / trap2sink |
| `config/main.py` | `MGMT_VRF_CONFIG` | CLI add 時 | mgmtVrfEnabled チェック |
| `minigraph.py` | `MGMT_INTERFACE` | minigraph 変換時 | 管理 IP から SNMP key を自動生成 |
| `minigraph.py` | `LOOPBACK_INTERFACE` | minigraph 変換時 | Loopback0 IP から SNMP key を自動生成 |
