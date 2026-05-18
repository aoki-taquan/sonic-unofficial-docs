# FEC_STATE 暗黙参照テーブル調査メモ

調査日: 2026-05-18
対象: STATE_DB `PORT_TABLE` の FEC 関連フィールド（`fec`, `supported_fecs`）
調査ファイル: `sonic-swss/orchagent/portsorch.cpp`, `sonic-utilities/scripts/intfutil`

---

## 参照関係まとめ

### fec フィールド (STATE_DB PORT_TABLE)

1. **書き手**: `PortsOrch::updateDbPortOperFec()` — STATE_DB `PORT_TABLE|<port>` に `fec` を書き込む
   - トリガー: SAI port_state_change 通知 (UP 時のみ) と `refreshPortStatus()` (warm boot)
   - 根拠: `portsorch.cpp:9864-9872`

2. **読み手**: `intfutil generate_fec_status()` — STATE_DB `PORT_TABLE|<port>` から `fec` を読む
   - `oper_status` も同テーブルから読み、`"up"` 以外なら `"N/A"` に上書きして表示
   - 根拠: `intfutil:911-914`

3. **FEC Admin 列の参照先は APPL_DB**: `intfutil` の FEC Admin 列は STATE_DB ではなく
   APPL_DB `PORT_TABLE:<port>` の `fec` フィールドを読む (intfutil:910)
   - CONFIG_DB の `PORT|<port>.fec` が portmgrd 経由で APPL_DB に書き込まれた値

### supported_fecs フィールド (STATE_DB PORT_TABLE)

1. **書き手**: `PortsOrch::initPortSupportedFecModes()` — SAI `SAI_PORT_ATTR_SUPPORTED_FEC_MODE` から
   プラットフォームサポート FEC モード一覧を取得して STATE_DB に書き込む
   - `fec_override_sup` (SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE) が true の場合のみ `"auto"` を末尾に追加
   - 根拠: `portsorch.cpp:3265-3327`

2. **読み手**: `isFecModeSupported()` — portsorch 内で CONFIG_DB から設定された `fec` 値の有効性チェックに使用
   - `m_portSupportedFecModes` キャッシュを経由し、STATE_DB を直接再読しない
   - 根拠: `portsorch.cpp:3205-3222`

### 間接依存

- **STATE_TRANSCEIVER_INFO_TABLE**: PortsOrch が購読する。トランシーバ検出情報。
  `supported_fecs` の lazy init は `postPortInit()` 時に実行されるため、
  トランシーバ換装後の再クエリは行われない (portsorch.cpp:984, 3270-3274)

- **CONFIG_DB PORT (fec フィールド)**: `doPortTask()` 内で FEC 設定変更時に
  `isFecModeSupported()` を呼び、`m_portSupportedFecModes` を参照 (portsorch.cpp:5323)
  ← これが `supported_fecs` の lazy init トリガーになる場合もある

---

## 依存テーブル一覧

| 方向 | 参照元 | 参照先テーブル | 参照フィールド | 用途 |
|------|--------|--------------|--------------|------|
| 書き手依存 | `PortsOrch` (portsorch.cpp) | `APPL_DB PORT_TABLE` | (portsorch 自身が APP_PORT_TABLE_NAME を保持) | oper_status や speed 等を APPL_DB に書き込む; fec は STATE_DB のみ |
| 読み手 (FEC Oper) | `intfutil` | `STATE_DB PORT_TABLE` | `fec`, `oper_status` | `show interfaces fec status` の FEC Oper 列 |
| 読み手 (FEC Admin) | `intfutil` | `APPL_DB PORT_TABLE` | `fec` | `show interfaces fec status` の FEC Admin 列 |
| 読み手 (FEC 設定有効性) | `PortsOrch::isFecModeSupported` | `m_portSupportedFecModes` (in-memory, 初回は STATE_DB に書き込んでから参照) | `supported_fecs` 相当 | CONFIG_DB PORT.fec 変更時の妥当性チェック |
| 書き手前提 | `PortsOrch::initPortSupportedFecModes` | `CONFIG_DB PORT` | `fec` | FEC 設定変更時に lazy init トリガー |
