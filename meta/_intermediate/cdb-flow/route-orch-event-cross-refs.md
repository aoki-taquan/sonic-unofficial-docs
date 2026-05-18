# route-orch-event — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/route-orch-event.md` Phase C 追加分。
本ページの主題は **RouteOrch の通知機構**（ResponsePublisher / NextHopObserver）であり、
以下の 2 つの方向で暗黙参照が存在する:

1. **ResponsePublisher** — fpmsyncd が `RESPONSE_CHANNEL` を購読するかどうかを制御する外部テーブル
2. **NextHopObserver** — `attach()` / `detach()` を呼ぶ側の Orch が依存する入力テーブル

`sonic-swss/orchagent/routeorch.cpp` / `routeorch.h` / `orchagent/response_publisher.cpp` /
`fpmsyncd/fpmsyncd.cpp` / `orchagent/mirrororch.cpp` / `orchagent/natorch.cpp` を精読した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/routeorch.cpp` | `publishRouteState()` (L3185), `notifyNextHopChangeObservers()` (L1270), `attach()` (L308) |
| `sonic-swss/orchagent/response_publisher.cpp` | `ResponsePublisher::publish()` — APPL_STATE_DB + RESPONSE_CHANNEL 書き込み |
| `sonic-swss/fpmsyncd/fpmsyncd.cpp` | `suppress-fib-pending` を読んで RESPONSE_CHANNEL 購読の有無を決定 (L78–120, L278–307) |
| `sonic-swss/orchagent/mirrororch.cpp` | `m_routeOrch->attach(this, entry.dstIp)` (L517) — ミラーセッション設定時に NextHopObserver として登録 |
| `sonic-swss/orchagent/natorch.cpp` | `m_routeOrch->attach(this, translatedIp)` (L414, L458, L504, L591) — NAT エントリ設定時に登録 |
| `sonic-swss/scripts/route_check.py` | `APPL_STATE_DB ROUTE_TABLE` の `err_str` を読んで整合チェック (L767–770) |

## YANG leafref

本ページの通知機構（ResponsePublisher / NextHopObserver）は YANG 未定義。
leafref は存在しない。すべての依存が実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. CONFIG_DB `DEVICE_METADATA|localhost.suppress-fib-pending` (ResponsePublisher 購読制御)

- **参照先テーブル**: `CONFIG_DB DEVICE_METADATA` (`CFG_DEVICE_METADATA_TABLE_NAME`)
- **参照方向**: 読み取り（起動時 + 動的変更を Subscribe 経由で検知）
- **条件**: fpmsyncd 起動時、および DEVICE_METADATA 変更通知を受け取ったとき
- **意味**:
  - `suppress-fib-pending == "enabled"` の場合のみ `NotificationConsumer` を生成し、`APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` を Redis Pub/Sub で購読する (fpmsyncd.cpp L113–117)
  - 実行中に `suppress-fib-pending` が `"enabled"` に変更された場合も動的に購読を開始 (fpmsyncd.cpp L278–289)
  - `"enabled"` 以外に変更された場合は購読を停止 (fpmsyncd.cpp L300–302)
  - この設定が欠如したまま fpmsyncd が稼働すると、`publishRouteState()` が送出する全通知は Redis の Pub/Sub バッファを素通りして消失する
- **evidence**: `fpmsyncd.cpp` L78, L82–83, L112–117, L278–302

### 2. APPL_STATE_DB `ROUTE_TABLE` (ResponsePublisher の書き込み先)

- **参照先テーブル**: `APPL_STATE_DB ROUTE_TABLE`
- **参照方向**: 書き込み（RouteOrch → APPL_STATE_DB）
- **条件**: SAI SET 操作成功時のみ
- **意味**:
  - `ResponsePublisher::publish()` が `protocol` と `err_str` フィールドを書き込む (response_publisher.cpp L93–148)
  - `route_check.py` が `APPL_STATE_DB ROUTE_TABLE` の `err_str` を読んで APPL_DB との整合を確認する (route_check.py L767–770)
  - fpmsyncd の `onRouteResponse()` が `RESPONSE_CHANNEL` 通知をトリガに `APPL_STATE_DB` の `err_str` を参照して suppress-fib-pending 応答を FRR へ返す (routesync.cpp L3156–3190)
- **evidence**: `response_publisher.cpp` L93–148, `route_check.py` L767–770

### 3. `MIRROR_SESSION` テーブル (MirrorOrch → NextHopObserver)

- **参照先テーブル**: `CONFIG_DB MIRROR_SESSION`
- **参照方向**: 間接参照（MirrorOrch が `attach()` を呼ぶトリガ）
- **条件**: MirrorOrch がミラーセッションエントリを処理するとき
- **意味**:
  - MirrorOrch がセッション設定時に `m_routeOrch->attach(this, entry.dstIp)` を呼び、
    宛先 IP の NextHopObserver として登録する (mirrororch.cpp L517)
  - 宛先 IP の最長プレフィックスマッチが変化するたびに `NextHopUpdate` が MirrorOrch に届き、
    ミラーセッションの ERSPAN 宛先ネクストホップを更新する
  - セッション削除時は `detach()` で登録解除 (mirrororch.cpp L557)
- **evidence**: `mirrororch.cpp` L517, L557

### 4. `NAT_ENTRY` / `NAT_TWICE_ENTRY` テーブル (NatOrch → NextHopObserver)

- **参照先テーブル**: `CONFIG_DB NAT_ENTRY`, `CONFIG_DB NAT_TWICE_ENTRY`
- **参照方向**: 間接参照（NatOrch が `attach()` を呼ぶトリガ）
- **条件**: NatOrch が DNAT / 双方向 NAT エントリを処理するとき
- **意味**:
  - NatOrch は翻訳後の IP アドレス (`translatedIp`) に対して `m_routeOrch->attach(this, translatedIp)` を呼び、
    その IP への経路変化を監視する (natorch.cpp L414, L458, L504, L591)
  - 翻訳先 IP の nexthop が変わると `NextHopUpdate` が NatOrch に届き、
    SAI NAT エントリの nexthop を更新する
  - エントリ削除時は `detach()` で登録解除 (natorch.cpp L558, L646, L688, L732)
- **evidence**: `natorch.cpp` L414, L458, L504, L558, L591, L646, L688, L732

### 5. `APPL_DB ROUTE_TABLE` (RouteOrch 管理のルートテーブル — Observer 通知の源)

- **参照先テーブル**: `APPL_DB ROUTE_TABLE`
- **参照方向**: 読み取り + 内部テーブル更新（RouteOrch::doRouteTask による）
- **条件**: RouteOrch が SAI 経路を追加/削除するたびに内部 `m_syncdRoutes` が更新される
- **意味**:
  - `notifyNextHopChangeObservers()` は `m_syncdRoutes`（RouteOrch 内部の経路テーブル）を参照して
    各 Observer の追跡 IP に対する最長プレフィックスマッチを計算する
  - APPL_DB `ROUTE_TABLE` の更新が RouteOrch を経由して内部テーブルに反映されることで、
    NextHopObserver への通知が発火する
- **evidence**: `routeorch.cpp` L1270–1340 (`notifyNextHopChangeObservers` 実装), L308–350 (`attach()`)

## 参照関係サマリ

```
RouteOrch 通知機構 (ResponsePublisher / NextHopObserver)

ResponsePublisher 依存:
  ├─ [暗黙] CONFIG_DB DEVICE_METADATA|localhost.suppress-fib-pending
  │         (fpmsyncd の RESPONSE_CHANNEL 購読の有無を制御 — 欠如すると通知消失)
  ├─ [書き込み先] APPL_STATE_DB ROUTE_TABLE
  │         (protocol + err_str を書き込み — route_check.py / fpmsyncd が参照)
  └─ [消費者] fpmsyncd RESPONSE_CHANNEL 購読
             (suppress-fib-pending 有効時のみ — onRouteResponse() → FRR へフィードバック)

NextHopObserver 依存:
  ├─ [暗黙] CONFIG_DB MIRROR_SESSION (MirrorOrch が attach/detach — mirrororch.cpp L517, L557)
  ├─ [暗黙] CONFIG_DB NAT_ENTRY / NAT_TWICE_ENTRY (NatOrch が attach/detach — natorch.cpp L414–732)
  └─ [内部依存] APPL_DB ROUTE_TABLE → m_syncdRoutes (最長プレフィックスマッチの計算源)
```

## evidence

- `orchagent/routeorch.cpp`: L308–350 (`attach()`), L1270–1340 (`notifyNextHopChangeObservers()`), L3185–3202 (`publishRouteState()`)
- `orchagent/response_publisher.cpp`: L93–148 (`publish()`)
- `fpmsyncd/fpmsyncd.cpp`: L78, L82–83, L112–117, L278–302 (`suppress-fib-pending` 制御)
- `fpmsyncd/routesync.cpp`: L3156–3190 (`setSuppressionEnabled`, `onRouteResponse`)
- `orchagent/mirrororch.cpp`: L517 (`attach`), L557 (`detach`)
- `orchagent/natorch.cpp`: L414, L458, L504, L558, L591, L646, L688, L732 (`attach`/`detach`)
- `scripts/route_check.py`: L767–770 (`APPL_STATE_DB ROUTE_TABLE` 参照)
