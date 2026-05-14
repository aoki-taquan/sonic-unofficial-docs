# extended-monitor (Event-Alarm Framework) — Phase A: field defaults

## 調査対象

Event-Alarm Framework の EVENT_DB テーブル群 (EVENT, ALARM, EVENT_STATS, ALARM_STATS) と
eventd manifest ファイル (`/etc/eventd.json`) の全フィールドについてコード由来デフォルトを特定する。

## ソースと Evidence

### eventd マニフェスト (primary source for table limits)

`sonic-buildimage/src/sonic-eventd` と HLD `SONiC/doc/event-alarm-framework/event-alarm-framework.md:487-498`

```json
{
    "config" : {
        "no-of-records": 40000,
        "no-of-days": 30
    }
}
```

| フィールド | デフォルト値 | 型/range |
|---|---|---|
| `no-of-records` | `40000` | int, 1..40000 |
| `no-of-days` | `30` | int, 1..30 |

### EVENT テーブル schema (EVENT_DB)

HLD `event-alarm-framework.md:504-538` より EVENT テーブルの各フィールドスキーマ:

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `id` | uint64 | — (自動採番) | システムが付与する連番 ID |
| `type-id` | string | — | イベント名 |
| `text` | string | — | 動的メッセージ |
| `time-created` | uint64 (epoch ns) | — | 発生タイムスタンプ |
| `action` | enum(RAISE/CLEAR/ACKNOWLEDGE/UNACKNOWLEDGE) | `""` (one-shot イベントは空) | アラームの場合のアクション |
| `resource` | string | `""` | イベントを発生させたリソース名 |
| `severity` | string (CRITICAL/MAJOR/MINOR/WARNING/INFORMATIONAL) | evprofile/default.json 記載値 | 重要度 |
| `revision` | uint64 | `0` | プロファイル内の revision 番号 |
| `acknowledged` | boolean | `false` | アラームのみ: ack 状態 |

### ALARM テーブル schema (EVENT_DB)

HLD `event-alarm-framework.md:569-605` より:

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `id` | uint64 | — (自動採番) | 一意 ID |
| `revision` | uint64 | `0` | プロファイル revision |
| `type-id` | string | — | アラーム名 |
| `text` | string | — | 動的メッセージ |
| `time-created` | uint64 (epoch ns) | — | 発生タイムスタンプ |
| `acknowledged` | boolean | `false` | ack 状態 |
| `acknowledge-time` | uint64 (epoch ns) | — | ack/unack 時刻 |
| `resource` | string | — | 発生リソース |
| `severity` | string | evprofile 由来 | 重要度 |

### EVENT_STATS テーブル schema (EVENT_DB)

HLD `event-alarm-framework.md:542-564` より:

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `events` | uint64 | `0` | 累計イベント数 |
| `raised` | uint64 | `0` | 累計アラーム RAISE 数 |
| `cleared` | uint64 | `0` | 累計アラーム CLEAR 数 |
| `acked` | uint64 | `0` | 累計アラーム ACK 数 |

### ALARM_STATS テーブル schema (EVENT_DB)

HLD `event-alarm-framework.md:607-634` より:

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `alarms` | uint64 | `0` | active アラーム総数 |
| `critical` | uint64 | `0` | CRITICAL severity の active 数 |
| `major` | uint64 | `0` | MAJOR severity の active 数 |
| `minor` | uint64 | `0` | MINOR severity の active 数 |
| `warning` | uint64 | `0` | WARNING severity の active 数 |
| `informational` | uint64 | `0` | INFORMATIONAL severity の active 数 |

### Event Profile デフォルト (evprofile/default.json)

HLD `event-alarm-framework.md:269-293` より。各イベント定義のデフォルトフィールド:

| フィールド | デフォルト値 | 説明 |
|---|---|---|
| `revision` | `0` | 数値。eventd が省略時に自動補完 |
| `enable` | `true` | 省略時 true 扱い |
| `severity` | 開発者指定 | CRITICAL/MAJOR/MINOR/WARNING/INFORMATIONAL |

HLD `event-alarm-framework.md:351-354` より:
> If not given, the default revision '0' is assigned to the event/alarm.

### YANG モデル (sonic-events-common.yang)

`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-events-common.yang`

デフォルト severity 拡張:
- `ALARM_SEVERITY_MINOR` — minor 扱いのアラームマーカー
- `ALARM_SEVERITY_MAJOR` — major 扱いのアラームマーカー
- `EVENT_SEVERITY_2` / `_3` / `_4` — イベント重要度レベル

### Heartbeat デフォルト (eventd.cpp)

`sonic-buildimage/src/sonic-eventd/src/eventd.cpp:43`

```cpp
#define HEARTBEAT_INTERVAL_SECS 2  /* Default: 2 seconds */
```

| 定数 | 値 | 説明 |
|---|---|---|
| `HEARTBEAT_INTERVAL_SECS` | `2` | eventd ハートビート間隔 (秒) |
| `MAX_CACHE_SIZE` | 約 698,947 件 (100MB / 150B) | キャッシュ最大イベント数 |
| `STATS_HEARTBEAT_MIN` | `300` ms | ハートビート最小単位 |

## デフォルト由来まとめ

| フィールド / 設定 | デフォルト値 | 由来 |
|---|---|---|
| `no-of-records` (eventd.json) | `40000` | HLD 仕様 / eventd manifest |
| `no-of-days` (eventd.json) | `30` | HLD 仕様 / eventd manifest |
| EVENT `acknowledged` | `false` | コード内 RAISE 時の初期値 |
| EVENT/ALARM `revision` | `0` | eventd: "default revision '0' is assigned" |
| EVENT/ALARM `action` | `""` (one-shot) / `RAISE` (alarm) | eventd EventConsumer ロジック |
| ALARM_STATS カウンタ群 | `0` | eventd 起動時ゼロ初期化 |
| EVENT_STATS カウンタ群 | `0` | eventd 起動時ゼロ初期化 |
| heartbeat 間隔 | `2` 秒 | `HEARTBEAT_INTERVAL_SECS=2` (eventd.cpp:43) |

## 永続化ルール (デフォルト動作)

| 再起動種別 | EVENT | ALARM | EVENT_STATS | ALARM_STATS |
|---|---|---|---|---|
| warm reboot | 保持 | クリア | 保持 | クリア |
| fast reboot | 保持 | クリア | 保持 | クリア |
| cold reboot | 保持 | クリア | 保持 | クリア |
| power reset | 定期 persist から復元 | クリア | 定期 persist から復元 | クリア |

> **Evidence**: `SONiC/doc/event-alarm-framework/event-alarm-framework.md` (Rev 0.3);
> `sonic-buildimage/src/sonic-eventd/src/eventd.cpp:43`;
> `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-events-common.yang`
