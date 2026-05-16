# COPP_TRAP — Phase B 書込み順依存スキャンノート

対象テーブル: `COPP_TRAP`
Consumer: `CoppMgr::doCoppTrapTask()` (`sonic-swss/cfgmgr/coppmgr.cpp`)、`CoppOrch::processCoppRule()` (`sonic-swss/orchagent/copporch.cpp`)
スキャン範囲: coppmgr.cpp 全行精読 (L1-986)、copporch.cpp L390-935 精読

---

## 検出した順序依存・タイミング依存

### 1. allPortsReady() ガード（ポート初期化先行必須）

- `CoppOrch::doTask()` L885-888: `gPortsOrch->allPortsReady()` が false の間は即 return。
- APPL_DB の `COPP_TABLE` からの全処理がブロックされる。
- PortsOrch の起動完了前に書き込まれた CONFIG_DB エントリは、ポート初期化完了後に一括処理される。
- 順序依存: `PORT` テーブルの初期化完了（PortsOrch）が COPP_TRAP より**先に**完了していること。
- evidence: `copporch.cpp:885`

### 2. COPP_GROUP が先行必須（trap_group 参照のペンディング機構）

- `CoppMgr::doCoppTrapTask()` L609: `trap_group.empty()` かつ `trap_ids.empty()` の場合、incomplete として erase して skip。
- `CoppMgr::addTrap()` L516-528 → `checkTrapGroupPending()` L62-79: 参照先 COPP_GROUP の trap_group_map に関連する trap が全て無効状態なら、APPL_DB への書き込みを保留する。
- `CoppOrch::processCoppRule()` L584: `m_trap_group_map` に対象グループが存在しない場合 `task_need_retry` を返し、次のイベントループで再試行する。
- 順序依存: `COPP_GROUP|<name>` が CONFIG_DB に存在し、CoppMgr / CoppOrch に処理済みであること。未処理の場合は COPP_TRAP の APPL_DB 書き込みが自動的に保留・リトライされる。
- evidence: `coppmgr.cpp:62-79`, `coppmgr.cpp:609`, `copporch.cpp:584`

### 3. FEATURE テーブルの先行ロード（always_enabled=false の trap）

- `CoppMgr` コンストラクタ (L327-332): 起動時に `CFG_FEATURE_TABLE` を全件ロードして `m_featuresCfgTable` に格納した後、COPP_TRAP の merge 処理を行う。
- `always_enabled` が `false`（または未設定）の trap は `isFeatureEnabled()` の結果に依存し、FEATURE テーブルが先に存在しない場合は有効化されない。
- `doFeatureTask()` L928-966: 動的な feature state 変化は即時 `setFeatureTrapIdsStatus()` で反映される。
- 順序依存: `always_enabled=false` の COPP_TRAP は `FEATURE|<trap-name>` の `state=enabled` が先に CONFIG_DB に存在することが推奨。起動時の処理順で、FEATURE テーブルが空の場合は全 non-always-enabled trap が未インストールのまま起動する。
- evidence: `coppmgr.cpp:327-332`, `coppmgr.cpp:90`, `coppmgr.cpp:173-191`

### 4. コンストラクタ内の処理順序（TRAP → GROUP）

- `CoppMgr` コンストラクタ内でのマージ順序: `mergeConfig(m_coppTrapInitCfg, ...)` (L334) → trap ループ → `mergeConfig(m_coppGroupInitCfg, ...)` (L372) → group ループ。
- **COPP_TRAP の処理（trap_id → trap_group マッピング構築）が COPP_GROUP の APPL_DB 書き込みより先に行われる**。COPP_TRAP がまず `m_coppTrapIdTrapGroupMap` を構築し、COPP_GROUP がその情報を `getTrapGroupTrapIds()` で参照して trap_ids リストを完成させる。
- 逆順では COPP_GROUP 書き込み時に trap_ids が空になる。
- 順序依存: **CONFIG_DB には COPP_GROUP より先に COPP_TRAP を書き込むのが安全**（コンストラクタ内の処理順に合致）。ただし init_cfg.json ではほぼ同時に書き込まれるため、この依存は主に動的追加時の話。
- evidence: `coppmgr.cpp:334-411`

### 5. DEL → SET 順序（trap_group 移動時の旧グループ更新）

- `doCoppTrapTask()` L706-736: trap_group を変更する SET の場合（`conf_present && trap_group != m_coppTrapConfMap[key].trap_group`）、旧グループの trap_ids を再計算して APPL_DB を更新する処理が含まれる。
- ただし変数代入の順序バグにより L724 の比較が実際に機能するかは要注意（L715-717 で先に新値を代入してから L724 で古い trap_group と比較している可能性）。
- **同一 COPP_TRAP の trap_group を変更するには DEL → SET の順序が推奨**。SET のみでも一応動作するが、旧グループの trap_ids 更新が意図通り行われない可能性がある。
- evidence: `coppmgr.cpp:706-738`

### 6. init_cfg / copp_cfg.j2 由来エントリの DEL → init_cfg 値への復元

- `doCoppTrapTask()` L769-805: `DEL_COMMAND` 受信後、`m_coppTrapInitCfg` に当該 key が存在する場合は init_cfg の値でエントリを再作成する。
- ユーザが CLI で `config copp trap del <name>` を実行しても、init_cfg 由来の trap は自動的に復元される（ユーザ設定をクリアして init に戻す意味）。
- 順序依存はないが、挙動として「DEL が完全な削除にならない」点を運用者が把握しておく必要がある。
- evidence: `coppmgr.cpp:769-805`

### 7. NULL フィールドによる明示的削除

- `doCoppTrapTask()` L580-595: SET コマンドで `NULL` フィールドを受け取った場合、既存 conf が存在すれば `removeTrap()` を呼んでからエントリを削除する。
- `mergeConfig()` L217-224: init_cfg マージ時も NULL フィールドは検出され、null_cfg フラグを立てて skip される。
- 順序依存: NULL フィールドによる SET は「delete」として機能し、後続の通常 SET が必要な場合は NULL フィールド SET → 通常 SET の順にする。
- evidence: `coppmgr.cpp:580-595`, `coppmgr.cpp:217-224`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | allPortsReady() 完了 → COPP_TRAP 処理 | 強制先行 | なし（PortsOrch 起動待ち） |
| 2 | COPP_GROUP 存在・処理済み → COPP_TRAP SET | 強制先行（自動保留・リトライ） | CoppMgr 保留キュー + CoppOrch task_need_retry |
| 3 | FEATURE state=enabled 先行 → always_enabled=false trap | 推奨先行 | 動的 feature 変化は doFeatureTask で後追い可 |
| 4 | COPP_TRAP 書込み先行 → COPP_GROUP 書込み | 推奨（コンストラクタ処理順に合致） | 同時書込み時は init_cfg の順序に依存 |
| 5 | trap_group 変更: DEL → SET | 推奨（旧グループ更新の確実性のため） | SET のみでも機能するが旧グループ更新が不安定 |
| 6 | init_cfg 由来 trap の DEL は復元される | 情報のみ（順序依存なし） | init 値への rollback が自動発生 |
| 7 | NULL フィールド SET → 通常 SET | 必須（削除→再追加のシーケンス） | NULL SET は delete として機能 |
