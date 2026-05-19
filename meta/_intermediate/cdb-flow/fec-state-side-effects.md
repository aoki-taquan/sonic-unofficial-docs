# FEC_STATE 副次 DB 書込調査メモ (Phase F)

調査日: 2026-05-19
対象: `PortsOrch` が FEC 関連処理を実行する際に STATE_DB `PORT_TABLE.fec` / `supported_fecs`
      の書込みに**付随して**発生する他テーブル・他 DB への書込み
調査ファイル: `sonic-swss/orchagent/portsorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## 副次 DB 書込の全体像

### トリガー A: ポート oper-status UP 通知（`updatePortNotifyOrchAgents`）

`fec` フィールドの書込みは `status == SAI_PORT_OPER_STATUS_UP` ブロック内で発生する
(portsorch.cpp:9668)。同一 UP イベントで以下が**同期的に**実行される:

1. `updatePortOperStatus(port, status)` → APPL_DB `PORT_TABLE` に `oper_status` 書込み
   (portsorch.cpp:9787 → 3916-3930、`m_portTable->set(port.m_alias, {oper_status=...})`)
2. `updateDbPortOperSpeed(port, speed)` → STATE_DB `PORT_TABLE` に `speed` 書込み
   (portsorch.cpp:9674,9678 → 9850-9857、`m_portStateTable.set(port.m_alias, {speed=...})`)
3. `updateDbPortOperFec(port, fec_str)` → STATE_DB `PORT_TABLE` に `fec` 書込み（本ページの主作用）
   (portsorch.cpp:9690,9694 → 9864-9870)

### トリガー B: `postPortInit()` でのポート初期化

`supported_fecs` の書込みは `postPortInit()` → `initPortSupportedFecModes()` で発生する
(portsorch.cpp:6461,3265)。`postPortInit()` の同一呼出しで以下が実行される:

1. `initPortSupportedSpeeds(alias, port_id)` → STATE_DB `PORT_TABLE` に `supported_speeds` 書込み
   (portsorch.cpp:6460 → 3159-3172、`m_portStateTable.set(alias, {supported_speeds=...})`)
2. `initPortSupportedFecModes(alias, port_id)` → STATE_DB `PORT_TABLE` に `supported_fecs` 書込み（本ページの主作用）
   (portsorch.cpp:6461 → 3265-3320)

### トリガー C: `addPort()` でのポート登録（COUNTERS_DB）

`addPort()` (portsorch.cpp:4118) は `m_counterNameMapUpdater->setCounterNameMap(p.m_alias, p.m_port_id)` を呼び、
COUNTERS_DB の `COUNTERS_PORT_NAME_MAP` ハッシュに `<port_alias> → <sai_port_oid>` マッピングを書き込む。
`initPortSupportedFecModes()` はその後の `postPortInit()` で呼ばれるため、`supported_fecs` 書込みより
`COUNTERS_PORT_NAME_MAP` 書込みが先に完了している。

---

## 副次書込一覧表

| # | 副次 DB | テーブル / キー | フィールド | 書込内容 | 呼出元 | 証跡 |
|---|---------|--------------|-----------|---------|--------|------|
| 1 | APPL_DB | `PORT_TABLE:<port>` | `oper_status` | `"up"` / `"down"` | `updateDbPortOperStatus()` ← ポート UP/DOWN | `portsorch.cpp:3916-3930` |
| 2 | STATE_DB | `PORT_TABLE\|<port>` | `speed` | oper speed 数値 (Mbps) / `"N/A"` | `updateDbPortOperSpeed()` ← ポート UP 時 | `portsorch.cpp:9850-9857` |
| 3 | STATE_DB | `PORT_TABLE\|<port>` | `supported_speeds` | サポート speed の CSV リスト | `initPortSupportedSpeeds()` ← `postPortInit()` | `portsorch.cpp:3159-3172` |
| 4 | COUNTERS_DB | `COUNTERS_PORT_NAME_MAP` | `<port_alias>` | SAI port OID 文字列 | `m_counterNameMapUpdater->setCounterNameMap()` ← `addPort()` | `portsorch.cpp:4114-4118` |

---

## 注意事項

- `oper_status` (APPL_DB) と `fec` / `speed` (STATE_DB) は同一 UP イベントで書かれるが、
  APPL_DB と STATE_DB への書込みは独立した Redis コマンドで実行される。両者の間に原子性はない。
- `COUNTERS_PORT_NAME_MAP` は `addPort()` 時 1 回だけ書かれる（ポート削除時は `delCounterNameMap` で削除）。
  FEC 設定変更では再書込みされない。
- ASIC_DB への SAI オブジェクト作成（`sai_port_api->set_port_attribute` の結果）は副次書込とは見なさない（主作用として別管理）。
