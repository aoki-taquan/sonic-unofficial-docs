# pwm (WATERMARK_TABLE) — Phase H platform 調査メモ

## 調査対象

- `sonic-swss/orchagent/watermarkorch.cpp` (全 348 行)
- `sonic-swss/orchagent/portsorch.cpp` (SAI_QUEUE_TYPE_ALL / watermark flex counter 設定部分)
- `sonic-swss/orchagent/orchdaemon.cpp` (WatermarkOrch 初期化部分)

## 結論: watermarkorch.cpp にプラットフォーム固有コードは存在しない

`watermarkorch.cpp` 全体を精読した結果、以下の条件分岐は**一切存在しない**:

- `gMySwitchType` / `voq` 参照: なし
- `platform` / `sub_platform` 文字列比較: なし
- `MLNX_PLATFORM_SUBSTRING` / `BRCM_PLATFORM_SUBSTRING` 等の定数参照: なし
- `isMlnxPlatform()` / `isBrcmDnxPlatform()` 等の helper 呼び出し: なし
- SAI capability クエリ (`sai_query_attribute_capability_info`): なし

## ASIC 依存として現れるプラットフォーム差

### SAI_QUEUE_TYPE_ALL キューの存在有無

`init_queue_ids()` (`watermarkorch.cpp:298`) は COUNTERS_DB `COUNTERS_QUEUE_TYPE_MAP` を読んで
`SAI_QUEUE_TYPE_UNICAST` / `SAI_QUEUE_TYPE_MULTICAST` / `SAI_QUEUE_TYPE_ALL` に分類する。

`SAI_QUEUE_TYPE_ALL` の存在は ASIC ベンダーに依存:
- **一部の ASIC** (例: Broadcom Jericho 系 DNX): `SAI_QUEUE_TYPE_ALL` のみをサポートし UC/MC の分離なし
- **多くの ASIC** (Broadcom XGS / Mellanox): `SAI_QUEUE_TYPE_UNICAST` + `SAI_QUEUE_TYPE_MULTICAST` を返す

`CLEAR_QUEUE_SHARED_ALL_REQUEST` ("Q_SHARED_ALL") の `clearSingleWm()` は `m_all_queue_ids` が空の場合
ゼロ回ループで終了する。ユーザーが `watermarkstat -c` 等でこのクリアを要求しても、ASIC が
`SAI_QUEUE_TYPE_ALL` を持たない場合はサイレントに何もしない (`watermarkorch.cpp:274-277`)。

### FLEX_COUNTER READ_AND_CLEAR モード — SAI ASIC 依存

watermark FlexCounter グループは `STATS_MODE_READ_AND_CLEAR` (`portsorch.cpp:867-873`) で設定される。
SAI の `SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES` に対する `READ_AND_CLEAR` アトミック操作を
サポートしない ASIC では `SAI_STATUS_NOT_SUPPORTED` が返る。この場合 flexcounter は統計を
収集できず COUNTERS_DB の watermark 値は更新されない。`WatermarkOrch` はこのエラーを検知しない。

### Lua プラグイン — ASIC 非依存

`watermark_queue.lua` と `watermark_pg.lua` は ASIC ベンダーにかかわらず同一スクリプトが登録される
(`portsorch.cpp:799-874`)。Nvidia (MLNX) 固有の Lua プラグイン (`nvda_port_trim_drop.lua`) は
watermark とは無関係のポート trim 統計用であり、WatermarkOrch には影響しない。

### VoQ (Voice over Quantum) / multi-asic の影響

`watermarkorch.cpp` に `gMySwitchType` 参照なし。VoQ モードでも WatermarkOrch は同一コードを実行する。
ただし VoQ モードでは `SAI_QUEUE_TYPE_UNICAST_VOQ` キューが存在するが、
`init_queue_ids()` の分岐に `SAI_QUEUE_TYPE_UNICAST_VOQ` が含まれておらず、VoQ ユニキャストキューは
watermark 収集対象外になる (`watermarkorch.cpp:298-326`, `portsorch.cpp:226` に型定義あり)。

## evidence ファイルパス

- `sonic-swss/orchagent/watermarkorch.cpp`: <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/watermarkorch.cpp>
- `sonic-swss/orchagent/portsorch.cpp` L799-874: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/portsorch.cpp>
