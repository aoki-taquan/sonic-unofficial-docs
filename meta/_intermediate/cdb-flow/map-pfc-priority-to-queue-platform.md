# MAP_PFC_PRIORITY_TO_QUEUE — Phase H: プラットフォーム差分

<!-- evidence: sonic-swss/orchagent/qosorch.cpp / sonic-buildimage/files/build_templates/qos_config.j2 / sonic-buildimage/device/**/ -->

## 1. ASIC capability チェック

`MAP_PFC_PRIORITY_TO_QUEUE` に対して `querySwitchCapability` 呼び出しは行われない。`SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_QUEUE` のサポートは ASIC 非依存（全プラットフォームで SAI API は同一）。capability 分岐なし。

対照的に `DSCP_TO_TC_MAP` は `gSwitchOrch->querySwitchCapability(SAI_OBJECT_TYPE_SWITCH, SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP)` で SWITCH レベル適用可否を確認する (`qosorch.cpp:1956`)。PFC 系マップにはこの SWITCH レベル適用パスが存在しない。

## 2. PFC priority/queue 数のプラットフォーム差

YANG 制約 `pattern "[0-7]?"` により pfc_priority / qindex ともに 0..7 (8 値) に制限される。ただし実際に使用されるエントリ数はプラットフォーム依存。

| 項目 | 値 | 条件 |
|------|----|------|
| YANG 最大 priority/queue 数 | 8 (0..7) | ハードコード制約 |
| 標準 AZURE fallback エントリ数 | 8 (0..7 identity map) | `qos_config.j2:209-220` — `generate_pfc_to_queue_map` 未定義プラットフォーム |
| Marvell (dbmvtx9180) | 8 エントリ (identity map, map名 `"AZURE"`) | `device/marvell/.../qos.json.j2:21-32` |
| DellEMC Z9332f | 8 エントリ (identity map, map名 `"DEFAULT"`) | `device/dell/x86_64-dellemc_z9332f_d1508-r0/.../qos.json.j2.pfc.reference` |
| DellEMC S52xx/S53xx | 8 エントリ (identity map, map名 `"AZURE"`) | `device/dell/x86_64-dellemc_s5232f_c3538-r0/.../qos.json.j2` |

全プラットフォームで確認した限り、pfc_priority → qindex は 0→0 .. 7→7 の identity map のみ。非 identity マッピング（例: priority 3 → queue 5 等）はコード上サポートされるが、公式デバイス設定には存在しない。

## 3. pfc_to_pg_map_supported_asics による PG マップ差

`qos_config.j2:163` に `pfc_to_pg_map_supported_asics = ['mellanox', 'barefoot']` が定義されている。これは **`PFC_PRIORITY_TO_PRIORITY_GROUP_MAP`（ingress 側）** のプラットフォーム制限であり、`MAP_PFC_PRIORITY_TO_QUEUE`（egress 側）への制限ではない。

- **Mellanox / barefoot (Tofino) ASICs**: PFC priority → PG マップが ASIC レベルで有効。PFC→Queue マップも全 8 エントリが有意に機能する
- **その他 ASIC**: PFC priority → PG マップは設定されないが、PFC→Queue マップ自体は引き続き設定可能

## 4. VOQ chassis 差

VOQ chassis (`gMySwitchType == "voq"`) での `MAP_PFC_PRIORITY_TO_QUEUE` 処理差分:

### MAP_PFC_PRIORITY_TO_QUEUE テーブル自体

`PfcToQueueHandler::processWorkItem()` には VOQ 分岐なし。マップオブジェクト (`SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_QUEUE`) の作成・削除は VOQ/非 VOQ で同一コードパス (`qosorch.cpp:993-1042`)。

### QUEUE テーブルとの連携

VOQ chassis では `QUEUE` テーブルの key 形式が異なる:
- 非 VOQ: `QUEUE|<port>|<index_range>` (トークン 2 個)
- VOQ: `QUEUE|<hostname>|<asic>|<port>|<index_range>` (トークン 4 個、`qosorch.cpp:1772-1786`)

VOQ chassis で `qos_config.j2` が生成する QUEUE エントリはシステムポートを対象とし、ロスレスキュー 3 / 4 に `wred_profile: AZURE_LOSSLESS` を設定する (`qos_config.j2:507-560`)。MAP_PFC_PRIORITY_TO_QUEUE の参照元となる `PORT_QOS_MAP` の適用範囲がシステムポートに拡張される。

### WRED / Scheduler での VOQ 分岐

`applyWredProfileToQueue()` は VOQ 時に `getPortVoQIds()` でキュー ID を取得する (`qosorch.cpp:1715-1723`)。PFC→Queue マップ自体は変わらず identity map だが、適用先キューが VOQ キューになる。

VOQ chassis でリモートポート (`SAI_SYSTEM_PORT_TYPE_REMOTE`) への scheduler 適用はスキップ（`qosorch.cpp:1639-1641`）。

## 5. map名のプラットフォーム差

| プラットフォーム | map名 | ソース |
|--------------|-------|-------|
| デフォルト (fallback) | `"AZURE"` | `qos_config.j2:211` |
| Marvell dbmvtx9180 | `"AZURE"` | `device/marvell/.../qos.json.j2` |
| DellEMC Z9332f (DEFAULT map) | `"DEFAULT"` | `device/dell/.../qos.json.j2.pfc.reference` |
| DellEMC S52xx/Z94xx | `"AZURE"` | `device/dell/.../qos.json.j2` |
| Supermicro sse_t7132s | `"AZURE"` | `device/supermicro/.../qos.json.j2` |
| Wistron sw_to3200k | `"AZURE"` | `device/wistron/.../qos.json.j2` |

DellEMC Z9332f の `.pfc.reference` ファイルのみ `"DEFAULT"` map名を使用。本番 qos.json.j2 では `"AZURE"` を使用。

## 6. 結論

- ASIC capability 分岐なし: `MAP_PFC_PRIORITY_TO_QUEUE` は全 ASIC で同一 SAI API 呼び出し
- priority / queue 数: YANG が 0..7 に固定。全プラットフォームで identity map が採用されている
- pfc_to_pg_map 制限 (mellanox/barefoot) は ingress 側 PG マップの話であり、本テーブル（egress 側 queue マップ）には影響しない
- VOQ chassis: マップ作成コードは共通、QUEUE key 形式とキュー ID 取得方法が VOQ で分岐
