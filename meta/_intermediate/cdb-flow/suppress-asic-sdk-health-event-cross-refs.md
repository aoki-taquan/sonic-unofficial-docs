# SUPPRESS_ASIC_SDK_HEALTH_EVENT — 暗黙参照テーブル調査 (Phase C)

## 調査対象

`sonic-swss/orchagent/switchorch.cpp` を中心に、`SUPPRESS_ASIC_SDK_HEALTH_EVENT` の処理が
参照・依存する他テーブル / リソースを網羅的に調査した。

## 検出された暗黙参照

### 1. STATE_DB `SWITCH_CAPABILITY|switch` (参照: 読み取り側)

`initAsicSdkHealthEventNotification()` 内で `querySwitchCapability()` を呼ぶことで
SAI のプラットフォームケイパビリティを確認し、結果を STATE_DB `SWITCH_CAPABILITY|switch` に書き込む。

- `ASIC_SDK_HEALTH_EVENT` フィールド: health event 通知サポート可否 (`true` / `false`)
- `REG_FATAL_ASIC_SDK_HEALTH_CATEGORY` フィールド: fatal severity の登録可否
- `REG_WARNING_ASIC_SDK_HEALTH_CATEGORY` フィールド: warning severity の登録可否
- `REG_NOTICE_ASIC_SDK_HEALTH_CATEGORY` フィールド: notice severity の登録可否

これらフィールドは SwitchOrch が書き手であり、`show event-driven-telemetry` 等の show コマンドが
`STATE_DB SWITCH_CAPABILITY|switch` を読んで表示する（sonic-utilities/show/main.py:2803, 2849）。

### 2. STATE_DB `ASIC_SDK_HEALTH_EVENT_TABLE` (出力先)

`onSwitchAsicSdkHealthEvent()` コールバック (`switchorch.cpp:1578`) が SAI から受け取った
ASIC/SDK health event を `STATE_DB ASIC_SDK_HEALTH_EVENT_TABLE` に書き込む。
`SUPPRESS_ASIC_SDK_HEALTH_EVENT` の設定内容が SAI フィルタを決定し、
SAI から届く health event 数 = STATE_DB への書き込みイベント数 を制御する。

### 3. SAI Switch capability (`SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY`)

`querySwitchCapability(SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY)` の結果で
SUPPRESS テーブルの初期登録が通るかどうかが決まる。SAI 非対応時は全 severity の登録をスキップ。

### 4. CONFIG_DB `SUPPRESS_ASIC_SDK_HEALTH_EVENT` 自参照 (起動時直接読み)

`initAsicSdkHealthEventNotification()` は Consumer 経由ではなく `Table cfgSuppressASHETable(&cfgDb, ...)` で
CONFIG_DB を直接読む (`switchorch.cpp:240-274`)。これが唯一の「起動時スナップショット」経路であり、
Consumer イベント駆動の通常 SET/DEL とは異なるコードパスを通る。

## 参照関係まとめ

| 参照先テーブル / リソース | 方向 | 条件 | evidence |
|--------------------------|------|------|----------|
| `STATE_DB SWITCH_CAPABILITY\|switch` (ASIC_SDK_HEALTH_EVENT フィールド) | 書き (SwitchOrch → STATE_DB) | orchagent 起動時 1 回 | `switchorch.cpp:231, 246` |
| `STATE_DB SWITCH_CAPABILITY\|switch` (REG_*_ASIC_SDK_HEALTH_CATEGORY フィールド) | 書き | 各 severity の capability 確認結果 | `switchorch.cpp:265-269` |
| `STATE_DB ASIC_SDK_HEALTH_EVENT_TABLE` | 書き (イベント受信時) | SAI health event コールバック `onSwitchAsicSdkHealthEvent` | `switchorch.cpp:1661` |
| SAI `SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY` capability | 読み (SAI クエリ) | 起動時 | `switchorch.cpp:220` |
| SAI `SAI_SWITCH_ATTR_REG_{FATAL,WARNING,NOTICE}_SWITCH_ASIC_SDK_HEALTH_CATEGORY` | 書き (SAI set_switch_attribute) | SET/DEL ごと | `switchorch.cpp:1366-1408` |
| CONFIG_DB `SUPPRESS_ASIC_SDK_HEALTH_EVENT` (直接 `hget`) | 読み (起動時スナップショット) | `initAsicSdkHealthEventNotification()` 内 | `switchorch.cpp:240-274` |

## 特記事項

- SUPPRESS テーブルの処理は APPL_DB 中継なし。CONFIG_DB → SAI の直接経路。
- `SWITCH_CAPABILITY|switch` の capability フィールドは起動時 1 回のみ書き込まれ、実行中に変わらない。
- `show event-driven-telemetry` / `show asic-sdk-health-event` は `SWITCH_CAPABILITY|switch.ASIC_SDK_HEALTH_EVENT` を
  読んでプラットフォームサポート有無を判断している（sonic-utilities/show/main.py:2803, 2849）。
