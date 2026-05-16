# AS_PATH_SET — Phase A: コード由来の暗黙デフォルト調査

調査日: 2026-05-14  
対象ページ: `docs/reference/config-db/as-path-set.md`

## 調査対象ファイル (entry grep 1回のみ)

```
sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py
sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.j2
sonic-buildimage/src/sonic-yang-models/yang-models/sonic-routing-policy-sets.yang
sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_as_path.py
```

## フィールド別 fallback パターン

### `name` (key, string)

- YANG: `key "name"` — 必須、デフォルトなし
- frrcfgd.py L2999: `as_set_name = prefix` — key から直接取得
- コード由来デフォルト: **なし**（省略不可）

### `action` (enum permit/deny)

- YANG: `type routing-policy-action-type` — デフォルトなし
- **bgpd.conf.db.j2 L16**: `bgp as-path access-list {{key}} permit {{path}}` — `action` を一切参照せず `permit` をハードコード
- **frrcfgd.py L1018**: `mbr_str = '{} permit {}'.format(as_set_name, asn)` — `action` を参照せず `permit` をハードコード
- frrcfgd.py L1977: `aspath_set_key_map = [('as_path_set_member', '{no:no-prefix}bgp as-path access-list {}', hdl_aspath_set)]` — key_map に `action` が含まれていない
- **結論: `action` フィールドは両コンシューマで完全無視。実効動作は常に `permit` 固定。**
  - `deny` を設定しても FRR には `permit` が発行される
  - YANG スキーマ定義のみ存在し、実装が追いついていない

### `as_path_set_member` (leaf-list string, ordered-by user)

- YANG: デフォルトなし、空リスト有効
- frrcfgd.py L2251: `if 'as_path_set_member' in entry:` — キーが存在しない場合は `as_path_set_list` に登録しない（スキップ）
- frrcfgd.py L3005: `as_set_data = data.get('as_path_set_member', None)` — 存在しない場合 `None`（FRR コマンドなし）
- frrcfgd.py L1016: `if op != CachedDataWithOp.OP_DELETE and len(args[1]) > 0:` — 空リストの場合 FRR push をスキップ
- bgpd.conf.db.j2 L14: `{% if 'as_path_set_member' in val %}` — キーなしはスキップ
- **結論: 省略または空リスト → FRR への `bgp as-path access-list` コマンド発行なし（エントリは存在するが機能しない）**

## まとめ

| フィールド | YANG default | コード実効デフォルト | 根拠 |
|-----------|-------------|-------------------|------|
| `name` | なし（key） | なし（必須） | frrcfgd.py L2999 |
| `action` | なし | **常に `permit` (フィールド無視)** | bgpd.conf.db.j2:16, frrcfgd.py:1018 |
| `as_path_set_member` | なし | 省略/空 → FRR push なし | frrcfgd.py:1016,2251,3005; j2:14 |

## 重要な discrepancy

`action` フィールドは YANG で `permit`/`deny` を定義しているが、frrcfgd.py および bgpd.conf.db.j2 の両実装ともに `action` を参照せず `permit` をハードコードしている。`deny` を CONFIG_DB に設定しても FRR には反映されない。
