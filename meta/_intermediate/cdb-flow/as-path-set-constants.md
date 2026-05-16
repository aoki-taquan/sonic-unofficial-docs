# AS_PATH_SET — Phase E: ハードコード定数調査

`docs/reference/config-db/as-path-set.md` の `<!-- constants -->` ブロック生成元中間メモ。`bgpcfgd` (AsPathMgr) と `frrcfgd` (sonic-frr-mgmt-framework) の双方を全行精読し、AS_PATH_SET 処理経路に埋め込まれた固定リテラル・定数を抽出した。

## 調査対象ファイル

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_as_path.py` (全 67 行)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:32, 129` (AsPathMgr 登録箇所)
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:96, 1009-1020, 1977, 2116, 2248-2253, 2998-3011`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.j2:11-20`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-routing-policy-sets.yang:28-39, 217-240`

---

## 1. action enum 値（YANG `routing-policy-action-type`）

| enum 値 | 用途 | コード上の扱い | evidence |
|---|---|---|---|
| `permit` | リスト entry の許可アクション | 両 consumer で**唯一発行されるリテラル**（ハードコード） | `sonic-routing-policy-sets.yang:30`; `bgpd.conf.db.j2:16`; `frrcfgd.py:1018` |
| `deny` | YANG では定義済みだが … | 両 consumer で**未使用**。CONFIG_DB に投入しても無視される | `sonic-routing-policy-sets.yang:33` |

**ハードコード literal**: 両 consumer (frr-mgmt-framework / bgpcfgd 経路) が `permit` を**テンプレート/format 文字列に直接埋め込み**、`action` フィールド値を参照しない。

- `bgpd.conf.db.j2:16` — `bgp as-path access-list {{key}} permit {{path}}`
- `frrcfgd.py:1018` — `'{} permit {}'.format(as_set_name, asn)`

## 2. FRR コマンドテンプレート（コマンド文字列リテラル）

| 用途 | リテラル | ソース |
|---|---|---|
| ADD コマンド | `bgp as-path access-list {} permit {}` | `frrcfgd.py:1977` (`aspath_set_key_map`) |
| ADD コマンド (j2 経路) | `bgp as-path access-list {{key}} permit {{path}}` | `bgpd.conf.db.j2:16` |
| 全削除（pre-update） | `no bgp as-path access-list <name>` | `frrcfgd.py:1015` (cmd_str `{no:no-prefix}` + name のみ) |
| AsPathMgr ADD (t2_group_asns) | `bgp as-path access-list T2_GROUP_ASNS permit _<asn>_` | `managers_as_path.py:56` |
| AsPathMgr DEL (clear group) | `no bgp as-path access-list T2_GROUP_ASNS` | `managers_as_path.py:52, 65` |

## 3. AsPathMgr (bgpcfgd) のハードコード識別子

bgpcfgd は AS_PATH_SET テーブルではなく `DEVICE_METADATA[localhost].t2_group_asns` を見て **固定名 access-list を 1 本だけ生成**する別経路を持つ。

| 定数 | 値 | 役割 | ソース |
|---|---|---|---|
| `T2_GROUP_ASNS` | `"T2_GROUP_ASNS"` (module 級定数) | AsPathMgr が生成する固定 access-list 名 | `managers_as_path.py:7` |
| `key` フィルタ | `"localhost"` 文字列直比較 | DEVICE_METADATA の特定 key のみ処理 | `managers_as_path.py:31, 61` |
| 内部キー名 | `"t2_group_asns"` 直比較 | data dict から asns を抜く際の固定キー | `managers_as_path.py:35` |
| ASN 区切り文字 | `","` (カンマ) | `t2_group_asns` 値を split する固定区切り | `managers_as_path.py:40` |
| ASN regex format | `_<asn>_` (前後アンダースコア) | FRR 正規表現として ASN を境界付きで埋める固定パターン | `managers_as_path.py:56` |

### AsPathMgr 内 regex リテラル

```python
# managers_as_path.py:43
regex = re.compile(r"bgp as-path access-list T2_GROUP_ASNS seq \d+ permit _(\d+)_")
```

- 抽出対象 access-list 名は `T2_GROUP_ASNS` のみハードコード（他名は無視）
- `seq <数>` を期待する点で FRR 出力形式に強く依存（FRR バージョン差で破綻リスクあり）
- ASN 部は `(\d+)` のみ。AS path regex full syntax は未対応 — `_<digit>+_` 形式以外は再同期できない

## 4. frrcfgd 経路のハードコード識別子

| 定数 / リテラル | 値 | 役割 | ソース |
|---|---|---|---|
| daemon バインド | `'bgpd'` | AS_PATH_SET は bgpd デーモンのみへ送信 | `frrcfgd.py:96` (`'AS_PATH_SET': ['bgpd']`) |
| 必須引数下限 | `len(args) < 2` で None 返却 | as-set 名 + メンバ列が揃わない場合は FRR push 抑止 | `frrcfgd.py:1010-1011` |
| 空リストガード | `len(args[1]) > 0` | `as_path_set_member` 空 → ADD コマンド未発行（先行 DEL のみ実行される場合あり） | `frrcfgd.py:1016` |
| 初期スキャン条件 | `'as_path_set_member' in entry` | スタートアップ時、メンバキーを持つ entry のみ `as_path_set_list` に登録 | `frrcfgd.py:2251` |

## 5. YANG 側の数値・長さ上限

| 項目 | 値 | 備考 |
|---|---|---|
| `name` 型 | `string` (length / pattern 制約なし) | 上限規定なし |
| `as_path_set_member` 型 | `string` (length / pattern 制約なし) | 上限規定なし — FRR 側で検証 |
| エントリ件数上限 | YANG / コード両方で**未定義** | `aspath_set_key_map` / `as_path_set_list` は dict で無制限 |
| 正規表現長上限 | YANG / SONiC 側で**未定義** | FRR `bgpd` の内部上限に依存（SONiC からは制御不能） |

**ハードコード上限なし**: regex 上限、メンバ数上限、エントリ数上限はいずれも SONiC レイヤでは未設定。`bgpd` プロセスの内部メモリ・パーサ上限が事実上の天井となるが、SONiC コードには定数として現れない。

## 6. 暗黙デフォルト（コード強制）

| フィールド | YANG default | 実効デフォルト | パターン |
|---|---|---|---|
| `action` | なし | **常に `permit`（フィールド無視）** | 両経路でリテラル hardcode |
| `as_path_set_member` | なし | 省略/空 → FRR push なし | `.get(..., None)` + `len > 0` guard |
| `name` | なし（key 必須） | 必須 | key parse のみ |

---

## 特記事項（discrepancy / 注意）

1. **`action: deny` は完全無視 (DISCREPANCY)** — YANG 上は `permit`/`deny` の enum だが、`bgpd.conf.db.j2:16` と `frrcfgd.py:1018` の双方で `permit` リテラルがハードコードされている。`deny` を発行する経路がコード上**存在しない**。
2. **AsPathMgr は AS_PATH_SET テーブルを購読しない** — bgpcfgd の `AsPathMgr` は AS_PATH_SET ではなく `DEVICE_METADATA` の `t2_group_asns` を読み、固定名 `T2_GROUP_ASNS` で 1 本だけ access-list を作る。AS_PATH_SET テーブルの主たる consumer は frr-mgmt-framework (`frrcfgd`)。
3. **regex 上限は SONiC 側にない** — メンバ正規表現の長さ・件数上限はコードで強制されない。FRR `bgpd` プロセスの内部上限に依存。運用上、長大 regex は `vtysh` レスポンス遅延の原因になりうる。
4. **AsPathMgr の FRR 出力パース** — `r"bgp as-path access-list T2_GROUP_ASNS seq \d+ permit _(\d+)_"` という固定 regex で FRR 既存設定を再同期する。FRR の `show running` 出力フォーマットが変わると同期破綻する脆い依存がある。
5. **全置換挙動** — frrcfgd は UPDATE 時に「先に `no bgp as-path access-list <name>` で全削除 → 再 ADD」のシーケンスを取る (`frrcfgd.py:1015-1019`)。差分追加はせず常に全置換。短時間ながら access-list 不在の窓が空く。

---

## スキャン証跡

- `managers_as_path.py` 全 67 行精読
- `frrcfgd.py` AS_PATH_SET 関連箇所 (96, 1009-1020, 1977, 2116, 2248-2253, 2998-3011) 精読
- `bgpd.conf.db.j2` AS_PATH_SET ブロック (11-20) 精読
- `sonic-routing-policy-sets.yang` AS_PATH_SET / action enum 定義部 (28-39, 217-240) 精読

定数抽出: action enum 2 件、コマンド literal 5 件、AsPathMgr ハードコード 5 件 + regex 1 件、frrcfgd ガード 4 件、暗黙デフォルト 3 件、合計 20 件。SONiC レイヤの数値上限は 0 件（FRR 委譲）。
