# SUPPRESS_ASIC_SDK_HEALTH_EVENT — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-19
ソース: `sonic-swss/orchagent/switchorch.cpp` (`SwitchOrch::initAsicSdkHealthEventNotification`, `SwitchOrch::onSwitchAsicSdkHealthEvent`, `SwitchOrch::set_switch_capability`)

---

## 概要

`SUPPRESS_ASIC_SDK_HEALTH_EVENT` の SET/DEL 処理後に `SwitchOrch` が書き込む副次 DB は以下の通り。

| DB | テーブル / キー | トリガ |
|----|----------------|--------|
| STATE_DB | `SWITCH_CAPABILITY\|switch` (フィールド: `ASIC_SDK_HEALTH_EVENT`, `REG_FATAL/WARNING/NOTICE_ASIC_SDK_HEALTH_CATEGORY`) | 起動時 1 回。SAI capability 確認結果を記録 |
| STATE_DB | `ASIC_SDK_HEALTH_EVENT_TABLE\|<timestamp>` | SAI コールバック経由。SUPPRESS 設定が SAI フィルタを決定し間接制御 |
| Events framework | `"asic-sdk-health-event"` イベント | SAI コールバック受信ごとに `event_publish` |

---

## 1. STATE_DB / `SWITCH_CAPABILITY|switch`

`SwitchOrch::initAsicSdkHealthEventNotification()` が `set_switch_capability(fvVector)` で書き込む。起動時 1 回のみ。

### 書き込まれるフィールド

| フィールド名 | 値 | 条件 | evidence |
|------------|------|------|----------|
| `ASIC_SDK_HEALTH_EVENT` | `"true"` | SAI が `SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY` をサポートし、コールバック登録成功 | `switchorch.cpp:231` |
| `ASIC_SDK_HEALTH_EVENT` | `"false"` | SAI 非対応またはコールバック登録失敗 | `switchorch.cpp:246` |
| `REG_FATAL_ASIC_SDK_HEALTH_CATEGORY` | `"true"` / `"false"` | fatal severity の SAI capability 確認結果 | `switchorch.cpp:258-276` |
| `REG_WARNING_ASIC_SDK_HEALTH_CATEGORY` | `"true"` / `"false"` | warning severity の SAI capability 確認結果 | `switchorch.cpp:258-276` |
| `REG_NOTICE_ASIC_SDK_HEALTH_CATEGORY` | `"true"` / `"false"` | notice severity の SAI capability 確認結果 | `switchorch.cpp:258-276` |

定数:
- `STATE_SWITCH_CAPABILITY_TABLE_NAME = "SWITCH_CAPABILITY"` (`schema.h:417`)
- `SWITCH_CAPABILITY_TABLE_ASIC_SDK_HEALTH_EVENT_CAPABLE = "ASIC_SDK_HEALTH_EVENT"` (`switchorch.h:30`)
- `SWITCH_CAPABILITY_TABLE_REG_FATAL_ASIC_SDK_HEALTH_CATEGORY = "REG_FATAL_ASIC_SDK_HEALTH_CATEGORY"` (`switchorch.h:31`)
- `SWITCH_CAPABILITY_TABLE_REG_WARNING_ASIC_SDK_HEALTH_CATEGORY = "REG_WARNING_ASIC_SDK_HEALTH_CATEGORY"` (`switchorch.h:32`)
- `SWITCH_CAPABILITY_TABLE_REG_NOTICE_ASIC_SDK_HEALTH_CATEGORY = "REG_NOTICE_ASIC_SDK_HEALTH_CATEGORY"` (`switchorch.h:33`)

!!! note "SET/DEL 操作は SWITCH_CAPABILITY を変化させない"
    SUPPRESS_ASIC_SDK_HEALTH_EVENT の SET/DEL は SAI `set_switch_attribute` のみ呼び出す。
    `SWITCH_CAPABILITY` への書き込みは起動時 `initAsicSdkHealthEventNotification()` 内のみ。

---

## 2. STATE_DB / `ASIC_SDK_HEALTH_EVENT_TABLE|<timestamp>` (間接副次効果)

SAI から health event コールバック `onSwitchAsicSdkHealthEvent()` が届いた時に
`m_asicSdkHealthEventTable->set(time_ss.str(), values)` で書き込まれる。

`SUPPRESS_ASIC_SDK_HEALTH_EVENT` の設定が SAI に登録するカテゴリフィルタを決定するため、
**SET 操作の結果として STATE_DB に書き込まれるイベントの数・種別が変わる**（直接書込ではなく間接制御）。

### 書き込みフィールド

| フィールド | 内容 | evidence |
|-----------|------|----------|
| `severity` | `"fatal"` / `"warning"` / `"notice"` | `switchorch.cpp:1655` |
| `category` | `"software"` / `"firmware"` / `"cpu_hw"` / `"asic_hw"` | `switchorch.cpp:1656` |
| `description` | SAI から届いたイベント説明文字列（不印字文字除去済み） | `switchorch.cpp:1657` |

定数: `STATE_ASIC_SDK_HEALTH_EVENT_TABLE_NAME = "ASIC_SDK_HEALTH_EVENT_TABLE"` (`schema.h:507`)

また、fatal イベント受信ごとに内部カウンタ `m_fatalEventCount` がインクリメントされる（`switchorch.cpp:1667`）。
このカウンタは `show event-driven-telemetry` 系の出力に使われる。

---

## 3. Events framework / `"asic-sdk-health-event"`

`event_publish(g_events_handle, "asic-sdk-health-event", &params)` (`switchorch.cpp:1663`) で
SAI コールバックごとにイベントフレームワークへパブリッシュされる。

パラメータ:

| キー | 内容 |
|------|------|
| `sai_timestamp` | イベント発生タイムスタンプ (`YYYY-MM-DD HH:MM:SS` 形式) |
| `severity` | severity 文字列 |
| `category` | category 文字列 |
| `description` | イベント説明 |
| `asic_name` | `gMyAsicName` が空でない場合のみ付与 |

SUPPRESS 設定によって SAI が届けるイベントが絞り込まれるため、このパブリッシュも間接的に制御される。

---

## 副次書込なし（スコープ外）

- **APPL_DB**: SUPPRESS_ASIC_SDK_HEALTH_EVENT は CONFIG_DB → SAI の直接経路。APPL_DB への書き込みは発生しない。
- **COUNTERS_DB / FLEX_COUNTER_DB**: 関連なし。
- **ASIC_DB**: SAI 経由で syncd が書き込む（orchagent の直接書込なし）。

---

## 書込フロー図

```
SUPPRESS_ASIC_SDK_HEALTH_EVENT SET/DEL (CONFIG_DB)
  └─ SwitchOrch::doCfgSuppressAsicSdkHealthEventTableTask()
       └─ registerAsicSdkHealthEventCategories()
            └─ SAI set_switch_attribute(REG_{FATAL,WARNING,NOTICE}_CATEGORY)
                 └─ ASIC_DB (syncd 経由)
                      └─ [間接効果] SAI フィルタ変化 → onSwitchAsicSdkHealthEvent() の呼ばれ方が変わる
                           ├─ m_asicSdkHealthEventTable->set()  → STATE_DB/ASIC_SDK_HEALTH_EVENT_TABLE
                           ├─ event_publish()                   → Events framework/"asic-sdk-health-event"
                           └─ m_fatalEventCount++ (fatal のみ)

SwitchOrch 起動時 (initAsicSdkHealthEventNotification)
  └─ set_switch_capability(fvVector)
       └─ m_switchTable.set("switch", ...)  → STATE_DB/SWITCH_CAPABILITY|switch
```
