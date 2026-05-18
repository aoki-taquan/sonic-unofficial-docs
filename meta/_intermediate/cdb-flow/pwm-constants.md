# WATERMARK_TABLE — Phase E ハードコード定数スキャンノート

対象ページ: `docs/reference/config-db/pwm.md`
対象テーブル: `CONFIG_DB WATERMARK_TABLE`
Producer/Consumer: `WatermarkOrch` (`sonic-swss/orchagent/watermarkorch.cpp`)
スキャン範囲: `watermarkorch.cpp` 全行精読 (2026-05-18)

---

## 検出した定数

### 1. `DEFAULT_TELEMETRY_INTERVAL` = 120

- `watermarkorch.cpp:9`: `#define DEFAULT_TELEMETRY_INTERVAL 120`
- `watermarkorch.cpp:41`: `auto intervT = timespec { .tv_sec = DEFAULT_TELEMETRY_INTERVAL, .tv_nsec = 0 };`
- コンストラクタで `SelectableTimer` の初期周期として使用。`WATERMARK_TABLE|TELEMETRY_INTERVAL` エントリが CONFIG_DB に存在しない場合に唯一の周期値となる。
- 外部変更: CONFIG_DB `WATERMARK_TABLE|TELEMETRY_INTERVAL|interval` フィールドで実行時上書き可能。

### 2. クリア要求文字列 (WATERMARK_CLEAR_REQUEST data)

- `watermarkorch.cpp:11-17` に 7 つの `#define` マクロ定数として定義。
- `doTask(NotificationConsumer)` (`watermarkorch.cpp:184-231`) が文字列比較でルーティング。
- `watermarkcfg` CLI が同一文字列を送信するため、コードと CLI の間に暗黙の契約が存在する。

| マクロ名 | 値 | 行 |
|---------|-----|-----|
| `CLEAR_PG_HEADROOM_REQUEST` | `"PG_HEADROOM"` | 11 |
| `CLEAR_PG_SHARED_REQUEST` | `"PG_SHARED"` | 12 |
| `CLEAR_QUEUE_SHARED_UNI_REQUEST` | `"Q_SHARED_UNI"` | 13 |
| `CLEAR_QUEUE_SHARED_MULTI_REQUEST` | `"Q_SHARED_MULTI"` | 14 |
| `CLEAR_QUEUE_SHARED_ALL_REQUEST` | `"Q_SHARED_ALL"` | 15 |
| `CLEAR_BUFFER_POOL_REQUEST` | `"BUFFER_POOL"` | 16 |
| `CLEAR_HEADROOM_POOL_REQUEST` | `"HEADROOM_POOL"` | 17 |

### 3. FLEX_COUNTER グループ名 ("QUEUE_WATERMARK" / "PG_WATERMARK")

- `watermarkorch.cpp:120`: `if (key == "QUEUE_WATERMARK" || key == "PG_WATERMARK")`
- `handleFcConfigUpdate()` 内の固定文字列比較。これ以外のキーは処理されず `m_wmStatus` は変化しない。
- `CFG_FLEX_COUNTER_TABLE_NAME` (`schema.h`) で定義されるテーブル名は別途ハードコード。

---

## ページ反映方針

- `<!-- /failure -->` の直後に `<!-- constants -->` ... `<!-- /constants -->` ブロックを挿入。
- `DEFAULT_TELEMETRY_INTERVAL` とクリア要求文字列定数を主軸にテーブル形式で整理。
- FLEX_COUNTER グループ名はサブセクションとして追記。
