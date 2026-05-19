# vrrp-track — Phase E ハードコード定数スキャンノート

対象テーブル: `VRRP_TRACK` / `VRRP6_TRACK`

## スキャン対象ソース

- `sonic-utilities/config/main.py` (add_track_interface L6986-7041, add_track_interface_v6 L7421-7470)
- `SONiC/doc/vrrp/sonic-vrrp.yang` (VRRP_TRACK container L135-180, VRRP6_TRACK container L255-300)
- `SONiC/doc/vrrp/VRRP_Adaptation_HLD.md` (L555-609)

## 検出した定数

### CLI スケール上限（ハードコード整数リテラル）

| 値 | 用途 | evidence |
|----|------|----------|
| `8` | 1 VRRP/VRRP6 インスタンスあたりの最大追跡インタフェース数。`count >= 8` で `ctx.fail()` | `config/main.py:7037-7038, 7465` |

### `priority_increment` パラメータ範囲とデフォルト（Click IntRange / YANG）

| 定数種別 | 値 | 定義箇所 |
|----------|-----|---------|
| CLI 下限 (`IntRange` min) | `10` | `config/main.py:6990, 7423` |
| CLI 上限 (`IntRange` max) | `50` | `config/main.py:6990, 7423` |
| CLI デフォルト | `20` | `config/main.py:6991, 7424` |
| YANG `uint8` 下限 | `1` | `sonic-vrrp.yang:174-175, 292-294` |
| YANG `uint8` 上限 | `255` | `sonic-vrrp.yang:175, 294` |

CLI と YANG の許容範囲は意図的に乖離している（CLI は運用的に安全な 10–50 に絞り、YANG は型制約の 1–255 をそのまま許容）。

### `vrid` (vrrp_id) パラメータ範囲

| 定数種別 | 値 | 定義箇所 |
|----------|-----|---------|
| CLI 下限 | `1` | `config/main.py:6988, 7421` (Click `IntRange(1, 255)`) |
| CLI 上限 | `255` | `config/main.py:6988, 7421` |
| YANG `uint8` 範囲 | `1..255` | `sonic-vrrp.yang:80-81, 208-209` |

### DB テーブル名文字列リテラル

| 文字列 | 用途 | evidence |
|--------|------|----------|
| `"VRRP_TRACK"` | CONFIG_DB テーブル名（key separator `\|` を含むフルキーは `VRRP_TRACK\|<intf>\|<vrid>\|<track_intf>`）| `config/main.py:7021, 7028, 7040, 7074, 7077` |
| `"priority_increment"` | VRRP_TRACK エントリの唯一のフィールド名 | `config/main.py:7023, 7026, 7469` |

## 結論

VRRP_TRACK テーブル固有の定数は少数で明確。`priority_increment` の CLI/YANG 乖離が最も注意を要するポイント。スケール上限 8 は YANG の `max-elements` には反映されておらず、CLI 側のリテラル整数のみで管理される。
