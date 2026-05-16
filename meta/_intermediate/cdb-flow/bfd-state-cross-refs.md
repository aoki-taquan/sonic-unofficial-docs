# STATE_DB BFD_SESSION_TABLE 暗黙参照スキャン (Phase C)

`docs/reference/config-db/bfd-state.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/orchagent/bfdorch.cpp` 一次、補助で `sonic-buildimage/src/sonic-bgpcfgd/staticroutebfd/main.py` および `sonic-swss/orchagent/vnetorch.cpp` / `neighorch.cpp` / `orchdaemon.cpp`。STATE_DB `BFD_SESSION_TABLE` (`bfdorch` が書き込み) に対し、Direction A (このテーブルを書く際に bfdorch が読み出す DB エントリ) と Direction B (このテーブルを消費する側) の双方を列挙する。

## スキャン手順

```
# Direction A: bfdorch.cpp 自身が読む他 DB / 他テーブル
grep -nE 'STATE_DB|APPL_DB|BgpGlobalStateOrch|bfd_session_lookup|m_state|tsa_enabled|use_software_bfd|gDirectory\.get' \
    .cache/sonic-sources/sonic-swss/orchagent/bfdorch.cpp

# Direction B: STATE_DB BFD_SESSION_TABLE を読む側
grep -rn "SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE\|STATE_BFD_SESSION_TABLE_NAME\|BFD_SESSION_TABLE" \
    .cache/sonic-sources/sonic-swss/orchagent/*.cpp \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/staticroutebfd/
```

## 検出された暗黙参照

### Direction A — `bfdorch` が STATE_DB `BFD_SESSION_TABLE` を書く際に読む CONFIG_DB / APPL_DB / 他 Orch

| テーブル / 値 | DB | 参照箇所 | 用途 | evidence |
|---|---|---|---|---|
| `BFD_SESSION_TABLE` | APPL_DB | `BfdOrch::doTask(Consumer&)` 全体 (`bfdorch.cpp:90-220` 付近) | APPL_DB の SET/DEL を受けて STATE_DB エントリを生成・削除する Direction A の入り口 | bfdorch.cpp:90,108,134 |
| `BGP_DEVICE_GLOBAL.tsa_enabled` | CONFIG_DB → `BgpGlobalStateOrch` 経由 | `bgp_global_state_orch->getTsaState()` | TSA 有効時に `shutdown_bfd_during_tsa=true` のセッションを `notify_session_state_down()` + STATE_DB から削除する分岐 (Phase 6 handler-branching と連動) | bfdorch.cpp:114-120,158,193,683-704,743-748 |
| `BGP_DEVICE_GLOBAL.use_software_bfd` | CONFIG_DB → `BgpGlobalStateOrch` 経由 | `bgp_global_state_orch->getSoftwareBfd()` | true なら STATE_DB `BFD_SESSION_TABLE` を書かず代わりに `BFD_SOFTWARE_SESSION_TABLE` に APPL_DB データを転記 | bfdorch.cpp:116,120,133-136,182-185,749-753 |
| ASIC_DB `SAI_OBJECT_TYPE_BFD_SESSION` (OID) | ASIC_DB (via SAI) | `sai_bfd_api->create_bfd_session(&bfd_session_id, ...)` の返却 OID を `bfd_session_lookup[bfd_session_id]` に格納 | STATE_DB key と SAI OID の対応表。SAI 通知 (`bfd_session_state_change`) で OID から STATE_DB key を逆引きして `hset(key, "state", ...)` | bfdorch.cpp:249-263,567-572,629-631 |
| switch `SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY` | SAI switch | constructor + `doTask(NotificationConsumer&)` | SAI 通知ハンドラ登録。SAI からの状態変化通知のみが STATE_DB の `state` フィールドを更新するトリガ | bfdorch.cpp:277,292 |

> 共依存関係: `BfdOrch` と `BgpGlobalStateOrch` は同一 `bfdorch.cpp` 内で定義され、`gDirectory` を介して相互参照する。`BgpGlobalStateOrch::doTask()` (bfdorch.cpp:793-840) で `tsa_enabled` の SET を受けると即座に `BfdOrch::handleTsaStateChange()` を呼び、STATE_DB エントリを一斉に再評価する (Direction A から書き戻し方向への循環)。

### Direction B — STATE_DB `BFD_SESSION_TABLE` を読む / 連動する消費者

| 消費者 | 参照経路 | 連動内容 | evidence |
|---|---|---|---|
| `VNetRouteOrch` / `VNetOrch` (vnetorch.cpp) | `SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE` observer | BFD Up/Down で VNet monitor ルートを切替 (`monitoring == VNET_MONITORING_TYPE_CUSTOM_BFD` 等) | vnetorch.cpp:2661,2761,786,968,1375,2457-2487 |
| `NeighOrch` (neighorch.cpp) | `SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE` observer | BFD Up で neighbor (next-hop) 状態を有効化 | neighorch.cpp:201,631 |
| `staticroutebfd` (sonic-bgpcfgd) | `SubscriberStateTable(state_db, STATE_BFD_SESSION_TABLE_NAME)` + 起動時 `db.keys(STATE_DB, "BFD_SESSION_TABLE\|*")` | STATIC_ROUTE bfd-enabled ルートで BFD Up セッションが残っている next-hop のみを APPL_DB `STATIC_ROUTE_TABLE` に書き込む。Up→Down で nexthop を外し、全 Down で APPL_DB エントリ削除 | staticroutebfd/main.py:24,116,118,253,275,296,721,736 |
| `BfdMonitorOrch` (orchdaemon.cpp 経由) | STATE_DB `BFD_SESSION_TABLE` | BFD 状態のオーケストレーション監視 | orchdaemon.cpp (BFD_SESSION_TABLE 登録) |
| `show bfd peers` (sonic-utilities) | STATE_DB `BFD_SESSION_TABLE` ダンプ | CLI 表示 | sonic-utilities `show/bfd.py` |

### 範囲外 (誤解されやすい隣接)

- `STATIC_ROUTE_BFD` テーブル名は CONFIG_DB に**存在しない**。`STATIC_ROUTE` の `bfd` フィールド (true/false) を `staticroutebfd` daemon が読み、STATE_DB `BFD_SESSION_TABLE` を参照して APPL_DB `STATIC_ROUTE_TABLE` の next-hop リストを再計算する経路で「STATIC_ROUTE × BFD」連携が成立する。bfd-state.md には「`STATIC_ROUTE.bfd=true` の派生として `staticroutebfd` 経由で消費される」と書く。
- `BFD_SOFTWARE_SESSION_TABLE` (STATE_DB) は `use_software_bfd=true` の代替テーブル。同 `bfdorch` が書くが本ページ範囲外 (派生ページ候補)。
- `bfd_session_lookup` (`std::map<sai_object_id_t, BfdSessionEntry>`) は **プロセス内メモリ**。DB ではないので暗黙参照ではなく内部状態として扱う。

## まとめ — `bfd-state.md` Phase C 記載対象

| 方向 | テーブル / 値 | カテゴリ |
|---|---|---|
| A (読み元) | APPL_DB `BFD_SESSION_TABLE` | 入り口 |
| A (分岐) | CONFIG_DB `BGP_DEVICE_GLOBAL.tsa_enabled` | handler-branching 連動 |
| A (分岐) | CONFIG_DB `BGP_DEVICE_GLOBAL.use_software_bfd` | 書き先テーブル切替 |
| A (対応表) | ASIC_DB `SAI_OBJECT_TYPE_BFD_SESSION` OID | SAI 通知逆引き |
| B (消費者) | `vnetorch` / `neighorch` (observer) | route / next-hop 切替 |
| B (消費者) | `staticroutebfd` (`STATIC_ROUTE.bfd=true` 派生) | APPL_DB `STATIC_ROUTE_TABLE` 再構築 |
| B (消費者) | `show bfd peers`, `BfdMonitorOrch` | 表示・監視 |

## 検証コマンド

```
grep -nE 'getTsaState|getSoftwareBfd|bfd_session_lookup|m_stateBfdSessionTable\.(hset|del|set)' \
    .cache/sonic-sources/sonic-swss/orchagent/bfdorch.cpp
grep -nE 'SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE' \
    .cache/sonic-sources/sonic-swss/orchagent/{vnetorch,neighorch,bfdorch}.cpp
grep -nE 'STATE_BFD_SESSION_TABLE_NAME|BFD_SESSION_TABLE' \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/staticroutebfd/main.py
```
