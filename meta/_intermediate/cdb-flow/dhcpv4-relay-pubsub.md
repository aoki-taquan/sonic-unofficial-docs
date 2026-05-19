# DHCPV4_RELAY — 通信メカニズム調査 (Phase G)

## 調査日
2026-05-19

## 結論

`DHCPV4_RELAY` テーブルは `SubscriberStateTable`（keyspace notification）では**直接購読されない**。
`dhcprelayd` は `FEATURE`・`VLAN`・`VLAN_INTERFACE` テーブルの変化をイベントとして受け取り、
その都度 `refresh_dhcrelay()` の中で `get_config_db_table(...)` によるスナップショット読み出しを行う。

## consumer 一覧

| consumer プロセス | 購読方式 | 対象テーブル | ソース |
|---|---|---|---|
| `dhcprelayd` | `SubscriberStateTable` (keyspace notification) | `FEATURE` | `dhcp_db_monitor.py:392-411, dhcprelayd.py:44,63` |
| `dhcprelayd` | `SubscriberStateTable` (条件付き有効化) | `VLAN` | `dhcp_db_monitor.py:281-299, dhcprelayd.py:100-101` |
| `dhcprelayd` | `SubscriberStateTable` (条件付き有効化) | `VLAN_INTERFACE` | `dhcp_db_monitor.py:302-324, dhcprelayd.py:100-101` |
| `dhcprelayd` | `get_config_db_table()` スナップショット読み出し | `DHCPV4_RELAY` (indirect) | `dhcprelayd.py:111-113` |
| `dhcprelayd` | `get_config_db_table()` スナップショット読み出し | `DEVICE_METADATA` | `dhcprelayd.py:64,111-112` |

## DhcpRelaydDbMonitor の動作

`dhcprelayd` は `DhcpRelaydDbMonitor.check_db_update()` を呼び出して
`swsscommon.Select.select(timeout=5000ms)` でイベントを待機する。

イベント受信時は各 `ConfigDbEventChecker` の `check_update_event()` を呼び出す。
初期状態では `DhcpServerFeatureStateChecker`（`FEATURE` テーブル）のみ有効。
`dhcp_server` feature が有効化されると `VLAN` と `VLAN_INTERFACE` の checker も動的に追加される。

## DHCPV4_RELAY テーブルの読み出しパス

`DHCPV4_RELAY` テーブルは keyspace notification を用いず、
`refresh_dhcrelay()` 内で `DEVICE_METADATA.has_sonic_dhcpv4_relay` を確認してから
`_start_dhcrelay_process()` を呼ぶ経路の中で間接的に参照される（`dhcprelayd.py:111-113`）。

実際の relay 設定（サーバ IP リスト等）は `dhcp4relay` C++ プロセスが supervisord 設定ファイルから
コマンドライン引数として受け取り、`DHCPV4_RELAY` テーブルを直接 subscribe しない旧来方式のラッパとして動作する。

## APPL_DB / STATE_DB への書き込み

`dhcprelayd` は CONFIG_DB・APPL_DB・STATE_DB への書き込みを行わない。
カウンタは `dhcp4relay` C++ プロセスが `COUNTERS_DB.COUNTERS_DHCPV4` に書き込む（Phase F 参照）。
