---
title: Debug Framework（コンポーネント dump 登録 / assert 拡張）
area: architecture
verification: discrepancy-found
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/debug-framework/debug_framework_design_spec.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli:
    - show debug
    - show interfaces pktdrop
  yang: []
---

!!! danger "裏取りステータス: discrepancy-found"
    HLD v0.3 (2019-07) は **master へ取り込まれていない**。verifier-batch-18 で確認:

    - `sonic-swss-common` に `Debugframework` クラス・`linkWithFramework` API・`SWSS_DEBUG_PRINT*` マクロ いずれも存在しない（`grep -r` で 0 件）
    - `sonic-swss/orchagent/natorch.cpp` の `gDebugDumpOrch->addDbgCompMap(...)` は `#ifdef DEBUG_FRAMEWORK` 内（41 行目および 138-142 行目）でガードされ、`DEBUG_FRAMEWORK` マクロは master ビルド構成で定義されていない（残骸コード）
    - `sonic-utilities/show/` 配下に `pktdrop`/`debug` 系の CLI ハンドラなし（`dropcounters.py` は別仕様）

    本ページは HLD 仕様の参考資料として残すが、現行 master の挙動とは一致しない。実装は `DebugDumpOrch`/`DebugDumpHandler` 個別クラスではなく、`debugcounterorch` (counter 専用) や `show techsupport` 等に分散している。

# Debug Framework（コンポーネント dump 登録 / assert 拡張）

## 概要

SONiC コンポーネント（特に OrchAgent モジュール）が **内部状態のスナップショットダンプ** を登録し、CLI / assert / 重大ログから一斉トリガできる仕組み[^1]。Redis チャネル経由でトリガを配り、SwSS 共有ライブラリの `SWSS_DEBUG_PRINT` マクロで出力先（syslog / per-component log）と post-action（compress-rotate / upload）を一元管理する。あわせて assert マクロを拡張して類型化された debug 情報収集を可能にする。

## 動作仕様

### 全体構造

```mermaid
flowchart LR
    CLI["CLI: show debug <comp>"] --> APP[(APPL_DB<br/>Dump table)]
    ASSERT[custom_assert] --> APP
    APP -- pub/sub --> FW[Debugframework<br/>singleton]
    FW --> CB1[RouteOrch dump]
    FW --> CB2[NeighborOrch dump]
    CB1 --> OUT[/var/log/<comp>_dump.log<br/>or syslog]
    CB2 --> OUT
    OUT --> POST[Post-action<br/>compress-rotate / upload]
```

### Framework クラスと登録 API

C++ singleton として SwSS 名前空間に実装される[^1]:

```cpp
class Debugframework {
public:
    static Debugframework &getInstance();
    typedef void (*DumpInfoFunc)(std::string, KeyOpFieldsValuesTuple);
    static void linkWithFramework(std::string &componentName,
                                   const DumpInfoFunc funcPtr);   // FW がスレッド作成
    static void linkWithFrameworkNoThread(std::string &componentName); // 自前スレッド
    static void invokeTrigger(std::string componentName, std::string args);
};
```

| API | FW がやること | コンポーネント側 |
|-----|---------------|------------------|
| `linkWithFramework` | Selectable + 受信スレッド + APPL_DB sub を作成、callback 起動 | DumpInfoFunc 登録のみ |
| `linkWithFrameworkNoThread` | 登録のみ。post-action は実施 | 自前で sub / event ループ / callback 呼び |

OrchAgent では既存の Redis event ループに乗せるため `linkWithFrameworkNoThread` を採用する[^1]。`DebugDumpOrch` という派生 Orch を 1 つ立て、`addDbgCompMap()` で RouteOrch / NeighborOrch 等が自分のダンプ関数を登録する。

### コンポーネント側ガイドライン

- `DumpInfoFunc` 型のコールバックを 1 本実装
- 中身では `SWSS_DEBUG_PRINT_BEGIN` ... `SWSS_DEBUG_PRINT(...)` ... `SWSS_DEBUG_PRINT_END` で囲む
- 引数 `KeyOpFieldsValuesTuple` の `dumpType` / `passthru` は **コンポーネント自身が解釈**（FW は不透明）
- thread-safe で実装する義務がある

### APP_DB スキーマ

```
DAEMON:<daemon_name>:
  DUMP_TYPE     = short | full
  DUMP_TARGET   = default | syslog
  PASSTHRU_ARGS = <csv>

DAEMON:<daemon_name>:           ; 完了応答
  RESPONSE_TYPE = pending | failure | successful
```

### CLI

| Syntax | 説明 |
|--------|------|
| `show debug all` | 全登録コンポーネント既定 action で dump |
| `show debug <component> [args]` | 指定コンポーネントのみ |
| `show debug actions` | 設定済みの FW action を表示 |
| `show interfaces pktdrop` | drop / error counter を全 if で表示 |

OrchAgent 例（HLD 抜粋）[^1]:

```
show debug routeorch routes -v VrfRED -p 100.100.4.0/24
show debug routeorch nhgrp
show debug neighorch nhops
show debug neighorch neigh
```

出力にはプレフィックス、ネクストホップ、SAI OID、ECMP グループ ref count などを含む（ASIC OID と app 構造体ポインタの紐付け確認に使う設計）。

### Configuration Defaults

| Parameter | options | Default |
|-----------|---------|---------|
| `DumpLocation` | syslog / filename | `/var/log/<comp>_dump.log` |
| `TargetComponent` | all / componentname | all |
| `Post-action` | upload / compress-rotate-keep | compress-rotate-keep |
| `Server-location` | ipaddress | 127.0.0.1 |
| `Upload-method` | scp / tftp | tftp |

### Assert 拡張

production code でも assert を残し、失敗時の挙動を分類する[^1]:

| type | 動作 |
|------|------|
| `DUMP` | FW 経由で当該モジュールの dump を呼ぶ |
| `BTRACE` | backtrace を吐いて続行 |
| `SYSLOG` | 失敗を syslog 記録 |
| `ABORT` | 既存の挙動（exception/crash）|

```cpp
#define assert(exp) Debugframework::custom_assert(exp, __PRETTY_FUNCTION__, __LINE__)
```

<!-- evidence:
source: sonic-net/SONiC/doc/debug-framework/debug_framework_design_spec.md#L96-L168 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  Debug Framework provides an API for components to register with the framework. ...
  Framework uses Redis notifications for communicating the trigger message ...
  Components register dump routine with debug framework using the API:
    Debugframework::linkWithFramework(...)
    Debugframework::linkWithFrameworkNoThread(...)
reasoning: 2 つの登録 API と Redis pub/sub ベースのトリガ機構の根拠。
-->

## tech-support 拡張・補助スクリプト

`show techsupport` は本 HLD の延長で **STATE_DB dump、ASIC 固有 dump、critical log の persistent log 切り出し** を追加[^1]。さらに次のヘルパーが付随する:

- "headline" 系の summary 印字スクリプト
- 収集情報の upload を非破壊的に行う helper
- debug ファイル数を policy で制限するスクリプト

## Warm boot / scalability

本 framework 自体は warm boot や scalability に影響を与えない[^1]。

## 制限事項

- v0.3 (2019-07) HLD のため API 名や CLI が現行 master と一致しているか未確認
- フレームワーク自体は実行コンテキストを持たない（option #1 で生成するスレッドは登録コンポーネント側のコンテキスト扱い）
- 引数の解釈はコンポーネント実装に委ねられ、統一フォーマットは無い

## 干渉する機能

- **show techsupport**（system 系の `show-techsupport` ページ参照）
- **`syslog` rate limit / redirect** 系の各 HLD（critical log 抽出は本 framework と連動）
- **OrchAgent 全般**: RouteOrch / NeighborOrch / 他 Orch が個別に dump を登録する想定

## 引用元

[^1]: `sonic-net/SONiC` `doc/debug-framework/debug_framework_design_spec.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- evidence (verifier-batch-18, discrepancy):
- sonic-swss-common: `Debugframework` / `linkWithFramework` / `SWSS_DEBUG_PRINT` 検索 0 件
- sonic-swss/orchagent/natorch.cpp:40-42, 138-142: `#ifdef DEBUG_FRAMEWORK` 内の dead code のみ（マクロは未定義）
- sonic-utilities/show/: `pktdrop` / `debug` 系 CLI ハンドラなし
-->

<!-- concerns hint:
- libswsscommon に Debugframework クラス / linkWithFramework が現行で存在するか確認
- DebugDumpOrch / addDbgCompMap の orchagent 取り込み確認
- APPL_DB Dump table / Dump done table の sonic-yang-models 反映確認
- show debug / show interfaces pktdrop CLI の sonic-utilities 取り込み確認
- 2019-07 v0.3 から 6 年以上経過しており現行実装との乖離可能性 高
-->
