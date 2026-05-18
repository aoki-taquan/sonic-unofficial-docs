# SYSLOG_CONFIG — Phase H プラットフォーム差異 調査証跡

## 調査対象ソース

- `sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh`
- `sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2`
- `sonic-host-services/scripts/hostcfgd` (`RSyslogCfg` クラス L1695-1743)
- `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py`

## RSyslogCfg クラス — プラットフォーム分岐なし

`hostcfgd` の `RSyslogCfg.update_rsyslog_config()` (L1715-1743) は全コード経路にわたって `platform` / `asic` / `chassis` / `namespace` / `is_multi_npu` への参照がゼロ。`is_multi_npu` フラグは `HostConfigDaemon.__init__` (L2182) で設定されるが、`RSyslogCfg` には一切渡されない。

## rsyslog-config.sh — Multi-ASIC 受信 IP 分岐

`rsyslog-config.sh` L3-19 は `SYSLOG_CONFIG|GLOBAL` の反映先ではなく、rsyslog デーモンの **受信側** IP アドレスを決定するスクリプト:

```bash
PLATFORM=$(sonic-db-cli CONFIG_DB HGET 'DEVICE_METADATA|localhost' platform)
ASIC_CONF=/usr/share/sonic/device/$PLATFORM/asic.conf
if [ -f "$ASIC_CONF" ]; then source $ASIC_CONF; fi

if [[ ($NUM_ASIC -gt 1) ]]; then
    udp_server_ip=$(ip -o -4 addr list docker0 | awk '{print $4}' | cut -d/ -f1)
else
    udp_server_ip=$(ip -j -4 addr list lo scope host | jq -r -M '.[0].addr_info[0].local')
fi
```

この分岐は「コンテナからのログをどの IP で受信するか」を決めるものであり、`SYSLOG_CONFIG|GLOBAL` フィールド (`format`, `severity`, `rate_limit_*`) の処理ロジック自体には影響しない。

## rsyslog.conf.j2 — グローバル設定のプラットフォーム分岐

`rsyslog.conf.j2` の `SYSLOG_CONFIG|GLOBAL` 参照箇所 (L51-52, L92) に `platform` / `asic` / `chassis` / `namespace` / `vendor` に基づく条件分岐はゼロ。`format`, `welf_firewall_name`, `severity` の適用ロジックはプラットフォーム非依存。

## multi-asic 構成における受信 IP の影響

| 構成 | `udp_server_ip` | `SYSLOG_CONFIG|GLOBAL` 処理への影響 |
|------|----------------|-------------------------------------|
| シングル NPU | `lo` の IPv4 アドレス | なし |
| Multi-ASIC (NUM_ASIC > 1) | `docker0` の IPv4 アドレス | なし（受信 IP が変わるだけ。format/severity/rate-limit は同一ロジック） |

## SmartSwitch / DPU

`hostcfgd` / `rsyslog.conf.j2` / `rsyslog-config.sh` のいずれにも SmartSwitch / DPU 固有の syslog-config 分岐なし。

## 結論

`SYSLOG_CONFIG|GLOBAL` の各フィールド (`format`, `severity`, `rate_limit_interval`, `rate_limit_burst`, `welf_firewall_name`) の処理において **プラットフォーム差異はない**。Multi-ASIC 固有の挙動は rsyslog の受信 IP 選択（`rsyslog-config.sh` 内）に限定され、`SYSLOG_CONFIG` の消費経路（`RSyslogCfg.update_rsyslog_config` → `rsyslog-config.service` 起動）には及ばない。
