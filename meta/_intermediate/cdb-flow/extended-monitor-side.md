# extended-monitor — Phase F: 副次 DB 書込スキャンノート

調査日: 2026-05-19
対象ページ: `docs/reference/config-db/extended-monitor.md`
対象設定: `/etc/eventd.json` (EVENT テーブル保持上限) + `/etc/evprofile/default.json` (イベントプロファイル)
Consumer/Producer: EventDB service (`eventd` 内 event_consumer + alarm_consumer)
スキャン範囲: `eventd.cpp` (全行)、`schema.h` (EVENT_DB テーブル名定数)、HLD section 3.1.2〜3.1.4

---

## 調査対象ソース

- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp` — イベント受信・処理・DB 書込
- `sonic-buildimage/src/sonic-eventd/src/eventd.h` — カウンタ定数・DBConnector 定義
- `sonic-swss-common/common/schema.h` — `EVENT_DB = 19`, テーブル名定数
- `SONiC/doc/event-alarm-framework/event-alarm-framework.md` — HLD section 3.1.2〜3.1.4, section 3.1.8

---

## 1. EVENT_DB への書込み

EventDB service は `/etc/evprofile/default.json` の内容をもとに受信イベントを処理し、EVENT_DB (Redis DB index 19) の以下の 4 テーブルへ書き込む。

### 書込みテーブル一覧

| DB | テーブル | 書込有無 | 書込条件 |
|----|---------|---------|---------|
| `EVENT_DB` (index 19) | `EVENT` | **あり** | すべての受信イベント（`enable=true` のもの）が書き込まれる |
| `EVENT_DB` (index 19) | `ALARM` | **あり** | `action=RAISE_ALARM` で追加、`CLEAR_ALARM` で削除 |
| `EVENT_DB` (index 19) | `EVENT_STATS` | **あり** | 受信イベントの統計カウンタ (累計) |
| `EVENT_DB` (index 19) | `ALARM_STATS` | **あり** | severity 別アクティブアラーム数。`critical`/`major`/`minor`/`warning`/`acknowledged` |
| `COUNTERS_DB` | `COUNTERS_EVENTS` | **あり（定期）** | `stats_collector::run_writer()` が最大 10ms 毎に発行済み/キャッシュ損失カウンタを書込み |
| `CONFIG_DB` | — | なし | eventd はファイル直接読み。CONFIG_DB アクセスなし |
| `APPL_DB` | — | なし | 書込みパスなし |
| `STATE_DB` | — | なし | 書込みパスなし |
| `ASIC_DB` | — | なし | SAI 非経由 |

### EVENT テーブルへの書込み詳細

HLD section 3.1.2 より:
- 受信イベントの `type-id`（evprofile の `name`）で `static_event_map` を参照し、`enable` フラグを確認
- `enable=false` の場合はデバッグログのみで破棄
- `enable=true` の場合: `id`（`time_t:32bit + 5桁連番`）を採番し EVENT テーブルへ書込み
- `no-of-records`（デフォルト 40000）または `no-of-days`（デフォルト 30 日）いずれかの上限到達でローテーション（古いエントリを削除）

### ALARM テーブルへの書込み詳細

| `action` フィールド値 | ALARM テーブルへの副次書込 | ALARM_STATS への影響 |
|---------------------|--------------------------|---------------------|
| `RAISE_ALARM` | 新規エントリ追加 (`acknowledged=false`) | 対応 severity カウンタ +1 |
| `CLEAR_ALARM` | エントリ削除（`id`+`resource` による検索） | 対応 severity カウンタ -1 |
| `ACK_ALARM` | `acknowledged=true`・`acknowledge_time` を更新 | `acknowledged` カウンタ +1、severity カウンタ -1 |
| `UNACK_ALARM` | `acknowledged=false`・`acknowledge_time` を更新 | `acknowledged` カウンタ -1、severity カウンタ +1 |
| 空文字列 (one-shot) | なし (EVENT テーブルのみ) | 変化なし |

---

## 2. pmon による ALARM_STATS 購読と LED 制御

HLD section 3.1.3 より:
- `pmon` コンテナが `ALARM_STATS` テーブルの `critical`/`major`/`minor`/`warning` カウンタを購読
- アクティブアラーム（RAISE 済み・未 CLEAR・未 ACK）の severity に応じてシステム LED を制御:
  - `critical` または `major` アラームあり → **Red**
  - `minor` または `warning` のみ → **Amber (Yellow)**
  - アクティブアラームなし → **Green**
- これは「副次書込」というより「副次購読」だが、LED 状態変化という外部への副作用を持つ

---

## 3. リブート時の書込み挙動

| リブート種別 | EVENT テーブル | ALARM / ALARM_STATS テーブル |
|------------|-------------|---------------------------|
| Cold reboot | **ディスク永続化あり** | 消去（再起動後にアプリが再 RAISE 必要） |
| Warm reboot | **ディスク永続化あり** | 消去（ALARM/ALARM_STATS 除外） |
| Fast reboot | **ディスク永続化あり** (EVENT + EVENT_STATS) | 消去 |
| Power reset | **ディスク永続化あり** (定期永続化 DB から復元) | 消去（定期永続化タイミング依存で一部損失の可能性） |

(根拠: HLD section 4.1.1〜4.4)

---

## 4. 外部サービスへの副作用まとめ

| 外部コンポーネント | 副次作用 | 方向 |
|----------------|---------|------|
| `pmon` | `ALARM_STATS` を購読してシステム LED を切り替え | EVENT_DB → pmon |
| `telemetry` (gNMI) | `xpub_path` (:5571) 経由でイベントストリームを購読し gNMI クライアントに転送 | ZMQ → telemetry |
| `sonic-gnmi` | `events_client.go` が ZMQ XPUB に接続し、gRPC EventStream として外部に配信 | ZMQ → 外部クライアント |

---

## 5. ページ反映方針

- `<!-- /constants -->` と `## 引用元` の間に `<!-- side-effects --> ... <!-- /side-effects -->` ブロックを挿入
- EVENT_DB 4 テーブル (EVENT/ALARM/EVENT_STATS/ALARM_STATS) への書込みを主軸に記述
- pmon LED 制御を「副次購読」として補足
- COUNTERS_DB 書込みは event-publisher.md との重複を避け「同じ stats_collector による」と簡潔に示す
- 引用元は既存 [^1][^3] を流用（HLD + eventd.cpp）
