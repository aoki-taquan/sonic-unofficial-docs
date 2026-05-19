# errordb-pubsub — Phase G 調査証跡

## 調査対象

`ERROR_DB` (ERROR_ROUTE_TABLE / ERROR_NEIGH_TABLE) の購読方式:
- ErrorListener クラスの登録 / 解除 API
- OrchAgent から ErrorListener への pub/sub 通知チャンネル
- fpmsyncd による購読実例

## 一次情報源

### HLD Section 3.3.1–3.3.2 (error_handling_design_spec.md)

```
## 3.3.2 Application registration
ErrorListener fpmErrorListener(APP_ROUTE_TABLE_NAME, (ERR_NOTIFY_FAIL | ERR_NOTIFY_POSITIVE_ACK));

Select s;
s.addSelectable(&fpmErrorListener);
```

- `ErrorListener` は `swss::Selectable` を継承し、`Select::addSelectable()` で orchdaemon / app の select() ループに組み込む
- コンストラクタ引数: テーブル名 (APP_ROUTE_TABLE_NAME)、通知フラグ (ERR_NOTIFY_FAIL | ERR_NOTIFY_POSITIVE_ACK)
- 複数アプリが同一テーブルを購読可能 (HLD 1.1.1)

### HLD Section 3.3.1 イベント処理シーケンス

失敗通知:
1. Syncd が ASIC_DB 通知チャネルで OrchAgent に失敗イベントを送信
2. OrchAgent が SAI 型 → ERROR_DB 型に翻訳 → HSET → PUBLISH (ERROR_DB チャンネル)
3. ErrorListener が PUBLISH を受信 → フィルタリング → アプリコールバック起動

成功通知:
1. Syncd が ASIC_DB 通知チャネルで OrchAgent に成功イベントを送信
2. OrchAgent が ERROR_DB エントリを DEL → PUBLISH
3. ErrorListener が受信 → ERR_NOTIFY_POSITIVE_ACK 登録アプリのみコールバック

### HLD Section 3.3.2 — 通知フラグ

| フラグ | 意味 |
|---|---|
| `ERR_NOTIFY_FAIL` | 失敗時のみ通知 (デフォルト) |
| `ERR_NOTIFY_POSITIVE_ACK` | 成功時にも通知 |

正式なビット値は HLD 未定義。実装ヘッダーは master 未マージ。

### HLD Section 3.3.3 — clear 時の挙動

OrchAgent が clear コマンドを通知チャンネル経由で受信し、ERROR_DB を DEL するが、**registered applications への PUBLISH は行わない**。

## 実装状況確認

```bash
# sonic-swss-common に ErrorListener / ErrorReporter クラスが存在するか確認
grep -r "ErrorListener\|ErrorReporter" .cache/sonic-sources/sonic-swss-common/
# → 0件 (master 未マージ)

grep -r "ErrorListener\|ErrorReporter" .cache/sonic-sources/sonic-swss/
# → 0件 (master 未マージ)
```

## 結論

ERROR_DB の購読方式は:
- `ErrorListener` クラス (`swss::Selectable` 継承) による pub/sub
- OrchAgent が `HSET` / `DEL` 後に ERROR_DB チャンネルへ `PUBLISH`
- ErrorListener が select() ループで待機し、フィルタリング後コールバック起動
- `ERR_NOTIFY_FAIL` (デフォルト) / `ERR_NOTIFY_POSITIVE_ACK` のフラグで購読対象を制御
- `sonic-clear error-database` は PUBLISH を発行しない（app 非通知）

実装は 2026-05 時点で master 未マージ。HLD Section 3.3.1-3.3.2 のみが根拠。
