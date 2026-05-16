# Phase A: AS_PATH_SET コード由来デフォルト調査メモ

対象ページ: `docs/reference/config-db/as-path-set.md`
調査日: 2026-05-14

## 調査ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-routing-policy-sets.yang` (L217-240)
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (L1009-1020, L2251, L2999, L3005)
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/bgpd.conf.db.j2` (L14-16)
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/bgpcfgd/managers_as_path.py` (L56, L65)

## フィールド別デフォルト

| フィールド | YANG default | コード実効デフォルト | パターン | 根拠 |
|-----------|-------------|-------------------|---------|------|
| `name` | なし（key） | なし（必須） | — | `frrcfgd.py:2999` key から直取得 |
| `action` | なし | **常に `permit`（フィールド無視）** | hardcode literal | `bgpd.conf.db.j2:16`; `frrcfgd.py:1018` |
| `as_path_set_member` | なし | 省略/空 → FRR push なし | `.get(..., None)` + `len > 0` guard | `frrcfgd.py:1016,2251,3005`; `bgpd.conf.db.j2:14` |

## 主要発見: `action` フィールドの実装乖離

`action`（`permit` / `deny`）は YANG スキーマに定義されているが、**両コンシューマで完全に無視されている**:

- `bgpd.conf.db.j2:16` — `bgp as-path access-list {{key}} permit {{path}}` と `permit` をテンプレートにハードコード。`action` キーを参照しない
- `frrcfgd.py:1018` — `'{} permit {}'.format(as_set_name, asn)` で `permit` をハードコード。`action` を key_map に含まない

結果として `action: deny` を CONFIG_DB に投入しても FRR には `bgp as-path access-list <name> permit <regex>` が発行される。`deny` として機能させることはできない（コード変更が必要）。

## `as_path_set_member` の空リスト挙動

- キーが存在しない場合: `frrcfgd.py:2251` `if 'as_path_set_member' in entry:` ガード → `as_path_set_list` に未登録
- 空リスト (`[]`) の場合: `frrcfgd.py:1016` `len(args[1]) > 0` ガード → FRR コマンド未発行
- DEL 操作時: 既存 access-list を `no bgp as-path access-list <name>` で全削除してから再作成（`frrcfgd.py:1015`）

## hard=0 確認

YANG にデフォルト値の定義なし（`leaf action` に `default` 文なし、`leaf-list as_path_set_member` に `default` 文なし）。コード側で `permit` をハードコードしているのが唯一の実効デフォルト。
