# suppress-asic-sdk-health-event — ordering (Phase B)

調査日: 2026-05-16  
対象ソース: `sonic-swss/orchagent/switchorch.cpp`, `orchdaemon.cpp`, `switchorch.h`

## 1. SwitchOrch 起動時の初期化順序

`orchdaemon.cpp:212` で `SwitchOrch` を生成する際、`SUPPRESS_ASIC_SDK_HEALTH_EVENT` を含む複数の `TableConnector` がまとめて渡される。

```
orchdaemon: gSwitchOrch = new SwitchOrch(m_applDb, switch_tables, stateDbSwitchTable)
  └─ SwitchOrch コンストラクタ (switchorch.cpp:163)
       └─ initAsicSdkHealthEventNotification()   ← SUPPRESS テーブルを最初に読む
```

`initAsicSdkHealthEventNotification()` の内部フロー:

1. `querySwitchCapability(SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY)` — プラットフォームが health event 通知をサポートするか確認 (switchorch.cpp:215)
2. サポートあり → `sai_switch_api->set_switch_attribute(gSwitchId, SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY, on_switch_asic_sdk_health_event)` でコールバック登録 (switchorch.cpp:222-226)
3. severity ごとに `querySwitchCapability(REG_FATAL/WARNING/NOTICE_CATEGORY)` を確認  
4. サポートされる severity について `cfgSuppressASHETable.hget(severity, "categories", suppressedCategories)` で CONFIG_DB を **起動時スナップショット** として読み取り (switchorch.cpp:261)
5. `registerAsicSdkHealthEventCategories(saiAttr, severity, suppressedCategories, isInitializing=true)` で SAI に登録 (switchorch.cpp:262)

→ **CONFIG_DB 書き込みが orchagent 起動前に存在していれば、コンストラクタ内で即座に SAI へ反映される。** 起動後の変更は `doCfgSuppressAsicSdkHealthEventTableTask` が Consumer イベント経由で都度適用する。

## 2. 起動時と実行時の違い

| タイミング | `isInitializing` | 全カテゴリ抑制時の SAI 登録 |
|-----------|-----------------|---------------------------|
| `initAsicSdkHealthEventNotification()` (起動時) | `true` | `interested_categories_set.empty()` → **SAI 登録をスキップ** (switchorch.cpp:1390-1394) — 通知ハンドラ未設定になる |
| `doCfgSuppressAsicSdkHealthEventTableTask()` (実行中 SET) | `false` | 全カテゴリ抑制でも SAI 登録は試行される |

## 3. 実行中の SET/DEL 処理順序

```
Consumer (SubscriberStateTable: CONFIG_DB.SUPPRESS_ASIC_SDK_HEALTH_EVENT)
  └─ doTask(Consumer &) → doCfgSuppressAsicSdkHealthEventTableTask()
       1. key バリデーション (空文字 → erase)            switchorch.cpp:1427
       2. severity → SAI attr 変換 (map.at(key))        switchorch.cpp:1435
       3. m_supportedAsicSdkHealthEventAttributes 確認    switchorch.cpp:1455
       4. categories フィールド解析 (SET のみ)            switchorch.cpp:1462-1465
       5. registerAsicSdkHealthEventCategories 呼出し     switchorch.cpp:1465 / 1477 / 1482
```

SET_COMMAND:
- `categories` フィールドあり → suppressed list を使って `registerAsicSdkHealthEventCategories(saiSeverity, key, fieldValue, false)`
- `categories` フィールドなし → 引数なし (全カテゴリ登録 = 抑制なし) で呼出し

DEL_COMMAND:
- `registerAsicSdkHealthEventCategories(saiSeverity, key)` を無条件呼出し → suppressed_category_list="" → 全カテゴリ購読 (抑制解除)

## 4. warm reboot との関係

`switchorch.cpp` 内の warm reboot ロジック (`RESTARTCHECK` 通知, switchorch.cpp:1543-1564) は `SUPPRESS_ASIC_SDK_HEALTH_EVENT` テーブルとは無関係。warm reboot 後に orchagent が再起動すると `initAsicSdkHealthEventNotification()` が再度走り、CONFIG_DB スナップショットから最新の suppressed categories を SAI に再登録する。

## 5. 依存関係まとめ

| 前提条件 | 不成立時の影響 |
|---------|--------------|
| SAI が `SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY` をサポートする | サポートなし → `CAPABILITY` テーブルに `false` を記録し、以降の全 severity 登録をスキップ |
| 各 severity が SAI でサポートされる (`m_supportedAsicSdkHealthEventAttributes`) | 非サポート severity への SET は silent skip (syslog NOTICE) |
| orchagent が起動してから CONFIG_DB に書き込む場合 | コンストラクタ読取り時に値なし → 全カテゴリ購読 (= 抑制なし) が起動時デフォルトになる |
| 起動前に CONFIG_DB に書き込む場合 | `cfgSuppressASHETable.hget()` で読取り → 起動時スナップショットとして反映 |
