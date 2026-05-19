---
title: DASH_ROUTE_RULE_TABLE テーブル
description: "DASH_ROUTE_RULE_TABLE — DASH インバウンドルーティングエントリ (Inbound Routing Rule) を保持するテーブル。ENI・VNI・SIP プレフィックス・優先度をキーとして、VNI トンネルデカプセルと PA 検証を制御する。"
area: reference
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/dash/dashrouteorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/SONiC
    path: doc/dash/dash-sonic-hld.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - DASH_ROUTE_RULE_TABLE
    - DASH_ENI_TABLE
    - DASH_VNET_TABLE
    - DASH_PREFIX_TAG_TABLE
  yang: []
---

# DASH_ROUTE_RULE_TABLE テーブル

## 概要

DASH (Disaggregated APIs for SONiC Hosts) のインバウンドルーティングエントリ (Inbound Routing Rule) を保持するテーブル[^1]。

外部から DASH スイッチへ流入するパケット (インバウンド方向) が VXLAN トンネルのデカプセルを受けるルールを定義する。エントリは ENI・VNI・SIP プレフィックス (または PREFIX TAG)・優先度の 4 要素で一意に識別され、PA 検証の要否と VNET マッピングを制御する。

`DashRouteOrch::doTaskRouteRuleTable()` (`sonic-swss/orchagent/dash/dashrouteorch.cpp`) が ZMQ 経由で受信した Protobuf メッセージを解釈し、SAI の `sai_dash_inbound_routing_api` を通じてデータプレーンに `sai_inbound_routing_entry_t` を作成する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("APP_DB / ZMQ<br/>DASH_ROUTE_RULE_TABLE")]
  OA["DashRouteOrch<br/>(dashrouteorch.cpp)"]
  SAI["SAI DASH Inbound Routing API<br/>(sai_dash_inbound_routing_api)"]
  CDB --> OA --> SAI
```

!!! note "凡例"
    APP_DB (ZMQ 経由) から SAI までの典型経路。詳細・例外は本ページ本文を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
DASH_ROUTE_RULE_TABLE:<eni>:<vni>:<prefix>[:<priority>]
```

| セグメント | 型 | 説明 |
|-----------|----|----|
| `<eni>` | string | ENI の MAC アドレス文字列 (例: `F4939FEFC47E`)。`DASH_ENI_TABLE` のキーと対応 |
| `<vni>` | uint32 | VXLAN VNI。インバウンドパケットのアウターヘッダ VNI に一致するか検査する |
| `<prefix>` | string | SIP プレフィックス (CIDR 形式) または `DASH_PREFIX_TAG_TABLE` のタグ名 |
| `<priority>` | uint32 | ルール優先度 (省略可能)。省略時は `0` にフォールバック。低い値ほど高優先 |

`<priority>` フィールドは旧フォーマット互換のため省略可能。orchagent は `<prefix>` の末尾セグメントが数字のみか検査し、数字でなければ全体を `<prefix>` として扱い `priority=0` に fallback する (`dashrouteorch.cpp:605-623`)。

## フィールド

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|----|-----------|------|
| `action_type` | routing_type enum | 任意 | — | 非推奨 (deprecated)。`ROUTING_TYPE_*` を指定する旧フィールド。新規実装では key の priority フィールドを使う |
| `priority` | uint32 | 任意 | `0` | 非推奨 (deprecated)。優先度は key のセグメントに移動済み |
| `protocol` | uint32 | 任意 | `0` (any) | マッチするプロトコル番号。`0` はプロトコルを問わずすべてにマッチ |
| `vnet` | string | 任意 | 未設定 | PA 検証やマッピングに使用する VNET 名 (`DASH_VNET_TABLE` の key) |
| `pa_validation` | bool | 任意 | `false` | `true` 時: SAI に `TUNNEL_DECAP_PA_VALIDATE` を渡し PA 検証を行う。`false` 時: `TUNNEL_DECAP` のみ |
| `metering_class_or` | uint32 | 任意 | 未設定 | メータリングクラス `or` ビット (`SAI_INBOUND_ROUTING_ENTRY_ATTR_METER_CLASS_OR`) |
| `metering_class_and` | uint32 | 任意 | 未設定 | メータリングクラス `and` ビット (`SAI_INBOUND_ROUTING_ENTRY_ATTR_METER_CLASS_AND`) |
| `region` | string | 任意 | 未設定 | 任意のリージョン ID。ベンダー最適化向け文字列。orchagent の現行コードには処理なし |

## 制約

- ENI (`DASH_ENI_TABLE`) が未登録の場合、`addInboundRouting` が `false` を返しリトライ
- `vnet` を指定した場合、`DASH_VNET_TABLE` に登録済みでなければリトライ (`gVnetNameToId` に未登録)
- `sip` / `sip_mask` は key の `<prefix>` を `IpPrefix` パースして得る。不正 CIDR は例外

## 購読者

- `DashRouteOrch` (`sonic-swss/orchagent/dash/dashrouteorch.cpp`): インバウンドルーティングエントリを受信し、`sai_dash_inbound_routing_api->create_inbound_routing_entry()` でデータプレーンにエントリを作成する。CRM リソースカウンタ (`CRM_DASH_IPV4_INBOUND_ROUTING` / `CRM_DASH_IPV6_INBOUND_ROUTING`) のインクリメントも担う

## 関連 CONFIG_DB

- [`DASH_ENI_TABLE`](dash-eni.md): ENI エントリ。`eni_id` を `sai_inbound_routing_entry_t` に渡す
- [`DASH_VNET_TABLE`](dash-vnet.md): `vnet` フィールドで参照する VNET (PA 検証・マッピング)
- [`DASH_PREFIX_TAG_TABLE`](dash-acl.md): `<prefix>` にタグ名を使用する場合の参照先
- [`DASH_ROUTE_TABLE`](route.md): アウトバウンドルーティング (対となるテーブル)

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 |
|------|------|
| ENI が `DASH_ENI_TABLE` に未登録 | `dash_orch_->getEni()` が `nullptr` → `addInboundRouting` が `false` → リトライ |
| `vnet` 指定時に `DASH_VNET_TABLE` 未登録 | `gVnetNameToId.find()` miss → リトライ |
| protobuf メッセージが不正 | `parsePbMessage()` 失敗 → エントリを consumer から削除 (リトライなし) |
| key に `<priority>` がない (旧フォーマット) | orchagent が末尾セグメントを数字判定し、数字でなければ `priority=0` で処理を続行 |
| 同一キーのエントリが既存 | `SAI_STATUS_ITEM_ALREADY_EXISTS` → `addInboundRoutingPost` が `false` を返し bulker 再試行 |
| `pa_validation` 未設定 | proto3 bool デフォルト `false` → `SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP` を設定 |
<!-- /cdb-exceptions -->

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

YANG / proto3 デフォルト以外の実装由来 fallback。`DashRouteOrch::addInboundRouting()` (`dashrouteorch.cpp:421-477`) の SAI 属性組み立てロジックから導出。

| フィールド | コード由来デフォルト | fallback 源 |
|-----------|-------------------|------------|
| `priority` (key) | `0` | key にセグメントがない旧フォーマット互換 — dashrouteorch.cpp:605 `priority = 0;`; 末尾が全数字でなければ prefix 全体をプレフィックスとみなし priority=0 |
| `protocol` | `0` (any) | proto3 uint32 デフォルト; HLD:613 "0 (any)" |
| `pa_validation` | `false` → `SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP` | proto3 bool デフォルト=false → 三項演算子で `TUNNEL_DECAP` が選択される — dashrouteorch.cpp:450 |
| `vnet` | SAI 未設定 (属性 push なし) | `has_vnet()` false → `SAI_INBOUND_ROUTING_ENTRY_ATTR_SRC_VNET_ID` を push しない — dashrouteorch.cpp:453-458 |
| `metering_class_or` | SAI 未設定 | `has_metering_class_or()` false → push しない — dashrouteorch.cpp:460-464 |
| `metering_class_and` | SAI 未設定 | `has_metering_class_and()` false → push しない — dashrouteorch.cpp:466-470 |
| `region` | SAI 未設定 | dashrouteorch.cpp に `region` を処理するコード未確認 (HLD に記載あり) |

### 補足

- **`pa_validation` の HLD/コード乖離**: HLD (dash-sonic-hld.md:615) は "Default is set to true" と記載しているが、proto3 の `bool` フィールドのデフォルトは `false` であり、コントローラが明示的に `pa_validation=true` を送らない限り orchagent は `TUNNEL_DECAP` (PA 検証なし) で動作する。discrepancy として記録する。

- **`priority` の二重表現**: priority はキーの最終セグメントと protobuf `RouteRule.priority` フィールドの両方に存在する。orchagent はキーセグメントを正として使用し (`ctxt.priority` に代入)、protobuf フィールドは `DashDumpPlugin` の `return_fields` 参照のみに使われる。

- **`region` フィールド**: HLD にスキーマとして定義されているが、`dashrouteorch.cpp` に `region` を読み込む `has_region()` パターンは確認できない。SAI への反映なし。HLD と実装の乖離 (discrepancy) として記録する。
<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

> 調査証跡: `meta/_intermediate/cdb-flow/route-rule-ordering.md`

### SET 時の先行必須テーブル

| # | 先行テーブル | 条件 | 理由 | 失敗時の挙動 |
|---|------------|------|------|------------|
| 1 | `DASH_ENI_TABLE` | 常時 | `addInboundRouting()` が `dash_orch_->getEni(ctxt.eni)` で ENI 存在を確認。`nullptr` を返すとリトライ | `return false` → ループ `it++` で自動リトライ |
| 2 | `DASH_VNET_TABLE` | `vnet` フィールドが protobuf に存在する場合のみ | `gVnetNameToId.find(ctxt.metadata.vnet())` が miss するとリトライ | `return false` → ループ `it++` で自動リトライ |

どちらも `task_need_retry` 相当（`return false` + ループ継続）の自動リトライ。
`DASH_ENI_TABLE` が登録され、かつ `vnet` 指定時は `DASH_VNET_TABLE` も登録されて初めて SAI に反映される。

### DEL 時の順序制約

`removeInboundRouting()` は依存テーブルの存在チェックを行わず SAI entry を直接削除する。
`DASH_ENI_TABLE` / `DASH_VNET_TABLE` の削除順序は問わない（逆参照エラーなし）。

### 起動時シーケンス

```
DashOrch が DASH_ENI_TABLE を処理 → ENI 登録完了
  ↓
（vnet フィールドあり時）DashVnetOrch が DASH_VNET_TABLE を処理 → gVnetNameToId に登録
  ↓
DashRouteOrch が DASH_ROUTE_RULE_TABLE エントリを処理 → SAI 反映
```

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`DashRouteOrch` は `DASH_ROUTE_RULE_TABLE` の処理時に以下の参照テーブル・リソースを読み書きする。

### 入力参照（DashRouteOrch が読み取るテーブル）

| テーブル / リソース | DB | 参照タイミング | 条件 | evidence |
|---|---|---|---|---|
| `DASH_ENI_TABLE` | APPL_DB (ZMQ) | `addInboundRouting()` 呼び出し時 | **常時必須** — ENI 未登録なら `return false` でリトライ | `dashrouteorch.cpp:425-428` |
| `DASH_VNET_TABLE` (`gVnetNameToId`) | APPL_DB (ZMQ) | `addInboundRouting()` 呼び出し時 | `vnet` フィールドが protobuf に存在する場合のみ — 未登録なら `return false` でリトライ | `dashrouteorch.cpp:430-433` |

**`DASH_ENI_TABLE` の補足**: `dash_orch_->getEni(ctxt.eni)` は `DashOrch` が管理する ENI マップを内部参照する。`addInboundRoutingPost()` でも `eni_id` を再取得し `sai_inbound_routing_entry_t.eni_id` に代入する (`dashrouteorch.cpp:521`)。

**`DASH_VNET_TABLE` の補足**: グローバル変数 `gVnetNameToId` は `DashVnetOrch` が `DASH_VNET_TABLE` エントリを処理した時点で登録される。`vnet` フィールドを持つルールは `DASH_VNET_TABLE` の処理完了後でないと SAI に反映されない。

### 出力参照（DashRouteOrch が書き込むテーブル）

| テーブル | DB | 書き込みタイミング | フィールド | evidence |
|---|---|---|---|---|
| `DASH_ROUTE_RULE_TABLE` (result) | APPL_STATE_DB | SAI 成功/失敗後 | `result`, `err_str` | `dashrouteorch.cpp:644,705` |

`dash_route_rule_result_table_` (`app_state_db` 上の `DASH_ROUTE_RULE_TABLE`) に SAI プログラミング結果を書き戻す。コントローラ側や DPU HA コンポーネントがプログラミング完了を確認するために使用する。SET 成功 → `writeResultToDB`、DEL 成功 → `removeResultFromDB` が呼ばれる (`dashrouteorch.cpp:644,656,705,712`)。

### 副作用: CRM リソースカウンタ

| カウンタ | 操作 | タイミング | evidence |
|---|---|---|---|
| `CRM_DASH_IPV4_INBOUND_ROUTING` | inc / dec | `addInboundRoutingPost()` 成功 / `removeInboundRoutingPost()` 成功 | `dashrouteorch.cpp:507,546` |
| `CRM_DASH_IPV6_INBOUND_ROUTING` | inc / dec | 同上 (`sip.isV4()` が false の場合) | `dashrouteorch.cpp:507,546` |

SIP アドレスファミリ（IPv4 / IPv6）に応じて異なる CRM カウンタを更新する。`CrmOrch` がリソース上限監視に使用する。

Evidence: `dashrouteorch.cpp` 全体スキャン; 詳細スキャンノートは `meta/_intermediate/cdb-flow/route-rule-cross-refs.md` を参照。
<!-- /cross-refs -->

<!-- constants -->
## ハードコード定数 (Phase E)

<!-- evidence: meta/_intermediate/cdb-flow/route-rule-constants.md -->

`DashRouteOrch` が `DASH_ROUTE_RULE_TABLE` 処理時に使用する、CONFIG_DB / YANG で管理されないハードコード定数の一覧。出典は `orchagent/dash/dashrouteorch.cpp`・`orchagent/dash/dashorch.h`・`common/schema.h`・`orchagent/crmorch.h`。

### 結果コード定数 (`dashorch.h`)

| 定数名 | 値 | 用途 | evidence |
|--------|-----|------|---------|
| `DASH_RESULT_SUCCESS` | `0` | SET / DEL 処理ループの初期値。SAI 成功時にそのまま result テーブルへ書き込まれる | `dashorch.h:35`; `dashrouteorch.cpp:585, 678` |
| `DASH_RESULT_FAILURE` | `1` | `addInboundRoutingPost()` が SAI バルク create 失敗を検出した場合に上書きされる | `dashorch.h:36`; `dashrouteorch.cpp:702` |

### テーブル名定数 (`schema.h`)

| 定数名 | 値 | 用途 | evidence |
|--------|-----|------|---------|
| `APP_DASH_ROUTE_RULE_TABLE_NAME` | `"DASH_ROUTE_RULE_TABLE"` | `dash_route_rule_result_table_` の構築時に使用。APPL_STATE_DB への SAI プログラミング結果書き戻し先テーブル名 | `schema.h:187`; `dashrouteorch.cpp:57` |

### CRM リソースタイプ定数 (`crmorch.h`)

| 定数名 | 分岐条件 | 用途 | evidence |
|--------|----------|------|---------|
| `CRM_DASH_IPV4_INBOUND_ROUTING` | `ctxt.sip.isV4() == true` | IPv4 SIP を持つ inbound routing エントリの CRM リソースカウンタ (inc/dec) | `crmorch.h:41`; `dashrouteorch.cpp:507, 546` |
| `CRM_DASH_IPV6_INBOUND_ROUTING` | `ctxt.sip.isV4() == false` | IPv6 SIP を持つ inbound routing エントリの CRM リソースカウンタ (inc/dec) | `crmorch.h:42`; `dashrouteorch.cpp:507, 546` |

### SAI アクション定数

| 定数名 | 選択条件 | 用途 | evidence |
|--------|----------|------|---------|
| `SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP_PA_VALIDATE` | `pa_validation == true` | PA アドレス検証付きのトンネルデカプセルを SAI に指示 | `dashrouteorch.cpp:450` |
| `SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP` | `pa_validation == false` (proto3 デフォルト) | PA 検証なしのトンネルデカプセルを SAI に指示 | `dashrouteorch.cpp:450` |

三項演算子 `ctxt.metadata.pa_validation() ? SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP_PA_VALIDATE : SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP` で選択される (`dashrouteorch.cpp:450`)。

### SAI 属性 ID 定数（条件付き push）

| 定数名 | push 条件 | evidence |
|--------|-----------|---------|
| `SAI_INBOUND_ROUTING_ENTRY_ATTR_ACTION` | 常時 | `dashrouteorch.cpp:448` |
| `SAI_INBOUND_ROUTING_ENTRY_ATTR_SRC_VNET_ID` | `has_vnet()` が true の場合のみ | `dashrouteorch.cpp:453-458` |
| `SAI_INBOUND_ROUTING_ENTRY_ATTR_METER_CLASS_OR` | `has_metering_class_or()` が true の場合のみ | `dashrouteorch.cpp:460-464` |
| `SAI_INBOUND_ROUTING_ENTRY_ATTR_METER_CLASS_AND` | `has_metering_class_and()` が true の場合のみ | `dashrouteorch.cpp:466-470` |

protobuf の `has_*()` で各フィールドの存在を確認してから `inbound_routing_attrs` に push する。フィールド不在時は SAI 属性を送らないため SAI ハードウェアのデフォルト値が適用される。

<!-- /constants -->

<!-- failure -->
## 失敗挙動 (Phase D)

<!-- evidence: meta/_intermediate/cdb-flow/route-rule-failure.md -->

`DASH_ROUTE_RULE_TABLE` の処理は 2 フェーズ bulker パターンを採用している。`addInboundRouting()` (pre-op) で SAI エントリを bulker にエンキューし、`inbound_routing_bulker_.flush()` 後に `addInboundRoutingPost()` (post-op) で結果を評価する。

### SET 操作の失敗パス

#### 1. 依存テーブル未登録 — 自動リトライ

`addInboundRouting()` (`dashrouteorch.cpp:421-477`) で依存テーブル未登録を検出した場合は `return false` を返す。`doTaskRouteRuleTable()` のループは `it++` でイベントを `m_toSync` に残し、次の orchagent タスクループで再処理する。

| 条件 | 理由 | 挙動 |
|---|---|---|
| `DASH_ENI_TABLE` に ENI 未登録 | `dash_orch_->getEni(ctxt.eni) == nullptr` | `return false` → リトライ |
| `DASH_VNET_TABLE` に vnet 未登録 | `gVnetNameToId.find()` miss | `return false` → リトライ |

#### 2. protobuf パース失敗 — ドロップ（リトライなし）

`parsePbMessage()` が失敗した場合はエントリを `consumer.m_toSync.erase(it)` で消費して処理を終了する (`dashrouteorch.cpp:635-640`)。イベントはドロップされ、リトライは行われない。

```
SWSS_LOG_WARN("Requires protobuff at InboundRouting :%s", key.c_str());
it = consumer.m_toSync.erase(it);
```

#### 3. SAI create 失敗 — `handleSaiCreateStatus` による振り分け

`addInboundRoutingPost()` (`dashrouteorch.cpp:479-515`) で SAI バルク結果を評価する。

| SAI ステータス | 処置 |
|---|---|
| `SAI_STATUS_SUCCESS` | CRM カウンタをインクリメントして `return true`（成功） |
| `SAI_STATUS_ITEM_ALREADY_EXISTS` | `return false`（bulker 再試行） |
| その他エラー | `handleSaiCreateStatus()` → `parseHandleSaiStatusFailure()` で task_need_retry / task_failed を判定 |

`task_failed` 判定時は `parseHandleSaiStatusFailure()` がエラーログを出力し `true` を返す（erase）。`task_need_retry` の場合は `false` を返してリトライ。

### DEL 操作の失敗パス

#### 4. SAI remove 失敗

`removeInboundRoutingPost()` (`dashrouteorch.cpp:535-563`) で SAI 削除結果を評価する。

| SAI ステータス | 処置 |
|---|---|
| `SAI_STATUS_SUCCESS` | CRM カウンタをデクリメントして `return true`（成功） |
| `SAI_STATUS_NOT_EXECUTED` | `return false`（bulker 再試行） |
| その他エラー | `handleSaiRemoveStatus()` → `parseHandleSaiStatusFailure()` で判定 |

### 結果テーブルへの書き込み失敗

`writeResultToDB()` は SET 成功後に呼ばれる (`dashrouteorch.cpp:644`)。SAI 失敗時は呼ばれないため `DASH_ROUTE_RULE_TABLE` (result) には成功エントリのみ書き込まれる。DEL 成功後は `removeResultFromDB()` でエントリを削除する (`dashrouteorch.cpp:656`)。

### 失敗パスまとめ

| 失敗シナリオ | イベント消費 | result テーブル | リトライ |
|---|---|---|---|
| ENI 未登録 (pre-op) | m_toSync に残留 | 書き込みなし | 自動リトライ |
| vnet 未登録 (pre-op) | m_toSync に残留 | 書き込みなし | 自動リトライ |
| protobuf パース失敗 | erase（ドロップ） | 書き込みなし | なし |
| SAI_STATUS_ITEM_ALREADY_EXISTS | m_toSync に残留 | 書き込みなし | bulker 再試行 |
| SAI create 失敗 (task_need_retry) | m_toSync に残留 | 書き込みなし | 自動リトライ |
| SAI create 失敗 (task_failed) | erase（ドロップ） | 書き込みなし | なし |
| SAI remove 失敗 (NOT_EXECUTED) | m_toSync に残留 | 削除されない | bulker 再試行 |
<!-- /failure -->

[^1]: sonic-net/SONiC `doc/dash/dash-sonic-hld.md` §3.2.10 "ROUTE RULE TABLE - INBOUND" (ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
