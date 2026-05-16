# BGP_ALLOWED_PREFIXES — 通信メカニズム (Phase G) 調査ノート

> **対象**: `docs/reference/config-db/bgp-allowed-prefixes.md`
> **調査日**: 2026-05-16
> **ソース**:
> - `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`
> - `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/manager.py`
> - `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py`
> - `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py`

## 1. 購読方式 — SubscriberStateTable + Select (keyspace 通知)

`bgpcfgd` は `Runner.run()` が `swsscommon.Select` で複数の `SubscriberStateTable` を監視する一本のイベントループ。テーブルごとに 1 つの `SubscriberStateTable` を生成し、`Manager.handler(key, op, fvs)` をディスパッチする集中型 dispatcher 構成。

- `runner.py:27` — `self.selector = swsscommon.Select()`
- `runner.py:49-51` — `subscriber = swsscommon.SubscriberStateTable(conn, table_name); self.selector.addSelectable(subscriber)`
- `runner.py:52` — `self.callbacks[db][table_name].append(manager.handler)`
- `runner.py:57-70` — `select(SELECT_TIMEOUT=1000ms)` → `subscriber.pop()` → `callback(key, op, dict(fvs))`
- `runner.py:71-73` — 各 pop ループ後に `cfg_manager.commit()` で vtysh push をまとめてフラッシュ

`SubscriberStateTable` は libswsscommon の Redis keyspace notification (`__keyspace@<db-id>__:<TABLE>|*` を PSUBSCRIBE) を裏側で張る実装。`ConsumerStateTable` / `NotificationConsumer` / `ProducerStateTable` は経由しない。

## 2. テーブル登録

`main.py:94` で `BGPAllowListMgr(common_objs, "CONFIG_DB", "BGP_ALLOWED_PREFIXES")` を Manager 配列に追加し、`Runner.add_manager()` 経由で `SubscriberStateTable(CONFIG_DB_conn, "BGP_ALLOWED_PREFIXES")` が `Select` に登録される。Manager 1 つ = テーブル 1 つ = subscriber 1 つの 1:1 関係。

`Runner.add_manager` (runner.py:31-52):

- `db_name="CONFIG_DB"` → `SonicDBConfig.getDbId("CONFIG_DB")` = 4
- `DBConnector("CONFIG_DB", 0)` を取得しキャッシュ
- `SubscriberStateTable(conn, "BGP_ALLOWED_PREFIXES")` を生成
- `self.selector.addSelectable(subscriber)` で Select に登録
- `self.callbacks[4]["BGP_ALLOWED_PREFIXES"].append(BGPAllowListMgr.handler)`

## 3. dispatch チェーン (Manager base)

`manager.py:34-53` が op 種別で振り分け:

```
Runner.run()                                   # runner.py:54-73
  └─ selector.select(1000ms)
  └─ for subscriber in subscribers:
       └─ subscriber.pop()  → (key, op, fvs)
       └─ callbacks[db][table](key, op, dict(fvs))
            = BGPAllowListMgr.handler(...)     # manager.py:34
                 ├─ op == SET_COMMAND
                 │   ├─ deps 揃い → set_handler(key, data)   # managers_allow_list.py:49
                 │   └─ deps 未充足 / False 戻り → set_queue 退避  # manager.py:46,49
                 ├─ op == DEL_COMMAND
                 │   └─ del_handler(key)                       # managers_allow_list.py:115
                 └─ それ以外 → log_err
  └─ cfg_manager.commit()                      # runner.py:71 vtysh バッチフラッシュ
```

### deps と再投入

`BGPAllowListMgr.__init__` (managers_allow_list.py:38-43) は `deps=[]` で `super().__init__(...)` を呼ぶため、`directory.subscribe([], on_deps_change)` は登録するが**待つべき依存は無い**。よって `wait_for_all_deps=True` でも `available_deps([])` は常に True を返し、初回イベントから即 `set_handler` に到達する。

ただし `set_handler` 自身が `return False` を返した場合 (manager.py:44-46) は `set_queue` に退避され、後続の `on_deps_change()` (manager.py:55-64) で再試行される。AllowList の場合は deps 空なので `on_deps_change` トリガが乏しく、実質的なリトライは「次の SET イベントが来るまで `set_queue` に残る」挙動。

> Phase D で詳述の **`return False` 暗黙リトライループ** はこの `set_queue` 機構と SubscriberStateTable の再 pop に依存しており、回数上限・バックオフはない。

## 4. 通信シーケンス図 (起動 → 定常運用)

```
bgpcfgd プロセス起動
  └─ main()                                # main.py
       └─ common_objs = { directory, cfg_mgr=ConfigMgr(frr), constants, state_db_conn }
       └─ managers = [ BGPDataBaseMgr×2, InterfaceMgr×6, ZebraSetSrc,
                       BGPPeerMgrBase×6,
                       BGPAllowListMgr("CONFIG_DB","BGP_ALLOWED_PREFIXES"),   # main.py:94
                       BBRMgr, StaticRouteMgr×2, AdvertiseRouteMgr, RouteMapMgr,
                       DeviceGlobalCfgMgr, AggregateAddressMgr, SRv6Mgr×2 ]
       └─ runner = Runner(cfg_mgr)
       └─ for m in managers: runner.add_manager(m)
            └─ runner.py:38-52
                 ├─ DBConnector("CONFIG_DB", 0) 取得 (1 接続を共有)
                 ├─ SubscriberStateTable(conn, "BGP_ALLOWED_PREFIXES")
                 │     └─ 内部で PSUBSCRIBE __keyspace@4__:BGP_ALLOWED_PREFIXES|*
                 ├─ selector.addSelectable(subscriber)
                 └─ callbacks[4]["BGP_ALLOWED_PREFIXES"] += [BGPAllowListMgr.handler]
       └─ runner.run()                     # メインループ
            └─ while g_run:
                 ├─ selector.select(1000ms)
                 ├─ for sub in subscribers:
                 │    └─ while (key,op,fvs) = sub.pop():
                 │         └─ callbacks[…](key, op, dict(fvs))
                 │              ↓ AllowList の場合
                 │              └─ BGPAllowListMgr.handler(key, op, data)
                 │                   ├─ SET → set_handler → __set_handler_validate
                 │                   │            └─ __update_policy → cfg_mgr.push_list(...)
                 │                   └─ DEL → del_handler → __remove_policy → cfg_mgr.push_list(...)
                 └─ cfg_manager.commit()   # vtysh セッションへバッチ送信
```

## 5. keyspace notification 詳細

| 項目 | 値 |
|------|-----|
| Redis DB 番号 | 4 (`SonicDBConfig.getDbId("CONFIG_DB")`) |
| PSUBSCRIBE パターン (実装由来) | `__keyspace@4__:BGP_ALLOWED_PREFIXES\|*` |
| 要求される `notify-keyspace-events` | `KEA` (CONFIG_DB の Redis サーバ起動時設定) |
| Select timeout | 1000 ms (`runner.py:21` `SELECT_TIMEOUT = 1000`) |
| イベント単位 | key 1 件単位 (`pop()` で `(key, op, fvs)` を順次取り出し) |
| 起動時スナップショット | あり — `SubscriberStateTable` 生成時に `STATE_TABLE` ベースで既存キーを内部キューに enqueue (swsscommon の標準挙動)。`bgpcfgd` 側に明示的な `get_table()` 全量取得は無い |
| バッチ性 | 1 select cycle 内で**全 subscriber を回し**、その後に `cfg_mgr.commit()` を 1 回呼ぶ。複数テーブル変更が 1 vtysh バッチに収まる |
| Producer 側 | 通常ユーザが `config bgp allowed-prefix add/del` や `sonic-cfggen` で CONFIG_DB に書く一般経路。`bgpcfgd` 自身は CONFIG_DB に書き戻さない |
| APPL_DB 中継 | なし — vtysh 直叩きで FRR に反映 (`cfg_mgr.push_list` → vtysh セッション) |
| STATE_DB 書き込み | なし (AllowList 経路は state 公開を行わない) |

## 6. 反映タイミング

```
ユーザが CONFIG_DB|BGP_ALLOWED_PREFIXES|<key> を SET
  ↓ (Redis keyspace event)
SubscriberStateTable が内部キューに enqueue
  ↓ (≤ 1000 ms)
Runner.run() の select() が起床
  ↓
subscriber.pop() → BGPAllowListMgr.handler(key, "SET", data)
  ↓
__set_handler_validate → __update_policy
  ↓
cfg_mgr.push_list([prefix-list, community-list, route-map ...])
  ↓
runner.run() ループ末の cfg_manager.commit() で vtysh セッションへバッチ送信
  ↓
FRR (bgpd) が prefix-list / route-map / community-list を反映
  ↓ (必要に応じ)
__find_peer_group → restart_peer_groups (vtysh "clear bgp ... soft")
```

通常パスでは **CONFIG_DB write から FRR 反映まで概ね 1 秒以内**。`set_handler` が `False` を返した場合は次のイベントで `set_queue` から再試行される (Phase D 参照)。

## 7. 他テーブル/プロセスとの非対称性

- **生産者 (Direction A)**: `sonic-utilities/config/main.py` の `config bgp allowed-prefix add/del` および minigraph_facts/`sonic-cfggen` 経路 (`docs/reference/config-db/bgp-allowed-prefixes.md` の "書き込み入り口" 参照)
- **消費者 (本ページ)**: `bgpcfgd` プロセスの `BGPAllowListMgr` (上記 dispatch)。同一テーブルを購読する他プロセスは無し (grep `BGP_ALLOWED_PREFIXES` で `sonic-buildimage` 内 bgpcfgd / yang / utilities のみがヒット)
- **下流**: FRR `bgpd` (vtysh 経由)。`SAI` 非経由

## 8. 結論

- 購読方式: **SubscriberStateTable + Select** (keyspace notification ベース)
- dispatch: **集中 Runner ループが Manager.handler に分岐** (op で SET/DEL 振り分け、`return False` は set_queue で暗黙リトライ)
- 中継 DB: なし (CONFIG_DB → vtysh 直)
- タイミング: ≤ 1 秒、1 select cycle = 1 vtysh commit バッチ
