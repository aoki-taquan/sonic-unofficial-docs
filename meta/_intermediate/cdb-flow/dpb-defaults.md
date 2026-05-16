# dpb-defaults — Phase A コード由来暗黙デフォルト調査

対象: `docs/reference/config-db/dpb.md`  
調査日: 2026-05-15

## 調査対象テーブル

CONFIG_DB `BREAKOUT_CFG` — Dynamic Port Breakout (DPB) 機能で導入。親ポートごとの現在の breakout モードを保持する。

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-breakout_cfg.yang` — YANG モデル
- `sonic-buildimage/src/sonic-config-engine/portconfig.py` — 起動時初期値生成
- `sonic-buildimage/src/sonic-config-engine/sonic-cfggen` — cfggen エントリポイント
- `sonic-utilities/config/main.py` — CLI `breakout` サブコマンド
- `SONiC/doc/dynamic-port-breakout/sonic-dynamic-port-breakout-HLD.md` — HLD

---

## フィールド列挙

| フィールド | スコープ | YANG default 宣言 |
|---|---|---|
| `brkout_mode` | per-port (親ポートキー) | なし |

YANG (`sonic-breakout_cfg.yang`) は `brkout_mode` に `default` 文を持たない。型は `string { length 1..64; }` のみ。

---

## コード由来の暗黙デフォルト

### 1. `brkout_mode` — 起動時初期値は `hwsku.json` の `default_brkout_mode`

**ソース**: `portconfig.py:37-38`
```python
BRKOUT_MODE = "default_brkout_mode"
CUR_BRKOUT_MODE = "brkout_mode"
```

**ソース**: `portconfig.py:475-478` (`parse_breakout_mode`)
```python
for intf in hwsku_dict[INTF_KEY]:
    brkout_table[intf] = {}
    brkout_table[intf][CUR_BRKOUT_MODE] = hwsku_dict[INTF_KEY][intf][BRKOUT_MODE]
return brkout_table
```

`sonic-cfggen` は起動時 (`sonic-cfggen:402-404`) に `get_breakout_mode()` を呼び出し、`hwsku.json` の各親ポートエントリの `default_brkout_mode` フィールドを `BREAKOUT_CFG.<port>.brkout_mode` として CONFIG_DB に書き込む。

```python
# sonic-cfggen:402-404
brkout_table = get_breakout_mode(hwsku, platform, args.port_config)
if brkout_table:
    deep_update(data, {'BREAKOUT_CFG': brkout_table})
```

**まとめ**:  
`brkout_mode` のデフォルト値はコード定数ではなく **プラットフォーム定義** (`hwsku.json` の `default_brkout_mode` フィールド) に完全依存する。YANG レイヤーは補完しない。CONFIG_DB に一度も書かれていない場合 CLI は `BREAKOUT_CFG table is NOT present in CONFIG DB` エラーを返す (`main.py:5481`)。

---

### 2. `brkout_mode` — CLI 書き込み (`config interface breakout`)

**ソース**: `sonic-utilities/config/main.py:5554`
```python
config_db.set_entry("BREAKOUT_CFG", interface_name, {'brkout_mode': target_brkout_mode})
```

`config interface breakout <port> <mode>` コマンドは breakout 完了後に `brkout_mode` を指定モードで上書きする。省略不可。利用可能な mode 一覧は `platform.json` の `breakout_modes` から取得 (`main.py:182-195`)。

---

## mode 文字列フォーマット

`brkout_mode` の値フォーマットは `portconfig.py:42` で定義:
```python
BRKOUT_PATTERN = r'(\d{1,6})x(\d{1,6}G?)(\[(\d{1,6}G?,?)*\])?(\((\d{1,6})\))?'
```

代表例:
- `1x100G[40G]` — 全レーン 1 ポート、デフォルト 100G (40G 切り替え可)
- `2x50G` — 2 ポート均等分割、各 50G
- `4x25G[10G]` — 4 ポート均等分割、各 25G (10G 切り替え可)
- `2x25G(2)+1x50G(2)` — 非均等混在モード
- `1x400G`, `2x200G`, `4x100G`, `8x50G` — 400G/800G 世代

---

## ハンドラ分岐なし

`BREAKOUT_CFG` テーブルは orchagent が直接購読しない。CLI (`portconfig` ライブラリ経由) が PORT テーブルを再構成し、orchagent は PORT テーブルの変更を受け取る間接フロー。BREAKOUT_CFG 自体はモード履歴管理テーブルとして機能する。
