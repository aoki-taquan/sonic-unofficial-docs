# PREFIX_SET — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples.py / db_migrator.py / init_cfg.json.j2 に PREFIX_SET への代入なし。OpenConfig RPC 経由または CLI で明示設定。

PREFIX_SET は `sonic-mgmt-common` (gNMI / REST) 経由でのみ設定されることが多く、トランスレーションレイヤが PREFIX_LIST に変換して CONFIG_DB に書き込む場合がある。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

bgpcfgd の `main.py` には PREFIX_SET を直接購読するマネージャなし。orchdaemon 側も同様。sonic-mgmt-common の transformer が担当。

条件付き登録なし (直接登録自体なし)。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### 該当なし

PREFIX_SET は sonic-mgmt-common のトランスレーションレイヤが `PREFIX_SET` → `PREFIX_LIST` 変換を担当する。orchagent / bgpcfgd が直接処理しないため、本フェーズの handler-branching 証跡なし。

<!-- /handler-branching -->
