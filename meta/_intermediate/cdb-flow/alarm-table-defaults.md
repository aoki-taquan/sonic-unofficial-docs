# ALARM テーブル フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: EVENT_DB `ALARM` (STATE_DB 系 — CONFIG_DB 外)

## 調査対象ファイル

- `SONiC/doc/event-alarm-framework/event-alarm-framework.md` (HLD Rev 0.3)
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp` (eventd proxy/cache 層)
- `sonic-buildimage/src/sonic-eventd/src/eventd.h`
- `sonic-mgmt-common/models/yang/common/openconfig-alarms.yang`

---

## テーブル概要

ALARM テーブルは EVENT_DB (Redis DB index 6) に存在し CONFIG_DB ではない。  
schema.h: `EVENT_CURRENT_ALARM_TABLE_NAME = "ALARM"` (sonic-swss-common/common/schema.h:552)

eventd の Alarm Consumer が以下のルールで管理:
- action=RAISE_ALARM → ALARM テーブルにエントリ追加
- action=CLEAR_ALARM → 対応エントリを削除
- action=ACK_ALARM → `acknowledged` = true、`acknowledge-time` 更新
- action=UNACK_ALARM → `acknowledged` = false、`acknowledge-time` 更新

---

## フィールド別 暗黙デフォルト

### キー構造

```
ALARM|<id>
```

`<id>` はシステムが割り当てる uint64 の sequential ID (フォーマット: `<32bit time_t><5桁連番>`)。

---

### `id` (uint64)

**コード由来デフォルト**: なし (システム自動採番)

HLD Section 3.1.2.2:
> Sequence-ID is of the format `<32 bit time_t><5 digit running sequence 00000 to 99999>`.

---

### `revision` (uint64)

**コード由来デフォルト**: `0`

HLD Section 3.1.2.3:
> If not given, the default revision '0' is assigned to the event/alarm.

event profile (default.json) に revision が未指定の場合に `0` が割り当てられる。

---

### `type-id` (string)

**コード由来デフォルト**: なし (必須フィールド)

event profile に登録された `name` 値がそのまま格納される。
例: `"TEMPERATURE_EXCEEDED"`, `"PSU_POWER_STATUS"` 等。

---

### `text` (string)

**コード由来デフォルト**: 静的メッセージ + 動的メッセージの連結

event profile の `message` フィールド (静的) にアプリケーションが渡す動的メッセージが付加される。
DB に `text` が存在しない場合は空文字列相当 (optional フィールド)。

---

### `time-created` (uint64 — timeticks64)

**コード由来デフォルト**: なし (システム自動設定)

HLD 例 (section 3.1.7):
```
"time-created": "1621460371062299951"
```
nanosecond 精度の UNIX timestamp (uint64)。イベント発生時刻をシステムが設定。

---

### `severity` (string — enum)

**コード由来デフォルト**: event profile の `severity` フィールド値

サポートされる値 (HLD Section 3.1.2.1):
- `CRITICAL` (maps to log-alert)
- `MAJOR` (maps to log-crit)
- `MINOR` (maps to log-error)
- `WARNING` (maps to log-warning)
- `INFORMATIONAL` (maps to log-notice) — アラームには非対応

event profile に `severity` が未指定の場合の挙動は HLD に記載なし。
開発者が `default.json` に明示することが必須とされている。

---

### `action` (string — enum)

**コード由来デフォルト**: ALARM テーブルに書き込まれるのは `RAISE` のみ

HLD Section 1.1 / 3.1.2:
> All events with an action field of RAISE get recorded in the ALARM table.

ALARM テーブルエントリの `action` フィールドは常に `"RAISE"` として格納される。
CLEAR_ALARM 受信時はエントリが **削除** されるため、テーブル内のエントリは常に action=RAISE 状態。

---

### `resource` (string)

**コード由来デフォルト**: なし (optional)

アプリケーションがイベント発行時に渡す `resource` パラメータ。
HLD 例: `"resource": "sensor/2"`, `"resource": "PSU 1"` 等。
未指定の場合はフィールド自体が存在しない (optional leaf)。

---

### `acknowledged` (boolean)

**コード由来デフォルト**: `false`

HLD Section 3.1.2 / redis 出力例:
```
"acknowledged": "false"
```

エントリ追加時 (RAISE_ALARM 処理) に `false` で初期化される。
ACK_ALARM 受信時に `true` に更新、UNACK_ALARM 受信時に `false` に戻る。

---

### `acknowledge-time` (uint64 — timeticks64) / `acknowledged` (重複フィールド名)

**コード由来デフォルト**: なし (ACK_ALARM 受信時のみ設定)

HLD Section 3.1.3:
> alarm consumer finds the raised record of the alarm in the ALARM table using the above lookup map and updates *acknowledged* flag to true. The *acknowledge-time* is updated with the timestamp of ack event.

RAISE 直後はフィールドが存在しない (未設定)。

---

## 要約表

| フィールド | 型 | コード由来デフォルト | fallback 源 |
|-----------|---|-------------------|------------|
| `id` | uint64 | システム自動採番 (`<time_t><5桁連番>`) | HLD Section 3.1.2.2 |
| `revision` | uint64 | `0` | event profile 未指定時 — HLD Section 3.1.2.3 |
| `type-id` | string | なし (event profile の `name`) | 必須フィールド |
| `text` | string | 静的メッセージ (event profile `message`) | optional; 動的メッセージと連結 |
| `time-created` | uint64 | システム自動設定 (nanosecond UNIX TS) | RAISE イベント発生時刻 |
| `severity` | string enum | event profile の `severity` 値 | 必須; CRITICAL/MAJOR/MINOR/WARNING |
| `action` | string enum | `"RAISE"` (固定) | ALARM テーブルは RAISE エントリのみ保持 |
| `resource` | string | なし (optional) | アプリケーションが渡すリソース識別子 |
| `acknowledged` | boolean | `"false"` | RAISE 時に false 初期化 — HLD Section 3.1.2 |
| `acknowledge-time` | uint64 | なし (ACK 時のみ設定) | ACK_ALARM/UNACK_ALARM 処理時 |

---

## 証拠リンク

- `SONiC/doc/event-alarm-framework/event-alarm-framework.md` Rev 0.3 — Section 3.1.7 (ALARM Table schema, redis 出力例)
- `sonic-swss-common/common/schema.h:552` — `EVENT_CURRENT_ALARM_TABLE_NAME = "ALARM"`
- `sonic-mgmt-common/models/yang/common/openconfig-alarms.yang` — alarm-state grouping
- HLD Section 3.1.2.3 — revision default = 0
- HLD Section 3.1.2.2 — sequence-id format
- HLD Section 3.1.3 — acknowledged, acknowledge-time 更新タイミング
