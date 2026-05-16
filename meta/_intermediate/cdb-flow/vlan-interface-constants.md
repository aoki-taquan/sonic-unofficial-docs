# VLAN_INTERFACE — Phase E: ハードコード定数調査メモ

対象ファイル:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

## 定数一覧

| 定数名 / マジック値 | 値 | 定義箇所 | 役割 |
|---------------------|-----|---------|------|
| `DEFAULT_MTU_STR` | `9100` | `intfmgr.cpp:29` | VLAN IF 含む全 IF の省略時 MTU 初期値。portsorch.cpp の `DEFAULT_SYSTEM_PORT_MTU` も同値 9100 |
| `LOOPBACK_DEFAULT_MTU_STR` | `"65536"` | `intfmgr.cpp:28` | Loopback ダミー IF 専用 MTU。VLAN IF には非適用 |
| `garp_enabled` (enabled 時) | `"2"` | `intfmgr.cpp:582` | `grat_arp=enabled` 時に `/proc/sys/net/ipv4/conf/<IF>/arp_accept` に書く値 |
| `garp_enabled` (disabled 時) | `"0"` | `intfmgr.cpp:586` | `grat_arp=disabled` 時に同ファイルに書く値 |
| `proxy_arp_status` (enabled 時) | `"1"` | `intfmgr.cpp:624` | `proxy_arp=enabled` 時に `/proc/sys/net/ipv4/conf/<IF>/proxy_arp` 等に書く値 |
| `proxy_arp_status` (disabled 時) | `"0"` | `intfmgr.cpp:628` | 同ファイルへの disabled 値 |
| `MacAddress().to_string()` | `"00:00:00:00:00:00"` | `intfmgr.cpp:1019` | `mac_addr` 省略時に APP_DB へ書くゼロ MAC |
| `scope` 固定値 | `"global"` | `intfmgr.cpp:1134` | IP prefix ロウの `scope` フィールドは常に `"global"` を APP_DB へ書く（dead field） |
| `family` 自動判定 | `IPV4_NAME` / `IPV6_NAME` | `intfmgr.cpp:1129` | IP prefix の型から自動判定 (`isV4()`) して APP_DB へ書く（dead field） |
| `admin_status` fallback | `"up"` | `intfmgr.cpp:863,868` | 不正値・省略時に `"up"` へフォールバック。`SWSS_LOG_WARN` を出力 |
| `nat_zone_id` 初期値 | `0` (uint32) | `intfsorch.cpp:713` | `nat_zone` 省略時の orchagent 内部変数初期値 |
| `loopback_action` マップ | `"drop"` → `SAI_PACKET_ACTION_DROP` | `intfsorch.cpp:1150` | `getSaiLoopbackAction()` による文字列→SAI 変換テーブル |
| `loopback_action` マップ | `"forward"` → `SAI_PACKET_ACTION_FORWARD` | `intfsorch.cpp:1151` | 同上 |
| `SAI_ROUTER_INTERFACE_ATTR_ADMIN_MPLS_STATE` | omit (default disabled) | `intfsorch.cpp:1278` | `mpls=disable` 時は SAI attrs に含めない（SAI 実装側デフォルト disabled） |
| `/proc/sys/net/ipv4/conf/<IF>/arp_accept` | `2` or `0` | `intfmgr.cpp:594` | grat_arp カーネルパス |
| `/proc/sys/net/ipv6/conf/<IF>/accept_untracked_na` | `2` or `0` | `intfmgr.cpp:608` | grat_arp (IPv6 NA 対応カーネルのみ) |
| `/proc/sys/net/ipv4/conf/<IF>/proxy_arp_pvlan` | `1` or `0` | `intfmgr.cpp:636` | proxy_arp カーネルパス (pvlan 用) |
| `/proc/sys/net/ipv4/conf/<IF>/proxy_arp` | `1` or `0` | `intfmgr.cpp:642` | proxy_arp カーネルパス (通常) |
| `sysctl net.mpls.conf.<IF>.input` | `1` (enable) / `0` (disable) | `intfmgr.cpp:176,180` | MPLS カーネルパラメータ設定値 |

## 特記事項

- `DEFAULT_MTU_STR = 9100` は VLAN IF 生成時に `ip link` コマンドへ渡される MTU のデフォルト値。CONFIG_DB に `mtu` フィールドが無ければ 9100 が使われる。
- `grat_arp=enabled` → `arp_accept=2` は「未solicited な ARP も更新する」モード（値 `1` は「gratuitous ARP のみ更新」で異なる意味のため注意）。
- `proxy_arp` は `proxy_arp` と `proxy_arp_pvlan` の両方を設定する。
- `accept_untracked_na` は IPv6 の unsolicited NA を受け入れるカーネルパラメータ。カーネルがサポートしない場合はスキップ (`test -f` で確認後に書く)。
- `loopback_action` 省略時は SAI attrs に含めない (`loopbackActionStr.empty()` チェック)。SAI 実装依存デフォルトになる (多くは `forward`)。
- `mac_addr` 省略時: intfmgr が `00:00:00:00:00:00` を APP_DB へ書き、orchagent はゼロ MAC を受け取ると `gMacAddress`（スイッチ全体 MAC）を SAI に適用 (`intfsorch.cpp:1199-1207`)。
