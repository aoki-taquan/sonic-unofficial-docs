# COMMUNITY_SET ハードコード定数 (Phase E)

## ソース

- `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-routing-policy-sets.yang` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-net/sonic-buildimage` `src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (同 SHA)
- `sonic-net/sonic-buildimage` `src/sonic-bgpcfgd/bgpcfgd/managers_rm.py` (同 SHA)
- `sonic-net/sonic-buildimage` `src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.comm_list.j2` (同 SHA)

---

## action フィールド enum 値 (sonic-routing-policy-sets.yang:28-39)

typedef `routing-policy-action-type`:

| enum 値 | 説明 | 行 |
|---|---|---|
| `permit` | マッチしたルートを許可 | `sonic-routing-policy-sets.yang:30` |
| `deny` | マッチしたルートを拒否 | `sonic-routing-policy-sets.yang:33` |

注: `action` フィールドは CONFIG_DB に記録されるが、`frrcfgd` の `hdl_com_set()` が FRR へ生成する community-list コマンドは常に `permit` 固定 (`frrcfgd.py:996-1006`)。CONFIG_DB に `deny` が入っていても FRR には `permit` が発行される（実質 deny は未実装）。

---

## set_type フィールド enum 値 (sonic-routing-policy-sets.yang:145-149)

| enum 値 | FRR コマンドキーワード | 説明 |
|---|---|---|
| `STANDARD` | `standard` | 数値 community (`AS:NN`) の完全一致マッチ |
| `EXPANDED` | `expanded` | 正規表現マッチ（例: `.*:100`） |

FRR コマンド生成: `set_type = args[1][0][0].lower()` → `bgp community-list {standard|expanded} <name> permit ...` (`frrcfgd.py:985-986`)。

誤設定: `EXPANDED` パターンを `STANDARD` に指定すると正規表現が数値として解釈され全件 reject。

---

## match_action フィールド enum 値 (sonic-routing-policy-sets.yang:153-158)

| enum 値 | 内部定数 (CommunityList) | FRR 生成挙動 |
|---|---|---|
| `ANY` | `MATCH_ANY = 1` (frrcfgd.py:1571) | member ごとに個別 `permit <member>` コマンドを生成 (OR 条件) |
| `ALL` | `MATCH_ALL = 0` (frrcfgd.py:1570) | 全 member を 1 行に結合した `permit <m1> <m2> ...` を生成 (AND 条件) |

`db_data_to_attr()` での変換 (`frrcfgd.py:1584-1591`): `val.lower() == 'all'` → `MATCH_ALL`、それ以外 → `MATCH_ANY`。つまり `all` / `ALL` 以外の値はすべて `MATCH_ANY` として扱われる。

---

## community_member フォーマット定数

### AS:NN 形式の数値範囲 (bgpcfgd/managers_rm.py:57-59)

`BGPRouteMapMgr` の `__set_handler_validate()` による検証:

| 条件 | 値 |
|---|---|
| フォーマット | `<AS>:<NN>` (コロン区切り2要素) |
| AS 範囲 | `range(0, 65536)` → 0〜65535 |
| NN 範囲 | `range(0, 65536)` → 0〜65535 |

### well-known community 名 (FRR vtysh 解釈、RFC1997 準拠)

FRR vtysh は以下の文字列リテラルを `bgp community-list standard` コマンドで直接受理する:

| well-known 名 | RFC 値 | 説明 |
|---|---|---|
| `no-export` | 0xFFFFFF01 (65535:65281) | IBGP / confederation 境界を超えてアドバタイズしない |
| `no-advertise` | 0xFFFFFF02 (65535:65282) | いかなる BGP ピアにもアドバタイズしない |
| `local-AS` | 0xFFFFFF03 (65535:65283) | confederation サブ AS 内のみ配布 (RFC 5065) |
| `internet` | 0x00000000 (0:0) | すべての BGP スピーカーに配布可能 |

`frrcfgd.py:998` の `' '.join(member_list)` でそのまま FRR vtysh に渡される。

---

## extended community マーカー定数 (CommunityList, frrcfgd.py:1572-1573)

`EXTENDED_COMMUNITY_SET` の `community_member` 値プレフィックス:

| 定数名 | 値 | FRR 変換後 | 行 |
|---|---|---|---|
| `CommunityList.RT_TYPE_MARK` | `'route-target:'` | `rt <value>` | `frrcfgd.py:1572` |
| `CommunityList.SOO_TYPE_MARK` | `'route-origin:'` | `soo <value>` | `frrcfgd.py:1573` |

変換ロジック: `bgpd.conf.db.comm_list.j2:32-45` でも同様に `'route-target' in cm` → `rt`、`'route-origin' in cm` → `soo` にプレフィックス変換。

---

## シーケンス番号なし

`COMMUNITY_SET` にはシーケンス番号フィールドなし（`PREFIX_LIST` と異なる）。`community_member` は `ordered-by user` leaf-list で順序を保持 (`sonic-routing-policy-sets.yang:169`)。

---

## スキャン証跡

- `frrcfgd.py:981-1007` `hdl_com_set()` 全行精読 — action/set_type/match_action の FRR コマンド生成ロジック確認
- `frrcfgd.py:1569-1603` `CommunityList` クラス全行精読 — MATCH_ALL/MATCH_ANY/RT_TYPE_MARK/SOO_TYPE_MARK 定数確認
- `bgpcfgd/managers_rm.py:54-65` `__set_handler_validate()` — community_id (AS:NN) の数値範囲検証確認
- `sonic-routing-policy-sets.yang:28-39,135-173` — routing-policy-action-type typedef / COMMUNITY_SET_LIST フィールド定義精読
- `bgpd.conf.db.comm_list.j2:1-54` 全行精読 — Jinja2 テンプレートでの permit 固定生成確認
