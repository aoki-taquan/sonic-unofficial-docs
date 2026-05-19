# COPP port-binding (genetlink フィールド) — Phase H プラットフォーム差分析

中間ファイル。最終成果は `docs/reference/config-db/copp-port.md` の `<!-- platform -->` ブロックに反映される。

## 分析対象ソース

- `sonic-swss/orchagent/copporch.cpp` (`createGenetlinkHostIf` L657-679, `doTask` L880-934, `getAttribsFromTrapGroup` L1154-1295)
- `sonic-swss/orchagent/copporch.h` (genetlink フィールド定数 L44-46)
- `sonic-swss/orchagent/orch.h` (`MLNX_PLATFORM_SUBSTRING` / `MRVL_PRST_PLATFORM_SUBSTRING` 定義 L41-42)

## プラットフォーム差の要点

### 1. SAI genetlink HostIf サポート

`createGenetlinkHostIf()` は `sai_hostif_api->create_hostif()` に `SAI_HOSTIF_ATTR_TYPE = SAI_HOSTIF_TYPE_GENETLINK` を渡す。
`SAI_HOSTIF_TYPE_GENETLINK` をサポートしないベンダー SAI では `SAI_STATUS_SUCCESS` 以外が返り、
`handleSaiCreateStatus()` でエラー処理 → `task_failed` となる。

**genetlink フィールド自体に `platform` 環境変数チェックは存在しない。** 非対応 SAI では
エラーログが出力され、処理は `task_failed` で終了する。

### 2. psample カーネルモジュール依存

`genetlink_name = "psample"` は Linux カーネルの psample モジュール（`CONFIG_PSAMPLE`）が必要。
SONiC の標準カーネルパッケージには psample が含まれるが、カスタムカーネルや一部ハードウェアアプライアンスでは
モジュールが存在しない場合がある。この場合 SAI が `create_hostif()` で GENETLINK HostIf を作成しようとしても、
カーネル側の netlink ソケット生成が失敗し SAI エラーが返る。

### 3. trap_priority の Mellanox / Marvell 除外（間接的影響）

genetlink フィールド自体の処理は platform 環境変数でゲートされないが、同じ `queue2_group1` グループに
`trap_priority` が設定されている場合、Mellanox (`"mellanox"`) および Marvell Prestera (`"marvell-prestera"`)
では `SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY` の SET が **サイレントスキップ** される。
genetlink HostIf 自体の作成は行われるが、trap の優先度設定は無効化される。

### 4. VOQ / Chassis 差

`copporch.cpp` に VOQ chassis 固有のコードパスは存在しない。genetlink port-binding は
CPU 宛トラフィック処理のためのホストインタフェース機能であり、VOQ ファブリックの転送パスとは独立している。

## プラットフォーム差サマリー

| プラットフォーム条件 | 影響 | 挙動 |
|---|---|---|
| SAI が `SAI_HOSTIF_TYPE_GENETLINK` 非対応 | `genetlink_name` / `genetlink_mcgrp_name` | `create_hostif()` 失敗 → task_failed |
| psample カーネルモジュール不在 | `genetlink_name = "psample"` | SAI / カーネル netlink 生成失敗 |
| `platform` 環境変数 `"mellanox"` 含む | `trap_priority` のみ（genetlink 自体は影響なし） | trap_priority SET をスキップ |
| `platform` 環境変数 `"marvell-prestera"` 含む | 同上 | 同上 |
| VOQ / Chassis 構成 | なし | genetlink 処理に変化なし |

## evidence

- `copporch.cpp` L657-679 `createGenetlinkHostIf()` — SAI API 呼び出し、エラー処理
- `copporch.cpp` L1265-1286 `getAttribsFromTrapGroup()` — genetlink フィールド収集（platform チェックなし）
- `copporch.cpp` L1184-1194 `getAttribsFromTrapGroup()` — trap_priority の platform チェック
- `copporch.cpp` L347-359 `initDefaultTrapIds()` — trap_priority の platform チェック
- `orch.h` L41-42 `MLNX_PLATFORM_SUBSTRING = "mellanox"`, `MRVL_PRST_PLATFORM_SUBSTRING = "marvell-prestera"`
