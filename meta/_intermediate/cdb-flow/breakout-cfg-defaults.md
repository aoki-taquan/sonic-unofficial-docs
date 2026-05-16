# Phase A — BREAKOUT_CFG フィールド暗黙デフォルト調査

## 対象フィールド

BREAKOUT_CFG テーブルのフィールドは 1 つのみ:

| フィールド | YANG 型 | YANG default 宣言 |
|-----------|---------|-----------------|
| `brkout_mode` | string (1..64) | なし（明示デフォルトなし） |

---

## フィールド別デフォルト分析

### `brkout_mode`

#### YANG 宣言
- `sonic-breakout_cfg.yang` に `default` 節なし。
- `mandatory` 節もなし → YANG レベルでは省略可能だが、空文字列は length 制約 (1..64) で弾かれる。

#### 書き込み時デフォルト（初期化経路）
`sonic-cfggen` + `portconfig.py` の `parse_breakout_mode()` による初期注入:

```python
# portconfig.py L37-38
BRKOUT_MODE = "default_brkout_mode"   # hwsku.json のキー名
CUR_BRKOUT_MODE = "brkout_mode"       # CONFIG_DB に書くキー名

# parse_breakout_mode() L467-478
for intf in hwsku_dict[INTF_KEY]:
    brkout_table[intf] = {}
    brkout_table[intf][CUR_BRKOUT_MODE] = hwsku_dict[INTF_KEY][intf][BRKOUT_MODE]
```

- 初期値は **hwsku.json の `default_brkout_mode` フィールド** そのまま。
- プラットフォーム・HWSKU ごとに異なる（例: `1x100G[40G]`、`4x25G[10G]`）。
- ハードコード固定値は存在しない。

#### 実行時 fallback
- `config interface breakout` コマンドで `target_brkout_mode` を `set_entry` する
  (`config/main.py` L5554)。実行時に別の fallback はない。
- `brkout_mode` が CONFIG_DB に存在しない場合、`show interfaces breakout` は
  対象ポートを **silently skip** する（エラーなし）。

---

## 検出された implicit behaviors

### 1. dead field なし
BREAKOUT_CFG テーブルは `brkout_mode` 1 フィールドのみ。dead field なし。

### 2. 書き込み経路依存の乖離
| 経路 | 書き込み値 |
|------|-----------|
| `sonic-cfggen` 初期化 | `hwsku.json` の `default_brkout_mode` |
| `config interface breakout` CLI | ユーザー指定 `mode` 引数（`target_brkout_mode`） |

- 乖離: 初期化後に CLI で変更された場合、CONFIG_DB の `brkout_mode` と
  `hwsku.json` の `default_brkout_mode` が異なる状態になる。
  **`config reload` 時に `sonic-cfggen` が再初期化すると hwsku.json の値に戻る**（意図的な動作）。

### 3. 複合必須制約
- `brkout_mode` の妥当性は `platform.json` の
  `interfaces.<port>.breakout_modes` で検証される（`_validate_interface_mode()` 経由）。
- `hwsku.json` の `default_brkout_mode` は `platform.json` と整合している前提だが、
  コードレベルでの相互検証はなく、不整合があると `BreakoutCfg.__init__` で
  `RuntimeError("Unsupported breakout mode {}!")` が発生する。

### 4. ハードコード固定値
なし。全値がプラットフォーム定義。

### 5. FEC 自動付与（PORT テーブル側、BREAKOUT_CFG 自身ではない）
`BreakoutCfg.get_config()` 内でチャイルドポートの PORT エントリ生成時:
```python
# portconfig.py L387-388
if entry.default_speed // lanes_per_port >= 50000:
    port_config['fec'] = 'rs'
```
- `brkout_mode` が 50G/lane 以上の構成の場合、PORT テーブルに `fec: rs` が自動付与。
- BREAKOUT_CFG 自身のフィールドではないが、`brkout_mode` 値に依存した PORT
  フィールドへの **暗黙派生**。

### 6. `subport` 自動算出
```python
# portconfig.py L383
'subport': "0" if total_num_ports == 1 else str(alias_id + 1)
```
- `brkout_mode` が `1xNNNg` の場合 `subport = "0"`、複数分割の場合 `1` から連番。

### 7. `port_config.ini` 使用時は BREAKOUT_CFG 非生成
`get_breakout_mode()` L464-465:
```python
else:
    return None  # .ini ファイル使用時は BREAKOUT_CFG テーブル自体を作らない
```
- `platform.json` がなく `port_config.ini` のみの環境では
  BREAKOUT_CFG テーブルが CONFIG_DB に存在しない状態が正常。
- この場合 `config interface breakout` 実行時に
  `BREAKOUT_CFG table is NOT present in CONFIG DB` エラーとなる（意図的 Guard）。

---

## YANG vs 実装の discrepancy

| 観点 | YANG | 実装 |
|------|------|------|
| `brkout_mode` 空文字 | length 1..64 で禁止 | `set_entry` 時 `ValueError` で弾く（二重防護） |
| `port` leafref | plain string（leafref 外し — コメント明記） | 同じ意図 |
| mandatory 宣言 | なし | 実装上は必須（get 時に KeyError になる） |

- `brkout_mode` に mandatory がないにもかかわらず、`cur_brkout_mode = cur_brkout_dict[interface_name]["brkout_mode"]`
  (L5488) で直接アクセスしており、フィールドが欠落すると `KeyError` で crash する。
  → **YANG と実装の乖離: YANG は optional、実装は事実上 mandatory**。

---

## ソース証跡

| ファイル | 行 | 内容 |
|---------|-----|------|
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-breakout_cfg.yang` | 全行 | YANG 定義（default 節なし） |
| `sonic-buildimage/src/sonic-config-engine/portconfig.py` | L37-38, L467-478 | 初期値注入ロジック |
| `sonic-buildimage/src/sonic-config-engine/portconfig.py` | L378-393 | FEC/subport 自動付与 |
| `sonic-buildimage/src/sonic-config-engine/sonic-cfggen` | L402-404 | `get_breakout_mode` 呼び出し、`BREAKOUT_CFG` への deep_update |
| `sonic-utilities/config/main.py` | L5488, L5554 | brkout_mode 読み取り・書き込み |
| `sonic-utilities/show/interfaces/__init__.py` | L228-235 | show 時の silent skip |
