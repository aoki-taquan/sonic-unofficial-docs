# srv6-my-sids — Phase H: プラットフォーム制約

evidence sources:
- sonic-swss orchagent/srv6orch.cpp (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- sonic-buildimage src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)

## SAI ケイパビリティ照会

`Srv6Orch::queryMySidCountersCapability()` (`srv6orch.cpp:144-155`):

```cpp
sai_attr_capability_t capability;
sai_status_t status = sai_query_attribute_capability(
    gSwitchId,
    SAI_OBJECT_TYPE_MY_SID_ENTRY,
    SAI_MY_SID_ENTRY_ATTR_COUNTER_ID,
    &capability
);
if (status != SAI_STATUS_SUCCESS) {
    SWSS_LOG_WARN("Could not query SRv6 MySID entry attribute SAI_MY_SID_ENTRY_ATTR_COUNTER_ID %d", status);
    return false;
}
return capability.set_implemented && capability.create_implemented;
```

ランタイムで SAI に問い合わせ、`set_implemented && create_implemented` の両方が true の場合のみカウンタ機能を有効化する。

## カウンタ非対応プラットフォームの挙動

`initializeCounters()` (`srv6orch.cpp:120-142`):
- `queryMySidCountersCapability()` が false を返した場合 → `SWSS_LOG_INFO("SRv6 counters are not supported on this platform")` を出力して return
- カウンタ関連オブジェクト（`m_asic_db`, `m_counter_db`, `m_mysid_counters_table`, `m_counter_update_timer`）は初期化されない
- `getMySidCountersSupported()` は false を返し、以降の SID 作成時にカウンタ属性 `SAI_MY_SID_ENTRY_ATTR_COUNTER_ID` は SAI に送らない (`srv6orch.cpp:1593`)

カウンタ無効化時のカウンタ変更要求への応答 (`srv6orch.cpp:257`):
```
SWSS_LOG_WARN("Ignoring SRv6 counters state change as they are not supported on this platform");
```

## gTraditionalFlexCounter モード

`gTraditionalFlexCounter` フラグ (`srv6orch.cpp:39`、extern) が true の場合:
- `initializeCounters()` で ASIC_DB `VIDTORID` テーブルを作成 (`srv6orch.cpp:133-136`)
- `doTask(SelectableTimer&)` (`srv6orch.cpp:294`) で `m_vid_to_rid_table->hget("", oid, value)` が true になるまでカウンタ ID リストの登録を保留する

非 Traditional モード（`gTraditionalFlexCounter == false`）では:
- `VIDTORID` の確認をスキップして即座に `m_counter_manager.setCounterIdList()` を呼び出す

## ECMP 非対応制限

`createUpdateMysidEntry()` (`srv6orch.cpp:1515-1519`):
```cpp
vector<string> adjv = tokenize(adj, ADJ_DELIMITER);
if (adjv.size() > 1) {
    SWSS_LOG_ERROR("Failed to create my_sid entry %s adj %s: ECMP adjacency not yet supported", ...);
    return false;
}
```

`end.x` / `ua` 等の nexthop 要求 action で adj にカンマ区切り複数 next-hop を指定すると即時エラー（自動回復なし）。単一 nexthop のみサポート。

## IPinIP Tunnel のプラットフォーム依存条件

`mySidTunnelRequired()` (`srv6orch.cpp:1417-1429`):
- IPinIP Tunnel の作成は `uN` または `uDT46` action かつ `decap_dscp_mode` が設定されている場合に限定
- それ以外の action（`end`, `end.x` 等）は常に false → Tunnel 未作成
- SAI 実装が `SAI_TUNNEL_TYPE_IPINIP` に対応していないプラットフォームでは `create_tunnel` が `SAI_STATUS_NOT_SUPPORTED` を返す可能性があるが、SONiC コードはランタイムケイパビリティ照会を行わない（`srv6orch.cpp:538`）

## action 受理可能範囲のプラットフォーム依存

`end_behavior_map` (`srv6orch.cpp:41-62`) に 19 種の action が登録されているが、**SAI が実装している action はプラットフォームによって異なる**。SAI API は `create_my_sid_entry` 時に `SAI_STATUS_NOT_SUPPORTED` 等を返すことがある。SONiC は action ごとの事前ケイパビリティ照会を行わず、SAI エラーをログ出力して `return false` するのみ。

bgpcfgd パスでは `supported_SRv6_behaviors = {'uN', 'uDT46'}` に絞り込まれるため、CONFIG_DB 経由では SAI 非対応 action の投入リスクは低い。

## まとめ表

| 機能 | プラットフォーム制約 | SONiC 側の検出方法 |
|------|-------------------|--------------------|
| MY_SID カウンタ | `SAI_MY_SID_ENTRY_ATTR_COUNTER_ID` の create/set 実装要 | `sai_query_attribute_capability()` で実行時判定 |
| ECMP nexthop | 未サポート（ソフトウェア制限） | adj のカンマ区切り数で判定（複数なら即エラー） |
| IPinIP Tunnel | SAI の `SAI_TUNNEL_TYPE_IPINIP` 対応が必要 | 実行時 SAI エラーのみ（事前照会なし） |
| FlexCounter 方式 | Traditional / Non-Traditional どちらも対応 | `gTraditionalFlexCounter` フラグで切替 |
| action サポート範囲 | プラットフォームの SAI 実装依存 | 事前照会なし（SAI エラーで判明） |
