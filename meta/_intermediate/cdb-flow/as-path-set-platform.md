# AS_PATH_SET — Phase H: プラットフォーム / SAI 差分

## 結論

**ASIC 種別・ベンダー・VOQ chassis / multi-asic 構成に対して AS_PATH_SET テーブルの値が分岐するロジックは存在しない**。AS_PATH_SET は FRR (`bgpd`) 制御プレーン上の AS path access-list で、SAI 非経由。サブスクライバ (`frrcfgd` / `bgpcfgd` の `AsPathMgr`) のロジックを全行精読しても、`platform` / `asic` / `switch_type` / `chassis` / `sub_role` / `namespace` で条件分岐するコード経路は無い。

ただし「AS_PATH_SET テーブル」と関連する **`AsPathMgr` (bgpcfgd) の有効化条件** には `DEVICE_METADATA.type` / `subtype` による「トポロジー role」の前段 gate が存在する。これは ASIC や HW プラットフォームではなく**論理 role**による分岐である点に注意。

---

## 1. AS_PATH_SET テーブルのコンシューマと platform 条件

| コンシューマ | 経路 | platform/asic 分岐 | 根拠 |
|------------|------|------------------|------|
| `frrcfgd` (sonic-frr-mgmt-framework) | `AS_PATH_SET` テーブル購読 → FRR `bgp as-path access-list` 発行 | **なし** | `frrcfgd.py:96, 1009-1020, 1977, 2116, 2248-2253, 2998-3011` を全 grep。`platform` / `asic` / `chassis` / `namespace` / `switch_type` / `sub_role` の参照 0 ヒット |
| `bgpcfgd` `AsPathMgr` (managers_as_path.py) | `DEVICE_METADATA.localhost.t2_group_asns` 購読 → `T2_GROUP_ASNS` 固定名で access-list 生成 | **なし**（マネージャ内部に分岐なし） | `managers_as_path.py` 全 67 行。`platform` / `asic` / `chassis` / `switch_type` / `sub_role` / `namespace` 参照 0 ヒット |
| Jinja2 テンプレート `bgpd.conf.db.j2` | AS_PATH_SET → 静的 FRR config 生成 | **なし** | `dockers/docker-fpm-frr/frr/bgpd/templates/bgpd.conf.db.j2:11-20` で AS_PATH_SET 部に platform 条件文 (`{% if %}`) 0 |

### grep 証跡

```text
$ grep -nE "platform|asic|switch_type|chassis|sub_role|namespace|vendor" \
    src/sonic-bgpcfgd/bgpcfgd/managers_as_path.py
(no matches)

$ grep -nE "platform|asic|switch_type|chassis|sub_role|namespace|vendor" \
    src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py | grep -iE "as.?path"
(no matches in AS_PATH_SET handler regions: L96, L1009-1020, L1977, L2116, L2248-2253, L2998-3011)
```

---

## 2. AsPathMgr の **登録条件** — トポロジー role による gate

AS_PATH_SET テーブル自身ではなく、`bgpcfgd` の `AsPathMgr` (T2_GROUP_ASNS 固定経路) は `main.py` L122-130 で次の役割を持つホストでのみ起動する:

| `DEVICE_METADATA.localhost` | AsPathMgr 起動 | 根拠 |
|---|---|---|
| `type == "SpineRouter"` かつ `subtype == "UpstreamLC"` | はい | `main.py:124-125` (`is_upstream_lc`) |
| `type == "UpperSpineRouter"` | はい | `main.py:126-127` (`is_upper_spine_router`) |
| 上記以外 (ToRRouter / LeafRouter / SpineChassisFrontendRouter / type 未設定…) | いいえ | `main.py:128-130` |

これは:

- **ASIC・HW プラットフォーム判定ではなく論理 role**（minigraph で決まる）
- T2 group ASN 経路（DEVICE_METADATA.t2_group_asns → `T2_GROUP_ASNS` access-list）にのみ影響
- ユーザが `AS_PATH_SET|<name>` を CONFIG_DB に直接入れる経路（frrcfgd 側）には**影響しない**

AS_PATH_SET テーブルの user-facing 動作は **role に関わらず常時 frrcfgd 経由で FRR に反映される**。

---

## 3. multi-asic / namespace の扱い

frrcfgd は per-namespace で 1 インスタンスずつ起動する（multi-asic 環境では `asicN` namespace ごとに独立した FRR インスタンスを持つ標準パターン）。ただし AS_PATH_SET ハンドラ内部に namespace 個別分岐は無く、各 namespace は自分の CONFIG_DB → 自分の FRR (`bgpd`) に同一ロジックで反映する。**「ホスト全体で 1 つの AS_PATH_SET を chassis 全体に伝播する」機構は存在しない**。

VoQ chassis / chassis-packet においても AS_PATH_SET 自体の振る舞いに差は無い（差が出るのは BGP_NEIGHBOR 側の next-hop-self / Loopback4096 update-source 等のテンプレ分岐であり、AS_PATH_SET には伝播しない）。

---

## 4. SAI 到達パスへの影響

AS_PATH_SET は **FRR `bgpd` プロセス内部の AS path access-list** として消費される。ROUTE_MAP の `match as-path` から参照され、BGP 経路選択時にフィルタとして働くが、

- APPL_DB への直接書き込み無し
- orchagent / syncd 介在無し
- SAI 経由無し

したがって ASIC 種別 (Broadcom / Mellanox / Marvell / Innovium / VPP) による下流挙動の差はゼロ。AS_PATH_SET によって受け入れ拒否された BGP 経路が **そもそも FIB に到達しない** ことで間接的に SAI 入力が変わるが、これは「プラットフォーム差」ではなく「policy 差」。

---

## 5. ベンダー hook / image_config 差分

```text
$ grep -RniE "as.?path.?set|aspath_set" files/image_config/ files/build_templates/
(no matches)
```

ベンダー固有 image_config / build_template 内に AS_PATH_SET に介入するファイルは無い。

---

## 6. 結果サマリ

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell / Innovium / VPP) | 影響なし | SAI 非経由 (FRR `bgpd` 内部 access-list) |
| multi-asic (`asicN` namespace) | 各 namespace 独立、ロジック同一 | frrcfgd は per-namespace 起動、AS_PATH_SET ハンドラに namespace 分岐なし |
| VOQ chassis / chassis-packet (`switch_type`) | 影響なし | `managers_as_path.py` / `frrcfgd.py` (AS_PATH_SET handler) で `switch_type` 参照 0 |
| `sub_role` (FrontEnd / BackEnd) | 影響なし | 同上で `sub_role` 参照 0 |
| `DEVICE_METADATA.type` / `subtype` | **AsPathMgr (T2_GROUP_ASNS 経路) の起動 gate のみ**。AS_PATH_SET テーブル自身には影響しない | `main.py:122-130` |
| ベンダー固有 hook | なし | `files/image_config/` / `files/build_templates/` に AS_PATH_SET 関連注入箇所 0 |
| テンプレート内分岐 (`bgpd.conf.db.j2`) | プラットフォーム条件なし | AS_PATH_SET 部の `{% if %}` 0 |

---

## ソース証跡

| ファイル | 行 | 内容 |
|---------|----|------|
| `src/sonic-bgpcfgd/bgpcfgd/main.py` | L122-130 | `is_upstream_lc` / `is_upper_spine_router` gate (役割 role による登録条件) |
| `src/sonic-bgpcfgd/bgpcfgd/managers_as_path.py` | L1-67 (全) | AsPathMgr 本体。platform/asic 分岐 0 |
| `src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | L96, L1009-1020, L1977, L2116, L2248-2253, L2998-3011 | AS_PATH_SET ハンドラ群。platform/asic 分岐 0 |
| `dockers/docker-fpm-frr/frr/bgpd/templates/bgpd.conf.db.j2` | L11-20 | AS_PATH_SET → FRR config 生成テンプレ。platform 条件 0 |
