# CONSOLE_PORT — Phase A: コード由来の暗黙デフォルト調査

## 調査対象フィールド

### CONSOLE_PORT テーブル

| フィールド | YANG 型 | YANG default | CLI 書き込み時挙動 | 実行時 fallback |
|---|---|---|---|---|
| `baud_rate` | uint32 | なし | `--baud` required。型: `click.INT`、DB 書き込み時に `str(baud)` に変換。未設定ポートへの接続時に `baud is None` → `InvalidConfigurationError` で即拒否 | なし |
| `flow_control` | `"0"\|"1"` | `"0"` (YANG) | `--flowcontrol` は is_flag=True。省略時は `False` → `"0"` を書き込む。minigraph 経由では `FlowControl` XML タグ存在かつ `text=="true"` の場合のみ `1`、それ以外 `0`。書き込み時に integer `0`/`1` を格納し、consutil 読み出し時に `== "1"` 文字列比較 | consutil の `flow_control` property: `FLOW_KEY in self._info and self._info[FLOW_KEY] == "1"` → フィールド自体が存在しない場合は `False` 扱い（YANG default `"0"` とは独立してコード側でも None-safe） |
| `remote_device` | stypes:hostname | なし | `--devicename` 省略時はエントリに key 自体を含めない（silent omit）。consutil 側 `remote_device` property: フィールドなし → `None` | なし。`None` のままで接続は続行可 |
| `escape_char` | `[a-z]` 1文字 | なし | `--escape` 省略時はエントリに key 自体を含めない。`config console escape <line> clear` で既存 key を del する。書き込み前に `escape.lower()` で強制小文字化 | consutil `escape_char` property: `self._info.get(FEATURE_ESCAPE_KEY, self._default_escape_char)` → 未設定なら `CONSOLE_SWITCH.default_escape_char` へ fallback。それも None なら picocom 起動コマンドに `-e` オプション自体を付けない |

### CONSOLE_SWITCH テーブル (`console_mgmt` キー)

| フィールド | YANG default | CLI 挙動 | 実行時 fallback |
|---|---|---|---|
| `enabled` | `"no"` (YANG) | `config console enable` → `"yes"`、`disable` → `"no"` 書き込み | consutil `_init_all`: `feature_state.get(FEATURE_ENABLED_KEY, "no")` → エントリ/フィールド不在時は `"no"` として扱う |
| `default_escape_char` | なし | `config console default_escape <char>` または `clear`。書き込み前に `escape.lower()` 強制小文字化。`clear` はフィールドを del して `set_entry` | consutil: `.get(DEFAULT_FEATURE_ESCAPE_KEY, None)` → 未設定なら `None`。CONSOLE_SWITCH 自体が disabled なら `_default_escape_char = None` に固定（フィールド有無を問わず） |

## 検出した暗黙デフォルト・特殊挙動

### 1. flow_control: YANG default と CLI 書き込みの二重保証
- YANG: `default "0"` — YANG validation 時にデフォルト補完
- CLI: `--flowcontrol` is_flag 省略 → `"0"` を明示書き込み（YANG default に依存しない）
- minigraph: `FlowControl` XML タグ存在 + `text=="true"` の場合のみ `1`、それ以外 `0`（integer 型で格納）
- **書き込み vs 実行時乖離**: minigraph は integer `0`/`1`、CLI は文字列 `"0"`/`"1"`。consutil 読み出しは `== "1"` 文字列比較なので minigraph 経由で integer `1` が格納された場合は `False` 判定になる（silent bug の可能性）

### 2. baud_rate: 必須フィールドだが YANG default なし
- CLI: `--baud` required なので CLI 経由では必ず設定される
- minigraph 経由: minigraph XML の `<Bandwidth>` タグから取得。タグ不在は実質エラーだが Python コードは None チェックなし（AttributeError になる可能性）
- 接続時: `if self.baud is None: raise InvalidConfigurationError` — 実行時ガードあり
- **dead field 状態**: DB に key が存在しても `baud_rate` フィールドがなければ接続不能（consutil が実行時エラー）

### 3. remote_device: optional で silent omit
- 省略 = エントリに含まれない（`""`/`null` でなく key 自体なし）
- consutil: `remote_device is None` でも接続は続行可（`__str__` に使われるが接続判断には不使用）

### 4. escape_char の fallback チェーン（ポート → グローバル → picocom デフォルト）
- `CONSOLE_PORT.escape_char` 設定あり → そのまま使用
- なし → `CONSOLE_SWITCH.default_escape_char` を使用
- なし → picocom に `-e` オプションなし（picocom 自身のデフォルト: `a` = Ctrl+A）
- **YANG pattern 制約**: `[a-z]` (小文字 1 文字のみ)。`config console escape` は `case_sensitive=True` だが書き込み前に `.lower()` で強制変換 → 大文字を入れてもエラーにならず小文字変換して格納される
- **YANG-実装 discrepancy**: YANG は `[a-z]` のみ受け付けるが、CLI の `click.Choice` は `string.ascii_letters`（大文字も含む）を受け入れる。lower() で変換後に YANG に書かれるため最終 DB 値は合法だが、ユーザーには「大文字を受け付けるように見える」UX の乖離がある

### 5. CONSOLE_SWITCH disabled 時の _default_escape_char 強制 None
- `feature_state.get(FEATURE_ENABLED_KEY, "no") != "yes"` の場合、`default_escape_char` フィールドが DB に存在していても `_default_escape_char = None` に固定（読み取り自体をスキップ）
- 結果として CONSOLE_SWITCH enabled 前に設定した `default_escape_char` はサイレントに無視される

### 6. device prefix のプラットフォーム依存
- `SysInfoProvider.DEVICE_PREFIX = "/dev/ttyUSB"` がデフォルト
- プラットフォームに `udevprefix.conf` が存在する場合は `/dev/<first-line>` に上書き
- CONSOLE_PORT の key (line_num) はこの prefix の後ろに付くデバイスパス番号と 1:1 対応
- **platform 依存**: プラットフォームごとに tty デバイス名が異なるため、同じ line_num でもアクセスする物理デバイスが変わりうる

## evidence 索引

| evidence | ファイル | 行 |
|---|---|---|
| flow_control YANG default "0" | sonic-console.yang | L62-63 |
| flow_control CLI is_flag | config/console.py | L98,L118 |
| flow_control minigraph int cast | minigraph.py | L616 |
| baud_rate CLI required | config/console.py | L97 |
| baud_rate consutil None guard | consutil/lib.py | L198-199 |
| escape_char lower() 強制 | config/console.py | L82,L126,L282 |
| escape_char CLI large-letter accept | config/console.py | L65,L101 (ascii_letters) |
| escape fallback chain | consutil/lib.py | L169 |
| enabled default "no" YANG | sonic-console.yang | L86-87 |
| enabled consutil fallback "no" | consutil/lib.py | L94 |
| default_escape_char disabled skip | consutil/lib.py | L93-98 |
| DEVICE_PREFIX default | consutil/lib.py | L297 |
| DEVICE_PREFIX platform override | consutil/lib.py | L301-307 |
| minigraph console_ports build | minigraph.py | L617-628 |
