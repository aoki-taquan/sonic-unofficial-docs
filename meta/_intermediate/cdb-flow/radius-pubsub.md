# radius — Phase G: CONFIG_DB Subscribe / PAM 再生成経路

ソース: `sonic-net/sonic-host-services/scripts/hostcfgd`

## Subscribe 登録一覧

| テーブル | コールバック | 行番号 |
|---|---|---|
| `RADIUS` | `radius_global_handler` | L2473 |
| `RADIUS_SERVER` | `radius_server_handler` | L2474 |
| `MGMT_INTERFACE` | `mgmt_intf_handler` → `handle_radius_source_intf_ip_chg` + `handle_radius_nas_ip_chg` | L2485 |
| `INTERFACE` | `phy_intf_handler` → `handle_radius_source_intf_ip_chg` | L2489 |
| `VLAN_INTERFACE` | `vlan_intf_handler` → `handle_radius_source_intf_ip_chg` | L2486 |
| `PORTCHANNEL_INTERFACE` | `portchannel_intf_handler` → `handle_radius_source_intf_ip_chg` | L2488 |
| `DEVICE_METADATA` | `device_metadata_handler` → `hostname_update` | L2492 |

## PAM 再生成コールチェーン

```
RADIUS|global 変更
  → radius_global_handler (L2324)
  → AaaCfg.radius_global_update (L527)
  → modify_conf_file (L641)
  → /etc/pam.d/common-auth-sonic 再生成
  → /etc/radius_nss.conf 更新
  → /etc/pam_radius_auth.d/<ip>_<port>.conf 再生成
  → aaastatsd start/stop
```

## 間接トリガー

- `MGMT_INTERFACE` IP 変化 → `handle_radius_nas_ip_chg()` → `modify_conf_file()` 再実行
- `INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` IP 変化 → `handle_radius_source_intf_ip_chg()` → `modify_conf_file()` 再実行
- `DEVICE_METADATA.hostname` 変化 → `hostname_update()` → `modify_conf_file()` 再実行

## evidence

- `hostcfgd:2473-2474` subscribe('RADIUS', ...) / subscribe('RADIUS_SERVER', ...)
- `hostcfgd:2528` listen(init_data_handler=self.load)
- `hostcfgd:2317-2329` radius_server_handler / radius_global_handler
- `hostcfgd:527-545` radius_global_update / radius_server_update
- `hostcfgd:641-851` modify_conf_file (PAM ファイル生成)
- `hostcfgd:500-525` handle_radius_source_intf_ip_chg
- `hostcfgd:840-851` aaastatsd start/stop
