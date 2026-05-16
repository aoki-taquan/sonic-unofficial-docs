# Srv6Orch — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/srv6-orch.md` Phase C 追加分。
APP_DB の 3 テーブル（`SRV6_SID_LIST_TABLE` / `SRV6_MY_SID_TABLE` / `PIC_CONTEXT_TABLE`）に対して
`Srv6Orch` が実装上行う外部 Orch / 外部テーブルへの暗黙参照を網羅した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/srv6orch.cpp` | `Srv6Orch` の全実装 |
| `sonic-swss/orchagent/srv6orch.h` | クラス宣言・メンバ定義 |
| `sonic-swss/orchagent/routeorch.h` | `gRouteOrch` 外部宣言 |

## 暗黙参照 (実装レベル)

### 1. VRF テーブル (CONFIG_DB) — SRV6_MY_SID_TABLE の DT 系アクション

- **参照先テーブル**: `VRF` (CONFIG_DB)
- **参照方向**: 存在確認 + OID 取得 + refcount 管理
- **条件**: `SRV6_MY_SID_TABLE` の `action` が `end.t` / `end.dt4` / `end.dt6` / `end.dt46` /
  `udt4` / `udt6` / `udt46` いずれかで、かつ `vrf` フィールドに custom VRF 名が指定されたとき
  （`mySidVrfRequired()` が true を返すケース）
- **参照元**: `srv6orch.cpp:1488` (`m_vrfOrch->isVRFexists(dt_vrf)`),
  `1491` (`m_vrfOrch->getVRFid(dt_vrf)`),
  `1639` (`m_vrfOrch->increaseVrfRefCount(dt_vrf)`),
  `1683` (`m_vrfOrch->decreaseVrfRefCount(...)`)
- **意味**:
  - `isVRFexists()` が false → `SWSS_LOG_ERROR("VRF %s doesn't exist in DB")` → `return false`。
    ペンディング機構はなく即時失敗。VRF を先に作成してから SRV6_MY_SID_TABLE に投入する必要がある。
  - `isVRFexists()` が true でも SAI OID が null → `SWSS_LOG_ERROR("VRF object not created for DT VRF %s")` → `return false`。VrfOrch の初期化待ち。
  - 登録成功時に `increaseVrfRefCount()`、削除時に `decreaseVrfRefCount()` で参照カウントを管理する。

### 2. NEIGH テーブル / NeighOrch — SRV6_MY_SID_TABLE の nexthop 系アクション

- **参照先**: `NeighOrch`（`NEIGH_TABLE` / ASIC 側 neighbor を管理）
- **参照方向**: 存在確認 + OID 取得 + refcount 管理、および neighbor 変化通知の受信
- **条件**: `SRV6_MY_SID_TABLE` の `action` が `end.x` / `end.dx4` / `end.dx6` / `udx4` / `udx6` /
  `end.b6.encaps` / `end.b6.encaps.red` / `end.b6.insert` / `end.b6.insert.red` / `ua`
  （`mySidNextHopRequired()` が true、かつ `adj` フィールドに nexthop アドレスが指定されたとき）
- **参照元**:
  - `srv6orch.cpp:110` `m_neighOrch->attach(this)` — 起動時に NeighOrch のオブザーバとして登録
  - `srv6orch.cpp:117` `m_neighOrch->detach(this)` — デストラクタで登録解除
  - `srv6orch.cpp:1524` `m_neighOrch->hasNextHop(nexthop)` — nexthop 存在確認
  - `srv6orch.cpp:1527` `m_neighOrch->getNextHopId(nexthop)` — SAI next_hop OID 取得
  - `srv6orch.cpp:1644` `m_neighOrch->increaseNextHopRefCount(nexthop, 1)`
  - `srv6orch.cpp:1689` `m_neighOrch->decreaseNextHopRefCount(nexthop, 1)`
  - `srv6orch.cpp:871` `m_neighOrch->updateSrv6Nexthop(nh, nexthop_id)` — SRv6 nexthop OID 通知
  - `srv6orch.cpp:900–924` `m_neighOrch->getNextHopRefCount(nh)` — SID LIST 削除時の nexthop refcount 確認
  - `srv6orch.cpp:1212` `updateNeighbor(const NeighborUpdate&)` — neighbor ADD/DEL 通知コールバック
- **意味**:
  - `hasNextHop()` が false → エントリを `m_pendingSRv6MySIDEntries` に保留し `return false`。
    NeighOrch から neighbor ADD 通知が届いた時点で `updateNeighbor()` → `createUpdateMysidEntry()` を再呼び出しして自動再インストール（`srv6orch.cpp:1532–1542`）。
  - neighbor DELETE 通知時: 該当 nexthop を使用しているインストール済み SID を ASIC から削除して
    pending に戻す（`srv6orch.cpp:1197–1210`）。
  - ECMP adj（カンマ区切り複数アドレス）は `"ECMP adjacency not yet supported"` エラーで全拒否
    （`srv6orch.cpp:1516–1519`）。実装制限であり全プラットフォーム共通。

### 3. SRV6_SID_LIST_TABLE (APP_DB) — SRV6_MY_SID_TABLE の nexthop 参照

- **参照先テーブル**: `SRV6_SID_LIST_TABLE` (APP_DB)
- **参照方向**: 存在確認 + refcount 管理（`sid_table_` キャッシュ経由）
- **条件**: `SRV6_MY_SID_TABLE` エントリが nexthop を持つとき（`end.x` / `end.b6.*` / `ua` 等）、
  nexthop の `srv6_segment` フィールドが SID リスト名を指定する
- **参照元**:
  - `srv6orch.cpp:875` `sid_table_[srv6_segment].nexthops.insert(nh)` — nexthop 作成時にリスト参照追加
  - `srv6orch.cpp:919–921` `sid_table_[nh.srv6_segment].nexthops.erase(nh)` — nexthop 削除時に参照解除
  - `srv6orch.cpp:1129–1132` DEL ガード: `sid_table_[sid_name].nexthops.size() > 0` → `task_need_retry`
- **意味**: SRV6_SID_LIST_TABLE エントリは参照カウントが 0 になるまで削除できない。
  SRV6_MY_SID_TABLE のエントリが参照している間は SID リストの削除がリトライキューに保留される。

### 4. RouteOrch / ROUTE_TABLE (APP_DB) — PIC_CONTEXT_TABLE の連携

- **参照先**: `RouteOrch`（`gRouteOrch`）、`APP_ROUTE_TABLE_NAME`
- **参照方向**: 通知（`notifyRetry` でルート再試行を指示）+ refcount 管理
- **条件**: `PIC_CONTEXT_TABLE` への SET 処理が完了した後、および
  `PIC_CONTEXT_TABLE` への DEL 時に `ref_count` が 0 になった後
- **参照元**:
  - `srv6orch.cpp:37` `extern RouteOrch *gRouteOrch`
  - `srv6orch.cpp:2312` `notifyRetry(gRouteOrch, APP_ROUTE_TABLE_NAME, make_constraint(RETRY_CST_PIC, key))` —
    PIC コンテキスト SET 完了後に RouteOrch の ROUTE_TABLE 再試行を起動
  - `srv6orch.cpp:1815–1833` `increasePicContextIdRefCount()` / `decreasePicContextIdRefCount()` —
    RouteOrch から呼び出される参照カウント管理 API
  - `srv6orch.cpp:2323` `addToRetry(APP_PIC_CONTEXT_TABLE_NAME, ...)` — ref_count > 0 時のリトライ登録
- **意味**:
  - `PIC_CONTEXT_TABLE` エントリが SET されると、RouteOrch は ROUTE_TABLE の PIC 関連ルートを
    再処理できるようになる（RETRY_CST_PIC 制約が解除される）。
  - `PIC_CONTEXT_TABLE` エントリへの DEL は `ref_count > 0` の間 `task_need_retry` となり、
    RouteOrch が `decreasePicContextIdRefCount()` で ref_count を 0 にした後に自動削除が実行される。

### 5. CONFIG_DB SRV6_MY_LOCATORS テーブル — MySID の DSCP mode 解決

- **参照先テーブル**: `SRV6_MY_LOCATORS` (CONFIG_DB)
- **参照方向**: 読み取り（locator block/node/func 長の取得）
- **条件**: `SRV6_MY_SID_TABLE` の `action` が `un` または `udt46` で、
  IPinIP トンネルを自動生成する際に `decap_dscp_mode` を解決するとき
- **参照元**:
  - `srv6orch.cpp:107` `m_locatorCfgTable(cfgDb, CFG_SRV6_MY_LOCATOR_TABLE_NAME)` — 起動時に CONFIG_DB 接続
  - `srv6orch.cpp:331–354` `getLocatorCfgFromDb(locator, cfg)` — `SRV6_MY_LOCATORS` から block/node/func 長取得
  - `srv6orch.cpp:1425–1427` `getMySidEntryDscpMode()` → `getLocatorCfgFromDb()` — MySID 処理中に呼び出し
- **意味**:
  - MySID キーからロケータ長を特定して SID プレフィックス（例: `fc00:0:1:1::/64`）を構成し、
    `SRV6_MY_SIDS` (CONFIG_DB) の `decap_dscp_mode` フィールドと照合する。
  - ロケータが `SRV6_MY_LOCATORS` に存在しない場合 → `SWSS_LOG_ERROR("Failed to get the SRv6 locator %s - not present in the CONFIG_DB")` → IPinIP トンネル生成不可 → `return false`。

### 6. CONFIG_DB SRV6_MY_SIDS テーブル — MySID の DSCP mode 取得

- **参照先テーブル**: `SRV6_MY_SIDS` (CONFIG_DB)
- **参照方向**: 読み取り（`decap_dscp_mode` フィールド取得）+ keyspace 通知受信
- **条件**: `action` が `un` / `udt46` で IPinIP トンネル生成が必要なとき。
  また CFG_SRV6_MY_SID_TABLE_NAME のエントリ変化は ConsumerStateTable 経由で `doTaskCfgMySidTable()` が処理
- **参照元**:
  - `srv6orch.cpp:106` `m_mysidCfgTable(cfgDb, CFG_SRV6_MY_SID_TABLE_NAME)` — CONFIG_DB 直接読み取り用
  - `srv6orch.cpp:376–397` `doTaskCfgMySidTable()` — `decap_dscp_mode` をキャッシュに保存
  - `srv6orch.cpp:430–480` `getMySidEntryDscpMode()` — キャッシュから DSCP mode を解決
  - `srv6orch.cpp:2384` `doTask()` dispatcher で `CFG_SRV6_MY_SID_TABLE_NAME` をルーティング
- **意味**:
  - `SRV6_MY_SIDS` の `decap_dscp_mode` が設定されている場合のみ IPinIP トンネルを生成する
    （`mySidTunnelRequired()` が `dscp_mode.has_value()` を確認）。
  - `decap_dscp_mode` 文字列が "uniform" / "pipe" 以外 → `SWSS_LOG_ERROR("Invalid MySID %s DSCP mode: %s")` → キャッシュ未登録で早期 return。

## 参照関係サマリ

```
SRV6_MY_SID_TABLE (APP_DB)
  ├─ [暗黙] VRF (CONFIG_DB)                   (DT 系 action の decap_vrf — 存在確認+OID+refcount)
  ├─ [暗黙] NeighOrch / NEIGH_TABLE           (nexthop 系 action の adj — hasNextHop+OID+refcount+notify)
  ├─ [暗黙] SRV6_MY_LOCATORS (CONFIG_DB)      (un/udt46 の IPinIP tunnel DSCP 解決 — 読み取り)
  └─ [暗黙] SRV6_MY_SIDS (CONFIG_DB)          (un/udt46 の decap_dscp_mode — 読み取り+通知)

SRV6_SID_LIST_TABLE (APP_DB)
  └─ [暗黙] SRV6_MY_SID_TABLE (APP_DB)        (nexthop 参照カウント — DEL ブロック機構)

PIC_CONTEXT_TABLE (APP_DB)
  └─ [暗黙] RouteOrch / APP_ROUTE_TABLE       (SET 後 route 再試行通知、DEL の ref_count 管理)
```

## evidence

- `srv6orch.cpp:98–117` (コンストラクタ、`m_vrfOrch`/`m_neighOrch`/`m_locatorCfgTable` 初期化、`attach`/`detach`)
- `srv6orch.cpp:1484–1500` (`isVRFexists` / `getVRFid` ガード)
- `srv6orch.cpp:1512–1542` (`hasNextHop` / `m_pendingSRv6MySIDEntries` ペンディング機構)
- `srv6orch.cpp:1639,1683` (VRF refcount inc/dec)
- `srv6orch.cpp:1644,1689` (NEIGH refcount inc/dec)
- `srv6orch.cpp:1197–1210` (neighbor DELETE 時 SID 削除 + pending 戻し)
- `srv6orch.cpp:1212–1248` (`updateNeighbor()` ADD 再インストール)
- `srv6orch.cpp:871–924` (`updateSrv6Nexthop` / SID LIST refcount 管理)
- `srv6orch.cpp:1129–1132` (SID LIST DEL ガード: nexthop 参照中は task_need_retry)
- `srv6orch.cpp:1815–1833` (`increasePicContextIdRefCount` / `decreasePicContextIdRefCount`)
- `srv6orch.cpp:2312` (`notifyRetry(gRouteOrch, APP_ROUTE_TABLE_NAME, ...)`)
- `srv6orch.cpp:331–397,430–480` (`getLocatorCfgFromDb` / `doTaskCfgMySidTable` / `getMySidEntryDscpMode`)
