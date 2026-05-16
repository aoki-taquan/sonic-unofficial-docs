# TC_TO_QUEUE_MAP — Phase H プラットフォーム差 証跡

## 調査ソース

- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-buildimage/files/build_templates/qos_config.j2`

---

## 1. ASIC キャパビリティ

`TC_TO_QUEUE_MAP` ハンドラ (`TcToQueueMapHandler::addQosItem()`) は SAI の `sai_qos_map_api->create_qos_map()` を呼ぶのみで、ASIC ケーパビリティクエリ（`querySwitchCapability`）を行わない。

- DSCP_TO_TC_MAP では `gSwitchOrch->querySwitchCapability(SAI_OBJECT_TYPE_SWITCH, SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP)` が実施されるが、TC_TO_QUEUE_MAP にはそれに相当するクエリがない（`qosorch.cpp` L1955 付近）。
- キャパビリティ差は SAI ベンダー実装に委ねられ、`create_qos_map()` 失敗時にエラーログ + `task_failed` が返る。

## 2. ベンダー別 queue 数差

### queue 数はプラットフォーム固有テンプレートで決定する

`qos_config.j2` の `TC_TO_QUEUE_MAP` 生成は以下の優先順で行われる:

```
1. generate_tc_to_queue_map() 定義あり かつ tunnel_qos_remap_enable=true
   → プラットフォーム固有関数（AZURE_UPLINK 等の追加マップを含む）
2. generate_tc_to_queue_map_per_sku() 定義あり
   → SKU 別マップ（HWSKU フォルダ内のテンプレートが上書き）
3. フォールバック（デフォルト）
   → TC 0–7 → queue 0–7 の恒等写像（マップ名 "AZURE"）
```

デフォルト（フォールバック）の定義:

```json
"TC_TO_QUEUE_MAP": {
    "AZURE": {
        "0": "0",
        "1": "1",
        "2": "2",
        "3": "3",
        "4": "4",
        "5": "5",
        "6": "6",
        "7": "7"
    }
}
```

### uplink ポート向け AZURE_UPLINK マップ

`different_tc_to_queue_map=true` かつ `tunnel_qos_remap_enable=true` かつ uplink ポートの条件が揃う場合、PORT_QOS_MAP の `tc_to_queue_map` に `"AZURE_UPLINK"` が適用される（`qos_config.j2` L451-453）。`AZURE_UPLINK` マップの内容はプラットフォーム固有関数 (`generate_tc_to_queue_map()`) が決定するため queue 数はプラットフォームによって異なる。

## 3. VOQ chassis 差

### VOQ chassis とは

`DEVICE_METADATA['localhost']['switch_type'] == 'voq'` のとき `voq_chassis=true` となる（`qos_config.j2` L28-29）。

### TC_TO_QUEUE_MAP 本体への直接影響

VOQ chassis モードでも `TC_TO_QUEUE_MAP` テーブル自体の生成ロジックは標準と同じ（`voq_chassis` フラグによる条件分岐は `QUEUE` テーブル生成にのみ適用される）。

### QUEUE テーブルの VOQ chassis 差

VOQ chassis では QUEUE エントリがシステムポート (`SYSTEM_PORT`) ベースで生成される:

```
system_port|3  → wred_profile: AZURE_LOSSLESS (lossless queue)
system_port|4  → wred_profile: AZURE_LOSSLESS (lossless queue)
system_port|0,1,2,5,6 → scheduler.0 (best-effort queues、active ポートのみ)
```

通常モードではポートごとに 8 キュー (0–7) が定義されるのに対し、VOQ chassis では SYSTEM_PORT 単位で一部のキューのみが明示的に設定される（`qos_config.j2` L507-552）。

### orchagent での VOQ 分岐

`qosorch.cpp` の `applyWredProfileToQueue()` では:

```cpp
if (gMySwitchType == "voq") {
    // gPortsOrch->getPortVoQIds(port) で VOQ 固有のキュー ID 取得
} else {
    // port.m_queue_ids で通常キュー ID 取得
}
```

VOQ モードでは `getPortVoQIds()` を通じて Virtual Output Queue の OID を取得する（L1772 付近）。TC_TO_QUEUE_MAP の SAI map 作成自体は共通パスだが、ポート適用時のキュー ID 解決が分岐する。

## 4. まとめ

| 差分観点 | 通常モード | VOQ chassis |
|---------|-----------|------------|
| TC_TO_QUEUE_MAP テーブル生成 | qos_config.j2 共通パス | 同上（変化なし） |
| キュー数 | HWSKU 依存（デフォルト 0–7） | SYSTEM_PORT ベース、一部のみ明示 |
| ポート適用時のキュー ID 解決 | `port.m_queue_ids` | `getPortVoQIds()` |
| ASIC ケーパビリティクエリ | なし（SAI に委ねる） | 同上 |
| uplink 向け別マップ | `AZURE_UPLINK`（条件付き） | 未適用（PORT_UPLINK は通常ポート） |
