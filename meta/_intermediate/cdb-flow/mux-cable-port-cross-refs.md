# Phase C: MUX_CABLE (per-port) 暗黙参照スキャン

`docs/reference/config-db/mux-cable-port.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-linkmgrd/src/DbInterface.cpp` および `sonic-net/sonic-swss/orchagent/muxorch.cpp`。

## スキャン手順

```
# linkmgrd 側: 起動時初期読み込みおよび subscribe テーブル一覧
grep -n "swss::Table\|swss::SubscriberStateTable\|getVlan\|getTorMac\|getLoopback\|getPort\|getProber\|getServer\|getSoC" \
    .cache/sonic-sources/sonic-linkmgrd/src/DbInterface.cpp

# orchagent 側: MuxOrch コンストラクタ + MuxAclHandler
grep -n "Table\|m_systemDefaults\|CFG_PEER_SWITCH\|STATE_MUX" \
    .cache/sonic-sources/sonic-swss/orchagent/muxorch.cpp
```

## 検出された暗黙参照テーブル

### linkmgrd 起動時一括読み込み (DbInterface.cpp:1843-1849)

`updateInterfaces()` / `run()` 内で以下の順序でテーブルを読み出す。

| テーブル (CONFIG_DB) | 参照箇所 | 用途 | evidence |
|---------------------|---------|------|---------|
| `DEVICE_METADATA` (`localhost.mac`) | `getTorMacAddress()` | ToR の MAC アドレスを取得。linkmgrd の ToR ID として使用 | DbInterface.cpp:589,594 |
| `VLAN` | `getVlanNames()` → `getVlanMacAddress()` | DualToR VLAN の MAC アドレスを取得 | DbInterface.cpp:609-613 |
| `LOOPBACK_INTERFACE` (`Loopback2|*` / `Loopback3|*`) | `getLoopbackInterfacesInfo()` | Loopback2/3 の IPv4 アドレスを linkmgrd の src/dst IP として使用 | DbInterface.cpp:742-746,671-694 |
| `MUX_CABLE` (本テーブル) | `getPortCableType()` / `getProberType()` / `getServerIpAddress()` / `getSoCIpAddress()` | per-port 設定の全フィールドを順次読み込み | DbInterface.cpp:1846-1849 |

### linkmgrd ランタイム subscribe (DbInterface.cpp:1819-1841)

`swssSelect` に登録されるテーブル。`MUX_CABLE` 以外の暗黙的な連動テーブル。

| テーブル | DB | 用途 | evidence |
|---------|----|------|---------|
| `MUX_LINKMGR` (CONFIG_DB) | CONFIG_DB | Link Prober 設定 (`interval_v4`/`interval_v6`/`positive_signal_count` 等) の動的変更を受信 | DbInterface.cpp:1820,1887-1888 |
| `BGP_DEVICE_GLOBAL` (CONFIG_DB) | CONFIG_DB | `tsa_enabled` フラグ変更を受信し TSA (Traffic Shift Away) モードに遷移 | DbInterface.cpp:1822,1892 |
| `APP_PORT_TABLE` (APPL_DB) | APPL_DB | ポートのリンクアップ / ダウンを検知してステートマシンをトリガ | DbInterface.cpp:1827 |
| `APP_MUX_CABLE_RESPONSE_TABLE` (APPL_DB) | APPL_DB | ycabled からの mux 切替完了応答を受信 | DbInterface.cpp:1829 |
| `APP_FORWARDING_STATE_RESPONSE_TABLE` (APPL_DB) | APPL_DB | ycabled からの forwarding state 応答を受信 | DbInterface.cpp:1831 |
| `STATE_MUX_CABLE_TABLE` (STATE_DB) | STATE_DB | orchagent が書き込む mux state 変化を監視 | DbInterface.cpp:1833 |
| `STATE_ROUTE_TABLE` (STATE_DB) | STATE_DB | デフォルトルート存在 / 消失の通知を受信し Active/Standby 決定に利用 | DbInterface.cpp:1835 |
| `MUX_CABLE_INFO_TABLE` (STATE_DB) | STATE_DB | ピア ToR のリンクステータスを取得 | DbInterface.cpp:1837 |
| `STATE_PEER_HW_FORWARDING_STATE_TABLE` (STATE_DB) | STATE_DB | ピア ToR の admin forwarding state を取得 | DbInterface.cpp:1839 |
| `STATE_ICMP_ECHO_SESSION_TABLE` (STATE_DB) | STATE_DB | ICMP エコーセッション状態を受信 | DbInterface.cpp:1841 |

### orchagent (MuxOrch) 側の暗黙参照 (muxorch.cpp)

| テーブル | 参照箇所 | 用途 | evidence |
|---------|---------|------|---------|
| `PEER_SWITCH` (CONFIG_DB) | `handlePeerSwitch()` / `MuxOrch::MuxOrch()` | ピア ToR の IPv4 (`address_ipv4`) を取得して nexthop 切替に使用。`MUX_CABLE` 処理の前提条件 | muxorch.cpp:2190,2335-2354 |
| `SYSTEM_DEFAULTS` (CONFIG_DB) | `MuxAclHandler::MuxAclHandler()` | `mux_tunnel_egress_acl.status` を参照し ACL が ingress/egress どちらかを決定 | muxorch.cpp:1388-1390 |
| `STATE_MUX_CABLE_TABLE` (STATE_DB) | `state_mux_cable_table_` | orchagent が SAI 反映後に STATE_DB へ mux state を書き戻す | muxorch.cpp:2199 |

## まとめ — `mux-cable-port.md` Phase C 記載対象

| カテゴリ | テーブル |
|---------|---------|
| linkmgrd 起動時一括読み込み (CONFIG_DB) | `DEVICE_METADATA` / `VLAN` / `LOOPBACK_INTERFACE` |
| linkmgrd ランタイム連動 (CONFIG_DB) | `MUX_LINKMGR` / `BGP_DEVICE_GLOBAL` |
| linkmgrd ランタイム連動 (APPL_DB) | `APP_PORT_TABLE` / `APP_MUX_CABLE_RESPONSE_TABLE` / `APP_FORWARDING_STATE_RESPONSE_TABLE` |
| linkmgrd ランタイム監視 (STATE_DB) | `STATE_MUX_CABLE_TABLE` / `STATE_ROUTE_TABLE` / `MUX_CABLE_INFO_TABLE` / `STATE_PEER_HW_FORWARDING_STATE_TABLE` / `STATE_ICMP_ECHO_SESSION_TABLE` |
| orchagent 暗黙依存 (CONFIG_DB) | `PEER_SWITCH` / `SYSTEM_DEFAULTS` |
| orchagent 書き戻し (STATE_DB) | `STATE_MUX_CABLE_TABLE` |

## 検証コマンド

```bash
grep -n "swss::Table\|swss::SubscriberStateTable" \
    .cache/sonic-sources/sonic-linkmgrd/src/DbInterface.cpp

grep -n "MuxOrch::MuxOrch\|MuxAclHandler::MuxAclHandler\|state_mux_cable_table_" \
    .cache/sonic-sources/sonic-swss/orchagent/muxorch.cpp
```

このスキャン結果から派生して `docs/reference/config-db/mux-cable-port.md` の `<!-- cross-refs -->` ブロックを生成する。
