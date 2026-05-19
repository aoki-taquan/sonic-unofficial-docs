# ip-mcast-route: Phase F — 副次 DB 書込 (side-effects)

調査日: 2026-05-19  
調査対象:
- `sonic-net/sonic-swss` `orchagent/p4orch/ip_multicast_manager.cpp`
- `sonic-net/sonic-swss` `orchagent/p4orch/l3_multicast_manager.cpp`

## 結論サマリー

`REPLICATION_IP_MULTICAST_TABLE` / `FIXED_IPV4_MULTICAST_TABLE` / `FIXED_IPV6_MULTICAST_TABLE`
への書き込みが引き起こす副次的な状態変化は以下に集約される。

1. **SAI ASIC 側への書き込み** (ASIC_STATE 経由; 主目的)
2. **P4OidMapper 内部テーブル更新** (in-process OID キャッシュ; Redis DB ではない)
3. **CRM カウンタ更新** (`COUNTERS_DB::CRM_IPMC_ENTRY` 相当; `gCrmOrch` 経由)
4. **VRF 参照カウント更新** (`VRFOrch` 内部カウンタ; FIXED テーブルのみ)
5. **APP_P4RT_TABLE へのステータス書き戻し** (失敗/成功通知; m_publisher 経由)

STATE_DB / APPL_DB への直接書き込みは一切ない。COUNTERS_DB への書き込みは CRM 経由のみ。

## 詳細

### 1. SAI / ASIC_STATE

| 操作 | テーブル | SAI API | コード根拠 |
|------|---------|---------|-----------|
| REPLICATION SET | SAI_OBJECT_TYPE_IPMC_GROUP | `sai_ipmc_group_api->create_ipmc_group()` | `l3_multicast_manager.cpp:L2196` |
| REPLICATION SET | SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER (replicas 数) | `sai_ipmc_group_api->create_ipmc_group_member()` | `l3_multicast_manager.cpp:L2262` |
| REPLICATION DEL | SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER | `sai_ipmc_group_api->remove_ipmc_group_member()` | `l3_multicast_manager.cpp:L2552` |
| REPLICATION DEL | SAI_OBJECT_TYPE_IPMC_GROUP | `sai_ipmc_group_api->remove_ipmc_group()` | `l3_multicast_manager.cpp:L2247` |
| FIXED SET (初回のみ) | SAI_OBJECT_TYPE_RPF_GROUP + SAI_OBJECT_TYPE_RPF_GROUP_MEMBER | `sai_rpf_group_api->create_rpf_group()` / `create_rpf_group_member()` | `ip_multicast_manager.cpp:L651-665` |
| FIXED SET | SAI_OBJECT_TYPE_IPMC_ENTRY | `sai_ipmc_api->create_ipmc_entry()` | `ip_multicast_manager.cpp:L761` |
| FIXED DEL | SAI_OBJECT_TYPE_IPMC_ENTRY | `sai_ipmc_api->remove_ipmc_entry()` | `ip_multicast_manager.cpp:L874` |
| FIXED DEL (最終エントリ削除後) | SAI_OBJECT_TYPE_RPF_GROUP_MEMBER + SAI_OBJECT_TYPE_RPF_GROUP | `sai_rpf_group_api->remove_rpf_group_member()` / `remove_rpf_group()` | `ip_multicast_manager.cpp:L688-694` |

### 2. P4OidMapper 内部テーブル (in-process 非 Redis)

| 操作 | SAI タイプ | キー | コード根拠 |
|------|-----------|------|-----------|
| REPLICATION SET 成功 | SAI_OBJECT_TYPE_IPMC_GROUP | multicast_group_id | `l3_multicast_manager.cpp:L2196` setOID |
| REPLICATION SET 成功 | SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER | replica.key | `l3_multicast_manager.cpp:L2262` setOID |
| REPLICATION DEL 成功 | SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER | replica.key | `l3_multicast_manager.cpp:L2552` eraseOID |
| REPLICATION DEL 成功 | SAI_OBJECT_TYPE_IPMC_GROUP | multicast_group_id | `l3_multicast_manager.cpp:L2247` eraseOID |
| FIXED SET 成功 | SAI_OBJECT_TYPE_IPMC_ENTRY | ip_multicast_entry_key | `ip_multicast_manager.cpp:L772` setDummyOID |
| FIXED SET 成功 | SAI_OBJECT_TYPE_IPMC_GROUP (refcount増) | multicast_group_id | `ip_multicast_manager.cpp:L776` increaseRefCount |
| FIXED DEL 成功 | SAI_OBJECT_TYPE_IPMC_GROUP (refcount減) | multicast_group_id | `ip_multicast_manager.cpp:L881` decreaseRefCount |
| FIXED DEL 成功 | SAI_OBJECT_TYPE_IPMC_ENTRY | ip_multicast_entry_key | `ip_multicast_manager.cpp:L883` eraseOID |

### 3. CRM カウンタ (FIXED_IPV4/IPV6_MULTICAST_TABLE のみ)

| 操作 | CRM リソースタイプ | コード根拠 |
|------|-----------------|-----------|
| FIXED SET 成功 | `CRM_IPMC_ENTRY` (+ 1) | `ip_multicast_manager.cpp:L774` `gCrmOrch->incCrmResUsedCounter()` |
| FIXED DEL 成功 | `CRM_IPMC_ENTRY` (- 1) | `ip_multicast_manager.cpp:L885` `gCrmOrch->decCrmResUsedCounter()` |

`REPLICATION_IP_MULTICAST_TABLE` の IPMC_GROUP / IPMC_GROUP_MEMBER に対応する CRM リソースタイプは
`l3_multicast_manager.cpp` 内に存在しない (コメントアウト済み: `L387` `// attr.id = SAI_IPMC_ENTRY_ATTR_COUNTER_ID;`)。

### 4. VRF 参照カウント (FIXED_IPV4/IPV6_MULTICAST_TABLE のみ)

| 操作 | VRF 操作 | コード根拠 |
|------|---------|-----------|
| FIXED SET 成功 (非空 vrf_id) | `VRFOrch::increaseVrfRefCount(vrf_id)` | `ip_multicast_manager.cpp:L775` |
| FIXED DEL 成功 (非空 vrf_id) | `VRFOrch::decreaseVrfRefCount(vrf_id)` | `ip_multicast_manager.cpp:L886` |

VRF 参照カウントは VRFOrch のインプロセスカウンタ。Redis には書き込まれない。

### 5. APP_P4RT_TABLE ステータス書き戻し

処理成功・失敗ともに `m_publisher->publish(APP_P4RT_TABLE_NAME, ...)` でコントローラ (`p4rt-app`) へ
ステータスコードを返す (`ip_multicast_manager.cpp:L132,L147,L159,L185,L230`)。
バッチ中断時は残エントリに `SWSS_RC_NOT_EXECUTED` が付与される (`L183-189`)。

### 6. STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB への直接書き込み — なし

grep 結果: `ip_multicast_manager.cpp` / `l3_multicast_manager.cpp` には `STATE_DB` `FLEX_COUNTER_DB`
`NotificationProducer` 等の直接書き込みは存在しない。
