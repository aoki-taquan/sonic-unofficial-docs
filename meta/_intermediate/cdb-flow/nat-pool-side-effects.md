# NAT_POOL — 副次 DB 書込調査 (Phase F)

調査対象: `sonic-swss/cfgmgr/natmgr.cpp` / `sonic-swss/orchagent/natorch.cpp`

## 書込経路まとめ

`NAT_POOL` エントリが `natmgrd::doNatPoolTask()` で処理され、対応する `NAT_BINDINGS` が存在して
全前提条件を満たすと以下の副次書込が発生する。

### APPL_DB: NAT_DNAT_POOL_TABLE

- 関数: `NatMgr::setDnatPoolfromNatPool(ADD/DELETE, ip_range)` → `addDnatPoolEntry()` / `removeDnatPoolEntry()`
- キー: pool 内の各 IP アドレス (`NAT_DNAT_POOL_TABLE|<ip>`)
- 値: `NULL: NULL` (フィールドなし、存在通知のみ)
- 参照元: `natmgr.cpp:1520`
- ref-count 管理: `m_natDnatPoolInfo[destIp]` で参照カウントを保持。複数 binding が同一 pool IP を参照する場合は
  ref-count が 0 になるまで削除しない (`natmgr.cpp:1540-1543`)
- 呼び出し箇所:
  - pool SET + binding 存在: `addDynamicNatRule()` L4672
  - pool DEL + binding 存在: `removeDynamicNatRule()` L4732

### ASIC_DB: SAI NAT_ENTRY (SAI_NAT_TYPE_DESTINATION_NAT_POOL)

- 関数: `NatOrch::addHwDnatPoolEntry(ip_address)` / `removeHwDnatPoolEntry(dstIp)`
- SAI API: `sai_nat_api->create_nat_entry()` / `sai_nat_api->remove_nat_entry()`
- nat_type: `SAI_NAT_TYPE_DESTINATION_NAT_POOL`
- 参照元: `natorch.cpp:1805`, `natorch.cpp:1837`
- 前提: `isNatEnabled()` が true。false の場合は SAI 書込をスキップして true を返す (`natorch.cpp:1789-1793`)
- 呼び出し: `doDnatPoolTableTask()` L3004 が APPL_DB `NAT_DNAT_POOL_TABLE` 変更を受けて呼び出す

### COUNTERS_DB: COUNTERS_GLOBAL_NAT

- フィールド `DNAT_ENTRIES` が DNAT エントリ (static/dynamic) の追加・削除ごとに更新される
- ただし DNAT pool 専用のカウンタはなく、`addHwDnatPoolEntry()` 自体は COUNTERS_DB を更新しない
- `COUNTERS_GLOBAL_NAT|Values` の `MAX_NAT_ENTRIES` は NatOrch 初期化時に
  SAI `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` クエリ値で一度だけ書込まれる (`natorch.cpp:127`, `natorch.cpp:135`)

### STATE_DB: 書込なし

`NatMgr` および `NatOrch` は STATE_DB への書込を行わない。
`STATE_PORT_TABLE` / `STATE_LAG_TABLE` / `STATE_INTERFACE_TABLE` は L3 インタフェース readiness
ガード用の読み取り専用アクセスのみ。

## 前提条件 (書込がスキップされる場合)

1. `isNatEnabled()` が false: `addDynamicNatRule()` 冒頭でスキップ (`natmgr.cpp:4632-4636`)
2. pool に紐づく `NAT_BINDINGS` が存在しない: `isPoolMappedtoBinding()` が false → APPL_DB 書込なし
3. L3 インタフェースが未準備: `getIpEnabledIntf()` が false → APPL_DB 書込なし (`natmgr.cpp:4654-4659`)
