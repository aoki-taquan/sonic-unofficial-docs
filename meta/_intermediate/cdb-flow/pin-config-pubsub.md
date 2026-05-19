# P4RT テーブル — 通信メカニズム (Phase G) 解析メモ

対象テーブル: `CONFIG_DB` の `P4RT`
Consumer: `p4rt.sh` (sonic-buildimage/dockers/docker-sonic-p4rt/p4rt.sh)
スキャン範囲: `p4rt.sh` L1–99, `p4rt_vars.j2` L1–5
スキャン日: 2026-05-19

---

## 1. 通信メカニズム概要

`P4RT` テーブルは **SubscriberStateTable も ConsumerStateTable も使わない**。
`p4rt.sh` がコンテナ起動時に `sonic-cfggen -d -t p4rt_vars.j2` を**一回だけ**呼び出して
CONFIG_DB 全体をスナップショット取得し、`P4RT` テーブルの値をバイナリ起動引数に変換する。

CONFIG_DB の変更イベントを watch する仕組みは一切存在しない。

## 2. 読み込みシーケンス

```
p4rt.sh
  L13: P4RT_VARS=$(sonic-cfggen -d -t ${P4RT_VARS_FILE})
         ↓
  p4rt_vars.j2 を Jinja2 テンプレートとして処理
  → P4RT["certs"], P4RT["p4rt_app"], DEVICE_METADATA["x509"] を JSON に展開
         ↓
  L15-17: jq で各フィールドを変数に展開
  L21-97: バイナリ起動引数 P4RT_ARGS を構築
         ↓
  L99: exec /usr/local/bin/p4rt ${P4RT_ARGS}
```

## 3. DB 購読チャンネル一覧

| 区間 | 方式 | 購読パターン / チャンネル |
|------|------|--------------------------|
| CONFIG_DB → p4rt.sh | `sonic-cfggen -d` 一括読み込み | なし（イベント駆動なし） |
| p4rt バイナリ → APPL_DB | gRPC リクエスト受信後に `P4RT_*` テーブルへ直接書き込み | 外部コントローラ起点（CONFIG_DB `P4RT` と無関係） |

**SubscriberStateTable / ConsumerStateTable / ProducerStateTable の使用: なし**

## 4. 再起動依存性

CONFIG_DB `P4RT` テーブルを変更しても `p4rt` コンテナが稼働中は変更が反映されない。
`sonic-cfggen -d -t` はコンテナ起動時 (`p4rt.sh`) の**シングルショット**であるため、
設定変更は `systemctl restart p4rt` によるコンテナ再起動後にのみ有効になる (`p4rt.sh:L13`)。

## 5. 関連コンポーネントの pubsub（P4RT テーブルとは独立）

`sonic-swss/orchagent/p4orch/` の P4 orch 群は APPL_DB の `P4RT_*` テーブル
（`P4RT_TABLE:*`, `P4RT_NEIGHBOR_TABLE:*` 等）を `ConsumerStateTable` で購読するが、
これは外部 gRPC コントローラ経由の書き込みであり、CONFIG_DB `P4RT` テーブルの
`SubscriberStateTable` とは別経路である。

## 6. 結論

| 評価項目 | 結果 |
|---------|------|
| SubscriberStateTable 使用 | なし |
| ConsumerStateTable 使用 | なし |
| ProducerStateTable 使用 | なし |
| Redis Pub/Sub チャンネル | なし |
| orchagent 経由の SAI 呼び出し | なし（p4rt バイナリが直接 P4Runtime → ASIC 制御） |
| 変更反映タイミング | コンテナ再起動時のみ |
