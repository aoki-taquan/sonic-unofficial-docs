# COPP port-binding (genetlink フィールド) — Phase B 書込み順依存分析

中間ファイル。最終成果は `docs/reference/config-db/copp-port.md` の `<!-- ordering -->` ブロックに反映済み。

## 分析対象ソース

- `sonic-swss/orchagent/copporch.cpp` (`doTask` L880-934, `processCoppTrapGroup` L730-872)
- `sonic-swss/orchagent/orchdaemon.cpp` (`OrchDaemon::init` L232-500)

## 書込み順依存の要点

### 1. `gPortsOrch->allPortsReady()` ゲート

`CoppOrch::doTask()` の先頭 (copporch.cpp L885-888):

```cpp
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

**全ポートが ready になるまで、COPP_GROUP の全処理がブロックされる**。
`PortsOrch::allPortsReady()` は SAI PortState が全ポートで確定し、初期化完了フラグが立つまで false を返す。
`m_toSync` キューに積まれたエントリは `allPortsReady()` が true になった後に順次処理される。

### 2. CoppOrch の初期化順序（orchdaemon.cpp）

`OrchDaemon::init()` における初期化順序:

```
L232: gPortsOrch = new PortsOrch(...)   # 最初に生成（外部参照 gPortsOrch が確定）
...
L341: gCoppOrch = new CoppOrch(...)     # PortsOrch 生成後に生成
```

`CoppOrch` コンストラクタ内で `initDefaultHostIntfTable()` / `initDefaultTrapGroup()` / `initDefaultTrapIds()` が呼ばれるが、これらは `gPortsOrch->allPortsReady()` に依存しない（SAI の初期状態で直接実行）。<!-- evidence: copporch.cpp L191-213 -->

### 3. `m_orchList` における CoppOrch の位置

```cpp
// orchdaemon.cpp L500
m_orchList = { gSwitchOrch, gCrmOrch, gPortsOrch, gBufferOrch, ..., gCoppOrch, gQosOrch, ... };
```

`m_orchList` の順序は warm start 時の状態復元順序および `allPortsReady()` 後の `m_toSync` 処理順序に影響する。
`gCoppOrch` は `gPortsOrch`、`gBufferOrch`、`gIntfsOrch` の後に位置し、ポート・バッファ初期化後に COPP 処理が行われることが保証される。<!-- evidence: orchdaemon.cpp L500 -->

### 4. genetlink フィールドの PORT 依存

`genetlink_name` / `genetlink_mcgrp_name` フィールドは SAI HOSTIF（genetlink 型）を作成する。
SAI HOSTIF は物理ポートには直接依存しないが、`allPortsReady()` ゲートが存在するため:

- **物理ポートの初期化完了前に CONFIG_DB に `COPP_GROUP` (genetlink フィールド付き) を書いても、SAI HostIf 作成は `allPortsReady()` 成立まで遅延される**
- 遅延中エントリは `m_toSync` に蓄積され、ready 後に一括処理される

### 5. DEL 時の順序依存なし

`genetlink_name` / `genetlink_mcgrp_name` フィールドを含む `COPP_GROUP` の DEL は、
`processCoppTrapGroup()` の `DEL_COMMAND` パスで `removeGenetlinkHostIf()` を呼ぶ。
削除に PORT の ready 状態チェックは介在しないが、`doTask()` ゲートが存在するため、
`allPortsReady()` が false の場合は DEL も遅延する。<!-- evidence: copporch.cpp L885-888, L1099-1119 -->

## まとめ（書込み順依存テーブル）

| 操作 | 必須順序・制約 | 違反時の結果 |
|------|--------------|------------|
| 起動時 genetlink HostIf 作成 | `allPortsReady()` が true になるまで自動遅延 | m_toSync に蓄積。PortsOrch 初期化完了後に自動処理 |
| 新規 `COPP_GROUP` (genetlink フィールド付き) 書込み | PortsOrch 初期化後が理想だが、事前書き込みも可（自動遅延） | `allPortsReady()` 前は処理がスキップ（次回 doTask 呼出しで再試行） |
| `COPP_GROUP` DEL (genetlink フィールドあり) | 順序制約なし（ただし `allPortsReady()` ゲートあり） | `allPortsReady()` 前は DEL も遅延 |
| init 時の CONFIG_DB 書込み順序 | `coppmgrd` が COPP_TRAP → COPP_GROUP の順で APPL_DB に書き込む（copp-group 参照）| 直接の genetlink 処理順序には影響しない |

## evidence

- `copporch.cpp:885-888` — `doTask()` の `allPortsReady()` ゲート
- `copporch.cpp:191-213` — `CoppOrch` コンストラクタの初期化シーケンス
- `orchdaemon.cpp:232` — `gPortsOrch = new PortsOrch(...)` (最初に生成)
- `orchdaemon.cpp:341` — `gCoppOrch = new CoppOrch(...)` (PortsOrch 後に生成)
- `orchdaemon.cpp:500` — `m_orchList` 順序（CoppOrch は PortsOrch の後）
- `copporch.cpp:1099-1119` — DEL 時の `removeGenetlinkHostIf()` パス
