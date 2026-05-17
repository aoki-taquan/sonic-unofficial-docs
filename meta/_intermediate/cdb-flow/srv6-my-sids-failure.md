# SRV6_MY_SIDS — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-17 (q67-f-srv6-sid3-next)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース:
- `sonic-net/sonic-swss/orchagent/srv6orch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | 自動回復 | evidence |
|---|---|---|---|---|---|
| ロケータ名が `SRV6_MY_LOCATORS` に未存在 | `sids_set_handler()` L62-69 | `return False`（処理中断）、依存購読を登録 | `log_warn` | あり: ロケータ登録時に `on_deps_change` コールバックで自動再試行 | `managers_srv6.py:62-69` |
| SID プレフィックスがロケータのサブネット外 | `sids_set_handler()` L74-76 | `return False`（恒久的失敗） | `log_err` | **なし**（自動再試行なし） | `managers_srv6.py:74-76` |
| `action` フィールド未指定 | `sids_set_handler()` L78-80 | `return False`（恒久的失敗） | `log_err` | **なし** | `managers_srv6.py:78-80` |
| `action` が `uN`/`uDT46` 以外の未サポート値 | `sids_set_handler()` L82-84 | `return False`（恒久的失敗） | `log_err` | **なし** | `managers_srv6.py:82-84` |
| `action` が `end_behavior_map` に存在しない（Srv6Orch 側） | `sidEntryEndpointBehavior()` L1369-1372 | `return false`（エントリ未作成） | `SWSS_LOG_ERROR("Invalid endpoint behavior function")` | **なし** | `srv6orch.cpp:1369-1376` |
| `decap_vrf` が `"default"` 以外かつ VRF が未存在（`isVRFexists()` false） | `createUpdateMysidEntry()` L1498-1501 | `return false`（エントリ未作成、自動再試行なし） | `SWSS_LOG_ERROR("VRF %s doesn't exist in DB")` | **なし** | `srv6orch.cpp:1498-1502` |
| `decap_vrf` が存在するが SAI OID が `SAI_NULL_OBJECT_ID` | `createUpdateMysidEntry()` L1492-1495 | `return false` | `SWSS_LOG_ERROR("VRF object not created for DT VRF %s")` | **なし** | `srv6orch.cpp:1492-1496` |
| nexthop（`end.x` / `ua` 等）が未解決（`hasNextHop()` false または OID が NULL） | `createUpdateMysidEntry()` L1524-1542 | エントリを `m_pendingSRv6MySIDEntries` に保留して `return false` | `SWSS_LOG_INFO` (pending) | あり: Neighbor ADD イベントで自動再インストール | `srv6orch.cpp:1524-1543` |
| ECMP adjacency（カンマ区切りの複数 adj）を指定 | `createUpdateMysidEntry()` L1516-1519 | `return false`（ECMP 未サポート） | `SWSS_LOG_ERROR("ECMP adjacency not yet supported")` | **なし** | `srv6orch.cpp:1516-1519` |
| `decap_dscp_mode` に `"uniform"`/`"pipe"` 以外の値を指定 | `addMySidCfgCacheEntry()` L388-392 | キャッシュへの登録がスキップ（`return`） | `SWSS_LOG_ERROR("Invalid MySID %s DSCP mode: %s")` | **なし** | `srv6orch.cpp:388-392` |
| IPinIP トンネル作成失敗（`uN`/`uDT46` で `decap_dscp_mode` 指定時） | `createUpdateMysidEntry()` L1554-1558 | `return false`（MY_SID エントリ未作成） | `SWSS_LOG_ERROR("Failed to create overlay router interface for MySID IPinIP tunnel")` など | **なし** | `srv6orch.cpp:1554-1565` |
| SAI `create_my_sid_entry` 失敗（SAI_STATUS_SUCCESS 以外） | `createUpdateMysidEntry()` L1607-1610 | `return false` | `SWSS_LOG_ERROR("Failed to create my_sid entry %s, rv %d")` | **なし** | `srv6orch.cpp:1607-1611` |
| SRv6 カウンタ有効時に `addMySidCounter` 失敗 | `createUpdateMysidEntry()` L1595-1598 | `return false`（MY_SID エントリ未作成） | `SWSS_LOG_ERROR("Failed to create SAI counter for SRv6 MySID entry")` | **なし** | `srv6orch.cpp:1595-1599, 190-191` |

### UPDATE 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | 自動回復 |
|---|---|---|---|---|
| VRF 属性 set_my_sid_entry_attribute 失敗 | `createUpdateMysidEntry()` L1619-1624 | `return false`（VRF 未更新） | `SWSS_LOG_ERROR("Failed to update VRF to my_sid_entry %s, rv %d")` | **なし** |
| NextHop 属性 set_my_sid_entry_attribute 失敗 | `createUpdateMysidEntry()` L1628-1633 | `return false`（NH 未更新） | `SWSS_LOG_ERROR("Failed to update nexthop to my_sid_entry %s, rv %d")` | **なし** |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | 自動回復 |
|---|---|---|---|---|
| 存在しない SID の削除要求 | `deleteMysidEntry()` L1660-1663 | `return false` | `SWSS_LOG_ERROR("My_sid_entry doesn't exist for %s")` | **なし** |
| SAI `remove_my_sid_entry` 失敗 | `deleteMysidEntry()` L1670-1673 | `return false`（エントリ残存） | `SWSS_LOG_ERROR("Failed to delete my_sid entry rv %d")` | **なし** |
| IPinIP トンネル Term エントリ削除失敗 | `deleteMysidEntry()` L1698-1701 | `return false`（残存 MY_SID テーブルから未消去） | `SWSS_LOG_ERROR("Failed to remove tunnel termination entry for MySID entry")` | **なし** |
| bgpcfgd 側で未存在 SID の削除 | `sids_del_handler()` L122-124 | `return`（silent skip） | `log_warn` | — |

### 未回復の孤立状態（運用上の注意）

- **ロケータより先に SID を削除しなかった場合**: `locators_del_handler()` はロケータ削除時に対応 SID エントリを自動削除しない。SID エントリが bgpcfgd 内のキャッシュに残留し、FRR 設定が不整合となる（`managers_srv6.py:106-115`）。
- **VRF 削除前に SID を削除しなかった場合**: VRFOrch refcount が正のまま VRF 削除がブロックされる（`srv6orch.cpp:1639, 1683`）。
- **Neighbor 消失時の自動 ASIC 削除**: nexthop が消えると `updateNeighbor()` が対応 MY_SID エントリを自動的に ASIC から削除し、`m_pendingSRv6MySIDEntries` に保留する（`srv6orch.cpp:1272-1342`）。Neighbor 再出現時に自動復元されるため通常はユーザー介入不要。

<!-- /failure -->
