# extended-monitor — Phase A: event/alarm 拡張監視設定のコード由来デフォルト

調査日: 2026-05-15
対象: eventd が読む `eventd.json` (EVENT テーブル保持上限) および `/etc/evprofile/default.json` (イベントプロファイル)

## 調査対象ソース

- `SONiC/doc/event-alarm-framework/event-alarm-framework.md` — HLD section 3.1.5 (Event Profile), 3.1.7 (Event Table / Alarm Table)
- `sonic-buildimage/src/sonic-eventd/src/eventd.h` — 定数定義
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp` — `run_eventd_service()` 実装

---

## 1. eventd.json — EVENT テーブル保持上限

HLD section 3.1.7 に記述。`/etc/eventd.json` として配置。

```json
{
    "config": {
        "no-of-records": 40000,
        "no-of-days": 30
    }
}
```

### フィールド別コード由来デフォルト

| フィールド | HLD デフォルト | 説明 | 範囲 |
|-----------|-------------|------|------|
| `no-of-records` | `40000` | EVENT テーブルが保持できる最大レコード数 | 1–40000 |
| `no-of-days` | `30` | イベントが EVENT テーブルに留まれる最大日数 | 1–30 |

いずれかの上限に達すると古いレコードから削除（wrap-around）。
どちらが先に達してもローテーションが発動する。

**実装状況**: HLD で定義されているが、利用可能な `sonic-eventd/src/eventd.cpp` ソースコード (840行) には `no-of-records`/`no-of-days` の読み込み実装が見当たらない。HLD は実装予定/部分実装の段階である可能性あり。実コードでは EVENT テーブルのサイズ上限を直接強制するロジックは `eventd.cpp` に未確認。

---

## 2. /etc/evprofile/default.json — イベントプロファイル

HLD section 3.1.5 に記述。eventd が起動時に読み込む。

```json
{
    "__README__": "...",
    "events": [
        {
            "name": "SYSTEM_STATUS",
            "revision": 0,
            "severity": "INFORMATIONAL",
            "enable": "true",
            "message": "System Status Information"
        },
        {
            "name": "TEMPERATURE_EXCEEDED",
            "revision": 0,
            "severity": "CRITICAL",
            "enable": "true",
            "message": "Temperature threshold is 75 degrees."
        }
    ]
}
```

### フィールド別コード由来デフォルト

| フィールド | デフォルト | 説明 |
|-----------|---------|------|
| `name` | 必須 (デフォルトなし) | イベント識別子 (event-id)。YANG タグと一致 |
| `revision` | `0` | イベント定義のリビジョン。変更時にインクリメント |
| `severity` | 開発者設定 (デフォルトなし) | `CRITICAL` / `MAJOR` / `MINOR` / `WARNING` / `INFORMATIONAL` |
| `enable` | `"true"` | イベント有効/無効フラグ。`"false"` でイベントを無視 |
| `message` | 開発者設定 (デフォルトなし) | 静的メッセージ (動的メッセージと結合して Event Table に書き込まれる) |

**デフォルト**: プロファイルファイルが存在しない場合、`event consumer` は `static_event_map` を空として扱い、受信イベントを全て未定義扱いで処理する。

---

## 3. EVENT/ALARM テーブルフィールド (EVENT_DB)

`schema.h:551-554` で定義。CONFIG_DB ではなく EVENT_DB (DB index 19) に格納。

```
EVENT_HISTORY_TABLE_NAME    = "EVENT"
EVENT_CURRENT_ALARM_TABLE_NAME = "ALARM"
EVENT_STATS_TABLE_NAME      = "EVENT_STATS"
EVENT_ALARM_STATS_TABLE_NAME = "ALARM_STATS"
```

### EVENT テーブルエントリのフィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|---|---------|------|
| `id` | uint64 | 自動採番 | 単調増加するシーケンス ID (time_t 32bit + 5桁連番) |
| `type-id` | string | 必須 | イベント名 (evprofile の `name` と対応) |
| `text` | string | `""` | 動的メッセージ + 静的メッセージの結合 |
| `time-created` | uint64 (timeticks64) | 発行時刻 | イベント発生時のタイムスタンプ (nanoseconds) |
| `action` | enum | `""` (one-shot) | `RAISE` / `CLEAR` / `ACK_ALARM` / `UNACK_ALARM` / 空 |
| `resource` | string | `""` | イベント発生源 (インタフェース名・IP アドレス等) |
| `severity` | string | `evprofile` の値 | `CRITICAL` / `MAJOR` / `MINOR` / `WARNING` / `INFORMATIONAL` |
| `revision` | uint64 | `0` | evprofile の `revision` と一致 |
| `acknowledged` | boolean | `false` | ALARM テーブルのみ。ユーザー確認フラグ |

### ALARM_STATS フィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|---|---------|------|
| `critical` | uint64 | `0` | RAISE 済みで未 CLEAR・未 ACK の CRITICAL アラーム数 |
| `major` | uint64 | `0` | 同 MAJOR |
| `minor` | uint64 | `0` | 同 MINOR |
| `warning` | uint64 | `0` | 同 WARNING |
| `acknowledged` | uint64 | `0` | ACK 済みアラーム数 (severity 合計) |

---

## 4. フラッディング防止パラメータ

HLD section 3.1.4.2 に記述。eventd 内部で実装。設定パラメータなし (ハードコード)。

- **最終イベントキャッシュ**: eventd は同一 event-id + resource の直前イベントをメモリに保持し、重複は破棄。
- **キャッシュ上限**: `MAX_CACHE_SIZE = MB(100) / 150 = 699050` 件 (`eventd.cpp:31-33`)
- **上限超過時**: `CAP_STATE_LAST` モードへ移行。runtime_id ごとの最終イベントのみ保持。

---

## 5. 実装確認 discrepancy

| 項目 | HLD 記載 | コード確認結果 |
|------|---------|------------|
| `eventd.json` `no-of-records` | 最大 40000 レコード | `eventd.cpp` に読み込み実装なし (未実装の可能性) |
| `eventd.json` `no-of-days` | 最大 30 日 | 同上 |
| `evprofile/default.json` 読み込み | HLD section 3.1.2 に記述 | 利用可能ソースでは EventDB サービス部分が不足している可能性 |

> **注意**: 上記 discrepancy は shallow clone / 部分的なソース取得による可能性がある。HLD (event-alarm-framework.md) の記述を正として扱い、実装確認は `code-verified` ではなく `hld-only` として扱う。
