# Phase H — LLDP_ENTRY_TABLE / LLDP_LOC_CHASSIS (APPL_DB) プラットフォーム差スキャンノート

調査対象: `APPL_DB:LLDP_ENTRY_TABLE` / `APPL_DB:LLDP_LOC_CHASSIS`
Consumer: `lldp-syncd` (書き手), `sonic-snmpagent` (`ieee802_1ab.py`), `sonic-mgmt-common/translib/lldp_app.go` (読み手)
スキャン範囲:
- `sonic-buildimage/dockers/docker-lldp/supervisord.conf.j2`
- `sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2`
- `sonic-buildimage/dockers/docker-lldp/lldpmgrd`
- `sonic-snmpagent/src/sonic_ax_impl/mibs/ieee802_1ab.py`
- `sonic-mgmt-common/translib/lldp_app.go`

---

## 1. multi-asic (namespace モード) — lldpd 起動オプション差

`supervisord.conf.j2` L52-56:

```jinja2
{% if namespace_id is defined and namespace_id|length %}
command=/usr/sbin/lldpd -d -I Ethernet[0-9]* -C Ethernet[0-9]*
{% else %}
command=/usr/sbin/lldpd -d -I Ethernet[0-9]*,eth0 -C eth0
{% endif %}
```

- **multi-asic (namespace_id あり)**: lldpd が `Ethernet[0-9]*` のみ監視。`eth0` (管理ポート) は除外される。各 ASIC namespace で独立した lldp コンテナが起動し、それぞれ独自の `LLDP_ENTRY_TABLE` を APPL_DB に書き込む。
- **single-asic**: lldpd が `Ethernet[0-9]*` + `eth0` を監視。eth0 の LLDP 情報も `LLDP_ENTRY_TABLE` に書き込まれる。

## 2. multi-asic — lldpd.conf.j2 の eth0 portid 設定スキップ

`lldpd.conf.j2` L15:

```jinja2
{% if not (namespace_id is defined and namespace_id|length) %}
configure ports eth0 lldp portidsubtype local {{ alias or port_name }}
{% endif %}
```

multi-asic 環境では eth0 の `portidsubtype local` 設定が生成されない（eth0 を lldpd が管理しないため不要）。

## 3. multi-asic — sonic-snmpagent の OID 重複問題とワークアラウンド

`ieee802_1ab.py` L449-455 のコメント:

> For multi-asic platform, it can happen that same interface index result is seen in SNMP walk, with a different remote time mark. To avoid repeating the data of same interface index with different remote time mark, remote time mark is made as 0 in the OID indexing.

multi-asic 環境では複数 namespace の LLDP_ENTRY_TABLE を統合して SNMP ウォークすると、同一の ifIndex が異なる namespace の timeMark で重複することがある。sonic-snmpagent はこれを `time_mark = 0` ハードコードで回避している（`lldp_rem_time_mark` フィールドの実際値は OID 計算に使わない）。

## 4. multi-asic — sonic-snmpagent の Namespace 対応 API

sonic-snmpagent は `Namespace.init_namespace_dbs()` / `Namespace.get_sync_d_from_all_namespace()` を使って全 ASIC namespace の APPL_DB を横断取得する。

- `LLDPRemTableUpdater.reinit_data()` → `Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_interface_tables, ...)` で全 namespace のポート OID マップを構築
- `LLDPLocalSystemDataUpdater` / `LocPortUpdater` / `LLDPRemManAddrUpdater` も同様に `Namespace.init_namespace_dbs()` で接続プールを初期化

single-asic では namespace は 1 つだけ存在するため、動作は実質的に同じ。

## 5. multi-asic — lldpmgrd の inband / recirc / backplane インタフェーススキップ

`lldpmgrd` L143-145:

```python
if any([port_name.startswith(inband_prefix()),
        port_name.startswith(recirc_prefix()),
        port_name.startswith(backplane_prefix())]):
    continue
```

multi-asic 環境ではチップ間通信用の internal port (`Rec0`, `Eth-IB*`, `BP*` 等) が PORT テーブルに存在するが、lldpmgrd はこれらを LLDP 設定対象から除外する。これらポートは LLDP_ENTRY_TABLE のキーとしても現れない設計。

## 6. multi-asic — `is_frontend_port_present_in_host()` による timeout 処理分岐

`lldpmgrd` L365:

```python
if device_info.is_frontend_port_present_in_host():
    logger.log_error("PORT_INIT_TIMEOUT...")
```

PORT_INIT_TIMEOUT (300 秒) 超過時にフロントエンドポートが存在しない場合（multi-asic の non-frontend namespace 等）はエラーログなしで `lldpcli resume` を実行する。フロントエンドポートが存在する namespace ではエラーログ付きで強制 resume。

## 7. SAI / ASIC 種別の依存

LLDP は SAI 非経由。lldpd が OS の netdev + lldpcli UNIX ソケット経由でデータプレーンとやり取りするため、Broadcom / Mellanox / Marvell / Innovium 等の ASIC 種別に依存しない。`LLDP_ENTRY_TABLE` の内容も ASIC 種別を反映しない。

## 8. lldp_app.go (sonic-mgmt-common) の namespace 対応

`lldp_app.go` の `getLldpInfoFromDB()` は `db.GetTable(neighTs)` を single DB 接続で呼び出す。multi-asic での namespace 間集約はトランスポート層 (gnmi-server / rest-server) で制御されるため、lldp_app.go 自体には namespace 分岐コードがない。

---

## 順序依存サマリ (プラットフォーム軸)

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell 等) | **影響なし** | LLDP は SAI 非経由。lldpd が OS netdev を直接操作 |
| multi-asic (namespace_id あり) | **影響あり**: lldpd 起動オプション差・eth0 除外・各 namespace 独立動作・SNMP OID 重複ワークアラウンド・inband/recirc/backplane スキップ | `supervisord.conf.j2:52-56`, `lldpd.conf.j2:15`, `ieee802_1ab.py:449-455`, `lldpmgrd:143-145` |
| VOQ chassis (supervisor + line cards) | 各 host で独立動作 | LLDP テーブルは host/namespace スコープ。集中管理機構なし |
| ベンダー固有 lldpd 拡張 | なし (community master) | community SONiC は open-lldp フォークのみ。ベンダー hook 注入箇所なし |
| VS (virtual switch / KVM) | **動作制限あり**: 物理 LLDPDU 送受信不可 | VS では NIC が LLDP PDU を pass-through しないため、`LLDP_ENTRY_TABLE` は空になる場合が多い。sonic-mgmt-common テスト環境でのみ mock table を使用 |
