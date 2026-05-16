# CONSOLE_PORT / CONSOLE_SWITCH — Phase B 書込み順依存スキャンノート

対象テーブル: `CONSOLE_PORT`, `CONSOLE_SWITCH`
Consumer: `consutil` (CLI、`sonic-utilities/consutil/lib.py`)、`minigraph.py` (書き込み側)
スキャン範囲: `ConsolePortProvider._init_all()`, `ConsolePortInfo.connect()`, `config/console.py` 全行、`minigraph.py` DeviceSerialLink パース部

---

## 検出した順序依存・タイミング依存

### 1. CONSOLE_SWITCH.enabled の先行必須 — 機能ゲート

- `ConsolePortProvider._init_all()` (lib.py L86-131) は最初に `CONSOLE_SWITCH|console_mgmt` を `get_entry()` で取得し、`enabled == "yes"` でなければ `self._default_escape_char = None` のまま処理を続ける。
- 接続試行時に `CONSOLE_SWITCH.enabled` が `"yes"` でない場合、`CONSOLE_PORT` エントリが存在していても `consutil` は機能を提供しない（「console switch が disabled」として扱われる）。
- **順序依存**: `CONSOLE_PORT` エントリを書き込む前に `CONSOLE_SWITCH|console_mgmt.enabled = "yes"` を設定しておくことが推奨。逆順では `config console add` は成功するが、`consutil connect` が disabled ガードに当たる。
- evidence: `consutil/lib.py:90-94`

### 2. CONSOLE_SWITCH.default_escape_char vs CONSOLE_PORT.escape_char — 上書き順序

- `ConsolePortInfo.escape_char` (lib.py L168-169): `self._info.get(FEATURE_ESCAPE_KEY, self._default_escape_char)` — ポート個別 `escape_char` が存在すれば優先、なければ `CONSOLE_SWITCH.default_escape_char` にフォールバック。
- `default_escape_char` は `_init_all()` で一度だけ取得され、`ConsolePortProvider` インスタンスの生存期間中は固定される（runtime 中の `CONSOLE_SWITCH` 変更は次回インスタンス生成まで反映されない）。
- **順序依存**: `CONSOLE_SWITCH.default_escape_char` は `CONSOLE_PORT.escape_char` より優先度が低い（上書きされる）。グローバルデフォルト設定を変更しても、ポート個別設定がある場合は影響しない。
- evidence: `consutil/lib.py:91-98`, `consutil/lib.py:168-169`

### 3. baud_rate 必須 — CONSOLE_PORT エントリの内部順序

- `ConsolePortInfo.connect()` (lib.py L189-224): `baud_rate` が `None`（フィールド不在）の場合、`InvalidConfigurationError` を送出して接続を拒否する (lib.py L198-199)。
- `config console add` では `--baud` オプションが `required=True` なので CLI 経由での不在は防がれるが、minigraph 経由や直接 DB 書き込みでは `baud_rate` なしエントリが生成可能。
- **順序依存（内部フィールド）**: `baud_rate` → `flow_control` → `remote_device` → `escape_char` の順で `console_entry` dict に追加してから `set_entry()` する (`config/console.py L117-129`)。`set_entry()` は atomic なため途中状態は発生しないが、`mod_entry()` による部分更新では `baud_rate` 欠如状態が一時的に生じる可能性がある（実際には `baud` の `mod_entry` は既存エントリ確認後に実施されるため通常は問題なし）。
- evidence: `consutil/lib.py:197-199`, `config/console.py:117-129`

### 4. remote_device 一意性制約 — add / update の順序制約

- `isExistingSameDevice()` (config/console.py L292-298): `get_table("CONSOLE_PORT")` で全エントリを走査し、同一 `remote_device` 名が存在すれば `True` を返す。
- `config console add` / `config console remote_device` で重複を検出した場合、書き込みは行われず `ctx.fail()` で終了する。
- **順序依存**: 既存ポートの `remote_device` を別ポートへ移動したい場合、先に古いポートの `remote_device` を削除（`config console remote_device <old_line>`（引数なし）= クリア）してから新しいポートへ追加する必要がある。逆順では「既に使用済み」エラーになる。
- evidence: `config/console.py:120-123`, `config/console.py:185-186`, `config/console.py:292-298`

### 5. minigraph 書き込みの flow_control 型問題 — 消費側との乖離

- `minigraph.py` (L616, L618-628) は `flow_control` フィールドを integer `0` / `1` として書き込む。
- `consutil/lib.py` (L153) は `self._info[FLOW_KEY] == "1"` で文字列比較するため、minigraph 由来の integer `1` は常に `False` 判定になる。
- **順序依存（ツール間）**: minigraph → `sonic-cfggen` 経由での初期化後、`config console flow_control enable <line>` を実行すると文字列 `"1"` で上書きされ、consutil が正しく認識するようになる。初期化のみで CLI 再設定を行わない場合は flow_control は常に disabled 扱いになる。
- evidence: `minigraph.py:616`, `consutil/lib.py:152-153`

### 6. STATE_DB への busy 状態書き込みタイミング

- `ConsolePortProvider._init_all(refresh=True)` (lib.py L108-118) は `SysInfoProvider.list_active_console_processes()` を呼び、アクティブな picocom プロセスを検出してから STATE_DB を更新する。
- `refresh=False` (デフォルト) の場合は STATE_DB の既存値をそのまま読むだけで、プロセス状態とは同期しない。
- **順序依存**: `show console status` 等のコマンドは `refresh=True` でインスタンスを生成するため最新状態を反映するが、`connect` 前の busy チェック (lib.py L193-195) も `refresh()` を呼ぶため最新状態を参照する。CONFIG_DB の変更は STATE_DB の busy 状態に影響しない（独立）。
- evidence: `consutil/lib.py:108-120`, `consutil/lib.py:189-196`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | CONSOLE_SWITCH.enabled=yes → CONSOLE_PORT エントリ追加 | 推奨先行（逆順でも DB 書き込みは成功するが接続不能） | CONSOLE_SWITCH 設定後は即時反映（次回 consutil 呼び出しから有効） |
| 2 | CONSOLE_SWITCH.default_escape_char は CONSOLE_PORT.escape_char で上書き | 優先度低（ポート個別設定が常に優先） | ポート個別 escape_char を clear すれば global に回帰 |
| 3 | baud_rate 必須 — フィールド不在で接続拒否 | 内部フィールド必須 | CLI (`--baud required`) で防御済み。直接 DB 書き込みは注意 |
| 4 | remote_device 移動: 旧ポートのクリア → 新ポートへ追加 | 先行必須（逆順で一意性エラー） | クリア後に追加の 2 ステップ操作 |
| 5 | minigraph integer flow_control → CLI 文字列再設定 | 初期化後に CLI 再設定推奨 | `config console flow_control enable <line>` で文字列上書き |
| 6 | CONFIG_DB 変更と STATE_DB busy 状態は独立 | 非依存 | refresh=True で最新プロセス状態を取得 |
