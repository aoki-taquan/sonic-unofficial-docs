---
title: ROUTE_TABLE (STATE_DB / APPL_STATE_DB)
description: "STATE_DB ROUTE_TABLE と APPL_STATE_DB ROUTE_TABLE — RouteOrch がデフォルト経路の存在状態と経路処理結果を書き込む読み取り専用テーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/routeorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/response_publisher.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - ROUTE
    - STATIC_ROUTE
  cli:
    - show ip route
    - show ipv6 route
  yang: []
---

# ROUTE_TABLE (STATE_DB / APPL_STATE_DB)

## 概要

SONiC には `ROUTE_TABLE` という名称のテーブルが **3 つの DB** に存在する。このページでは `orchagent` (`RouteOrch`) が書き込む **STATE_DB** と **APPL_STATE_DB** の 2 テーブルを扱う。

| DB | 用途 | 書込み主体 |
|----|------|-----------|
| `APPL_DB` | fpmsyncd が FRR 経路を書き込む（[ROUTE_TABLE (APPL_DB)](route.md) 参照） | `fpmsyncd` |
| **`STATE_DB`** | デフォルト経路 (0.0.0.0/0 / ::0/0) の存在状態のみを書き込む | `RouteOrch` |
| **`APPL_STATE_DB`** | SAI への経路プログラミング結果（`protocol` + `err_str`）を書き込む | `RouteOrch` via `ResponsePublisher` |

!!! warning "設定 DB ではない"
    STATE_DB / APPL_STATE_DB の `ROUTE_TABLE` はどちらも **読み取り専用の状態情報**。経路の追加・削除は APPL_DB の `ROUTE_TABLE` または CONFIG_DB の `STATIC_ROUTE` で行う。

<!-- cdb-mermaid -->
### データフロー

```mermaid
flowchart LR
  APPDB[("APPL_DB\nROUTE_TABLE")]
  OA["RouteOrch\norchagent"]
  SAI["SAI\nsai_route_api"]
  STATEDB[("STATE_DB\nROUTE_TABLE\nstate=ok/na")]
  APPLSTATE[("APPL_STATE_DB\nROUTE_TABLE\nprotocol + err_str")]

  APPDB -->|"subscribe"| OA
  OA -->|"updateDefRouteState()"| STATEDB
  OA -->|"SAI call"| SAI
  OA -->|"publishRouteState()"| APPLSTATE
```

<!-- /cdb-mermaid -->

---

## STATE_DB ROUTE_TABLE

### key 構造

```text
ROUTE_TABLE|<prefix>
```

`<prefix>` は IPv4 デフォルト経路（`0.0.0.0/0`）または IPv6 デフォルト経路（`::0/0` / `::/0`）のみ。  
一般のユニキャスト経路は STATE_DB の ROUTE_TABLE には書き込まれない。

### フィールド一覧

| フィールド | 型 | 取り得る値 | 説明 |
|-----------|----|-----------|----|
| `state` | string | `"ok"` / `"na"` | デフォルト経路が存在する場合 `"ok"`、削除された場合 `"na"` |

### 書き込みトリガー

`RouteOrch::updateDefRouteState(string ip, bool add)` が呼ばれたとき:

- `add=true` → `state = "ok"`（デフォルト経路をプログラム完了）
- `add=false` → `state = "na"`（デフォルト経路を削除）

<!-- defaults -->
## コード由来デフォルト詳細 (Phase A)

<!-- evidence: meta/_intermediate/cdb-flow/route-state-defaults.md -->

### STATE_DB `state` フィールド

ソース: `orchagent/routeorch.cpp` lines 287–295[^1]

```cpp
void RouteOrch::updateDefRouteState(string ip, bool add)
{
    vector<FieldValueTuple> tuples;
    string state = add?"ok":"na";
    FieldValueTuple tuple("state", state);
    tuples.push_back(tuple);

    m_stateDefaultRouteTb->set(ip, tuples);
}
```

| 条件 | `state` の値 |
|------|-------------|
| デフォルト経路を SAI に追加成功後 | `"ok"` |
| デフォルト経路を SAI から削除後 | `"na"` |
| 一般ユニキャスト経路 | **エントリ自体が存在しない** |

`"na"` は「フィールド不在」ではなく「デフォルト経路なし」という**明示的状態**である点に注意。フィールドが存在しない状態はデフォルト経路が一度もプログラムされていない初期状態のみ。

### APPL_STATE_DB `protocol` フィールド

ソース: `orchagent/routeorch.cpp` lines 3185–3202[^1]

```cpp
void RouteOrch::publishRouteState(const RouteBulkContext& ctx, const ReturnCode& status)
{
    std::vector<FieldValueTuple> fvs;

    if (ctx.is_set)
    {
        fvs.emplace_back("protocol", ctx.protocol);
    }

    m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, fvs, status, replace);
}
```

- SET 操作時: `protocol` フィールドを `ctx.protocol` の値で書き込む
- DEL 操作時: `fvs` が空 → `ResponsePublisher` がエントリ全体を APPL_STATE_DB から削除
- `ctx.protocol` の初期値は `""` で、APPL_DB の `protocol` フィールドが存在する場合のみ上書きされる

| APPL_DB の `protocol` フィールド | APPL_STATE_DB の `protocol` 値 |
|---------------------------------|-------------------------------|
| `"bgp"` 等が存在する | `"bgp"` 等（そのままコピー） |
| フィールド不在 | `""` （空文字列） |

### APPL_STATE_DB `err_str` フィールド

`ResponsePublisher::publish()` が自動付与するフィールド[^2]:

```cpp
swss::FieldValueTuple err_str("err_str", PrependedComponent(status) + status.message());
intent_attrs_copy.insert(intent_attrs_copy.begin(), err_str);
```

| SAI 結果 | `err_str` の値 |
|---------|----------------|
| 成功 | `"SWSS_RC_SUCCESS"` |
| SAI エラー | `"[SAI] <エラーメッセージ>"` |
| その他失敗 | `"<エラーメッセージ>"` |

成功時は APPL_STATE_DB に `protocol` と `err_str` の 2 フィールドが書き込まれる。失敗時は通知チャンネルに送出されるが APPL_STATE_DB への書き込みはスキップされる。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

> 証跡: `meta/_intermediate/cdb-flow/route-state-ordering.md`

STATE_DB / APPL_STATE_DB への `ROUTE_TABLE` 書き込みは `RouteOrch` が SAI 操作を完了させた後に行われる。以下に強制先行条件と推奨順序を示す。

### 強制先行条件

| 順序 | 先行リソース | 後続 | 違反時の挙動 | evidence |
|------|-------------|------|-------------|---------|
| 1 | `PORT` 初期化完了（`allPortsReady()`） | STATE_DB / APPL_STATE_DB への動的書き込み | `RouteOrch::doTask()` が即 `return`。APPL_DB の ROUTE_TABLE イベントを処理しないため書き込みも発生しない | `routeorch.cpp:609-611` |
| 2 | SAI `create_route_entry()` 成功 | `STATE_DB ROUTE_TABLE` への `state=ok` 書き込み | SAI 失敗時は `updateDefRouteState()` が呼ばれず STATE_DB が未更新のまま。デフォルト経路のみが対象 | `routeorch.cpp:2700-2703` |

### 推奨先行条件

| 順序 | 先行リソース | 後続 | 理由 | evidence |
|------|-------------|------|------|---------|
| 3 | SAI バルク操作完了 | `APPL_STATE_DB ROUTE_TABLE` への `err_str`/`protocol` 書き込み | `publishRouteState()` はバルク応答処理後に呼ばれる。SAI 失敗時も `err_str` が書き込まれる点が STATE_DB と異なる | `routeorch.cpp:920-923, 2729, 2970` |

### 特殊シーケンス

| 操作 | タイミング | 根拠 |
|------|---------|------|
| `STATE_DB ROUTE_TABLE\|0.0.0.0/0 state=na` の初期書き込み | `RouteOrch` コンストラクタ実行時（`allPortsReady()` 不要） | orchagent 起動直後から `state=na` が存在する。ポート初期化前でも確認可能 | <!-- evidence: routeorch.cpp:126-130, 155-156 --> |
| `STATE_DB state=na` 書き込み（DEL パス） | SAI `set_route_entry` で packet_action を DROP に変更成功後 | DEL 失敗時は `state=na` にならず `state=ok` のまま残る | <!-- evidence: routeorch.cpp:2856 --> |

<!-- /ordering -->

---

## APPL_STATE_DB ROUTE_TABLE

### key 構造

```text
ROUTE_TABLE:<prefix>
ROUTE_TABLE:<vrf_name>:<prefix>
```

APPL_DB の `ROUTE_TABLE` と同一キー空間。orchagent が SAI プログラミングに成功した後にのみ書き込まれる。

### フィールド一覧

| フィールド | 型 | 書込み条件 | 説明 |
|-----------|----|-----------|----|
| `protocol` | string | SET 操作かつ SAI 成功時 | APPL_DB から引き継いだ経路プロトコル名（`bgp`、`static`、`kernel` 等、または `""`） |
| `err_str` | string | SET / DEL 操作時 | SAI 操作結果メッセージ。成功時 `"SWSS_RC_SUCCESS"` |

---

## 購読者 (consumer)

| プロセス | 参照 DB / テーブル | 用途 |
|---------|-----------------|------|
| `fpmsyncd` | APPL_STATE_DB `ROUTE_TABLE` | SAI プログラミング結果を RESPONSE_CHANNEL 経由で受け取り、FRR へフィードバック |
| `route_check.py` | APPL_STATE_DB `ROUTE_TABLE` | route_check が APPL_DB と APPL_STATE_DB の整合を確認 |
| BGP suppress / error-handling | STATE_DB `ROUTE_TABLE` | デフォルト経路の有無に基づく advertise 制御 |

## 関連リファレンス

- APPL_DB: [`ROUTE_TABLE (APPL_DB)`](route.md) — fpmsyncd が書き込む経路テーブル
- CONFIG_DB: [`STATIC_ROUTE`](static-route.md) — 静的経路の設定元

## 引用元

[^1]: RouteOrch STATE/APPL_STATE 書込み実装: `orchagent/routeorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/routeorch.cpp#L287>
[^2]: ResponsePublisher err_str 付与: `orchagent/response_publisher.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/response_publisher.cpp#L102>
[^3]: STATE_ROUTE_TABLE_NAME 定数: `common/schema.h`. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h#L494>

<!-- ops-hint -->
## 運用ヒント

### 確認コマンド

```bash
# STATE_DB のデフォルト経路状態を確認
sonic-db-cli STATE_DB hgetall 'ROUTE_TABLE|0.0.0.0/0'
sonic-db-cli STATE_DB hgetall 'ROUTE_TABLE|::/0'

# APPL_STATE_DB の経路プログラミング結果を確認
sonic-db-cli APPL_STATE_DB hgetall 'ROUTE_TABLE:10.0.0.0/24'

# route_check.py でテーブル整合確認
sudo route_check.py
```

### 典型エントリ例

```
# STATE_DB: デフォルト経路あり
STATE_DB ROUTE_TABLE|0.0.0.0/0
  state: ok

# STATE_DB: デフォルト経路なし（削除後）
STATE_DB ROUTE_TABLE|0.0.0.0/0
  state: na

# APPL_STATE_DB: BGP 経路のプログラミング成功
APPL_STATE_DB ROUTE_TABLE:10.1.0.0/24
  err_str: SWSS_RC_SUCCESS
  protocol: bgp
```

### よくある問題

- STATE_DB の `state=na` が残る → デフォルト経路が FRR から削除されたが APPL_DB からも消えているか確認（`sonic-db-cli APPL_DB hgetall 'ROUTE_TABLE:0.0.0.0/0'`）
- APPL_STATE_DB にエントリがない → SAI プログラミングに失敗している可能性。`/var/log/syslog` の orchagent ログで `err_str` を確認
<!-- /ops-hint -->
