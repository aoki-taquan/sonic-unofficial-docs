# nat-counters-defaults.md — Phase A 中間ファイル

対象: `docs/reference/config-db/nat-counters.md`
調査日: 2026-05-15

## 調査ファイル

- `sonic-swss/orchagent/natorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss-common/common/schema.h` (SHA: 158de8d3463ff4b841653f6d57190bb142b80d9c)

## テーブル定数 (schema.h)

```
COUNTERS_NAT_TABLE          = "COUNTERS_NAT"         (schema.h:260)
COUNTERS_NAPT_TABLE         = "COUNTERS_NAPT"        (schema.h:261)
COUNTERS_TWICE_NAT_TABLE    = "COUNTERS_TWICE_NAT"   (schema.h:262)
COUNTERS_TWICE_NAPT_TABLE   = "COUNTERS_TWICE_NAPT"  (schema.h:263)
COUNTERS_GLOBAL_NAT_TABLE   = "COUNTERS_GLOBAL_NAT"  (schema.h:264)
```

## COUNTERS_NAT — 単体 NAT カウンタ

書き込み元: `NatOrch::updateNatCounters()` (natorch.cpp:4049-4061)
初期化: `updateNatCounters(ipAddr, 0, 0)` — `addSnatEntry` / `addDnatEntry` 直後 (natorch.cpp:789, 1322)

キー: `<external_ip>` (例: `65.55.45.1`)

```cpp
// natorch.cpp:4055-4058
FieldValueTuple p("NAT_TRANSLATIONS_PKTS",  std::to_string(nat_translations_pkts));
FieldValueTuple q("NAT_TRANSLATIONS_BYTES", std::to_string(nat_translations_bytes));
```

| フィールド | 型 | 初期値 | ソース行 |
|-----------|-----|--------|---------|
| `NAT_TRANSLATIONS_PKTS` | uint64 (string) | `"0"` | natorch.cpp:789 (addSnatEntry 内 updateNatCounters 呼び出し) |
| `NAT_TRANSLATIONS_BYTES` | uint64 (string) | `"0"` | natorch.cpp:789 |

削除: `deleteNatCounters(ipAddr)` — SNAT/DNAT エントリ削除時 (natorch.cpp:4063-4067)

## COUNTERS_NAPT — 単体 NAPT カウンタ

書き込み元: `NatOrch::updateNaptCounters()` (natorch.cpp:4077-4089)
初期化: `updateNaptCounters(proto, ip, port, 0, 0)` — `addSnatEntry` / `addDnatEntry` NAPT 版 直後 (natorch.cpp:873)

キー: `<protocol>:<ip>:<port>` (例: `TCP:10.0.0.1:1024`)

```cpp
// natorch.cpp:4084-4087
FieldValueTuple p("NAT_TRANSLATIONS_PKTS",  to_string(nat_translations_pkts));
FieldValueTuple q("NAT_TRANSLATIONS_BYTES", to_string(nat_translations_bytes));
```

| フィールド | 型 | 初期値 | ソース行 |
|-----------|-----|--------|---------|
| `NAT_TRANSLATIONS_PKTS` | uint64 (string) | `"0"` | natorch.cpp:873 |
| `NAT_TRANSLATIONS_BYTES` | uint64 (string) | `"0"` | natorch.cpp:873 |

削除: `deleteNaptCounters(proto, ip, port)` (natorch.cpp:4092-4097)

## COUNTERS_TWICE_NAT — Twice NAT カウンタ

書き込み元: `NatOrch::updateTwiceNatCounters()` (natorch.cpp:4108-4120)
初期化: `updateTwiceNatCounters(key, 0, 0)` — `addTwiceNatEntry` 直後

キー: `<src_ip>:<dst_ip>` (例: `10.0.0.1:20.0.0.1`)

```cpp
// natorch.cpp:4113-4116
FieldValueTuple p("NAT_TRANSLATIONS_PKTS",  to_string(nat_translations_pkts));
FieldValueTuple q("NAT_TRANSLATIONS_BYTES", to_string(nat_translations_bytes));
```

| フィールド | 型 | 初期値 |
|-----------|-----|--------|
| `NAT_TRANSLATIONS_PKTS` | uint64 (string) | `"0"` |
| `NAT_TRANSLATIONS_BYTES` | uint64 (string) | `"0"` |

削除: `deleteTwiceNatCounters(key)` (natorch.cpp:4070-4074)

## COUNTERS_TWICE_NAPT — Twice NAPT カウンタ

書き込み元: `NatOrch::updateTwiceNaptCounters()` (natorch.cpp:4122-4135)
初期化: `updateTwiceNaptCounters(key, 0, 0)` — `addTwiceNaptEntry` 直後

キー: `<proto>:<src_ip>:<src_port>:<dst_ip>:<dst_port>`

```cpp
// natorch.cpp:4128-4131
FieldValueTuple p("NAT_TRANSLATIONS_PKTS",  to_string(nat_translations_pkts));
FieldValueTuple q("NAT_TRANSLATIONS_BYTES", to_string(nat_translations_bytes));
```

| フィールド | 型 | 初期値 |
|-----------|-----|--------|
| `NAT_TRANSLATIONS_PKTS` | uint64 (string) | `"0"` |
| `NAT_TRANSLATIONS_BYTES` | uint64 (string) | `"0"` |

削除: `deleteTwiceNaptCounters(key)` (natorch.cpp:4100-4105)

## COUNTERS_GLOBAL_NAT — グローバル統計

書き込み元: NatOrch コンストラクタおよび各 `update*Counters()` 関数

キー: `"Values"` (固定)

### 初期書き込み (NatOrch コンストラクタ, natorch.cpp:124-135)

```cpp
// natorch.cpp:66-73 (デフォルト値設定)
admin_mode   = "disabled";
timeout      = 600;         // NAT タイムアウト
tcp_timeout  = 86400;       // TCP NAT タイムアウト (1日)
udp_timeout  = 300;         // UDP NAT タイムアウト

// natorch.cpp:127-130 (COUNTERS_DB への書き込み)
FieldValueTuple p("MAX_NAT_ENTRIES", to_string(maxAllowedSNatEntries));  // SAI query
FieldValueTuple q("TIMEOUT",         to_string(timeout));                 // 600
FieldValueTuple r("UDP_TIMEOUT",     to_string(udp_timeout));             // 300
FieldValueTuple s("TCP_TIMEOUT",     to_string(tcp_timeout));             // 86400
```

`maxAllowedSNatEntries` は `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` から取得。
失敗時は 0 のまま書き込まれ、`gIsNatSupported = false` が設定される。

### 実行時更新 (natorch.cpp:4481-4589)

```cpp
void NatOrch::updateStaticNatCounters(int count)      { FieldValueTuple("STATIC_NAT_ENTRIES", ...) }
void NatOrch::updateStaticNaptCounters(int count)     { FieldValueTuple("STATIC_NAPT_ENTRIES", ...) }
void NatOrch::updateStaticTwiceNatCounters(int count) { FieldValueTuple("STATIC_TWICE_NAT_ENTRIES", ...) }
void NatOrch::updateStaticTwiceNaptCounters(int count){ FieldValueTuple("STATIC_TWICE_NAPT_ENTRIES", ...) }
void NatOrch::updateDynamicNatCounters(int count)     { FieldValueTuple("DYNAMIC_NAT_ENTRIES", ...) }
void NatOrch::updateDynamicNaptCounters(int count)    { FieldValueTuple("DYNAMIC_NAPT_ENTRIES", ...) }
void NatOrch::updateDynamicTwiceNatCounters(int count){ FieldValueTuple("DYNAMIC_TWICE_NAT_ENTRIES", ...) }
void NatOrch::updateDynamicTwiceNaptCounters(int count){ FieldValueTuple("DYNAMIC_TWICE_NAPT_ENTRIES", ...) }
void NatOrch::updateSnatCounters(int count)           { FieldValueTuple("SNAT_ENTRIES", ...) }
void NatOrch::updateDnatCounters(int count)           { FieldValueTuple("DNAT_ENTRIES", ...) }
```

初期値はすべて `"0"` (NatOrch コンストラクタで `totalEntries = totalSnatEntries = totalDnatEntries = 0;` natorch.cpp:76-80)

### 全フィールド一覧 (COUNTERS_GLOBAL_NAT|Values)

| フィールド | 型 | 初期値 | 更新タイミング | ソース行 |
|-----------|-----|--------|---------------|---------|
| `MAX_NAT_ENTRIES` | uint32 (string) | SAI query 値 (失敗時 `"0"`) | コンストラクタのみ | natorch.cpp:127 |
| `TIMEOUT` | uint32 (string) | `"600"` | コンストラクタのみ | natorch.cpp:128 |
| `UDP_TIMEOUT` | uint32 (string) | `"300"` | コンストラクタのみ | natorch.cpp:129 |
| `TCP_TIMEOUT` | uint32 (string) | `"86400"` | コンストラクタのみ | natorch.cpp:130 |
| `STATIC_NAT_ENTRIES` | int (string) | `"0"` | static NAT エントリ追加/削除 | natorch.cpp:4486 |
| `STATIC_NAPT_ENTRIES` | int (string) | `"0"` | static NAPT エントリ追加/削除 | natorch.cpp:4497 |
| `STATIC_TWICE_NAT_ENTRIES` | int (string) | `"0"` | static Twice NAT エントリ追加/削除 | natorch.cpp:4508 |
| `STATIC_TWICE_NAPT_ENTRIES` | int (string) | `"0"` | static Twice NAPT エントリ追加/削除 | natorch.cpp:4519 |
| `DYNAMIC_NAT_ENTRIES` | int (string) | `"0"` | dynamic NAT エントリ追加/削除 | natorch.cpp:4530 |
| `DYNAMIC_NAPT_ENTRIES` | int (string) | `"0"` | dynamic NAPT エントリ追加/削除 | natorch.cpp:4541 |
| `DYNAMIC_TWICE_NAT_ENTRIES` | int (string) | `"0"` | dynamic Twice NAT エントリ追加/削除 | natorch.cpp:4552 |
| `DYNAMIC_TWICE_NAPT_ENTRIES` | int (string) | `"0"` | dynamic Twice NAPT エントリ追加/削除 | natorch.cpp:4563 |
| `SNAT_ENTRIES` | int (string) | `"0"` | SNAT エントリ追加/削除 | natorch.cpp:4574 |
| `DNAT_ENTRIES` | int (string) | `"0"` | DNAT エントリ追加/削除 | natorch.cpp:4585 |

## コード由来デフォルトまとめ (Phase A)

| フィールド | テーブル | 初期値 | ソース |
|-----------|---------|--------|--------|
| `NAT_TRANSLATIONS_PKTS` | `COUNTERS_NAT` / `COUNTERS_NAPT` | `"0"` | natorch.cpp:789,873 |
| `NAT_TRANSLATIONS_BYTES` | `COUNTERS_NAT` / `COUNTERS_NAPT` | `"0"` | natorch.cpp:789,873 |
| `NAT_TRANSLATIONS_PKTS` | `COUNTERS_TWICE_NAT` / `COUNTERS_TWICE_NAPT` | `"0"` | natorch.cpp 各 addTwice* 直後 |
| `NAT_TRANSLATIONS_BYTES` | `COUNTERS_TWICE_NAT` / `COUNTERS_TWICE_NAPT` | `"0"` | 同上 |
| `MAX_NAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | SAI query 値 (失敗時 `"0"`) | natorch.cpp:127 |
| `TIMEOUT` | `COUNTERS_GLOBAL_NAT\|Values` | `"600"` | natorch.cpp:128 |
| `UDP_TIMEOUT` | `COUNTERS_GLOBAL_NAT\|Values` | `"300"` | natorch.cpp:129 |
| `TCP_TIMEOUT` | `COUNTERS_GLOBAL_NAT\|Values` | `"86400"` | natorch.cpp:130 |
| `STATIC_NAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | natorch.cpp:4486 |
| `STATIC_NAPT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | natorch.cpp:4497 |
| `STATIC_TWICE_NAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | natorch.cpp:4508 |
| `STATIC_TWICE_NAPT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | natorch.cpp:4519 |
| `DYNAMIC_NAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | natorch.cpp:4530 |
| `DYNAMIC_NAPT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | natorch.cpp:4541 |
| `DYNAMIC_TWICE_NAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | natorch.cpp:4552 |
| `DYNAMIC_TWICE_NAPT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | natorch.cpp:4563 |
| `SNAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | natorch.cpp:4574 |
| `DNAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | natorch.cpp:4585 |

## 暗黙挙動・注意点

1. **COUNTERS_NAT* は 5 秒周期で更新**: タイマー `NAT_HITBIT_N_CNTRS_QUERY_PERIOD=5` (natorch.h:37) で SAI hit bit + counter を定期取得。リアルタイムではない。
2. **MAX_NAT_ENTRIES=0 → NAT 機能無効**: SAI 問い合わせ失敗または 0 → `gIsNatSupported=false` → `enableNatFeature()` が即座に return (natorch.cpp:2541-2544)。
3. **COUNTERS_GLOBAL_NAT TIMEOUT 系は起動時のみ書き込み**: CONFIG_DB の `NAT_GLOBAL.nat_timeout` が後から変更されても COUNTERS_GLOBAL_NAT は更新されない。
4. **Static エントリのカウンタ**: `entry_type="static"` でも SAI hit bit 取得対象 (`checkIfNatEntryIsActive` は static を常に active=1 扱い, natorch.cpp:4160-4163)。エージアウトされない。
