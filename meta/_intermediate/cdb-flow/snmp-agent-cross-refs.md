# snmp-agent cross-refs (Phase C)

## 調査対象

`SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_USER` テーブルからの暗黙クロス参照

## 調査ソース

- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` 全行精読 (2026-05-17)
- `sonic-buildimage/dockers/docker-snmp/supervisord.conf.j2` 全行精読 (2026-05-17)
- `sonic-utilities/config/main.py` L4095–4210, L4709–4800 精読 (2026-05-17)
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` L2308–2324 精読 (2026-05-17)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang` 全体精読 (2026-05-17)

## SNMP_AGENT_ADDRESS_CONFIG の暗黙参照

### 1. MGMT_VRF_CONFIG — CLI 経路での VRF チェック

`config snmp agentaddress add <ip>` 実行時に `-v` オプションを省略した場合、
CLI (`config/main.py:4154-4157`) は `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled` を参照し、
Management VRF が有効になっているにもかかわらず VRF 未指定の場合はエラーで早期リターンする。

YANG leafref なし。実装のみの暗黙依存。

### 2. MGMT_INTERFACE / LOOPBACK_INTERFACE — minigraph 経路での自動生成

`minigraph.py:2308-2322` は `MGMT_INTERFACE` と `LOOPBACK_INTERFACE` のアドレス一覧を元に
`SNMP_AGENT_ADDRESS_CONFIG` エントリを自動生成する。
multi-asic 環境では自動生成が行われず空辞書となる。

### 3. DEVICE_METADATA.localhost.switch_type — supervisord.conf.j2 経由

`supervisord.conf.j2:53-57` が `DEVICE_METADATA['localhost']['switch_type']` を参照して
`snmp-subagent` の起動コマンドを切り替える。`SNMP_AGENT_ADDRESS_CONFIG` テーブル自身は
このパスに関与しないが、`docker-snmp` コンテナ起動の前提テーブルとして依存する。

## SNMP_USER の暗黙参照

### 1. SNMP_COMMUNITY — snmpd.conf.j2 での隣接テーブル展開

`snmpd.conf.j2` は同一テンプレートで `SNMP_COMMUNITY`（v1/v2c）と `SNMP_USER`（v3）を
展開する。両テーブルの有無は独立して判定される（`{% if SNMP_COMMUNITY is defined %}`、
`{% if SNMP_USER is defined %}`）。

YANG leafref なし。`SNMP_USER` 自身は `SNMP_COMMUNITY` を参照しないが、
snmpd.conf テンプレートの意味上は v3 アクセスには `SNMP_USER`、v1/v2c アクセスには
`SNMP_COMMUNITY` が必要という前提がある。

### 2. DEVICE_METADATA.localhost — snmpd 起動共通前提

`supervisord.conf.j2:53-57` が `DEVICE_METADATA['localhost']['switch_type']` を必須参照する。
`SNMP_USER` の存在有無にかかわらず、`DEVICE_METADATA.localhost` が CONFIG_DB に
存在しない場合は docker-snmp コンテナ自体が起動しない。

## 結論

両テーブルともに YANG leafref は持たない。クロス参照はすべてテンプレートエンジン / CLI / minigraph の
実装レベルのみに存在する。
