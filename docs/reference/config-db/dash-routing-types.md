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
