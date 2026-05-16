# SYSLOG_SERVER — Phase H プラットフォーム差異 調査証跡

## 調査対象ソース

- `sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh`
- `sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2`
- `sonic-buildimage/files/image_config/rsyslog/rsyslog-container.conf.j2`
- `sonic-host-services/scripts/hostcfgd`
- `sonic-buildimage/src/sonic-config-engine/smartswitch_config.py`

## Multi-ASIC 差異

### rsyslog-config.sh L3-19

```bash
PLATFORM=$(sonic-db-cli CONFIG_DB HGET 'DEVICE_METADATA|localhost' platform)
ASIC_CONF=/usr/share/sonic/device/$PLATFORM/asic.conf
if [ -f "$ASIC_CONF" ]; then
    source $ASIC_CONF
fi

# On Multi NPU platforms we need to start the rsyslog server on the docker0 ip address
# for the syslogs from the containers in the namespaces to work.
# on Single NPU platforms we continue to use loopback address

if [[ ($NUM_ASIC -gt 1) ]]; then
    udp_server_ip=$(ip -o -4 addr list docker0 | awk '{print $4}' | cut -d/ -f1)
else
    udp_server_ip=$(ip -j -4 addr list lo scope host | jq -r -M '.[0].addr_info[0].local')
fi
```

**分岐まとめ**:

| 条件 | `udp_server_ip` | 理由 |
|------|----------------|------|
| `NUM_ASIC == 1` | `lo` の先頭 IPv4 アドレス | 単一 NPU ではコンテナが loopback 経由で送信 |
| `NUM_ASIC > 1` | `docker0` の IPv4 アドレス | 複数 NPU では namespace 内コンテナが docker0 経由で送信 |

### rsyslog.conf.j2 L31-44: docker0 二重 listen

```jinja2
input(type="imudp" address="{{udp_server_ip}}" port="514")
{% if docker0_ip and docker0_ip != "" and docker0_ip != udp_server_ip %}
input(type="imudp" address="{{docker0_ip}}" port="514")
{% endif%}

input(type="imrelp" address="{{udp_server_ip}}" port="2514")
{% if docker0_ip and docker0_ip != "" and docker0_ip != udp_server_ip %}
input(type="imrelp" address="{{docker0_ip}}" port="2514")
{% endif%}
```

`docker0_ip` は `rsyslog-config.sh` で `dhcp_server` Feature が有効な場合にのみ設定される。Multi-ASIC では `udp_server_ip` 自体が docker0 IP となるため条件 `docker0_ip != udp_server_ip` が偽となり二重 listen にはならない。

## pmon コンテナ向けプラットフォームフィルタ

### rsyslog-container.conf.j2 L44-57

```jinja2
set $.PLATFORM=getenv("PLATFORM");

{% if container_name == 'pmon' %}
if ($.PLATFORM == "x86_64-mlnx_msn2700-r0" or $.PLATFORM == "x86_64-mlnx_msn2700a1-r0"
    or $.PLATFORM == "x86_64-mlnx_msn2410-r0") then {
    if $programname contains "sensord" and $msg contains "Error getting sensor data: dps460/#" then stop
}
{% endif %}
```

- PSU ファームウェアバグ (dps460) に起因するノイズログ (`ERR pmon#sensord`) を該当プラットフォームでのみ抑制
- `pmon` コンテナに限定。SYSLOG_SERVER リモート転送設定には影響しない

## SmartSwitch / DPU 差異

- `hostcfgd` に SmartSwitch/DPU 固有の syslog 分岐なし（全コードを grep 確認）
- `smartswitch_config.py` に syslog 関連コードなし
- `rsyslog-config.sh` / `rsyslog.conf.j2` に SmartSwitch 固有分岐なし
- DPU の `NUM_ASIC` は通常 1 → シングル NPU と同等の loopback 受信設定

## 結論

SYSLOG_SERVER テーブルのリモート転送設定（`hostcfgd` / `rsyslog.conf.j2` が生成する forwarding action）自体にプラットフォーム分岐はない。プラットフォーム差異は rsyslog の **受信側** IP アドレス選択（Multi-ASIC で docker0 使用）と、**pmon コンテナ内**のノイズフィルタ（Mellanox 特定機種）に限定される。
