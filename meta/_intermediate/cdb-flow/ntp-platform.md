# NTP — プラットフォーム差調査 (Phase H)

Task F Phase H: `NTP` / `NTP_SERVER` / `NTP_KEY` テーブル適用時のプラットフォーム/構成差を `hostcfgd` (`sonic-host-services`) および `chrony.conf.j2` / `chronyd-starter.sh` (`sonic-buildimage`) から精読した結果。

## 結論

**プラットフォーム差あり**。以下 3 点が確認された:

1. **SmartSwitch (NPU side)**: `chrony.conf.j2` が `DEVICE_METADATA.localhost.subtype == 'SmartSwitch'` かつ `type != 'SmartSwitchDPU'` のとき `allow` + `binddevice bridge-midplane` を追加し、NTP server 機能を有効化する
2. **MGMT_VRF 有効時**: `chronyd-starter.sh` が `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled` をランタイムに確認し、chrony を mgmt VRF 上で起動する。これは single-asic / multi-asic 双方に影響する
3. **multi-asic / chassis**: NTP 処理は host CONFIG_DB のみ対象であり、`asicN` namespace への接続はしないが、`chrony.conf.j2` の `bindacqaddress` は host 上のインタフェース IP を参照するため、データプレーン側インタフェース (Ethernet/Loopback) が multi-asic 環境で正しくアドレスを持つかどうかが `src_intf` 設定の有効性に影響する

## 根拠

### 1. SmartSwitch — NTP server 機能の自動有効化

`chrony.conf.j2` L57-64 (sonic-buildimage 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd):

```jinja2
{# Enable the NTP server configuration only if the switch type is smartswitch -#}
{% if device_metadata.subtype == 'SmartSwitch' and device_metadata.type != 'SmartSwitchDPU' -%}
{# Enable NTP server functionality if server_role is enabled or DHCP configuration is enabled -#}
{% if global.server_role == 'enabled' or global.dhcp == 'enabled' -%}
allow
binddevice bridge-midplane
{% endif -%}
{% endif -%}
```

条件分岐の詳細:

| プラットフォーム | `subtype` | `type` | `allow` + `binddevice bridge-midplane` 追加 |
|----------------|-----------|--------|---------------------------------------------|
| 通常スイッチ (T0/T1 等) | `SmartSwitch` 以外 | 任意 | **追加されない** |
| SmartSwitch NPU | `SmartSwitch` | `SmartSwitchDPU` 以外 | `server_role=enabled` または `dhcp=enabled` のとき追加 |
| SmartSwitch DPU | `SmartSwitch` | `SmartSwitchDPU` | **追加されない** |

デフォルトで `dhcp == 'enabled'` (init_cfg.json.j2 L212) であるため、SmartSwitch NPU では **`server_role` の設定値に関わらず** NTP server として動作する（`dhcp=enabled` が `or` 条件を満たすため）。

`binddevice bridge-midplane` は SmartSwitch 内の NPU-DPU 間ブリッジインタフェース。DPU がこのインタフェース経由で NPU を NTP server として参照する構成が前提。

非 SmartSwitch では `server_role` フィールドは **dead field** — `chrony.conf.j2` が当該ブロックに到達しないため、値にかかわらず `allow` も `binddevice` も生成されない。

### 2. MGMT_VRF — chronyd-starter.sh によるランタイム VRF 選択

`chronyd-starter.sh` (sonic-buildimage 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd) L1-16:

```sh
VRF_ENABLED=$(sonic-db-cli CONFIG_DB HGET "MGMT_VRF_CONFIG|vrf_global" "mgmtVrfEnabled" 2> /dev/null)
if [ "$VRF_ENABLED" = "true" ]; then
    VRF_CONFIGURED=$(sonic-db-cli CONFIG_DB HGET "NTP|global" "vrf" 2> /dev/null)
    if [ "$VRF_CONFIGURED" = "default" ]; then
        exec /usr/sbin/chronyd $DAEMON_OPTS
    else
        exec ip vrf exec mgmt /usr/sbin/chronyd $DAEMON_OPTS
    fi
else
    exec /usr/sbin/chronyd $DAEMON_OPTS
fi
```

VRF 選択ロジック:

| `MGMT_VRF_CONFIG.mgmtVrfEnabled` | `NTP|global.vrf` | chronyd 起動方法 |
|----------------------------------|------------------|-----------------|
| `false` (または読み取り失敗) | 任意 | デフォルト VRF で起動 |
| `true` | `"default"` | デフォルト VRF で起動 |
| `true` | それ以外 (例: `"mgmt"`) | `ip vrf exec mgmt chronyd` |

MGMT VRF は single-asic / multi-asic 環境のいずれでも host 単位で有効化される。multi-asic chassis においても `MGMT_VRF_CONFIG` は host CONFIG_DB の一部であり、NTP は host 側のネットワーク (eth0 / mgmt VRF) のみで動作する。

さらに `MgmtIfaceCfg.update_mgmt_vrf()` (`hostcfgd` L1645-1693) は MGMT_VRF_CONFIG の変更時に chrony を stop/start する:

```python
run_cmd(['systemctl', 'stop', 'chrony'], True, True)
run_cmd(['systemctl', 'restart', 'interfaces-config'], True, True)
run_cmd(['systemctl', 'start', 'chrony'], True, True)
```

この再起動によって `chronyd-starter.sh` が再評価され、新しい VRF 状態に合わせて chrony が起動し直される。

### 3. multi-asic / VOQ chassis での NTP 適用範囲

`NtpCfg` (`hostcfgd` L1272-1406) は host CONFIG_DB のみを参照し、`asicN` namespace への接続を一切行わない。NTP はホスト管理プレーンで完結する機能であるため、ASIC 数・namespace 数に依存しない。

ただし `src_intf` の有効性は環境に依存する:

| `src_intf` 値 | 参照テーブル | multi-asic での注意点 |
|---------------|------------|---------------------|
| `eth0` | `MGMT_INTERFACE` | eth0 は host に 1 つ。multi-asic でも同じ |
| `LoopbackX` | `LOOPBACK_INTERFACE` | host CONFIG_DB の LOOPBACK_INTERFACE に IP が設定されているかを確認 |
| `EthernetX` | `INTERFACE` | multi-asic 環境ではデータプレーン側インタフェースが ASIC namespace に存在し、host CONFIG_DB の `INTERFACE` にはアドレスが設定されない場合がある |
| `PortChannelX` | `PORTCHANNEL_INTERFACE` | 同上 |

`chrony.conf.j2` の `get_ip_on_interface` マクロは host CONFIG_DB の各テーブルを参照して `bindacqaddress` を生成する。multi-asic 環境で `EthernetX` / `PortChannelX` を `src_intf` に設定しても、host CONFIG_DB の `INTERFACE` / `PORTCHANNEL_INTERFACE` にアドレスがなければ `bindacqaddress` が空となり、NTP パケットのソース IP 制限が実質的に無効になる（エラーではなくサイレントに eth0 または任意インタフェースで送信される）。

また `chrony.conf.j2` L109 の mgmt VRF 分岐:

```jinja2
{% if not ((NTP) and NTP['global']['vrf'] == 'mgmt') -%}
```

`vrf == 'mgmt'` のとき `bindacqaddress` ディレクティブ自体が生成されない。mgmt VRF 上では chrony が eth0 を管理インタフェースとして使用するため、`src_intf` 設定は不要かつ無視される。

### 4. SmartSwitch DPU の NTP 設定独立性

DPU は独立した SONiC インスタンスとして動作する。DPU 側の `hostcfgd` は DPU の host CONFIG_DB を読み取り、同一の `NtpCfg` コードパスで chrony を設定する。

| 観点 | 挙動 |
|------|------|
| DPU の NTP サーバ | NPU 側の `allow`/`binddevice bridge-midplane` を介して NPU を参照するよう、DPU の `NTP_SERVER` に NPU ブリッジ IP を設定する運用が想定 |
| DPU の `server_role` | DPU の `chrony.conf.j2` は `type == 'SmartSwitchDPU'` 条件で `allow` ブロックに入らないため dead field |
| NPU-DPU 間同期 | ネットワーク接続は `bridge-midplane` を通じて自動的に確立される前提。DPU 側で `NTP_SERVER` に NPU bridge IP を追加するオペレータ操作が必要 |

## まとめ

| プラットフォーム差 | 影響するフィールド / 挙動 | ソース |
|-------------------|--------------------------|--------|
| SmartSwitch NPU のみ NTP server 機能有効化 | `NTP.server_role`、`NTP.dhcp` → `allow`/`binddevice bridge-midplane` | `chrony.conf.j2:57-64` |
| MGMT VRF 有効時の chrony VRF 起動 | `NTP.vrf`、`MGMT_VRF_CONFIG.mgmtVrfEnabled` | `chronyd-starter.sh:1-16`、`hostcfgd:1645-1693` |
| multi-asic での `src_intf` 無効化リスク | `NTP.src_intf` (EthernetX/PortChannelX) | `chrony.conf.j2:86-116` |
| SmartSwitch DPU では `server_role` dead | `NTP.server_role` | `chrony.conf.j2:58` |
