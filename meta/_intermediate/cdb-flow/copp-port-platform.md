# COPP port-binding (genetlink フィールド) — Phase H プラットフォーム差分析

中間ファイル。最終成果は `docs/reference/config-db/copp-port.md` の `<!-- platform -->` ブロックに反映済み。

対象ページ: `docs/reference/config-db/copp-port.md`
対象フィールド: `COPP_GROUP.genetlink_name` / `COPP_GROUP.genetlink_mcgrp_name`
スキャン範囲: `copporch.cpp` L657-714 (createGenetlinkHostIf/removeGenetlinkHostIf), L419-493 (createGenetlinkHostIfTable), L1265-1286 (getAttribsFromTrapGroup), `coppmgr.cpp` L82-106 (setFeatureTrapIdsStatus), `copp_cfg.j2` L131-134

## 分析対象ソース

- `sonic-swss/orchagent/copporch.cpp` (`createGenetlinkHostIf` L657-679, `doTask` L880-934, `getAttribsFromTrapGroup` L1154-1295)
- `sonic-swss/orchagent/copporch.h` (genetlink フィールド定数 L44-46)
- `sonic-swss/orchagent/orch.h` (`MLNX_PLATFORM_SUBSTRING` / `MRVL_PRST_PLATFORM_SUBSTRING` 定義 L41-42)
- `sonic-swss/cfgmgr/coppmgr.cpp` (`setFeatureTrapIdsStatus` L82-106)
- `sonic-buildimage/files/image_config/copp/copp_cfg.j2` (sflow COPP_TRAP L131-134)

## 検出したプラットフォーム差

### 1. SAI `SAI_HOSTIF_TYPE_GENETLINK` サポート

`createGenetlinkHostIf()` 内の `sai_hostif_api->create_hostif()` に `SAI_HOSTIF_TYPE_GENETLINK` を渡す (`copporch.cpp:664-667`)。SAI 実装がこの HostIf 型をサポートしない場合、`create_hostif()` は `SAI_STATUS_NOT_SUPPORTED` 等を返す。`handleSaiCreateStatus()` (L669-675) が `false` を返し、呼び出し元の `processCoppRule()` が `task_failed` を返す。

コード内に platform 条件分岐は存在しない（mellanox/marvell 分岐なし）。SAI 実装側のサポート有無のみで動作が決まる。

証跡: `copporch.cpp:657-679`

### 2. カーネル psample モジュール依存

genetlink HostIf の名前として `"psample"` が使われる。カーネルが `psample` モジュールをロードしていない場合、SAI 側では `create_hostif()` が成功して HostIf オブジェクトが作成されるが、カーネル側の genetlink ソケットが存在しないためパケット転送が行われない。これは SAI/orchagent 側には検知されない（silent failure）。

SONiC 標準イメージ (sonic-buildimage) は kernel config で `psample` を有効化しているが、カスタムカーネルや一部ベンダーイメージでは手動ロードが必要な場合がある。

### 3. `FEATURE|sflow` 状態とプラットフォームの組み合わせ

`copp_cfg.j2:131-134` で `sflow` COPP_TRAP が定義されており、`is_always_enabled` は未設定（デフォルト `false`）。`FEATURE|sflow` が無効の場合、`setFeatureTrapIdsStatus("sflow", false)` 経由で `sample_packet` trap が `queue2_group1` の `trap_ids` から除外される (`coppmgr.cpp:82-106`)。

この状態で `queue2_group1` が APPL_DB に書き込まれると、`createGenetlinkHostIfTable()` が空の `genetlink_trap_ids` で呼ばれ HOSTIF_TABLE_ENTRY が 0 件になる（`copporch.cpp:843-848`）。genetlink HostIf は SAI に存在するが trap は転送されない。

### 4. platform 環境変数と genetlink の無関係

`copporch.cpp` の `getenv("platform")` チェック (L353, L1188) は `trap_priority` SET のスキップ条件として Mellanox/Marvell を判定するものであり、genetlink 処理とは無関係。genetlink フィールドの処理に platform 環境変数の参照は存在しない。

ただし同じ `queue2_group1` の `trap_priority` フィールドは Mellanox / Marvell Prestera でサイレントスキップされる（間接的影響）。

## プラットフォーム差サマリ

| 条件 | 影響フィールド | 挙動 | 検知方法 |
|------|--------------|------|---------|
| SAI が `SAI_HOSTIF_TYPE_GENETLINK` 未サポート | `genetlink_name` / `genetlink_mcgrp_name` | `create_hostif()` 失敗 → `task_failed` | `SWSS_LOG_ERROR` + swss.log |
| カーネル `psample` モジュール未ロード | — (SAI 操作は成功) | genetlink HostIf は作成されるが sflow パケット転送なし | `lsmod \| grep psample` |
| `FEATURE\|sflow` 無効 | `sample_packet` trap_id の有無 | genetlink HostIfTable が空 → sflow 転送なし | `sonic-db-cli APPL_DB hget COPP_TABLE\|queue2_group1 trap_ids` |
| `FEATURE\|sflow` 有効 + SAI サポートあり | `genetlink_name` / `genetlink_mcgrp_name` | 正常動作 | `show copp config` / `show sflow` |
| `platform` 環境変数に `"mellanox"` / `"marvell-prestera"` 含む | `trap_priority` のみ（genetlink 自体は影響なし） | trap_priority SET をサイレントスキップ | orch.h L41-42 |

## evidence

- `copporch.cpp` L657-679 `createGenetlinkHostIf()` — SAI API 呼び出し、エラー処理
- `copporch.cpp` L1265-1286 `getAttribsFromTrapGroup()` — genetlink フィールド収集（platform チェックなし）
- `copporch.cpp` L1184-1194 `getAttribsFromTrapGroup()` — trap_priority の platform チェック
- `copporch.cpp` L347-359 `initDefaultTrapIds()` — trap_priority の platform チェック
- `orch.h` L41-42 `MLNX_PLATFORM_SUBSTRING = "mellanox"`, `MRVL_PRST_PLATFORM_SUBSTRING = "marvell-prestera"`
- `coppmgr.cpp` L82-106 `setFeatureTrapIdsStatus()` — sflow feature 状態で trap_ids を除外
- `copp_cfg.j2` L131-134 — sflow COPP_TRAP 定義
