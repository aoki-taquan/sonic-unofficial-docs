# pfcwd-state — Platform / SAI Capability 差異調査 (Phase H)

## 調査対象ファイル

- `sonic-swss/orchagent/pfcwdorch.cpp`
- `sonic-swss/orchagent/pfcactionhandler.cpp`
- `sonic-swss/orchagent/pfc_detect_*.lua` (全プラットフォーム)
- `sonic-swss/orchagent/pfc_restore*.lua`

## Lua プラグイン分岐

`PfcWdSwOrch` コンストラクタ (`pfcwdorch.cpp:693-700`) でプラットフォーム別 Lua スクリプトを選択:

```cpp
string detectPluginName = "pfc_detect_" + this->m_platform + ".lua";
if (this->m_platform == CISCO_8000_PLATFORM_SUBSTRING) {
    restorePluginName = "pfc_restore_" + this->m_platform + ".lua";
} else {
    restorePluginName = "pfc_restore.lua";
}
```

実在する detect スクリプト:
- `pfc_detect_broadcom.lua`
- `pfc_detect_cisco-8000.lua`
- `pfc_detect_mellanox.lua`
- `pfc_detect_barefoot.lua`
- `pfc_detect_marvell-prestera.lua`
- `pfc_detect_marvell-teralynx.lua`
- `pfc_detect_clounix.lua`
- `pfc_detect_nephos.lua`
- `pfc_detect_vs.lua` (仮想スイッチ)

restore スクリプト:
- `pfc_restore.lua` (broadcom / mellanox / barefoot / marvell / nephos / vs 等)
- `pfc_restore_cisco-8000.lua` (Cisco 8000 専用)

Cisco 8000 のみ restore スクリプトが分離されている。

## Cisco 8000 固有制約

1. `action=forward` は未サポート (`pfcwdorch.cpp:233-235`): `task_invalid_entry` を返す。`drop` または `alert` のみ有効。
2. `PfcWdLossyHandler` コンストラクタ/デストラクタでの PFC マスク変更をスキップ (`pfcactionhandler.cpp:548`): storm 検知時にハードウェアの PFC ビットを変更しない。
3. 専用 restore スクリプト `pfc_restore_cisco-8000.lua` を使用。

## Broadcom 固有動作 (PFC DLR INIT)

`gSwitchOrch->checkPfcDlrInitEnable()` が `true` の場合:

1. 最初の `pfcwd start` でスイッチレベル属性 `SAI_SWITCH_ATTR_PFC_DLR_PACKET_ACTION` を設定 (`pfcwdorch.cpp:244-252`)。この設定はスイッチ全体に影響する。
2. 2 ポート目以降: 新しい `action` が最初と一致しない場合 `task_invalid_entry` (`pfcwdorch.cpp:257-262`)。全ポートで統一した action が必要。
3. PFC マスク変更スキップ: `PfcWdLossyHandler` での `getPortPfc` / `setPortPfc` 呼び出しをスキップ (`pfcactionhandler.cpp:548`)。
4. `PfcWdSaiDlrInitHandler` / `PfcWdDlrHandler` で `SAI_QUEUE_ATTR_PFC_DLR_INIT` を使用 (`pfcactionhandler.cpp:230-300`)。

Broadcom で DLR が無効な場合は通常の `PfcWdLossyHandler` (PFC マスク変更) が使用される。

### `shared_egress_acl_table` 分岐 (Broadcom ACL)

`PfcWdAclHandler` において `shared_egress_acl_table = (platform == BRCM_PLATFORM_SUBSTRING && ...)` が true の場合、egress ACL テーブルを共有する別パスが実行される (`pfcactionhandler.cpp:351-524`)。

## プラットフォーム環境変数

`m_platform` は `getenv("platform")` から取得 (`pfcwdorch.cpp:46`)。未定義の場合 `""` となり `SWSS_LOG_ERROR` を出力して初期化失敗。

## 仮想スイッチ (VS)

`pfc_detect_vs.lua` が存在し、VS プラットフォームで PFC WD の動作検証が可能。ただし COUNTERS_DB の PFC カウンタはハードウェアに基づかないため、storm 検知は Lua の模擬実装による。

## COUNTERS_DB フィールドへの影響まとめ

| 条件 | COUNTERS_DB への影響 |
|------|---------------------|
| Cisco 8000 | `action=forward` を持つエントリは書き込まれない (`task_invalid_entry`) |
| Broadcom + DLR | スイッチレベル action が統一されない場合は書き込まれない |
| PFC マスク未設定 (全プラットフォーム) | `registerInWdDb()` が空集合で即 return → 書き込みなし |
| VS | 正常に書き込まれるが storm 検知は模擬 |
