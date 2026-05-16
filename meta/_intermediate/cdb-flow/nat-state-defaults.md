# nat-state-defaults.md — Phase A 中間ファイル

対象: `docs/reference/config-db/nat-state.md`
調査日: 2026-05-14

## 調査ファイル

- `sonic-swss/natsyncd/natsync.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/natorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/natorch.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss-common/common/schema.h` (SHA: 158de8d3463ff4b841653f6d57190bb142b80d9c)
- `sonic-buildimage/dockers/docker-nat/restore_nat_entries.py` (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)

## STATE_DB NAT_RESTORE_TABLE

定数: `STATE_NAT_RESTORE_TABLE_NAME = "NAT_RESTORE_TABLE"` (schema.h:439)

### キー・フィールド

書き込み元: `restore_nat_entries.py` — warm reboot 後の NAT conntrack 復元スクリプト

```python
# restore_nat_entries.py:49-52
statedb = swsscommon.DBConnector("STATE_DB", 0)
tbl = swsscommon.Table(statedb, "NAT_RESTORE_TABLE")
fvs = swsscommon.FieldValuePairs([("restored", "true")])
tbl.set("Flags", fvs)
```

| key | フィールド | 値 | 書き込みタイミング |
|-----|-----------|-----|-------------------|
| `Flags` | `restored` | `"true"` | natsyncd/restore_nat_entries.py 起動後、conntrack 復元完了時 |

### 読み取り元: natsync.cpp

```cpp
// natsync.cpp:102
m_stateNatRestoreTable.hget("Flags", "restored", value);
```

`natsyncd` が warm start 中の reconciliation 開始前にこのフラグを確認し、`"true"` になってから APPL_DB との差分処理を行う。

## COUNTERS_DB NAT テーブル群

定数 (schema.h):
```
COUNTERS_NAT_TABLE     = "COUNTERS_NAT"   (schema.h:260)
COUNTERS_NAPT_TABLE    = "COUNTERS_NAPT"  (schema.h:261)
COUNTERS_TWICE_NAT_TABLE  = "COUNTERS_TWICE_NAT"  (schema.h:262)
COUNTERS_TWICE_NAPT_TABLE = "COUNTERS_TWICE_NAPT" (schema.h:263)
COUNTERS_GLOBAL_NAT_TABLE = "COUNTERS_GLOBAL_NAT" (schema.h:264)
```

### COUNTERS_NAT (単体 NAT エントリのカウンタ)

キー: `<external_ip>` (IP アドレス文字列)

フィールド (natorch.cpp:4055-4058):
```cpp
FieldValueTuple p("NAT_TRANSLATIONS_PKTS",  std::to_string(nat_translations_pkts));
FieldValueTuple q("NAT_TRANSLATIONS_BYTES", std::to_string(nat_translations_bytes));
```

| フィールド | 型 | 初期値 | 説明 |
|-----------|-----|--------|------|
| `NAT_TRANSLATIONS_PKTS` | uint64 (string) | `"0"` (natorch.cpp:789) | SAI から取得したパケット数 |
| `NAT_TRANSLATIONS_BYTES` | uint64 (string) | `"0"` (natorch.cpp:789) | SAI から取得したバイト数 |

初期値セット: `updateNatCounters(ipAddr, 0, 0)` — addSnatEntry / addDnatEntry 直後に呼ばれる (natorch.cpp:789, 1322)

### COUNTERS_NAPT (単体 NAPT エントリのカウンタ)

キー: `<protocol>:<ip>:<port>` (例: `TCP:10.0.0.1:1024`)

| フィールド | 型 | 初期値 | 説明 |
|-----------|-----|--------|------|
| `NAT_TRANSLATIONS_PKTS` | uint64 (string) | `"0"` (natorch.cpp:873) | SAI から取得したパケット数 |
| `NAT_TRANSLATIONS_BYTES` | uint64 (string) | `"0"` (natorch.cpp:873) | SAI から取得したバイト数 |

### COUNTERS_TWICE_NAT (Twice NAT エントリのカウンタ)

キー: `<src_ip>:<dst_ip>`

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `NAT_TRANSLATIONS_PKTS` | uint64 (string) | SAI から取得したパケット数 |
| `NAT_TRANSLATIONS_BYTES` | uint64 (string) | SAI から取得したバイト数 |

### COUNTERS_TWICE_NAPT (Twice NAPT エントリのカウンタ)

キー: `<proto>:<src_ip>:<src_port>:<dst_ip>:<dst_port>`

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `NAT_TRANSLATIONS_PKTS` | uint64 (string) | SAI から取得したパケット数 |
| `NAT_TRANSLATIONS_BYTES` | uint64 (string) | SAI から取得したバイト数 |

### COUNTERS_GLOBAL_NAT (NAT グローバルカウンタ)

キー: `"Values"` (固定)

初期書き込み: NatOrch コンストラクタ (natorch.cpp:124-135)

```cpp
FieldValueTuple p("MAX_NAT_ENTRIES", to_string(maxAllowedSNatEntries));
FieldValueTuple q("TIMEOUT",         to_string(timeout));         // default 600
FieldValueTuple r("UDP_TIMEOUT",     to_string(udp_timeout));     // default 300
FieldValueTuple s("TCP_TIMEOUT",     to_string(tcp_timeout));     // default 86400
```

実行時更新: `updateSnatCounters(count)` / `updateDnatCounters(count)` (natorch.cpp:4569-4589)

```cpp
FieldValueTuple p("SNAT_ENTRIES", to_string(count));  // updateSnatCounters
FieldValueTuple p("DNAT_ENTRIES", to_string(count));  // updateDnatCounters
```

| フィールド | 型 | 初期値 | 書き込み元 |
|-----------|-----|--------|-----------|
| `MAX_NAT_ENTRIES` | uint32 (string) | `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` 値; 取得失敗時 0 | NatOrch コンストラクタ (natorch.cpp:127) |
| `TIMEOUT` | uint32 (string) | `"600"` | NatOrch コンストラクタ (natorch.cpp:128) |
| `UDP_TIMEOUT` | uint32 (string) | `"300"` | NatOrch コンストラクタ (natorch.cpp:129) |
| `TCP_TIMEOUT` | uint32 (string) | `"86400"` | NatOrch コンストラクタ (natorch.cpp:130) |
| `SNAT_ENTRIES` | int (string) | `"0"` | `updateSnatCounters()` — SNAT エントリ追加/削除時 |
| `DNAT_ENTRIES` | int (string) | `"0"` | `updateDnatCounters()` — DNAT エントリ追加/削除時 |

## コード由来デフォルト (Phase A まとめ)

| フィールド | テーブル | デフォルト / 初期値 | ソース |
|-----------|---------|---------------------|--------|
| `restored` | `STATE_DB:NAT_RESTORE_TABLE\|Flags` | (なし → warm reboot 時のみ書き込まれる) | `restore_nat_entries.py:51` |
| `NAT_TRANSLATIONS_PKTS` | `COUNTERS_NAT` / `COUNTERS_NAPT` 等 | `"0"` (エントリ登録時) | `natorch.cpp:789,873` |
| `NAT_TRANSLATIONS_BYTES` | `COUNTERS_NAT` / `COUNTERS_NAPT` 等 | `"0"` (エントリ登録時) | `natorch.cpp:789,873` |
| `MAX_NAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | SAI query 値 (0 if unsupported) | `natorch.cpp:127` |
| `TIMEOUT` | `COUNTERS_GLOBAL_NAT\|Values` | `"600"` | `natorch.cpp:128` |
| `UDP_TIMEOUT` | `COUNTERS_GLOBAL_NAT\|Values` | `"300"` | `natorch.cpp:129` |
| `TCP_TIMEOUT` | `COUNTERS_GLOBAL_NAT\|Values` | `"86400"` | `natorch.cpp:130` |
| `SNAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` (起動時 totalSnatEntries=0) | `natorch.cpp:76,4574` |
| `DNAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` (起動時 totalDnatEntries=0) | `natorch.cpp:76,4585` |

## 暗黙挙動・乖離

1. **NAT_RESTORE_TABLE は warm reboot 時のみ書き込まれる**: 通常起動では `restore_nat_entries.py` が何もせず終了し、NAT_RESTORE_TABLE|Flags は存在しない。natsyncd は `hget("Flags", "restored", value)` が失敗 → value="" で reconciliation なしで進む。

2. **COUNTERS_GLOBAL_NAT|Values.MAX_NAT_ENTRIES はプラットフォーム依存**: SAI の `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` が 0 を返すと `maxAllowedSNatEntries=0` のまま書き込まれる。この場合 `gIsNatSupported=false` になり NAT 機能全体が無効化される (natorch.cpp:100-122)。

3. **COUNTERS テーブルは SAI 問い合わせ周期 (5秒) で更新**: `NAT_HITBIT_N_CNTRS_QUERY_PERIOD=5` (natorch.h:37) のタイマーで定期的に SAI hit bit + counter を取得。リアルタイムではない。

4. **Static NAT エントリのカウンタ**: `entry_type == "static"` でも `addedToHw=true` の場合は SAI hit bit 問い合わせが行われ、COUNTERS_NAT に更新される (natorch.cpp:4160-4164)。Dynamic エントリはエージアウト前に最後のカウンタ値が取得される。
