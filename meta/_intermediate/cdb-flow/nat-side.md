# Phase F 調査メモ: NAT_GLOBAL 副次 DB 書込 (STATE_DB / APPL_DB / COUNTERS_DB)

調査日: 2026-05-15
対象テーブル: CONFIG_DB `NAT_GLOBAL` / `NAT_POOL` / `NAT_BINDINGS` / `STATIC_NAT`

## 調査対象ファイル

- `sonic-swss/cfgmgr/natmgr.cpp` (NatMgr)
- `sonic-swss/orchagent/natorch.cpp` (NatOrch)
- `sonic-swss-common/common/schema.h` (テーブル名定数)

---

## 副次 DB 書込まとめ

### APPL_DB への書込

| テーブル定数 | 実テーブル名 | 書込コンポーネント | 書込条件 | ソース |
|---|---|---|---|---|
| `APP_NAT_GLOBAL_TABLE_NAME` | `NAT_GLOBAL_TABLE` | `NatMgr` | `admin_mode` 変更時または timeout 変更 (NAT 有効時のみ) | `natmgr.cpp:5706, 5756, 7317, 7360` |
| `APP_NAT_TABLE_NAME` | `NAT_TABLE` | `NatMgr` | STATIC_NAT エントリ追加 (`addStaticNatEntry()`) | `natmgr.cpp:2052-2053` |
| `APP_NAT_DNAT_POOL_TABLE_NAME` | `NAT_DNAT_POOL_TABLE` | `NatMgr` | DNAT pool エントリ追加/削除 | `natmgr.cpp:1520, 1543` |

**主な書込フィールド (NAT_GLOBAL_TABLE)**:
- `admin_mode`: `"enabled"` / `"disabled"`
- `nat_tcp_timeout`: 非デフォルト値 (≠ 86400) 時のみ書込
- `nat_udp_timeout`: 非デフォルト値 (≠ 300) 時のみ書込
- `nat_timeout`: 非デフォルト値 (≠ 600) 時のみ書込

### STATE_DB への書込

`NatMgr` / `NatOrch` いずれも STATE_DB への **書込はなし**。
STATE_DB を「読む」操作のみ:
- `STATE_PORT_TABLE`: Ethernet readiness ガード
- `STATE_LAG_TABLE`: PortChannel readiness ガード
- `STATE_VLAN_TABLE`: Vlan readiness ガード
- `STATE_INTERFACE_TABLE`: L3 インタフェース readiness ガード

### COUNTERS_DB への書込

`NatOrch` がコンストラクタおよびエントリ追加/削除ごとに書込。

| テーブル定数 | 実テーブル名 | キー形式 | 書込フィールド | 書込タイミング |
|---|---|---|---|---|
| `COUNTERS_GLOBAL_NAT_TABLE` | `COUNTERS_GLOBAL_NAT` | `Values` | `MAX_NAT_ENTRIES`, `TIMEOUT`, `UDP_TIMEOUT`, `TCP_TIMEOUT` | NatOrch コンストラクタ起動時 |
| `COUNTERS_GLOBAL_NAT_TABLE` | `COUNTERS_GLOBAL_NAT` | `Values` | `STATIC_NAT_ENTRIES`, `STATIC_NAPT_ENTRIES`, `STATIC_TWICE_NAT_ENTRIES`, `STATIC_TWICE_NAPT_ENTRIES` | 各 static エントリ追加/削除時 |
| `COUNTERS_GLOBAL_NAT_TABLE` | `COUNTERS_GLOBAL_NAT` | `Values` | `DYNAMIC_NAT_ENTRIES`, `DYNAMIC_NAPT_ENTRIES`, `DYNAMIC_TWICE_NAT_ENTRIES`, `DYNAMIC_TWICE_NAPT_ENTRIES` | 各 dynamic エントリ追加/削除時 |
| `COUNTERS_GLOBAL_NAT_TABLE` | `COUNTERS_GLOBAL_NAT` | `Values` | `SNAT_ENTRIES`, `DNAT_ENTRIES` | エントリ方向カウント更新時 |
| `COUNTERS_NAT_TABLE` | `COUNTERS_NAT` | `<global_ip>` | `NAT_TRANSLATIONS_PKTS`, `NAT_TRANSLATIONS_BYTES` | NAT hitbit query タイマー (5秒ごと) |
| `COUNTERS_NAPT_TABLE` | `COUNTERS_NAPT` | `<proto>:<ip>:<port>` | `NAT_TRANSLATIONS_PKTS`, `NAT_TRANSLATIONS_BYTES` | NAPT hitbit query タイマー (5秒ごと) |
| `COUNTERS_TWICE_NAT_TABLE` | `COUNTERS_TWICE_NAT` | `<src_ip>:<dst_ip>` | `NAT_TRANSLATIONS_PKTS`, `NAT_TRANSLATIONS_BYTES` | Twice NAT hitbit query タイマー (5秒ごと) |
| `COUNTERS_TWICE_NAPT_TABLE` | `COUNTERS_TWICE_NAPT` | `<proto>:<src_ip>:<src_port>:<dst_ip>:<dst_port>` | `NAT_TRANSLATIONS_PKTS`, `NAT_TRANSLATIONS_BYTES` | Twice NAPT hitbit query タイマー (5秒ごと) |

ソース: `natorch.cpp:51-56, 124-135, 4060, 4067, 4074, 4089, 4097, 4105, 4119, 4134, 4481-4588`

---

## 書込発生の詳細条件

### NatMgr コンストラクタ起動時
なし (APPL_DB への書込はない; COUNTERS_DB への初期化は NatOrch が担当)

### admin_mode=enabled → APPL_DB 書込
`NatMgr::enableNatFeature()` (`natmgr.cpp:5667-5733`) が以下を APPL_DB `NAT_GLOBAL_TABLE|Values` に書込:
- `admin_mode = "enabled"` (常に書込)
- `nat_tcp_timeout` (非デフォルト値のみ)
- `nat_udp_timeout` (非デフォルト値のみ)
- `nat_timeout` (非デフォルト値のみ)

### admin_mode=disabled → APPL_DB 書込
`NatMgr::disableNatFeature()` (`natmgr.cpp:5736-5767`) が:
- `admin_mode = "disabled"` を `NAT_GLOBAL_TABLE|Values` に書込

### タイムアウト変更時 (admin_mode=enabled のみ)
`NatMgr::doNatGlobalTask()` SET ブランチ (`natmgr.cpp:7315-7318`) で:
- 変更があった timeout フィールドのみ APPL_DB に書込 (nat_enabled チェック後)

### NatOrch コンストラクタ起動時
`COUNTERS_GLOBAL_NAT|Values` に初期値を書込:
- `MAX_NAT_ENTRIES`: SAI `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` 返値
- `TIMEOUT = 600`, `UDP_TIMEOUT = 300`, `TCP_TIMEOUT = 86400`

### NAT hitbit タイマー (5秒周期)
`COUNTERS_NAT / COUNTERS_NAPT / COUNTERS_TWICE_NAT / COUNTERS_TWICE_NAPT` にパケット/バイトカウンタを更新

---

## FLUSH 通知 (副次効果)

`FLUSHNATSTATISTICS` 通知を受信すると、`NatOrch` が全 NAT/NAPT エントリの `COUNTERS_*` テーブルエントリを 0 にリセット (`natorch.cpp:3955-4038`)。

`NAT_DB_CLEANUP_NOTIFICATION` 通知を受信すると、全 dynamic NAT エントリを削除し COUNTERS_DB のエントリも削除する。

---

## 証跡サマリ

| DB | テーブル | 方向 | コンポーネント |
|---|---|---|---|
| APPL_DB | `NAT_GLOBAL_TABLE` | WRITE | NatMgr |
| APPL_DB | `NAT_TABLE` | WRITE | NatMgr |
| APPL_DB | `NAT_DNAT_POOL_TABLE` | WRITE | NatMgr |
| COUNTERS_DB | `COUNTERS_GLOBAL_NAT` | WRITE | NatOrch |
| COUNTERS_DB | `COUNTERS_NAT` | WRITE | NatOrch |
| COUNTERS_DB | `COUNTERS_NAPT` | WRITE | NatOrch |
| COUNTERS_DB | `COUNTERS_TWICE_NAT` | WRITE | NatOrch |
| COUNTERS_DB | `COUNTERS_TWICE_NAPT` | WRITE | NatOrch |
| STATE_DB | 各 STATE_*_TABLE | READ ONLY | NatMgr |
