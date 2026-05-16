# AS_PATH_SET — Phase B 書込み順依存 調査メモ

対象ページ: `docs/reference/config-db/as-path-set.md`
調査日: 2026-05-15

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_as_path.py` | `AsPathMgr` — DEVICE_METADATA.t2_group_asns 経由の固定名 `T2_GROUP_ASNS` 書込経路 |
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py` | `AsPathMgr` の起動 gate（DEVICE_METADATA.type/subtype 依存） |
| `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | `BGPConfigDaemon` — AS_PATH_SET SET/DEL ハンドラ本体 |
| `sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.j2` | bgpd 起動時 AS_PATH_SET レンダリング順 |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-map.yang` | `match_as_path` leafref 制約（ROUTE_MAP → AS_PATH_SET） |

---

## 検出した書込み順依存

### 1. AS_PATH_SET → ROUTE_MAP（leafref 連動）

`sonic-route-map.yang:263-268` で `ROUTE_MAP.match_as_path` は AS_PATH_SET の `name` を指す leafref:

```yang
leaf match_as_path{
    type leafref {
        path "/rpolsets:sonic-routing-policy-sets/rpolsets:AS_PATH_SET/rpolsets:AS_PATH_SET_LIST/rpolsets:name";
    }
}
```

YANG validation 段で参照先 AS_PATH_SET エントリが存在しない `ROUTE_MAP|<name>|<seq>` の CONFIG_DB 投入は弾かれる（sonic-mgmt-framework 経路）。`config_db.json` 直書き / `sonic-db-cli` 経由では YANG 検証を素通りするが、`frrcfgd` は ROUTE_MAP の `match as-path <name>` を FRR に送る一方、AS_PATH_SET 未登録だと FRR `bgpd` 側で「未定義 access-list を match に指定」と扱われ、ヒットしないルール (FRR の挙動) となる。

- **順序制約**: `AS_PATH_SET|<name>` (`as_path_set_member` 含む SET) → `ROUTE_MAP|<rm>|<seq>` (`match_as_path: <name>`)
- 逆順で書くと: YANG 経路では reject、直書き経路では FRR 上で常時 unmatch (silent skip)
- evidence: `sonic-route-map.yang:263-268`; `frrcfgd.py:1940` (`match_as_path` → `match as-path {}` テンプレ)

### 2. AS_PATH_SET エントリ単体での UPDATE は全置換（短時間の不在窓）

`hdl_aspath_set()` (`frrcfgd.py:1009-1020`) は SET / UPDATE / DEL いずれでも、まず既存登録があれば `no bgp as-path access-list <name>` を発行（L1014-1015）してから、続けて全メンバを `permit <regex>` で再追加（L1016-1019）する。

```python
if as_set_name in daemon.as_path_set_list:
    cmd_list.append(cmd_str.format(...no = ...False))  # no bgp as-path access-list <name>
if op != CachedDataWithOp.OP_DELETE and len(args[1]) > 0:
    for asn in args[1]:
        mbr_str = '{} permit {}'.format(as_set_name, asn)
        cmd_list.append(...)
```

- **順序制約**: 差分追加なし、常に「全 no → 全 permit」シーケンス
- **副作用**: vtysh コマンドの実行間（同一 `configure terminal` セッション内なので原子に近いが、bgpd 内部で行ごとに評価される）に短時間 access-list が「存在しない」状態が生じる。その間に ROUTE_MAP `match as-path` ヒット判定が走るとマッチ条件不成立扱いになる
- evidence: `frrcfgd.py:1009-1020, 3008-3011`

### 3. 起動時の AS_PATH_SET → ROUTE_MAP 順（bgpd.conf.db.j2 のテンプレ順）

`bgpd.conf.db.j2` のレンダリング順 (L1-30):

```
include bgpd.conf.db.pref_list.j2          # PREFIX_LIST
include bgpd.conf.db.route_map.j2          # ROUTE_MAP  ← 順序に注意 (後述)
AS_PATH_SET ループ (L11-20)                # AS_PATH_SET
include bgpd.conf.db.comm_list.j2          # COMMUNITY_SET
BGP_GLOBALS ループ (L24-)                  # router bgp
```

`bgpd.conf.db.route_map.j2` が `bgpd.conf.db.j2` の AS_PATH_SET ブロック (L11-20) **より先** に include されている (L9 vs L11-20)。bgpd は設定ファイルを逐行評価するため、起動時 `route-map ... match as-path <name>` が先に登場し、`bgp as-path access-list <name> permit <regex>` は後から追加される構造になる。

FRR `bgpd` の vtysh 解析仕様により未定義 access-list を match に指定したルールは「未定義参照」として保持され、後段で `bgp as-path access-list <name> permit ...` が登場した時点で実質有効化される（bgpd 内部の遅延解決）。それでも:

- **起動時の挙動**: bgpd 起動直後 `route-map ... match as-path` が評価されてから AS_PATH_SET 登録までの間、対象 route-map はマッチしない状態になる窓がある
- **緩和**: `frr-reload` ではなく `vtysh reload` を使う場合、L11-20 の順序は変更されないので運用上は無視される程度の窓
- evidence: `bgpd.conf.db.j2:6-20`

### 4. bgpd デーモン起動順（frrcfgd → bgpd の前提）

`frrcfgd.py:96` で `AS_PATH_SET` は `['bgpd']` にバインドされる:

```python
'AS_PATH_SET': ['bgpd'],
```

`frrcfgd` は vtysh 経由で bgpd に対してコマンドを送出するため、bgpd プロセス未起動時の SET は失敗する（vtysh が socket open 失敗 → コマンド drop → syslog ERR + continue、再試行なし — Phase A `ops-hint` 参照）。

- **順序制約**: `bgpd` 起動完了 → `frrcfgd` の AS_PATH_SET ハンドラ呼出
- **実装的保証**: `docker-fpm-frr` 内で bgpd は frrcfgd より早く起動（supervisord 順序）。ただしホストリブート直後の極短時間に CONFIG_DB へ書き込まれた AS_PATH_SET は、frrcfgd の `init_config_db()` (L2248-2253) で「設定済み一覧」としてキャッシュされ、後段の `bgp_table_handler_common` 経路で再送される — つまり起動順そのものは frrcfgd 内部キャッシュにより吸収される
- evidence: `frrcfgd.py:96, 2248-2253`

### 5. AsPathMgr (bgpcfgd) — DEVICE_METADATA → t2_group_asns → 固定 `T2_GROUP_ASNS`

`AsPathMgr` は `AS_PATH_SET` テーブルではなく `DEVICE_METADATA|localhost|t2_group_asns` を購読し、固定名 `T2_GROUP_ASNS` で 1 本だけ access-list を生成する別経路 (`managers_as_path.py:30-66`)。

#### 5-1. 起動 gate（`main.py:122-130`）

```python
device_metadata = config_db.get_table("DEVICE_METADATA")
is_upstream_lc = (... type=="SpineRouter" and subtype=="UpstreamLC")
is_upper_spine_router = (... type=="UpperSpineRouter")
if is_upstream_lc or is_upper_spine_router:
    managers.append(AsPathMgr(...))
```

`bgpcfgd` プロセス起動時の DEVICE_METADATA スナップショットで判定される。起動後に `type/subtype` を変更しても、bgpcfgd 再起動が無い限り AsPathMgr は (起動しない / 止まらない)。

- **順序制約**: DEVICE_METADATA.type/subtype 設定 → bgpcfgd 起動 → AsPathMgr 有効化 → `t2_group_asns` SET 反映
- evidence: `main.py:122-130`

#### 5-2. FRR 既存設定の読み戻し依存（`managers_as_path.py:43-49`）

```python
regex = re.compile(r"bgp as-path access-list T2_GROUP_ASNS seq \d+ permit _(\d+)_")
self.cfg_mgr.update()
for line in self.cfg_mgr.get_text():
    match = regex.match(line)
    ...
```

`AsPathMgr.set_handler` は FRR `running-config` を読み戻して既存 ASN を差分計算する。`cfg_mgr.update()` が FRR から最新 config を取得していない段階で SET が来ると、差分が正しく取れない（古いキャッシュに対する差分計算）。

- **順序制約**: bgpd 起動完了 → cfg_mgr に FRR 設定取得 → `t2_group_asns` SET 処理
- **脆弱性**: regex がリテラル `T2_GROUP_ASNS` `seq \d+ permit _(\d+)_` に強く依存するため、ユーザが手で `AS_PATH_SET|T2_GROUP_ASNS` を書くと AsPathMgr 経路と衝突する可能性あり（後述 #6）
- evidence: `managers_as_path.py:43-49`

### 6. AsPathMgr と frrcfgd AS_PATH_SET 経路の名前空間衝突

`AsPathMgr` が生成する固定名は `T2_GROUP_ASNS`。ユーザが `AS_PATH_SET|T2_GROUP_ASNS` を CONFIG_DB に書き込むと、frrcfgd 経路と AsPathMgr 経路の両方が同名 access-list を取り合う:

- frrcfgd の `hdl_aspath_set` は SET 毎に `no bgp as-path access-list T2_GROUP_ASNS` で全削除 (L1014-1015)
- AsPathMgr は次回 `set_handler` 呼出時に FRR の `running-config` から消えた ASN を「削除済み」と誤認 → 全再追加

両者の書き込みは互いに無効化しあい、最後に書いた方が一時的に勝つだけで安定しない。

- **順序制約**: ユーザ AS_PATH_SET 名は `T2_GROUP_ASNS` を**避ける**こと（運用上の名前衝突回避）
- evidence: `managers_as_path.py:7, 43, 52, 56, 65`; `frrcfgd.py:1014-1015`

### 7. AS_PATH_SET DEL → ROUTE_MAP `match as-path` の後始末

AS_PATH_SET を DEL すると `frrcfgd` は `no bgp as-path access-list <name>` を発行する (`frrcfgd.py:3008-3009`)。一方、ROUTE_MAP の `match_as_path: <name>` は CONFIG_DB に残ったまま。FRR `bgpd` 側では match 条件が「未定義 access-list 参照」になり、評価時にマッチ不成立。

- **推奨順序**: `ROUTE_MAP|<rm>|<seq>` の `match_as_path` フィールドを **先に DEL（または別名へ swap）** → `AS_PATH_SET|<name>` DEL
- 逆順でも CONFIG_DB / FRR は壊れないが、ROUTE_MAP は silent skip 状態のまま放置される
- evidence: `frrcfgd.py:1940, 3008-3009`; `sonic-route-map.yang:263-268`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `AS_PATH_SET|<name>` SET → `ROUTE_MAP|...|match_as_path:<name>` SET | 強制先行 (YANG leafref / FRR silent skip) | なし。順序遵守 |
| 2 | UPDATE 時は「全 no → 全 permit」シーケンス | 原子的でないが同一 vtysh セッション | メンテ窓・低トラフィック時に実施 |
| 3 | bgpd 起動時テンプレ順: ROUTE_MAP → AS_PATH_SET | bgpd 内部の遅延解決で吸収（窓あり） | 起動時のみの一過性、運用無視可 |
| 4 | bgpd 起動完了 → frrcfgd AS_PATH_SET ハンドラ | supervisord で保証 + frrcfgd init キャッシュで吸収 | なし |
| 5 | DEVICE_METADATA.type/subtype 設定 → bgpcfgd 再起動 → AsPathMgr 起動 → t2_group_asns SET | 強制先行（起動 gate） | type/subtype 変更後 bgpcfgd 再起動 |
| 6 | AS_PATH_SET 名 `T2_GROUP_ASNS` は予約（AsPathMgr が独占） | 名前衝突回避（運用ルール） | ユーザ AS_PATH_SET 名から除外 |
| 7 | ROUTE_MAP の `match_as_path` DEL → AS_PATH_SET DEL | 推奨（FRR silent skip 防止） | 逆順でも DB 整合性は壊れない |

---

## 評価サマリ

- **強制順序**: #1, #5（破ると意図通りに動かない）
- **同期性緩和（実装で吸収）**: #3, #4
- **運用ルール**: #2, #6, #7
- **競合経路**: AsPathMgr (T2_GROUP_ASNS 固定経路) と frrcfgd (一般 AS_PATH_SET) は別テーブル購読・同一 FRR 名前空間。`T2_GROUP_ASNS` 名は予約済み扱い
