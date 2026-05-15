# ALARM テーブル — ハードコード定数 (Task F Phase E)

ALARM テーブル (EVENT_DB) で参照される、コードに直接埋め込まれた定数を整理した中間メモ。`docs/reference/config-db/alarm-table.md` の `<!-- constants -->` ブロック生成元。

## 1. severity 列挙値 (eventd / OpenConfig alarms)

Alarm の severity は YANG (`openconfig-alarms`) の enum と eventd 側の文字列を一致させて運用される。値は固定リテラルでハードコードされている。

| 値 | 適用 | 出典 |
|----|------|------|
| `CRITICAL` | アラーム可 | `SONiC/doc/event-alarm-framework/event-alarm-framework.md:136` |
| `MAJOR`    | アラーム可 | 同上 :138 |
| `MINOR`    | アラーム可 | 同上 :140 |
| `WARNING`  | アラーム可 | 同上 :142 |
| `INFORMATIONAL` | **アラーム不可** (one-shot event のみ) | 同上 :144, :348 |

- `severity` フィールドの値は event profile (`default.json`) の文字列をそのまま eventd が ALARM テーブルへ書き込む。コード側に enum 定数定義はなく、文字列比較で扱われる。
- ALARM テーブルに `INFORMATIONAL` のエントリは作られない (HLD Section 3.1.4 / 3.1.5 で明示)。

## 2. ALARM / EVENT テーブル名定数

`sonic-swss-common/common/schema.h` で固定:

```c
// schema.h:551-554
#define EVENT_HISTORY_TABLE_NAME          "EVENT"
#define EVENT_CURRENT_ALARM_TABLE_NAME    "ALARM"
#define EVENT_STATS_TABLE_NAME            "EVENT_STATS"
#define EVENT_ALARM_STATS_TABLE_NAME      "ALARM_STATS"
```

## 3. 保持上限 (EVENT 側) — ALARM はスナップショットで上限なし

EVENT テーブルのみ retention あり。ALARM はリブートクリアの揮発スナップショットで上限なし (HLD 3.1.7)。ただし運用上 ALARM が雪崩を起こすと隣接の EVENT 側で上限ヒットしうるため、参考として記載。

| 定数 | 値 | 出典 |
|------|----|------|
| `no-of-records` (EVENT) | `40000` (range 1-40000) | HLD :482, :491, :496 |
| `no-of-days` (EVENT) | `30` (range 1-30) | HLD :482, :492, :497 |

ALARM 自身には records / days 上限が定義されていない (HLD 3.1.7 で明記)。

## 4. eventd 内部キャッシュ・ポーリング定数 (alarm pub/sub 経路に影響)

`sonic-buildimage/src/sonic-eventd/src/`:

| 定数 | 値 | ファイル:行 |
|------|----|------------|
| `EVT_SIZE_AVG` | `150` (bytes/event 想定) | `eventd.cpp:31` |
| `MAX_CACHE_SIZE` | `MB(100) / EVT_SIZE_AVG` (= 約 699,050) | `eventd.cpp:33` |
| `MB(N)` | `(N) * 1024 * 1024` | `eventd.cpp:30` |
| `CAPTURE_SERVICE_POLLING_DURATION` | `10` | `eventd.h:25` |
| `CAPTURE_SERVICE_POLLING_INCREMENT` | `10` | `eventd.h:26` |
| `CAPTURE_SERVICE_POLLING_MAX_DURATION` | `100` | `eventd.h:27` |
| `CAPTURE_SERVICE_POLLING_RETRIES` | `100` | `eventd.h:28` |

これらは ALARM テーブル「行」のスキーマ定数ではなく、eventd の内部 capture バッファ寸法。ALARM 経路の挙動を理解する補足として記載。

## 5. action 列挙 (ALARM テーブルでは固定 `RAISE`)

eventd が処理する `action` 値:

- `RAISE_ALARM` → ALARM 行追加 (`action=RAISE`)
- `CLEAR_ALARM` → ALARM 行削除
- `ACK_ALARM` → `acknowledged=true`
- `UNACK_ALARM` → `acknowledged=false`

これらは文字列リテラルでアプリ→eventd の event payload に乗る。コード上の `#define` ではなく、HLD Section 3.1.4 / 3.1.5 で規定されたプロトコル定数。

## 6. ALARM テーブル本体に影響する確定ハードコード定数 (constants ブロックに採用するもの)

`docs/reference/config-db/alarm-table.md` に追加する `<!-- constants -->` ブロックは、ALARM テーブルの**スキーマ・運用**に直接効く以下に絞る:

1. severity 列挙 5 値 (うち `INFORMATIONAL` は alarm 不可)
2. テーブル名固定文字列 `"ALARM"` (`schema.h:552`)
3. ALARM 行の retention: なし (リブートでクリア・上限なし)
4. EVENT 側 retention: 40000 records / 30 days (参考)

eventd 内部キャッシュ寸法は ops 観点で出現するが、ALARM スキーマ表面には現れないため `<!-- constants -->` ブロックには載せず本メモのみに残す。

## 出典

- `sonic-swss-common/common/schema.h` line 551-554
- `sonic-buildimage/src/sonic-eventd/src/eventd.h` line 25-28
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp` line 30-33
- `SONiC/doc/event-alarm-framework/event-alarm-framework.md` line 136-144, 346-348, 480-499
