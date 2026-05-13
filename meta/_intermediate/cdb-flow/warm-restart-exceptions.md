# WARM_RESTART テーブル — 例外条件・特殊挙動

## スキーマ検証

- **`module` 列挙値**: `bgp` / `teamd` / `swss` / `system` のみ許可。それ以外は YANG バリデーションで reject[^e1]。
- **フィールドとモジュールの対応**:
  - `bgp_eoiu` / `bgp_timer`: `must "current()/../module = 'bgp'"` — bgp 以外のモジュールに設定すると `"bgp_timer is only supported for module bgp."` エラー[^e1]。
  - `teamsyncd_timer`: `must "current()/../module = 'teamd'"` — 同様[^e1]。
  - `neighsyncd_timer`: `must "current()/../module = 'swss'"` — 同様[^e1]。
- **タイマー範囲**:
  - `bgp_timer` / `teamsyncd_timer`: `1..3600`[^e1]。
  - `neighsyncd_timer`: `1..9999`[^e1]。
  - 範囲外は `"Timer must be X..Y"` エラー。

## エラー時動作

- YANG 制約違反は `sonic-yang` ライブラリが処理する。`sonic-cfggen` / `config load` の段階でエラーが発生し DB には書き込まれない。
- 各 mgr/daemon は WARM_RESTART エントリを起動時に読み込む。`enable` フラグが `true` で warm-restart が有効化された場合、`SWSS_LOG_NOTICE("warmstart state set to REPLAYED/RECONCILED")` を記録する[^e2]。

[^e1]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-warm-restart.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-warm-restart.yang>
[^e2]: `sonic-swss/cfgmgr/vlanmgr.cpp` (warmstart ロジック参照) <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vlanmgr.cpp>
