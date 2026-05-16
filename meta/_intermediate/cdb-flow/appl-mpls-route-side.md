# APPL_DB LABEL_ROUTE_TABLE — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-15 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/appl-mpls-route.md`（APPL_DB `LABEL_ROUTE_TABLE`）の主購読者である
`routeorch::doLabelTask()` 経路、および `nhgorch` の MPLS NH 経路で、STATE_DB / COUNTERS_DB /
APPL_STATE_DB への副次書き込みが行われるか。

## 走査範囲

- `.cache/sonic-sources/sonic-swss/orchagent/mplsrouteorch.cpp` (961 行)
- `.cache/sonic-sources/sonic-swss/orchagent/nhgorch.cpp` (1160 行) — MPLS NH (`isLabeled()`) 部
- `.cache/sonic-sources/sonic-swss/orchagent/routeorch.cpp` の `doLabelTask` 呼出経路と
  STATE_DB / APPL_STATE_DB 共有資源

## 走査コマンドと結果

### 1. `mplsrouteorch.cpp` / `nhgorch.cpp` の副次 DB 書込

```bash
grep -nE "STATE_DB|COUNTERS_DB|APPL_STATE_DB|FlexCounter|gStateDb|gCountersDb|m_stateDb|m_countersDb|notificationProducer" \
  mplsrouteorch.cpp nhgorch.cpp nhgbase.cpp
```

結果: **マッチ 0 件**。

`mplsrouteorch.cpp` は SAI `inseg_entry` および MPLS NH の作成・更新・削除のみを行い、
SAI 以外の DB（STATE_DB / COUNTERS_DB / APPL_STATE_DB）への書き込みを一切含まない。
`nhgorch.cpp` の MPLS 関連分岐 (`isLabeled()` 等、L63 / L82 / L107 / L230 / L563 / L677) も
SAI NH 操作と内部マップ更新のみ。

### 2. `routeorch.cpp` の STATE_DB / APPL_STATE_DB 共有資源

```bash
grep -nE "m_stateDefaultRouteTb|STATE_ROUTE_TABLE|m_publisher" routeorch.cpp
```

検出箇所:

- L126–127 `m_stateDb = DBConnector("STATE_DB", 0); m_stateDefaultRouteTb = Table(STATE_ROUTE_TABLE_NAME)`
- L294 `m_stateDefaultRouteTb->set(ip, tuples)` (`updateDefRouteState`)
- L57–58, L1231, L3192–3201 `m_publisher.publish(APP_ROUTE_TABLE_NAME, ...)` (APPL_STATE_DB 同期)

これらはすべて IPv4 / IPv6 のデフォルトルート (`APP_ROUTE_TABLE_NAME`) 経路で利用される共有資源。
`doLabelTask()` (`mplsrouteorch.cpp:54-510`) からは呼ばれない:

- `updateDefRouteState()` の呼出元は `doTask()` の IPv4/IPv6 経路 (`routeorch.cpp:618` で
  `APP_LABEL_ROUTE_TABLE_NAME` のときは `return;` で MPLS 経路に分岐し、その後の `m_publisher.flush()`
  および STATE_DB 更新パスには到達しない)
- `m_publisher.publish(APP_ROUTE_TABLE_NAME, ...)` は `APP_ROUTE_TABLE_NAME` (= `ROUTE_TABLE`)
  キーで APPL_STATE_DB に書き戻されるもので、`APP_LABEL_ROUTE_TABLE_NAME` (= `LABEL_ROUTE_TABLE`)
  に対する APPL_STATE_DB ミラーは存在しない

### 3. FlexCounter / COUNTERS_DB

```bash
grep -nE "FlexCounter|COUNTERS_DB" mplsrouteorch.cpp nhgorch.cpp
```

結果: **マッチ 0 件**。MPLS inseg / NH に対する FlexCounter 統計収集は実装されていない
（IPv4/IPv6 ルートと異なり、SAI `inseg_entry` 用の counter は SAI ベンダ依存で未統合）。

## 結論

APPL_DB `LABEL_ROUTE_TABLE` の SET / DEL に伴う **STATE_DB / COUNTERS_DB / APPL_STATE_DB
への副次書き込みは存在しない**。副作用は SAI `inseg_entry` および MPLS NH (SAI `next_hop`)
オブジェクトの ASIC 反映に閉じる。

## 根拠サマリ

| 検証項目 | ファイル/行 | 結果 |
|---|---|---|
| `mplsrouteorch.cpp` 内の副次 DB 書込 | `sonic-swss/orchagent/mplsrouteorch.cpp` 全行 | 0 件 |
| `nhgorch.cpp` MPLS 分岐の副次 DB 書込 | `sonic-swss/orchagent/nhgorch.cpp` (`isLabeled()` 経路) | 0 件 |
| STATE_DB `ROUTE_TABLE` への波及 | `routeorch.cpp:294` (`updateDefRouteState`) | 非該当 (IPv4/IPv6 経路のみ) |
| APPL_STATE_DB `ROUTE_TABLE` ミラー | `routeorch.cpp:3201` (`m_publisher.publish`) | 非該当 (`APP_ROUTE_TABLE_NAME` キー固定) |
| FlexCounter 連携 | `mplsrouteorch.cpp` / `nhgorch.cpp` | 0 件 |
