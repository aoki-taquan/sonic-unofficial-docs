---
title: DASH_ROUTING_TYPE テーブル
description: "DASH_ROUTING_TYPE テーブル — DASH データプレーンの転送アクション（routing type）を名前付きで定義する。ENI ルートテーブルや VNET マッピングテーブルから leafref 参照される。"
area: reference
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/dash/dashorch.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/dash/dashvnetorch.cpp
    ref: HEAD
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dash.yang
    ref: HEAD
related:
  config_db:
    - DASH_ROUTING_TYPE
    - DASH_ROUTE_TABLE
    - DASH_VNET_MAPPING_TABLE
  cli: []
  yang:
    - sonic-dash
hard: 0
---

# DASH_ROUTING_TYPE テーブル

## 概要

DASH データプレーンにおける転送アクション（routing type）を名前付きで定義する[^1]。各エントリは **routing type 識別子**（`direct`、`vnet_encap`、`privatelink` 等）に対して、適用する転送アクション名・アクション種別・カプセル化方式・VNI を関連付ける。

`DashOrch` (`sonic-swss/orchagent/dash/dashorch.cpp`) が `DASH_ROUTING_TYPE_TABLE` を購読し、受信した protobuf メッセージ (`dash::route_type::RouteType`) をメモリ上の `routing_type_entries_` マップに格納する。`DashVnetOrch` 等はこのマップを `getRouteTypeActions()` 経由で参照し、SAI 属性（`SAI_DASH_ENCAPSULATION_VXLAN` 等）に変換する。

!!! note "ストレージは APPL_DB"
    本テーブルの実際の書き込み先は **APPL_DB** の `DASH_ROUTING_TYPE_TABLE` である。CONFIG_DB には保存されない。YANG モデル (`sonic-dash.yang`) が定義する `DASH_ROUTING_TYPE` は設定検証モデルとして機能する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  EXT["外部コントローラ / CLI"]
  APPDB[("APPL_DB<br/>DASH_ROUTING_TYPE_TABLE")]
  OA["DashOrch<br/>(orchagent)"]
  MEM["routing_type_entries_<br/>(in-memory map)"]
  VNET["DashVnetOrch<br/>DashRouteOrch"]
  SAI["SAI DASH API"]
  HW["DPU / ASIC"]
  EXT --> APPDB --> OA --> MEM
  VNET -->|getRouteTypeActions()| MEM
  VNET --> SAI --> HW
```

!!! note "凡例"
    `DASH_ROUTING_TYPE_TABLE` に書き込まれた routing type は orchagent のメモリに保持され、VNET マッピング・ルートエントリのプログラム時に SAI 属性へ変換される。
<!-- /cdb-mermaid -->

<!-- ordering -->
## 書込み順依存 (Phase B)

<!-- evidence: sonic-swss/orchagent/dash/dashorch.cpp addRoutingTypeEntry:441 / getRouteTypeActions:82 / dashvnetorch.cpp addOutboundCaToPa:313 -->

`DASH_ROUTING_TYPE_TABLE` 自体は外部テーブルに依存せず任意のタイミングで SET できる。ただし `DASH_VNET_MAPPING_TABLE` のプログラミング時に routing type の登録が必須となるため、以下の SET 順序を守ることが重要。

### 依存 1: DASH_ROUTING_TYPE_TABLE は前提テーブルなし（自己完結）

```
DASH_ROUTING_TYPE_TABLE|<routing_type>  SET
```

`addRoutingTypeEntry()` (`dashorch.cpp:441-455`) は外部 orchagent の状態を一切参照しない。受信した protobuf を `routing_type_entries_` マップに格納するのみ。`parsePbMessage()` のデシリアライズ失敗時のみ erase してスキップ（再試行なし）。

**違反時**: なし（前提テーブルが存在しない）。

### 依存 2: DASH_ROUTING_TYPE_TABLE → DASH_VNET_MAPPING_TABLE（必須先行・自動回復あり）

```
DASH_ROUTING_TYPE_TABLE|<routing_type>  SET 完了（routing_type_entries_ に格納済み）
  ↓
DASH_VNET_MAPPING_TABLE|<vnet>:<ip>  SET
```

`DashVnetOrch::addOutboundCaToPa()` (`dashvnetorch.cpp:313-319`) は `getRouteTypeActions()` を呼び、該当 routing type が `routing_type_entries_` に存在しない場合に `return false` でエントリを保留する。上位 `doTask()` が `it++` で ConsumerBase の次の周回まで保留し、ROUTING_TYPE が登録された後に自動再処理される（無限ポーリング）。

**違反時**: `DASH_VNET_MAPPING_TABLE` のエントリが保留され、`DASH_ROUTING_TYPE_TABLE` SET 後に自動回復する。

### 依存 3: DEL 推奨順序（VNET Mapping → ROUTING_TYPE）

```
DASH_VNET_MAPPING_TABLE|<vnet>:<ip>  DEL  先行（推奨）
  ↓
DASH_ROUTING_TYPE_TABLE|<routing_type>  DEL
```

`removeRoutingTypeEntry()` (`dashorch.cpp:457-471`) は即時 `routing_type_entries_` から削除する。VNET Mapping が残ったまま ROUTING_TYPE を先に削除すると、VNET Mapping の再 SET や orchagent 再起動時の replay で `getRouteTypeActions()` miss が発生し Mapping が処理待ちになる。

**違反時**: 即時機能影響はないが、VNET Mapping の再設定が必要になる。

| # | 依存関係 | 方向 | 違反時挙動 |
|---|----------|------|-----------|
| 1 | DASH_ROUTING_TYPE_TABLE SET の前提テーブルなし | — | — |
| 2 | ROUTING_TYPE SET → VNET_MAPPING SET | 強制先行（自動再試行・自動回復） | VNET Mapping 保留、自動回復 |
| 3 | VNET_MAPPING DEL → ROUTING_TYPE DEL | 推奨先行（違反しても即時影響なし） | VNET Mapping 再設定時に再試行待ち |

<!-- /ordering -->

## key 構造

```text
DASH_ROUTING_TYPE_TABLE|<routing_type>
```

- `<routing_type>`: `direct` / `vnet` / `vnet_direct` / `vnet_encap` / `drop` / `appliance` / `privatelink` / `privatelinknsg` / `servicetunnel` のいずれか（YANG pattern 定義による）

実際のキー名は orchagent で大文字変換 + `ROUTING_TYPE_` プレフィックスが付与されてから `dash::route_type::RoutingType_Parse()` で enum 値に変換される (`dashorch.cpp:487-490`)。

## フィールド

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | enum string | ✅ | - | routing type 識別子。YANG pattern: `direct\|vnet\|vnet_direct\|vnet_encap\|drop\|appliance\|privatelink\|privatelinknsg\|servicetunnel` |
| `action_name` | string (1–255 文字) | - | - | 転送アクションの論理名。任意のラベル。SAI には渡されない |
| `action_type` | enum string | - | - | 実適用アクション種別。`none\|maprouting\|direct\|staticencap\|appliance\|4to6\|mapdecap\|decap\|drop` |
| `encap_type` | enum string | 条件付き | - | カプセル化方式。`vxlan\|nvgre`。`action_type=staticencap` のときのみ有効 |
| `vni` | uint32 (1–16777215) | - | - | トンネル VNI。`action_type=staticencap` のときに `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_TUNNEL_KEY` として使用 |

### フィールド詳細

#### `action_type` の実効動作

| `action_type` | SAI 変換 | 使用場面 |
|--------------|---------|---------|
| `staticencap` | VXLAN/NVGRE カプセル化アクション生成 (`SAI_DASH_ENCAPSULATION_VXLAN` 等) | `vnet_encap`、`privatelink` 等 |
| `maprouting` | VNET マッピングテーブル参照でオーバーレイアドレスを解決 | `vnet`、`vnet_direct` |
| `drop` | 明示的な破棄 | `drop` routing type |
| その他 | orchagent 処理対象外 (protobuf のみ記録) | appliance、servicetunnel 等 |

#### `encap_type` の条件

`action_type=staticencap` のとき、`dashvnetorch.cpp:325-338` の分岐で `encap_type` を SAI 定数に変換する。`encap_type` が指定されていない（または無効値）の場合は `SWSS_LOG_ERROR` を発してエントリの追加をスキップする（`return true` で consumer からは削除）。

#### `vni` の省略時動作

`action.has_vni()` が false（protobuf フィールド未設定）の場合、`routing_type_tunnel_key = 0` のまま推移し、VNI 属性は SAI に設定されない (`dashvnetorch.cpp:341-343`)。

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

YANG schema (`sonic-dash.yang`) は `DASH_ROUTING_TYPE_LIST` の各フィールドに明示的な `default` ステートメントを持たない。実行時のデフォルト・フォールバックはすべて orchagent コード (`dashorch.cpp`、`dashvnetorch.cpp`) による。

| フィールド | コード由来デフォルト / fallback | 種別 | evidence |
|-----------|-------------------------------|------|----------|
| `action_name` | protobuf の zero value (`""`) — SAI には渡されない | YANG default なし・SAI 非使用 | `sonic-dash.yang:369-374`（SAI 変換コードなし） |
| `action_type` | protobuf の zero value (`ACTION_TYPE_UNSPECIFIED` = 0) — orchagent はそのまま格納。SAI 変換は `staticencap` / `maprouting` 等のみ | YANG default なし | `dashvnetorch.cpp:325` — `action.action_type()` チェック |
| `encap_type` | `action_type=staticencap` の場合は **実質必須**。省略時 `SAI_DASH_ENCAPSULATION_INVALID` のまま SAI に渡されてエラー | 条件付き必須・コード強制 | `dashvnetorch.cpp:322, 337-339` |
| `vni` | 省略時 `routing_type_tunnel_key = 0`。SAI の VNI 属性は設定されない（ASIC 実装依存のデフォルト VNI が適用） | YANG default なし・暗黙 0 | `dashvnetorch.cpp:341-343` |

### 補足

- **protobuf ベースのエントリ管理**: `DASH_ROUTING_TYPE_TABLE` は他の DASH テーブルと同様に protobuf シリアライズ形式で APPL_DB に書き込まれる。`parsePbMessage()` (`dashorch.cpp:501`) でデシリアライズ失敗するとエントリは consumer キューから削除されスキップされる。
- **routing type 名の正規化**: キー文字列は `std::transform(..., ::toupper)` で大文字化後 `"ROUTING_TYPE_"` プレフィックスを付与して enum に変換 (`dashorch.cpp:487-490`)。無効な routing type 名の場合は `SWSS_LOG_WARN` を出してスキップ。
- **YANG pattern 列挙値**: `direct | vnet | vnet_direct | vnet_encap | drop | appliance | privatelink | privatelinknsg | servicetunnel` のみ受理 (`sonic-dash.yang:365`)。YANG validation を通過した後 orchagent に到達するため、実運用での無効値は発生しにくい。
- **再登録保護**: `addRoutingTypeEntry()` は既存エントリへの上書きを `SWSS_LOG_WARN` + `return true` でサイレントスキップする (`dashorch.cpp:445-449`)。更新が必要な場合はまず削除してから再設定する必要がある。
<!-- /defaults -->

<!-- ordering -->
## エントリ投入順序・依存関係 (Phase B)

### 投入の必須順序

`DASH_ROUTING_TYPE_TABLE` は他の DASH テーブルへの先行依存を持たず、任意のタイミングで書き込める。
ただし、以下のテーブルは routing type が登録済みであることを前提とする。

```
[前提なし] DASH_ROUTING_TYPE_TABLE — 最初に書き込み可能
    ↓
[1] DASH_VNET_MAPPING_TABLE  ← getRouteTypeActions() で routing_type_entries_ を参照
```

`DashVnetOrch::addOutboundCaToPa()` (`dashvnetorch.cpp:313-319`) は `DashOrch::getRouteTypeActions()` を呼び出し、`routing_type_entries_` に該当エントリが存在しない場合 `false` を返してリトライキューに戻す。
`DashRouteOrch` が扱う `DASH_ROUTE_TABLE` / `DASH_ROUTE_GROUP_TABLE` は静的マップ (`sOutboundAction`) を使うため `routing_type_entries_` に依存しない。

| 違反パターン | 挙動 | 自動回復 |
|---|---|---|
| routing type 未登録で VNET マッピング投入 | `getRouteTypeActions()` が `false` → VnetMap リトライ | routing type 登録後の次 doTask() で自動解消 |
| 同一 routing type への SET 二重投入 | `addRoutingTypeEntry()` が `SWSS_LOG_WARN` + スキップ | 自動回復なし（DEL → SET が必要） |
| VNET マッピング残存状態で routing type DEL | `routing_type_entries_` から即時削除（SAI ガードなし） | 孤立エントリが DPU 側に残る |

### 削除の逆順制約

削除は投入の逆順で行う必要がある。

```
[1] DASH_VNET_MAPPING_TABLE — DEL（参照エントリを先にすべて削除）
    ↓
[2] DASH_ROUTING_TYPE_TABLE — DEL
```

`removeRoutingTypeEntry()` (`dashorch.cpp:457-469`) は `routing_type_entries_` から即時削除して `return true` を返す。
既存 VNET マッピングが SAI / DPU 側にプログラム済みでも orchagent はガードしないため、VNET マッピングを先に削除しないと孤立エントリが残る。

### warm-reboot 挙動

`DashOrch` は `addOrchList` に登録されており (`orchdaemon.cpp:1414`)、`warmRestoreAndSyncUp()` の doTask() 3 イテレーション対象となる。
`m_orchList` の登録順は `DashAclOrch → DashVnetOrch → DashRouteOrch → DashOrch → ...` であり (`orchdaemon.cpp:1412-1420`)、`DashVnetOrch` が `DashOrch` より先に処理される。

warm-reboot 後のリプレイで `DASH_VNET_MAPPING_TABLE` が先にキューに積まれると `getRouteTypeActions()` miss でリトライが発生するが、`DashOrch` が `routing_type_entries_` を補充した後の次イテレーションで自動解消し、3 イテレーション以内に収束する設計となっている。

### 順序依存サマリ

| # | 先行テーブル / 操作 | 後続テーブル / 操作 | 緩和策 |
|---|-------------------|-------------------|--------|
| 1 | なし（先行依存なし） | `DASH_ROUTING_TYPE_TABLE` 書込 | 任意のタイミングで書込可 |
| 2 | `DASH_ROUTING_TYPE_TABLE` 登録 | `DASH_VNET_MAPPING_TABLE` 書込 | routing type 未登録 → VnetMap リトライキュー |
| 3 | `DASH_ROUTING_TYPE_TABLE` DEL | `DASH_ROUTING_TYPE_TABLE` SET（変更時） | DEL 後に SET を再投入（DEL→SET 順守） |
| 4 | `DASH_VNET_MAPPING_TABLE` DEL | `DASH_ROUTING_TYPE_TABLE` DEL | 参照元 VNET マッピングを先に削除しないと孤立エントリ |

- 中間トレース: `meta/_intermediate/cdb-flow/dash-routing-types-ordering.md`
<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`DASH_ROUTING_TYPE_TABLE` は他の DASH テーブルへの暗黙参照を持たない。外部 OID 解決も CRM カウンタ更新も行わない自己完結型テーブルであり、他テーブルから参照される側（被参照）として機能する。

### DASH_ROUTING_TYPE_TABLE が参照するテーブル

| 参照先テーブル / リソース | 参照方向 | 条件 | ブロッキング | evidence |
|--------------------------|---------|------|------------|----------|
| *(なし)* | — | — | — | — |

`DashOrch::addRoutingTypeEntry()` (`dashorch.cpp:441-455`) は外部 orchagent・テーブルを一切参照せず、受信した protobuf を `routing_type_entries_` in-memory マップに格納するのみ。

### DASH_ROUTING_TYPE_TABLE を参照するテーブル（被参照・逆方向）

| 被参照元テーブル | 参照方法 | 参照条件 | 未登録時の挙動 | evidence |
|---------------|---------|---------|--------------|---------|
| `DASH_VNET_MAPPING_TABLE` | `getRouteTypeActions()` で `routing_type_entries_` を検索 | VNET マッピング SET 時・常時 | `return false` → VnetMapping をリトライキューに戻す | `dashvnetorch.cpp:313–319` |

`DashVnetOrch::addOutboundCaToPa()` は `gDirectory.get<DashOrch*>()->getRouteTypeActions(ctxt.metadata.routing_type(), route_type_actions)` を呼ぶ。`routing_type_entries_` に該当エントリがなければ `SWSS_LOG_WARN` を出して `false` を返し、上位 `doTask()` がこのエントリを次の周回まで保留する（自動回復）。

### 結果 DB 書き込み (APP_STATE_DB)

SET 完了後に `writeResultToDB(dash_routing_type_result_table_, routing_type_str, DASH_RESULT_SUCCESS)` (`dashorch.cpp:517`) が APP_STATE_DB の `DASH_ROUTING_TYPE_TABLE` に結果を書き込む。DEL 完了後は `removeResultFromDB()` (`dashorch.cpp:524`) で削除する。外部コントローラ（gNMI 等）が SAI プログラム結果を参照するための非同期通知チャネルとして機能する。

### CRM カウンタ

使用なし。`DASH_ROUTING_TYPE_TABLE` は SAI OID を返さないため CRM リソースカウンタは不使用。

- 中間トレース: `meta/_intermediate/cdb-flow/dash-routing-types-cross-refs.md`
<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

<!-- evidence: sonic-swss/orchagent/dash/dashorch.cpp doTaskRoutingTypeTable:473 / addRoutingTypeEntry:441 / removeRoutingTypeEntry:457 / dashvnetorch.cpp addOutboundCaToPa:300 -->

`DASH_ROUTING_TYPE_TABLE` の SET/DEL 処理は `doTaskRoutingTypeTable()` (`dashorch.cpp:473`) が担当する。SAI API 呼び出しは行わず orchagent メモリへの格納のみのため、SAI 由来の失敗は発生しない。

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | result_table ステータス | evidence |
|---|---|---|---|---|
| 無効な routing type 名（`RoutingType_Parse()` 失敗） | `doTaskRoutingTypeTable()` L490 | WARN ログ → `erase(it)` → 恒久スキップ | なし | `dashorch.cpp:490-494` |
| protobuf デシリアライズ失敗（`parsePbMessage()` false） | `doTaskRoutingTypeTable()` L501 | WARN ログ → `erase(it)` → 恒久スキップ | なし | `dashorch.cpp:501-505` |
| 同一 routing type の二重登録（重複検出） | `addRoutingTypeEntry()` L445 | WARN ログ → `return true`（冪等・成功扱い、既存エントリ上書きなし） | `DASH_RESULT_SUCCESS` | `dashorch.cpp:445-449` |
| `addRoutingTypeEntry()` が false を返す（拡張点） | `doTaskRoutingTypeTable()` L508 | `result = DASH_RESULT_FAILURE` → `it++`（再試行） → `writeResultToDB(FAILURE)` | `DASH_RESULT_FAILURE` | `dashorch.cpp:513-517` |
| `action_type=staticencap` かつ `encap_type` 不正（VXLAN/NVGRE 以外）— VNET マッピング参照時 | `addOutboundCaToPa()` L337（`dashvnetorch.cpp`） | ERROR ログ → `return true`（consumer から erase、VNET マッピング未作成） | — | `dashvnetorch.cpp:337-338` |
| `getRouteTypeActions()` で該当 routing type 未登録 — VNET マッピング参照時 | `addOutboundCaToPa()` L315（`dashvnetorch.cpp`） | INFO ログ → `return false`（VNET マッピング作成保留） | — | `dashvnetorch.cpp:315-318` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | result_table ステータス | evidence |
|---|---|---|---|---|
| 存在しない routing type の削除 | `removeRoutingTypeEntry()` L461 | WARN ログ → `return true`（冪等・成功扱い） | result エントリ削除 | `dashorch.cpp:461-464` |
| `removeRoutingTypeEntry()` が false を返す（拡張点） | `doTaskRoutingTypeTable()` L521 | `it++`（再試行） | result エントリ残留 | `dashorch.cpp:526-528` |
| 不明な操作コード（SET/DEL 以外） | `doTaskRoutingTypeTable()` L533 | ERROR ログ → `erase(it)` → 恒久スキップ | なし | `dashorch.cpp:533-534` |

### 補足

- **result_table 書き込み先**: `APPL_STATE_DB` の `APP_DASH_ROUTING_TYPE_TABLE_NAME` テーブル（`dashorch.cpp:73`）。フィールド `result` に `0`（SUCCESS）または `1`（FAILURE）を書き込む（`DASH_RESULT_SUCCESS` / `DASH_RESULT_FAILURE`、`dashorch.h:35-36`）。
- **SAI 連携なし**: `DASH_ROUTING_TYPE_TABLE` エントリ自体は SAI API を呼ばず orchagent メモリ（`routing_type_entries_`）にのみ格納される。SAI 失敗が発生するのはこの routing type を参照する VNET マッピング・ルートエントリの作成時（`dashvnetorch.cpp`、`dashrouteorch.cpp`）。
- **依存側の失敗伝播**: VNET マッピングが `getRouteTypeActions()` で `false` を返した場合、そのエントリは consumer キューに保留（`return false` → `it++` パターン）。routing type が後から登録されると次の tick で自動再処理される。
- **二重登録の冪等性**: 重複は WARN ログのみで既存エントリは変更されない。更新には DEL → SET が必要（`addRoutingTypeEntry()` は上書きをサポートしない）。

- 中間トレース: `meta/_intermediate/cdb-flow/dash-routing-types-failure.md`
<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

<!-- evidence: sonic-swss/orchagent/dash/dashorch.h:29-36 / dashorch.cpp:487-488 / dashrouteorch.cpp:41-47 / dashvnetorch.cpp:322-343 / dashtunnelorch.cpp:289-292 / sonic-dash.yang:356-398 -->

### 結果コード定数 (dashorch.h)

| 定数名 | 値 | 用途 | evidence |
|--------|-----|------|---------|
| `DASH_RESULT_SUCCESS` | `0` | SET/DEL 成功時に `APP_DASH_ROUTING_TYPE_TABLE_NAME` の `result` フィールドに書き込む値 | `sonic-swss/orchagent/dash/dashorch.h:35` |
| `DASH_RESULT_FAILURE` | `1` | `addRoutingTypeEntry()` が `false` 返却した場合（protobuf parse 失敗）に result フィールドへ書き込む値 | `sonic-swss/orchagent/dash/dashorch.h:36` |

### キー変換ハードコード文字列 (dashorch.cpp)

APPL_DB キー（小文字）を protobuf enum 名に変換する 2 段変換がハードコードされている。

| 変換ステップ | 処理内容 | evidence |
|-------------|---------|---------|
| 大文字変換 | `std::transform(..., ::toupper)` でキー全体を大文字化。例: `"vnet_encap"` → `"VNET_ENCAP"` | `sonic-swss/orchagent/dash/dashorch.cpp:487` |
| プレフィックス付加 | `"ROUTING_TYPE_"` を先頭に付加。例: `"VNET_ENCAP"` → `"ROUTING_TYPE_VNET_ENCAP"` | `sonic-swss/orchagent/dash/dashorch.cpp:488` |

> **注意**: 外部コントローラは APPL_DB キーを **プレフィックスなし小文字**（例: `vnet_encap`）で書き込む必要がある。`ROUTING_TYPE_` 付きで書き込むと二重付加になり `RoutingType_Parse()` が失敗する。

### ROUTING_TYPE → SAI アクション変換マップ (`sOutboundAction`)

`dashrouteorch.cpp:41-47` でハードコードされた静的マップ。これに含まれない routing type は `DashRouteOrch::addOutboundRouting()` での SAI プログラミングが別ブランチ処理またはスキップされる。

| RoutingType enum | 対応 SAI アウトバウンドアクション | evidence |
|-----------------|--------------------------------|---------|
| `ROUTING_TYPE_VNET` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET` | `sonic-swss/orchagent/dash/dashrouteorch.cpp:43` |
| `ROUTING_TYPE_VNET_DIRECT` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET_DIRECT` | `sonic-swss/orchagent/dash/dashrouteorch.cpp:44` |
| `ROUTING_TYPE_DIRECT` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_DIRECT` | `sonic-swss/orchagent/dash/dashrouteorch.cpp:45` |
| `ROUTING_TYPE_DROP` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_DROP` | `sonic-swss/orchagent/dash/dashrouteorch.cpp:46` |

`ROUTING_TYPE_PRIVATELINK` は `dashvnetorch.cpp:374` に専用ブランチあり（`sOutboundAction` 外）。`ROUTING_TYPE_APPLIANCE` / `ROUTING_TYPE_PRIVATELINKNSG` / `ROUTING_TYPE_SERVICETUNNEL` は sOutboundAction 未登録。

### ENCAP_TYPE → SAI 変換定数

| encap_type enum | 対応 SAI encapsulation | evidence |
|----------------|----------------------|---------|
| `ENCAP_TYPE_VXLAN` | `SAI_DASH_ENCAPSULATION_VXLAN` | `sonic-swss/orchagent/dash/dashvnetorch.cpp:327-329`, `dashtunnelorch.cpp:289` |
| `ENCAP_TYPE_NVGRE` | `SAI_DASH_ENCAPSULATION_NVGRE` | `sonic-swss/orchagent/dash/dashvnetorch.cpp:331-333`, `dashtunnelorch.cpp:292` |

### YANG pattern 制約（許容値の全一覧）

CONFIG_DB / APPL_DB に書き込める値をソースから確認。

| フィールド | YANG pattern 許容値 | evidence |
|-----------|---------------------|---------|
| `name` (routing type) | `direct` / `vnet` / `vnet_direct` / `vnet_encap` / `drop` / `appliance` / `privatelink` / `privatelinknsg` / `servicetunnel` | `sonic-dash.yang:365` |
| `action_type` | `none` / `maprouting` / `direct` / `staticencap` / `appliance` / `4to6` / `mapdecap` / `decap` / `drop` | `sonic-dash.yang:379` |
| `encap_type` | `vxlan` / `nvgre` | `sonic-dash.yang:385` |
| `vni` | `1..16777215`（24bit VNI 全有効範囲、RFC 7348） | `sonic-dash.yang:392` |

> **スキャン証跡**: `dashorch.h` L29-36、`dashorch.cpp` L45-46,73,487-488、`dashrouteorch.cpp` L41-47,78-130,326、`dashvnetorch.cpp` L314-374,771、`dashtunnelorch.cpp` L289-292、`sonic-dash.yang` L356-398 読了。定数 2 (result code) + 2 (key transform) + 4 (sOutboundAction) + 2 (encap) + 4 (YANG pattern) = 14 件抽出。中間ファイル: `meta/_intermediate/cdb-flow/dash-routing-types-constants.md`
<!-- /constants -->

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`DASH_ROUTE_TABLE`](dash-route-table.md)（routing_type を leafref 参照）
- CONFIG_DB: [`DASH_VNET_MAPPING_TABLE`](dash-vnet-mapping-table.md)（routing_type フィールドで本テーブルを参照）

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-swss/orchagent/dash/dashorch.cpp` — `doTaskRoutingTypeTable()` (L473-537), `addRoutingTypeEntry()` (L441-455), `getRouteTypeActions()` (L82-94). <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/dash/dashorch.cpp>

[^2]: `sonic-swss/orchagent/dash/dashvnetorch.cpp` — `addOutboundCaToPa()` (L300-410), encap_type/vni 変換 (L322-344). <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/dash/dashvnetorch.cpp>

[^3]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dash.yang` — `DASH_ROUTING_TYPE` container (L356-398). <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-dash.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型的な routing type 設定例

```bash
# VNET encap (VXLAN) routing type の確認
sonic-db-cli APPL_DB keys 'DASH_ROUTING_TYPE_TABLE|*'
sonic-db-cli APPL_DB hgetall 'DASH_ROUTING_TYPE_TABLE|vnet_encap'

# 設定済み routing type の一覧
sonic-db-cli APPL_DB keys 'DASH_ROUTING_TYPE_TABLE|*' | sort
```

### よくある問題

- **encap_type 未指定でのエラー**: `action_type=staticencap` を指定しながら `encap_type` を省略すると orchagent が `SWSS_LOG_ERROR` を記録し、VNET マッピングのプログラムが失敗する
- **routing type 名の大文字小文字**: キー名は小文字で書き込むのが正しい。orchagent が内部で大文字変換するが、YANG pattern は小文字のみ許容
- **更新は削除→再作成が必要**: `addRoutingTypeEntry()` は既存エントリをスキップするため、routing type の変更は DEL → SET の順で実施する
<!-- /ops-hint -->
