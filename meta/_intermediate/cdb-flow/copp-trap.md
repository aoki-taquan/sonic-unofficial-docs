# CONFIG_DB 例外条件分析: COPP_TRAP

## Consumer

- `coppmgr` (`cfgmgr/coppmgr.cpp`): COPP_TRAP と COPP_GROUP を結合して APPL_DB `COPP_TABLE` に書き込む。
- `orchagent` の `CoppOrch`: SAI hostif trap を生成。

## 例外条件

### 1. NAT trap_id (SNAT_MISS / DNAT_MISS) → NAT 非対応時 ignore
- ソース: `copporch.cpp` L400-406
- `gIsNatSupported == false` のスイッチで `SAI_HOSTIF_TRAP_TYPE_SNAT_MISS` / `DNAT_MISS` が来ると `SWSS_LOG_NOTICE("Ignoring the trap_id: %s, as NAT is not supported")` → その trap_id をスキップ。

### 2. SAI 非対応 trap_id → ignore
- ソース: `copporch.cpp` L408-413
- `isTrapIdSupported(trap_id)` が false の場合 `SWSS_LOG_NOTICE("Ignoring the trap_id: %s, since not supported by vendor SAI")` → スキップ。ベンダー SAI が実装していない trap は適用されない。

### 3. 不明な trap_id enum 値 → NOTICE ログ
- ソース: `copporch.cpp` L283
- SAI の enum capability クエリ結果に未知の値が含まれる場合 `SWSS_LOG_NOTICE("Unknown trap id enum value: %d")` を出力。サポート済みリストに追加されない。

### 4. trap group が未存在 → APPL_DB 書き込みなし
- ソース: `copporch.cpp` L62-81 (`checkTrapGroupPending`)
- `trap_group` に指定したグループが pending (COPP_GROUP 未到着) の場合、`coppmgr` は APPL_DB への書き込みを保留する。COPP_GROUP が到着次第再処理。

### 5. trap_ids のうち一部が disable → 当該 trap を除外して書き込み
- ソース: `coppmgr.cpp` `isTrapIdDisabled()` L173-191
- feature が無効 (`is_always_enabled != "true"` かつ feature が off) の場合、その trap_id を `COPP_TABLE` の `trap_ids` から除外。trap_group が空になると APPL_DB エントリを削除。

### 6. task_failed → プロセス終了
- ソース: `copporch.cpp` L922
- COPP_TRAP 処理で `task_failed` が返った場合 `SWSS_LOG_ERROR("Processing copp task item failed, exiting.")` でプロセスを終了。
