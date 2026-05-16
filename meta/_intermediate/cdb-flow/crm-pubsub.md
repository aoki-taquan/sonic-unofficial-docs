# CRM 通信メカニズム (Phase G 中間ファイル)

対象ページ: `docs/reference/config-db/crm.md`
ソース: `sonic-swss/orchagent/crmorch.cpp`, `orchdaemon.cpp`
生成日: 2026-05-16

---

## 1. CONFIG_DB 購読経路

- **購読方式**: `Orch(db, tableName)` 基底クラス経由の `SubscriberStateTable` (swss Consumer フレームワーク)
- **テーブル**: `CRM`（key: `Config`）
- **インスタンス化**: `orchdaemon.cpp:194` — `gCrmOrch = new CrmOrch(m_configDb, CFG_CRM_TABLE_NAME)`
- **イベントハンドラ**: `CrmOrch::doTask(Consumer &)` (crmorch.cpp:440)
  - SET → `handleSetCommand()` で各フィールド処理
  - DEL → `SWSS_LOG_ERROR("Unsupported operation type")` のみ (crmorch.cpp:463)

## 2. SelectableTimer ポーリング経路

| 項目 | 値 | evidence |
|------|----|---------|
| タイマー型 | `SelectableTimer` | crmorch.cpp:402 |
| 初期間隔 | 300 秒 (`CRM_POLLING_INTERVAL_DEFAULT = 5 * 60`) | crmorch.cpp:12, 402 |
| Executor 名 | `"CRM_COUNTERS_POLL"` | crmorch.cpp:417 |
| ハンドラ | `CrmOrch::doTask(SelectableTimer &)` | crmorch.cpp:751 |
| 間隔変更 | `polling_interval` SET → `m_timer->setInterval()` + `m_timer->reset()` | crmorch.cpp:490-492 |

### doTask(SelectableTimer &) 内呼び出し順

1. `getResAvailableCounters()` — SAI から各リソース available カウンタ取得
2. `updateCrmCountersTable()` — `COUNTERS_DB["CRM_STATS"]` に書き込み
3. `checkCrmThresholds()` — 閾値比較・syslog WARN/INFO 発火

## 3. SAI 呼出経路

### 系統 A: `sai_object_type_get_availability()`

- 対象: objType != SAI_OBJECT_TYPE_NULL のリソース（route / neighbor / nexthop_group / FDB / IPMC / MPLS / SRv6 / DASH 系）
- シグネチャ: `sai_object_type_get_availability(gSwitchId, objType, attrCount, &attr, &availCount)`
- evidence: crmorch.cpp:800

### 系統 B: `sai_switch_api->get_switch_attribute()`

- 対象: objType == NULL のリソース（ACL table/group/entry/counter / nexthop_group_member / TWAMP 等）または系統 A が失敗した場合のフォールバック
- シグネチャ: `sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr)`
- evidence: crmorch.cpp:808

### NOT_SUPPORTED 処理

`SAI_STATUS_NOT_SUPPORTED` / `SAI_STATUS_NOT_IMPLEMENTED` 系の戻り値で `res.resStatus = CRM_RES_NOT_SUPPORTED` をセットし、以降の polling サイクルから除外。(crmorch.cpp:817)

## 4. orchdaemon 登録順序

```
orchdaemon.cpp:194  gCrmOrch = new CrmOrch(m_configDb, CFG_CRM_TABLE_NAME)
orchdaemon.cpp:500  m_orchList = { gSwitchOrch, gCrmOrch, gPortsOrch, ... }
```

`gSwitchOrch` の直後（2 番目）に登録。CRM は起動シーケンスの早期に CONFIG_DB 購読を確立する。

## 5. データフロー全体図

```
CONFIG_DB["CRM|Config"]
  ↓ (SubscriberStateTable / Consumer)
CrmOrch::doTask(Consumer &)
  └─ handleSetCommand()
       ├─ polling_interval → m_timer->setInterval() + reset()
       ├─ threshold_type   → m_resourcesMap 更新 + exceededLogCounter リセット
       ├─ low_threshold    → m_resourcesMap 更新
       └─ high_threshold   → m_resourcesMap 更新

SelectableTimer [300s]
  ↓ (満了ごと)
CrmOrch::doTask(SelectableTimer &)
  ├─ getResAvailableCounters()
  │    ├─ sai_object_type_get_availability()  [route/neighbor/FDB/DASH 等]
  │    └─ sai_switch_api->get_switch_attribute()  [ACL/TWAMP 等]
  ├─ updateCrmCountersTable()
  │    └─ COUNTERS_DB["CRM_STATS"]
  └─ checkCrmThresholds()
       └─ syslog WARN (THRESHOLD_EXCEEDED) / INFO (THRESHOLD_CLEAR)
```
