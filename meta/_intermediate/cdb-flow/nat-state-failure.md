# nat-state — Phase D 失敗挙動 (intermediate)

slug: nat-state
phase: D (failure)
tables: STATE_DB:NAT_RESTORE_TABLE, COUNTERS_DB:COUNTERS_NAT*
daemons: restore_nat_entries.py, NatOrch (natorch.cpp), natsyncd (natsync.cpp)

## 主要失敗パターン

1. SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY 取得失敗 → MAX_NAT_ENTRIES="0" → gIsNatSupported=false → NAT 全機能無効
2. sai_nat_api->create_nat_entry() 失敗 → COUNTERS_NAT|<ip> 初期値書き込みスキップ → show nat statistics でカウンタ欠落
3. enableNatFeature() の SAI_SWITCH_ATTR_NAT_ENABLE set 失敗 → SWSS_LOG_ERROR + 処理継続 (タイマーは起動)
4. restore_nat_entries.py 例外 → sys.exit(1) → NAT_RESTORE_TABLE|Flags.restored 未書き込み → natsyncd が reconciliation 開始できない
5. gIsNatSupported==false で enableNatFeature() → 即時 return → タイマー未起動 → カウンタ未更新

## evidence

- natorch.cpp: L107-135 (constructor SAI query), L773-789 (addDNatEntry), L1307-1322 (addSNatEntry), L2541-2545, L2557-2562 (enableNatFeature)
- restore_nat_entries.py: L85-91 (main try/except), L47-52 (set_statedb_nat_restore_done)
- natsync.cpp: L96-108 (isNatRestoreDone)
