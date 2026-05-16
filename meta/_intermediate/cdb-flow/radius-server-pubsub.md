# radius-server — Phase G: CONFIG_DB Subscribe / PAM 再生成経路

ソース: `sonic-net/sonic-host-services/scripts/hostcfgd`

## Subscribe 登録一覧

| テーブル | コールバック | 行番号 |
|---|---|---|
| `RADIUS_SERVER` | `radius_server_handler` | L2474 |
| `RADIUS` | `radius_global_handler` | L2473 |
| `LOOPBACK_INTERFACE` | `lpbk_handler` → `handle_radius_source_intf_ip_chg` | L2483 |
| `MGMT_INTERFACE` | `mgmt_intf_handler` → `handle_radius_source_intf_ip_chg` | L2485 |
| `VLAN_INTERFACE` | `vlan_intf_handler` → `handle_radius_source_intf_ip_chg` | L2486 |
| `DEVICE_METADATA` | `hostname_update` 経由 | L2492 |

## PAM 再生成コールチェーン

```
RADIUS_SERVER 変更
  → radius_server_handler (L2317)
  → AaaCfgMgr.radius_server_update (L535)
  → modify_conf_file (L681)
  → /etc/pam_radius_auth.d/<ip>_<port>.conf 生成
  → /etc/sonic/radius_nss.conf 更新
  → common-auth-sonic PAM スタック更新
  → aaastatsd start/stop
```

## src_intf 経由の追加トリガー

インタフェース設定変更 → `handle_radius_source_intf_ip_chg` → `src_intf` が一致するエントリを検索 → `modify_conf_file` 再実行。

## evidence

- `hostcfgd:2317-2322` radius_server_handler
- `hostcfgd:2474` subscribe('RADIUS_SERVER', ...)
- `hostcfgd:535-545` radius_server_update
- `hostcfgd:681-851` modify_conf_file (PAM ファイル生成)
- `hostcfgd:500-525` handle_radius_source_intf_ip_chg
