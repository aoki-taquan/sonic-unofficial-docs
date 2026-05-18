# BREAKOUT_CFG (DPB) — Phase E ハードコード定数調査

## 調査対象ファイル

- `sonic-utilities/config/config_mgmt.py`
- `sonic-buildimage/src/sonic-config-engine/portconfig.py`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-breakout_cfg.yang`

## 発見定数

### config_mgmt.py: MAX_WAIT = 60

```python
# config_mgmt.py:429
MAX_WAIT = 60
...
self._verifyAsicDB(db=dataBase, ports=delPorts, portMap=if_name_map, timeout=MAX_WAIT)
```

`_verifyAsicDB()` は 1 秒 sleep × timeout 回のポーリングで ASIC_DB のポート消滅を確認する。
`MAX_WAIT = 60` は `breakOutPort()` ローカル定数。設定変更不可（CLI オプションなし）。
タイムアウト超過時は `Exception("Ports are present in ASIC DB after 60 secs")` を raise して処理中断。

### portconfig.py: 文字列定数

```python
# portconfig.py:36-42
PORT_STR = "Ethernet"
BRKOUT_MODE = "default_brkout_mode"
CUR_BRKOUT_MODE = "brkout_mode"
INTF_KEY = "interfaces"
BRKOUT_PATTERN = r'(\d{1,6})x(\d{1,6}G?)(\[(\d{1,6}G?,?)*\])?(\((\d{1,6})\))?'
BRKOUT_PATTERN_GROUPS = 6
```

- `PORT_STR = "Ethernet"`: 子ポート名生成時のプレフィックス。ポート名が `Ethernet<N>` 形式であることをハードコードで仮定。
- `BRKOUT_MODE = "default_brkout_mode"`: `hwsku.json` キー名。
- `CUR_BRKOUT_MODE = "brkout_mode"`: `BREAKOUT_CFG` に書くフィールド名。
- `BRKOUT_PATTERN`: breakout mode 文字列の正規表現。`(\d{1,6})` で最大 6 桁の数値を許容。
- `BRKOUT_PATTERN_GROUPS = 6`: 正規表現グループ数検証用定数。

### YANG: brkout_mode の長さ制約

```yang
# sonic-breakout_cfg.yang:41
length 1..64;
```

`brkout_mode` フィールドの文字列長は YANG で 1〜64 文字に制限される。ポート名 (`port-name`) は 1〜255 文字。

## 結論

| 定数 | 値 | 設定可否 | ソース |
|------|----|---------|--------|
| `MAX_WAIT` | 60 秒 | 不可（ハードコード） | `config_mgmt.py:429` |
| `PORT_STR` | `"Ethernet"` | 不可 | `portconfig.py:36` |
| `BRKOUT_MODE` | `"default_brkout_mode"` | 不可 | `portconfig.py:37` |
| `CUR_BRKOUT_MODE` | `"brkout_mode"` | 不可 | `portconfig.py:38` |
| `BRKOUT_PATTERN` | 正規表現 | 不可 | `portconfig.py:42` |
| `brkout_mode` 最大長 | 64 文字 | YANG で規定 | `sonic-breakout_cfg.yang:41` |
| `port-name` 最大長 | 255 文字 | YANG で規定 | `sonic-breakout_cfg.yang:34` |
