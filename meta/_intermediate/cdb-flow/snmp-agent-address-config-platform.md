# snmp-agent-address-config — Phase H: プラットフォーム差異

調査日: 2026-05-17  
スキャン対象: `sonic-buildimage/dockers/docker-snmp/`, `sonic-buildimage/src/sonic-config-engine/minigraph.py`, `sonic-buildimage/dockers/docker-snmp/supervisord.conf.j2`

## 調査結果

### single-ASIC vs. multi-ASIC

`minigraph.py:2312-2324` に明示的な分岐がある。

```python
if not is_multi_asic() and asic_name is None:
    results['SNMP_AGENT_ADDRESS_CONFIG'] = {}
    port = '161'
    for intf in list(mgmt_intf.keys()) + list(lo_intfs.keys()):
        ...
        results['SNMP_AGENT_ADDRESS_CONFIG'][snmp_key] = {}
else:
    results['SNMP_AGENT_ADDRESS_CONFIG'] = {}
```

- **single-ASIC**: `MGMT_INTERFACE` + `LOOPBACK_INTERFACE` の全 IP アドレスを port=161, vrf='' で自動登録
- **multi-ASIC / chassis**: 空辞書。自動登録しない。`SNMP_AGENT_ADDRESS_CONFIG` は CLI で手動登録するか、空のまま (fallback で udp:161/udp6:161)

### chassis-packet (switch_type)

`supervisord.conf.j2:53-56` で `switch_type == 'chassis-packet'` の場合のみ snmp-subagent に `--enable_dynamic_frequency` フラグを追加する分岐がある。これは `SNMP_AGENT_ADDRESS_CONFIG` のリッスンアドレス設定には影響しないが、同一コンテナで動く snmp-subagent の挙動を変える。

```jinja
{% if DEVICE_METADATA['localhost']['switch_type'] == 'chassis-packet' %}
command=/usr/bin/env python3 -m sonic_ax_impl --enable_dynamic_frequency
{% else %}
command=/usr/bin/env python3 -m sonic_ax_impl
{% endif %}
```

### snmpd.conf.j2 コメント

`snmpd.conf.j2:16-17`:
```
# Listen for connections on all ip addresses, including eth0, ipv4 lo for multi-asic platform
# Listen on managment and loopback0 ips for single asic platform
```

multi-ASIC では `SNMP_AGENT_ADDRESS_CONFIG` が空のため `snmpd.conf.j2` の else 分岐 (L32-33) が実行され、**全インタフェース** (`udp:161` / `udp6:161`) でリッスンする。single-ASIC では minigraph 自動生成により管理 IP + Loopback0 IP のみに絞られる。

### link-local IPv6 (zone id) の扱い

`minigraph.py:2317-2318`:
```python
if ip_addr.version == 6 and ip_addr.is_link_local:
    agent_addr = str(ip_addr) + '%' + intf[0]
```

link-local IPv6 アドレスの場合はインタフェース名を zone id として付与 (`fe80::1%Management0`)。`snmpd.conf.j2:20` の `protocol()` マクロは `split('%')[0]` で zone id を除去してから `|ipv6` フィルタで UDP プロトコル種別を判定する。

### platform 差異まとめ

| 環境 | minigraph 自動生成 | fallback 挙動 | snmp-subagent オプション |
|------|-------------------|--------------|------------------------|
| single-ASIC | MGMT_IF + LO0 IP を port=161 で自動登録 | 自動生成があるので else 分岐は通常不要 | `sonic_ax_impl`（追加オプションなし） |
| multi-ASIC / chassis | 空辞書（自動生成なし） | `udp:161` + `udp6:161` の全 IF fallback | `sonic_ax_impl`（追加オプションなし） |
| chassis-packet | 空辞書（自動生成なし） | `udp:161` + `udp6:161` の全 IF fallback | `sonic_ax_impl --enable_dynamic_frequency` |
