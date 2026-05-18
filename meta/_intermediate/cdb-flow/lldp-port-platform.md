# プラットフォーム差分調査: LLDP_PORT (Phase H)

調査日: 2026-05-18  
対象ソース:
- `sonic-buildimage/dockers/docker-lldp/lldpmgrd`
- `sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2`
- `sonic-buildimage/dockers/docker-lldp/supervisord.conf.j2`

## 調査結果

### ASIC 種別による影響

`LLDP_PORT` の処理は `lldpmgrd` (Python) + `lldpd` (open-lldp フォーク) のユーザー空間スタックで完結し、SAI を経由しない。したがって ASIC 種別（Broadcom / Mellanox / Marvell / Innovium 等）は `LLDP_PORT` の挙動に影響を与えない。

`lldpmgrd` 内に `sai.profile`・`SAI_SWITCH_ATTR`・platform 文字列を参照するコードは存在しない。

### multi-asic (namespace) における挙動差

`supervisord.conf.j2` の `namespace_id` 分岐により、namespace 内の `lldpd` は eth0 を管理対象から除外する:

```jinja2
{% if namespace_id is defined and namespace_id|length %}
command=/usr/sbin/lldpd -d -I Ethernet[0-9]* -C Ethernet[0-9]*
{% else %}
command=/usr/sbin/lldpd -d -I Ethernet[0-9]*,eth0 -C eth0
{% endif %}
```

`lldpd.conf.j2` にも対応する分岐があり、namespace 内では eth0 の portidsubtype 設定がスキップされる:

```jinja2
{% if not (namespace_id is defined and namespace_id|length) %}
configure ports eth0 lldp portidsubtype local {{ mgmt_if.port_name }}
{% endif %}
```

`LLDP_PORT|<Ethernet*>` のフロントエンドポートに対する `lldpmgrd` の処理ロジック（`generate_pending_lldp_config_cmd_for_port` / `process_pending_cmds`）は namespace の有無によらず同一。ただし multi-asic 構成では各 namespace の `lldpmgrd` インスタンスが独立して稼働するため、`LLDP_PORT` エントリは該当 namespace の CONFIG_DB に書く必要がある。

### VOQ chassis における hostname 解決

`lldpmgrd` は `DEVICE_METADATA|localhost` の `chassis_hostname` を `hostname` より優先する:

```python
# lldpmgrd:253
hostname = device_dict.get("chassis_hostname") or device_dict.get("hostname")
```

VOQ chassis 構成では `chassis_hostname` が設定され、line card ホスト名ではなくシャーシ全体名が LLDP System Name TLV に使われる。`LLDP_PORT` テーブル自体の処理には直接影響しないが、同一デーモン内で管理される。

### backplane / inband / recirc インターフェース

`lldpmgrd` は `LLDP_PORT` に書かれていても以下の prefix を持つポートはスキップする（プラットフォーム非依存の共通ロジック）:

```python
# lldpmgrd:141-142
if any([port_name.startswith(inband_prefix()),
        port_name.startswith(recirc_prefix()),
        port_name.startswith(backplane_prefix())]):
    return
```

これらの prefix は `sonic_py_common.interface` が返すプラットフォーム共通値であり、ASIC 種別によらず同一の除外ロジックが適用される。

## 結論

| 観点 | 結果 |
|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell 等) | 影響なし |
| multi-asic (namespace あり) | eth0 管理除外・per-namespace 独立インスタンス |
| VOQ chassis | `chassis_hostname` 優先（System Name TLV に影響、LLDP_PORT 処理には非影響） |
| SmartSwitch | community master に SmartSwitch 固有 LLDP_PORT 分岐なし |
