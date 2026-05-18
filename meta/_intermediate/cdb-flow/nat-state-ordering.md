# nat-state — Phase B ordering 調査メモ

## 対象テーブル
- `STATE_DB:NAT_RESTORE_TABLE|Flags`
- `COUNTERS_DB:COUNTERS_NAT|<ip>`
- `COUNTERS_DB:COUNTERS_NAPT|<proto:ip:port>`
- `COUNTERS_DB:COUNTERS_TWICE_NAT|<src_ip:dst_ip>`
- `COUNTERS_DB:COUNTERS_TWICE_NAPT|<proto:src_ip:src_port:dst_ip:dst_port>`
- `COUNTERS_DB:COUNTERS_GLOBAL_NAT|Values`

## 主要依存

1. warm reboot: `restore_nat_entries.py` → `NAT_RESTORE_TABLE|Flags.restored = "true"` → natsyncd reconciliation 開始
   - evidence: `natsync.cpp:96-108` (`isNatRestoreDone`)
2. NatOrch constructor → `COUNTERS_GLOBAL_NAT|Values` 1 回書込み
   - evidence: `natorch.cpp:108-134`
3. SAI NAT エントリ登録 → `COUNTERS_NAT|<ip>` / `COUNTERS_NAPT` 初期値 `0` 書込み
   - evidence: `natorch.cpp:789` (`updateNatCounters(ip_address, 0, 0)`)
4. `admin_mode=enabled` → `m_natQueryTimer` 起動 → 5 秒周期 `queryCounters()` → `COUNTERS_NAT*` 更新
   - evidence: `natorch.cpp:2565`, `natorch.cpp:3099-3115`
5. `admin_mode=disabled` → `m_natQueryTimer` 停止 → カウンタ更新停止
   - evidence: `natorch.cpp:2602`
6. `MAX_NAT_ENTRIES=0` → `gIsNatSupported=false` → NAT SAI 操作全スキップ（カウンタキーは書かれる）
   - evidence: `natorch.cpp:100-122`, `natorch.cpp:2541-2544`

## 非依存
- `NAT_RESTORE_TABLE` と `COUNTERS_DB:COUNTERS_NAT*` は独立した書き手が管理し相互ブロックなし
