# FEC_STATE 書込み順依存調査メモ

調査日: 2026-05-18
対象: STATE_DB `PORT_TABLE` の FEC 関連フィールド（`fec`, `supported_fecs`）
調査ファイル: `sonic-swss/orchagent/portsorch.cpp`

---

## 書込みトリガーと順序制約

### `fec` フィールドの書込み順序

`updateDbPortOperFec(port, fec_str)` (portsorch.cpp:9864) の呼び出しは 2 経路:

1. **ポート oper-status UP 遷移時** (portsorch.cpp:9682–9694):
   - syncd から `port_status` 通知を受信 → `updatePortOperStatus()` を呼んだ後
   - ポートが `SAI_PORT_OPER_STATUS_UP` のときのみ書き込む（DOWN 時は書き込まない）
   - 順序: `updatePortOperStatus()` → (`getPortOperFec` + `fecToStr`) → `updateDbPortOperFec()`

2. **orchagent 起動時 `refreshPortStatus()`** (portsorch.cpp:9885–9930):
   - warm boot: `onWarmBootEnd()` → `refreshPortStatus()` (portsorch.cpp:6431)
   - cold boot: `postPortInit()` 後のポート初期化完了時点で `PortInitDone` 受信 → その後最初の oper-status UP 通知で書き込まれる
   - `refreshPortStatus()` は PHY ポートのみを対象に SAI を直接ポーリング

### `supported_fecs` フィールドの書込み順序

`initPortSupportedFecModes(alias, port_id)` (portsorch.cpp:3265) の呼び出しは 2 経路:

1. **cold boot / postPortInit()**: `addPort()` 完了後 `postPortInit()` 内で呼び出し (portsorch.cpp:6461)
   - 依存: ポートが SAI に作成済み (`initializePorts()` 成功) であること
   - 依存: `PortInitDone` 受信前に完了する（ポート登録段階）

2. **doPortTask() での FEC 設定時**: `isFecModeSupported()` → `initPortSupportedFecModes()` (portsorch.cpp:5323)
   - lazy init。`m_portSupportedFecModes` に未登録のときのみ SAI クエリ実行
   - 一度登録されると再クエリしない（orchagent 再起動まで固定）

---

## 検出された順序依存

| # | 依存関係 | 方向 | 根拠 |
|---|----------|------|------|
| 1 | SAI ポート作成 (`initializePorts`) → `supported_fecs` 書込み | **強制先行** | `initPortSupportedFecModes` は `port_id` が有効な SAI OID でなければ SAI クエリ不可 (portsorch.cpp:6461, 3265) |
| 2 | `postPortInit()` 完了 → `supported_fecs` STATE_DB 書込み | **ポート登録時 1 回限り** | cold boot では `addPort()` の後 `postPortInit()` を呼ぶ (portsorch.cpp:4078) |
| 3 | ポート oper-status UP 通知受信 → `fec` 書込み | **イベント駆動・UP 時のみ** | DOWN 遷移では書き込まれない。最後の UP 時の値が残留 (portsorch.cpp:9682–9694) |
| 4 | `oper_fec_sup` フラグ確定 (orchagent 初期化) → `fec` 書込み許可 | **初期化先行** | `oper_fec_sup` は PortsOrch コンストラクタ内 (portsorch.cpp:1001–1010) で一度だけ評価。false なら `fec` は常に `"N/A"` |
| 5 | `fec_override_sup` フラグ確定 → `supported_fecs` の `"auto"` 末尾追加 | **初期化先行** | `fec_override_sup` も コンストラクタ (portsorch.cpp:990–998) で確定。true でなければ `"auto"` は絶対に出現しない |
| 6 | warm boot: `onWarmBootEnd()` → `refreshPortStatus()` → `fec` 再同期 | **warm boot 限定・起動後 1 回** | `m_isWarmRestoreStage=false` になった直後に全 PHY ポートの FEC 値を SAI から再取得して上書き (portsorch.cpp:6431) |

---

## consumer との観測タイミング

- `intfutil` (`show interfaces fec status`) は STATE_DB を直接読むため、
  ポートが UP になるまで `fec` フィールドに最後の値か初期値が残る可能性がある。
- `supported_fecs` は `postPortInit()` 完了後に 1 回書かれるため、
  `intfutil` が参照するタイミングが初期化前であれば未確定状態。
- warm boot 中は `refreshPortStatus()` 完了前に `fec` が stale 状態になりうる。
