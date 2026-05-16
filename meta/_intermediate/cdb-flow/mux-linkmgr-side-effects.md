# MUX_LINKMGR — Phase F 副次 DB 書込 調査メモ

調査日: 2026-05-16
ソース: sonic-linkmgrd/src/DbInterface.cpp, DbInterface.h, schema.h

## STATE_DB への書込

### MUX_LINKMGR_TABLE (STATE_DB)

- テーブル名: `MUX_LINKMGR_TABLE` (schema.h:459: `STATE_MUX_LINKMGR_TABLE_NAME`)
- 書込関数: `DbInterface::handleSetMuxLinkmgrState()` (DbInterface.cpp:463-473)
- フィールド: `state` ← `link_manager::ActiveStandbyStateMachine::Label` の文字列表現
  - 値: `active` / `standby` / `unknown` / `wait`
- トリガ: linkmgrd のリンクステートマシンがプローバ結果に基づいて状態遷移したとき
- ポート単位: `mStateDbMuxLinkmgrTablePtr->hset(portName, "state", ...)` — ポート名 (例: `Ethernet0`) がキー
- 公開用途: `show mux status` CLI が STATE_DB `MUX_LINKMGR_TABLE` を読んで表示する

### MUX_METRICS_TABLE (STATE_DB)

- テーブル名: `MUX_METRICS_TABLE` (schema.h:460: `STATE_MUX_METRICS_TABLE_NAME`)
- 書込関数: `DbInterface::handlePostMuxMetrics()` (DbInterface.cpp:484-)
- MUX 切替開始/完了のタイムスタンプをポート単位で記録
- `SwitchingStart` イベント時に既存エントリを `del()` してから再書込

### MUX_SWITCH_CAUSE (STATE_DB)

- テーブル名: `MUX_SWITCH_CAUSE` (DbInterface.h:63: `STATE_MUX_SWITCH_CAUSE_TABLE_NAME`)
- MUX 切替原因を記録 (linkmgrd ステートマシン遷移理由)

## xcvrd との通信 (APPL_DB 経由)

### linkmgrd → xcvrd (コマンド送信)

1. **MUX state probe** (i2c 経由):
   - テーブル: `MUX_CABLE_COMMAND_TABLE` (APP_DB)
   - 関数: `DbInterface::handleProbeMuxState()` (DbInterface.cpp:437-444)
   - フィールド: `command` = `"probe"`
   - xcvrd が i2c で MUX チップのハードウェア状態を読み返す

2. **Forwarding state probe** (gRPC 経由):
   - テーブル: `FORWARDING_STATE_COMMAND` (APP_DB)
   - 関数: `DbInterface::handleProbeForwardingState()` (DbInterface.cpp:451-456)
   - フィールド: `command` = `"probe"`
   - xcvrd が gRPC 経由でトランシーバのフォワーディング状態を確認

### xcvrd → linkmgrd (レスポンス受信)

- `MUX_CABLE_RESPONSE_TABLE` (APP_DB): MUX state probe レスポンス
- `FORWARDING_STATE_RESPONSE` (APP_DB): forwarding state probe レスポンス
- `HW_FORWARDING_STATE_PEER` (APP_DB): peer ToR のフォワーディング状態
- `HW_MUX_CABLE_TABLE_PEER` (STATE_DB): peer ToR の HW MUX 状態

## MUX_LINKMGR パラメータと副次書込の関係

`MUX_LINKMGR|LINK_PROBER` の `interval_v4` / `interval_v6` / `positive_signal_count` /
`negative_signal_count` が変更されると:
1. linkmgrd がプローバタイマーを再設定
2. 次の probe サイクルから `probeMuxState()` / `probeForwardingState()` の呼出頻度が変わる
3. 状態遷移が発生すれば `setMuxLinkmgrState()` → STATE_DB `MUX_LINKMGR_TABLE` 書込

つまり MUX_LINKMGR フィールド変更は直接 STATE_DB を書き換えないが、
プローバの動作変化を通じて間接的に STATE_DB `MUX_LINKMGR_TABLE` の `state` フィールド遷移を誘発する。

## 証跡ファイル

- `sonic-linkmgrd/src/DbInterface.cpp` L120-167, L437-473
- `sonic-linkmgrd/src/DbInterface.h` L58, L63, L180-215
- `sonic-swss-common/common/schema.h` L140-149, L459-460
