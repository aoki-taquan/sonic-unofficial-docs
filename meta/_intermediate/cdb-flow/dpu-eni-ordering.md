# DPU / ENI / VDPU / REMOTE_DPU — Phase B 書込み順依存スキャンノート

対象ページ: `docs/reference/config-db/dpu-eni.md`
対象テーブル: `CONFIG_DB`
  - `DPU`
  - `REMOTE_DPU`
  - `VDPU`
  - `DPUS`
  - `APPL_DB: DASH_ENI_FORWARD_TABLE`
Producer/Consumer: `DashEniFwdOrch` (`sonic-swss/orchagent/dash/dashenifwdorch.cpp`)
スキャン範囲: `DpuRegistry::populate()` / `processDpuTable()` / `processRemoteDpuTable()` / `processVdpuTable()` / `DashEniFwdOrch::lazyInit()` / `addOperation()` / `initLocalEndpoints()` / `handleNeighUpdate()` / `EniFwdCtxBase::createAclRule()` / `deleteAclRule()` / `addAclTable()` の全行精読

---

## 検出した順序依存・タイミング依存

### 1. lazyInit() — 最初の DASH_ENI_FORWARD_TABLE エントリ到着で DPU テーブルを一括読込

- `DashEniFwdOrch::addOperation()` は処理冒頭で `lazyInit()` を呼ぶ (`dashenifwdorch.cpp:150`)。
- `lazyInit()` 内で `ctx->populateDpuRegistry()` → `DpuRegistry::populate()` が実行され、`DPU` / `REMOTE_DPU` / `VDPU` の 3 テーブルを一括スナップショット読込する。
- **順序依存（強制先行）**: `DASH_ENI_FORWARD_TABLE` エントリが到着するより前に `DPU` / `REMOTE_DPU` テーブルが CONFIG_DB に存在していなければ、`DpuRegistry` が空のまま ENI が登録される。この場合 ACL ルールは「DPU が見つからず redirect 先なし」として生成失敗する。
- evidence: `dashenifwdorch.cpp:131-146`, `dashenifwdorch.cpp:150`

### 2. DPU → REMOTE_DPU → VDPU の固定処理順

- `DpuRegistry::populate()` は `processDpuTable()` → `processRemoteDpuTable()` → `processVdpuTable()` をこの順で呼ぶ (`dashenifwdorch.cpp:218-220`)。
- `processVdpuTable()` は `main_dpu_ids` に含まれる DPU 名を `dpus_name_map_` (processDpuTable / processRemoteDpuTable が構築する) に問い合わせる (`dashenifwdorch.cpp:331-339`)。
- **順序依存（強制）**: `VDPU` を先に投入しても、`DPU` / `REMOTE_DPU` が `dpus_name_map_` に存在しなければ `SWSS_LOG_WARN("Invalid DPU ID")` でその DPU がスキップされる。DpuRegistry 構築は起動時 1 回かぎりなので、スキップされた DPU は動的には回復しない（再起動が必要）。
- evidence: `dashenifwdorch.cpp:330-339`

### 3. Neighbor 解決 → LOCAL DPU への ACL ルール生成

- `lazyInit()` 完了後に `initLocalEndpoints()` が呼ばれ、LOCAL DPU の `pa_ipv4` を `neigh_dpu_map_` に登録し、`ctx->resolveNeighbor()` でネクストホップ解決をリクエストする (`dashenifwdorch.cpp:78-104`)。
- Neighbor が未解決 (`isNeighborResolved()` が偽) のうちに ENI ADD が来ると、ACL ルールの `redirect` アクションに使う OID が確定せず、ルールが**インストールされない**。
- Neighbor が Up 通知されると `handleNeighUpdate()` が呼ばれ (`dashenifwdorch.cpp:31-46`)、`dpu_eni_map_` を介して影響する ENI を特定し `eni_itr->second.update(update)` で ACL ルールを再評価する。
- **順序依存**: LOCAL DPU 向け ENI の ACL ルールは、必ず「Neighbor Up 通知後」に確定する。Neighbor が Down 状態のままでは ACL ルールは存在しない（インストールされない）。
- evidence: `dashenifwdorch.cpp:48-76`, `dashenifwdorch.cpp:78-104`

### 4. ACL TABLE → ACL RULE の先行生成

- `EniFwdCtxBase::createAclRule()` は `acl_rule_count_ == 0` のとき (最初のルール追加時のみ) `addAclTable()` を呼んでから ACL ルールを `rule_table_->set()` する (`dashenifwdorch.cpp:576-583`)。
- `addAclTable()` は `APPL_DB: ACL_TABLE_TYPE_TABLE` → `APPL_DB: ACL_TABLE_TABLE` の順で ProducerStateTable に書き込む (`dashenifwdorch.cpp:625-643`)。
- **順序依存**: ENI ごとに最初の ACL ルールが作成される際には必ず ACL TABLE が先行して APPL_DB に書かれる。AclOrch はテーブルを先に受理しないとルールを処理できないため、この順序は必須。
- evidence: `dashenifwdorch.cpp:576-601`, `dashenifwdorch.cpp:603-650`

### 5. ACL TABLE の削除は最後の ACL RULE 削除後に自動実施

- `EniFwdCtxBase::deleteAclRule()` は `acl_rule_count_` が 0 になったとき `deleteAclTable()` を自動呼び出しし、`ACL_TABLE_TABLE` と `ACL_TABLE_TYPE_TABLE` を APPL_DB から削除する (`dashenifwdorch.cpp:585-600`)。
- **順序依存（逆方向）**: ENI を全削除しても、ルールが 1 件でも残っている間は ACL TABLE は存在し続ける。全 ENI の最後の ACL ルールが `deleteAclRule()` で削除されて初めて、TABLE が削除される。
- evidence: `dashenifwdorch.cpp:585-601`, `dashenifwdorch.cpp:646-650`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `DPU` / `REMOTE_DPU` 存在 → `DASH_ENI_FORWARD_TABLE` 到着 | **強制先行** | ENI より前に DPU テーブルを投入すること。後から DPU を投入しても動的には反映されない (再起動が必要) |
| 2 | `DPU` / `REMOTE_DPU` 登録 → `VDPU` populate | **強制先行** | `processVdpuTable()` は `dpus_name_map_` を参照するため、DPU/REMOTE_DPU が先に読まれていなければ VDPU が空になる |
| 3 | LOCAL DPU の Neighbor Up → ACL ルール確定 | 非同期（イベント駆動） | `NeighOrch` に attach してイベント受信。Neighbor Down 中は ACL ルールなし。Up 通知後に自動再評価 |
| 4 | `ACL_TABLE_TABLE` 先行書込み → `ACL_RULE_TABLE` 書込み | **強制先行** | 最初の ENI ADD 時に `addAclTable()` を自動実行。AclOrch がテーブルを先に受理するまでルールはキューで待機 |
| 5 | 全 ACL ルール削除 → `ACL_TABLE_TABLE` 削除 | 逆順（最後に自動） | `acl_rule_count_` が 0 になったとき `deleteAclTable()` が自動呼び出し |

---

## ページ反映方針

- `<!-- ordering -->` ブロックを既存の「購読者」セクションの直前に挿入する。
- サマリ表 + 主要制約の散文（依存 #1, #2, #3 を主軸）を含める。
- 既存の `<!-- defaults -->` / `<!-- cdb-mermaid -->` / `<!-- cdb-exceptions -->` / `<!-- value-behavior -->` / `<!-- ref-triangle -->` / `<!-- ops-hint -->` ブロックは触らない。
