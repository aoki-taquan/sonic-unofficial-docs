# LLDP / LLDP_PORT — Phase H プラットフォーム差 調査メモ

調査対象:
- `sonic-buildimage/dockers/docker-lldp/lldpmgrd`
- `sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2`
- `sonic-buildimage/dockers/docker-lldp/supervisord.conf.j2`
- `sonic-buildimage/dockers/docker-lldp/lldpdSysDescr.conf.j2`

調査日: 2026-05-18

## multi-asic (namespace) における挙動差

`supervisord.conf.j2` に namespace 分岐が存在する:

```jinja2
{% if namespace_id is defined and namespace_id|length %}
command=/usr/sbin/lldpd -d -I Ethernet[0-9]* -C Ethernet[0-9]*
{% else %}
command=/usr/sbin/lldpd -d -I Ethernet[0-9]*,eth0 -C eth0
{% endif %}
```

- **非 multi-asic (namespace_id 未設定)**: `lldpd -I Ethernet[0-9]*,eth0 -C eth0`
  — eth0 (management port) を含む全インタフェースが LLDP 対象。`eth0` が chassis ID 源泉として使われる。
- **multi-asic / namespace あり**: `lldpd -I Ethernet[0-9]* -C Ethernet[0-9]*`
  — eth0 を除外。各 namespace (asic0/asic1...) の lldpd インスタンスがフロントエンドポートのみを管理する。管理 IP の TLV は送出されない（MGMT_INTERFACE が namespace namespace_id に見えないため）。

`lldpd.conf.j2` にも:

```jinja2
{% if not (namespace_id is defined and namespace_id|length) %}
configure ports eth0 lldp portidsubtype local {{ mgmt_if.port_name }}
{% endif %}
```

— namespace 内ではこのブロックがスキップされ、eth0 の portidsubtype 設定が行われない。

## chassis_hostname

`lldpmgrd` の hostname 解決で `chassis_hostname` が優先される:

```python
hostname = device_dict.get("chassis_hostname") or device_dict.get("hostname")
```

VOQ chassis 等では `DEVICE_METADATA|localhost.chassis_hostname` が設定され、line card ホスト名ではなくシャーシ全体名が LLDP TLV に載る。

## is_frontend_port_present_in_host

```python
if device_info.is_frontend_port_present_in_host():
    self.log_error(...)
```

`PORT_INIT_TIMEOUT` 超過時の ERROR ログ出力を制御する条件。multi-asic 構成でフロントエンドポートが present でない場合 (management-only ホスト等) はエラーログなしでタイムアウト処理される。

## ASIC 種別による影響

LLDP は SAI 非経由 (lldpd ユーザー空間デーモン) で動作するため、ASIC 種別 (Broadcom / Mellanox / Marvell 等) は原理的に無関係。`sai.profile` / SAI capability query も参照しない。

## 結論

| 観点 | 影響 | 根拠 |
|------|------|------|
| ASIC 種別 | なし | SAI 非経由 |
| multi-asic (namespace) | あり | supervisord / lldpd.conf.j2 の namespace_id 分岐 |
| VOQ chassis | 部分あり | chassis_hostname 優先解決 |
| SmartSwitch | 不明 (調査対象外) | — |
