# CONFIG_DB 例外条件分析: COPP_GROUP

## Consumer

- `coppmgr` (`cfgmgr/coppmgr.cpp`): COPP_GROUP + COPP_TRAP を結合し APPL_DB `COPP_TABLE` に書き込む。
- `orchagent` の `CoppOrch`: APPL_DB から受信し SAI hostif trap group / policer を生成・更新。

## 例外条件

### 1. デフォルト copp.json との merge: NULL cfg → スキップ
- ソース: `coppmgr.cpp` `mergeConfig()` L222-224
- ユーザー側の CONFIG_DB エントリのフィールドが `NULL` の場合、そのキー全体を init (デフォルト) 設定からも除外する (`null_cfg=true` → `m_cfg` に追加しない)。

### 2. coppmgr: 重複エントリ (isDupEntry) → APPL_DB 更新スキップ
- ソース: `coppmgr.cpp` `isDupEntry()` L263-284
- APPL_DB の既存値と全フィールドが一致する場合、`m_appCoppTable.set()` を呼ばない。重複設定の場合に SAI を不必要に叩かないため。

### 3. policer の meter / mode / color は変更不可 → エラーログのみで続行
- ソース: `copporch.cpp` L1331-1347
- 既存ポリサーへの `SAI_POLICER_ATTR_METER_TYPE` / `_MODE` / `_COLOR_SOURCE` 変更を試みると `SWSS_LOG_ERROR("Trying to modify policer attribute: (meter/mode/color) ...")` を出力し当該属性の変更を**スキップ**して次属性へ。他の属性の更新は続行。

### 4. 未知フィールド → false 返却 (task_failed)
- ソース: `copporch.cpp` L1290-1292
- `parseTrapGroupAttribute()` で認識できないフィールドが来た場合 `SWSS_LOG_ERROR("Unknown copp field specified:%s")` して `return false` → 処理失敗。

### 5. out_of_range / 汎用例外 → エラーログ + APPL_DB から削除
- ソース: `copporch.cpp` L902-907
- `processCoppRule()` が `out_of_range` または `exception` をスローした場合 `SWSS_LOG_ERROR` してエントリを queue から削除 (再試行なし)。

### 6. task_failed → syslog + exit
- ソース: `copporch.cpp` L922
- `task_failed` が返った場合 `SWSS_LOG_ERROR("Processing copp task item failed, exiting.")` でプロセスを終了。
