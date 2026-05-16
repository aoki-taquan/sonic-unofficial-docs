# BREAKOUT_CFG ハードコード定数 (Phase E)

調査日: 2026-05-16
対象ページ: `docs/reference/config-db/breakout-cfg.md`

## ソースファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-config-engine/portconfig.py` | BreakoutCfg クラス・コア定数（主要定数源） |
| `sonic-utilities/config/main.py` | `config interface breakout` CLI コマンド実装 |
| `sonic-buildimage/src/sonic-config-engine/sonic-cfggen` | BREAKOUT_CFG 初期化スクリプト |

## 検出されたハードコード定数

### portconfig.py モジュール定数（L36-43）

| 定数名 | 値 | 説明 |
|--------|-----|------|
| `PORT_STR` | `"Ethernet"` | 子ポート名生成時のプレフィックス。`"Ethernet" + str(base_id + lane_id)` で名前を構築 |
| `BRKOUT_MODE` | `"default_brkout_mode"` | `hwsku.json` 内でデフォルト breakout モードを保持するキー名 |
| `CUR_BRKOUT_MODE` | `"brkout_mode"` | BREAKOUT_CFG テーブルのフィールド名（CONFIG_DB に書き込まれるキー） |
| `INTF_KEY` | `"interfaces"` | `platform.json` / `hwsku.json` 内のインターフェース定義セクションのキー名 |
| `BRKOUT_PATTERN` | `r'(\d{1,6})x(\d{1,6}G?)(\[(\d{1,6}G?,?)*\])?(\((\d{1,6})\))?'` | breakout モード文字列パースに使用する正規表現パターン |
| `BRKOUT_PATTERN_GROUPS` | `6` | `BRKOUT_PATTERN` の期待グループ数 |

### FEC 自動付与しきい値（portconfig.py L387）

| 定数 | 値 | 説明 |
|------|----|------|
| FEC 自動付与しきい値 | `50000` (Mbps) | `default_speed // lanes_per_port >= 50000` のとき `fec: rs` を PORT テーブルに自動付与。50G/lane 以上で FEC 強制 |

### subport 割り当てルール（portconfig.py L383）

| 条件 | `subport` 値 | 説明 |
|------|-------------|------|
| `total_num_ports == 1`（非分割） | `"0"` | 単一ポートは subport = 0 |
| `total_num_ports > 1`（分割） | `"1"` 〜 `"N"`（連番） | 子ポートに 1 始まりの連番を付与 |

### config/main.py 定数（L92-121）

| 定数名 | 値 | 説明 |
|--------|-----|------|
| `SONIC_CFGGEN_PATH` | `"/usr/local/bin/sonic-cfggen"` | `sonic-cfggen` スクリプトの絶対パス（breakout 初期化に使用） |
| `DEFAULT_CONFIG_DB_FILE` | `"/etc/sonic/config_db.json"` | CONFIG_DB 永続化ファイルのデフォルトパス |
| `INTF_KEY` | `"interfaces"` | `platform.json` 内インターフェース定義キー（portconfig.py と共通） |
| `PORT_SPEED` | `"speed"` | PORT テーブルの speed フィールド名 |

### breakout モード文字列フォーマット（BRKOUT_PATTERN より）

正規表現 `(\d{1,6})x(\d{1,6}G?)(\[(\d{1,6}G?,?)*\])?(\((\d{1,6})\))?` が許容するフォーマット:

| フォーマット例 | 意味 |
|--------------|------|
| `1x100G` | 1 ポート × 100G（全レーン非分割） |
| `2x50G` | 2 ポート × 50G（2 分割） |
| `4x25G` | 4 ポート × 25G（4 分割） |
| `1x100G[40G]` | 1 ポート、デフォルト 100G・代替 40G サポート |
| `2x25G(2)+1x50G(2)` | ハイブリッド分割（2x25G に 2 レーン + 1x50G に 2 レーン） |
| `1x50G(2)+2x25G(2)` | ハイブリッド分割（1x50G に 2 レーン + 2x25G に 2 レーン） |

## 特記事項

- `PORT_STR = "Ethernet"` はコード全体でハードコードされており、ポート名は常に `"EthernetN"` 形式になる。エイリアス（`etp1a` 等）は `platform.json` の `breakout_modes` リストで定義されるが、内部キーは常に `Ethernet` ベース
- `BRKOUT_PATTERN` の最大桁数制限（`\d{1,6}`）により、ポート数・速度の最大値は事実上 6 桁（999999）に制限されるが、実用上は問題ない
- FEC しきい値 `50000` Mbps（50G/lane）はコードにハードコード。将来的な 800G/lane 等への対応は要修正箇所
- `sonic-cfggen` L402-404 で `config reload` 時に `hwsku.json` の `default_brkout_mode` が BREAKOUT_CFG に書き込まれる。これにより CLI 変更が `config reload` で失われる（意図的な挙動）
