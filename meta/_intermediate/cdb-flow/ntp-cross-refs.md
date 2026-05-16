# NTP テーブル群 暗黙参照スキャン (Phase C)

`docs/reference/config-db/ntp.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-host-services/scripts/hostcfgd`（`NtpCfg` クラス）および `sonic-net/sonic-buildimage/files/image_config/chrony/chrony.conf.j2`・`files/image_config/chrony/chronyd-starter.sh`。

## スキャン手順

```bash
grep -n "MGMT_VRF\|MGMT_INTERFACE\|DEVICE_METADATA\|mgmtVrfEnabled\|ntp\|NTP\|chrony" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd

grep -n "DEVICE_METADATA\|device_metadata\|MGMT_INTERFACE\|MGMT_VRF" \
    .cache/sonic-sources/sonic-buildimage/files/image_config/chrony/chrony.conf.j2

grep -n "MGMT_VRF_CONFIG\|mgmtVrfEnabled\|NTP\|vrf" \
    .cache/sonic-sources/sonic-buildimage/files/image_config/chrony/chronyd-starter.sh
```

## 検出された暗黙参照

### 1. MGMT_VRF_CONFIG — chronyd-starter.sh ランタイム読み出し

`chronyd-starter.sh` は chrony サービス起動時に `sonic-db-cli` 経由で直接 CONFIG_DB を参照する。

| 参照キー | 参照箇所 | 用途 | evidence |
|---|---|---|---|
| `MGMT_VRF_CONFIG\|vrf_global.mgmtVrfEnabled` | `chronyd-starter.sh:3-16` | `"true"` なら mgmt VRF を使用。`"false"` なら default VRF で chrony を起動 | `chronyd-starter.sh:3-16` |
| `NTP\|global.vrf` | `chronyd-starter.sh:5-11` | `mgmtVrfEnabled=true` のとき、値が `"default"` 以外なら `ip vrf exec mgmt chronyd` で起動 | `chronyd-starter.sh:7-11` |

**`NTP.vrf` フィールドの YANG `must` 制約は DB 書込時にのみ評価される。** `chronyd-starter.sh` はブート時およびランタイム変更ごとに `MGMT_VRF_CONFIG` を再確認するため、`MGMT_VRF_CONFIG.mgmtVrfEnabled=false` に戻した後も `NTP.vrf=mgmt` が残存していると chrony 起動失敗が発生する（経路依存乖離）。

`hostcfgd` の `MgmtIfaceCfg.update_mgmt_vrf()` (hostcfgd:1645-1669) は `MGMT_VRF_CONFIG` 変更時に `systemctl stop chrony` → `systemctl start chrony` を呼び出す。この際 NTP も影響を受ける。

| subscribe | handler | NTP への影響 | evidence |
|---|---|---|---|
| `MGMT_VRF_CONFIG` | `mgmt_vrf_handler` → `MgmtIfaceCfg.update_mgmt_vrf()` | chrony の stop/start を発火。失敗時は `LOG_ERR` のみで mgmt_vrf_enabled キャッシュ未更新 | hostcfgd:2352,2496,1659-1669 |

### 2. MGMT_INTERFACE — chrony.conf.j2 テンプレート参照

`chrony.conf.j2` L91-92 は `NTP.src_intf = 'eth0'` のとき `MGMT_INTERFACE` テーブルから IP アドレスを解決して `bindacqaddress` ディレクティブを生成する。

```jinja2
{%- set ns.source_intf_ipv4 = get_ip_on_interface(ns.source_intf, MGMT_INTERFACE, true) %}
{%- set ns.source_intf_ipv6 = get_ip_on_interface(ns.source_intf, MGMT_INTERFACE, false) %}
```

`init_cfg.json.j2` は `NTP.src_intf = "eth0"` をデフォルト注入するため、**標準構成では常に `MGMT_INTERFACE` が参照される**。

また `hostcfgd` の `lpbk_handler` は Loopback インタフェース変更時に `NtpCfg.handle_ntp_source_intf_chg()` を呼び出し、src_intf に一致するインタフェースが変化した場合に chrony を再起動する (hostcfgd:2362-2365)。

| テーブル | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `MGMT_INTERFACE` | `chrony.conf.j2` テンプレート生成時 | `src_intf=eth0` 時に eth0 の IPv4/IPv6 アドレスを `bindacqaddress` に変換 | `chrony.conf.j2:91-92` |
| `MGMT_INTERFACE` | `mgmt_intf_handler` (subscribe) | `eth0` IP 変化時に `MgmtIfaceCfg.update_mgmt_iface()` → `interfaces-config` 再起動。NTP への直接コールバックはないが、`bindacqaddress` が指す IP が変化するため次回 chrony 再起動時に反映 | hostcfgd:2345-2351,2485 |

### 3. DEVICE_METADATA — chrony.conf.j2 テンプレート参照

`chrony.conf.j2` L15-16 はテンプレート先頭で `DEVICE_METADATA.localhost` を参照し、`subtype` / `type` フィールドを SmartSwitch 判定に使用する。

```jinja2
{# Getting DEVICE_METADATA localhost configuration -#}
{% set device_metadata = (DEVICE_METADATA | d({})).get('localhost', {}) -%}
```

L57-63 の SmartSwitch 条件分岐:

```jinja2
{% if device_metadata.subtype == 'SmartSwitch' and device_metadata.type != 'SmartSwitchDPU' -%}
{% if global.server_role == 'enabled' or global.dhcp == 'enabled' -%}
allow
binddevice bridge-midplane
{% endif -%}
{% endif -%}
```

`DEVICE_METADATA.localhost.subtype` が `'SmartSwitch'` かつ `type != 'SmartSwitchDPU'` のときのみ、`NTP.server_role` が参照され `allow`/`binddevice bridge-midplane` が生成される。**非 SmartSwitch では `DEVICE_METADATA` を読んでも NTP 動作は変わらない**（subtype 条件を通過しないため）。

| フィールド | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `DEVICE_METADATA.localhost.subtype` | `chrony.conf.j2` テンプレート生成時 | SmartSwitch 判定 — true のとき NTP server_role/dhcp を `allow` に変換 | `chrony.conf.j2:15-16,57-63` |
| `DEVICE_METADATA.localhost.type` | `chrony.conf.j2` テンプレート生成時 | `SmartSwitchDPU` 除外条件 | `chrony.conf.j2:58` |

`hostcfgd` では `device_metadata_handler` が `DEVICE_METADATA` 変更を購読するが (hostcfgd:2404-2408,2492-2494)、コールバック先は `DeviceMetaCfg.hostname_update` / `timezone_update` / `rsyslog_config` のみ。**`NtpCfg` への直接コールバックはない** — `DEVICE_METADATA.subtype` が変化しても chrony.conf.j2 が再生成されるのは次回 chrony 再起動時のみ（NTP / NTP_SERVER / NTP_KEY のいずれかが変更されるかサービス再起動が起きるまで反映されない）。

## まとめ — `ntp.md` Phase C 記載対象

| カテゴリ | テーブル | 参照経路 |
|---|---|---|
| ランタイム直接読み出し | `MGMT_VRF_CONFIG` | `chronyd-starter.sh` が `sonic-db-cli` で `vrf_global.mgmtVrfEnabled` を読み取り |
| ランタイム直接読み出し | `MGMT_VRF_CONFIG` | hostcfgd `mgmt_vrf_handler` が chrony stop/start を制御 |
| テンプレート参照 | `MGMT_INTERFACE` | `chrony.conf.j2:91-92` で `src_intf=eth0` 時の IP アドレス解決 |
| テンプレート参照 | `DEVICE_METADATA` | `chrony.conf.j2:15-16,57-63` で SmartSwitch 判定 |

## 検証コマンド

```bash
grep -n "MGMT_VRF\|MGMT_INTERFACE\|DEVICE_METADATA\|mgmtVrfEnabled" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd

grep -n "DEVICE_METADATA\|MGMT_INTERFACE" \
    .cache/sonic-sources/sonic-buildimage/files/image_config/chrony/chrony.conf.j2
```

このスキャン結果から派生して `docs/reference/config-db/ntp.md` の `<!-- cross-refs -->` ブロックを生成する。
