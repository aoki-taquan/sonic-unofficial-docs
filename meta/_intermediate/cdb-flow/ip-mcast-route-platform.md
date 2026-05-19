# ip-mcast-route — プラットフォーム差 (Phase H) 調査メモ

## 調査対象

`docs/reference/config-db/ip-mcast-route.md` Phase H 追加分。
P4RT IPMC (REPLICATION_IP_MULTICAST_TABLE / FIXED_IPV4_MULTICAST_TABLE / FIXED_IPV6_MULTICAST_TABLE) の
プラットフォーム固有挙動・制約を調査する。

## 調査ファイル

- `sonic-swss/orchagent/p4orch/ip_multicast_manager.cpp`
- `sonic-swss/orchagent/p4orch/l3_multicast_manager.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/crmorch.cpp`, `crmorch.h`

## 結果

### プラットフォーム条件分岐なし

`ip_multicast_manager.cpp` / `l3_multicast_manager.cpp` に `getenv("platform")` / `MLNX_PLATFORM_SUBSTRING` / `broadcom` 等のプラットフォーム判定コードは存在しない。ASIC 種別に関わらず同一コードパスで動作する。

### IPMC エントリ容量: SAI_SWITCH_ATTR_AVAILABLE_IPMC_ENTRY

`IpMulticastManager` は IPMC エントリ作成成功時に `gCrmOrch->incCrmResUsedCounter(CRM_IPMC_ENTRY)` を呼ぶ (`ip_multicast_manager.cpp:774`)。削除時は `decCrmResUsedCounter(CRM_IPMC_ENTRY)` (`ip_multicast_manager.cpp:885`)。`CrmOrch` は `SAI_SWITCH_ATTR_AVAILABLE_IPMC_ENTRY` (`crmorch.cpp:89`) で残容量を監視する。容量はハードウェア依存。

### P4Orch は常に生成 — ただし P4RT 非対応 ASIC では SAI エラーが発生

`orchdaemon.cpp:849` で `gP4Orch = new P4Orch(...)` は常に実行される（プラットフォーム条件なし）。P4RT / IPMC をサポートしない ASIC では、SAI 呼び出し (`create_ipmc_group` / `create_ipmc_entry`) がエラーを返し、`L3MulticastManager::processAddReplicationIpMulticastEntry` / `IpMulticastManager::createIPMCEntry` が `SWSS_RC_UNIMPLEMENTED` 等の SAI エラーを上流に返す。

### multi-asic 環境

`P4Orch` / `L3MulticastManager` / `IpMulticastManager` には multi-asic (is_multi_npu) や namespace への明示的な対応コードが存在しない。orchagent はシングル ASIC の global namespace プロセスとして動作し、multi-asic 構成での分散処理は考慮されていない。実質的に single-ASIC（または switch_type=dpu）専用のサブシステム。

### VOQ chassis

`switch_type == "voq"` 向けの分岐なし。P4RT マルチキャストは VOQ chassis には適用されない。

## 結論

P4RT IPMC にはプラットフォーム固有コードパスがなく、ASIC 差はすべて SAI 実装（create_ipmc_group/entry の成否）に委ねられる。エントリ上限は `SAI_SWITCH_ATTR_AVAILABLE_IPMC_ENTRY` で管理される。multi-asic / VOQ 専用対応なし。

## evidence

- `sonic-swss/orchagent/p4orch/ip_multicast_manager.cpp:774,885` — `gCrmOrch->incCrmResUsedCounter/decCrmResUsedCounter(CRM_IPMC_ENTRY)`
- `sonic-swss/orchagent/crmorch.cpp:89` — `CRM_IPMC_ENTRY` → `SAI_SWITCH_ATTR_AVAILABLE_IPMC_ENTRY`
- `sonic-swss/orchagent/orchdaemon.cpp:849` — P4Orch 無条件生成
