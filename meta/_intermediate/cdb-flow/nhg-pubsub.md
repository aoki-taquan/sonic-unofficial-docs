# NEXTHOP_GROUP_TABLE (APPL_DB) — 通信メカニズム (Phase G) 解析メモ

対象: `APPL_DB` の `NEXTHOP_GROUP_TABLE` テーブル。消費者は `NhgOrch` (orchagent)。

## 1. CONFIG_DB Subscribe — 非使用

`NEXTHOP_GROUP_TABLE` は **APPL_DB** テーブルであり、CONFIG_DB の Subscribe 機構は使用しない。書き込み元は `fpmsyncd` (`routesync.cpp`) で、FRR/Zebra から kernel netlink 経由で受信した ECMP ルートを変換して APPL_DB へ直接 `HSET` する。

## 2. APPL_DB 購読 — `NhgOrch` (ConsumerStateTable ベース)

`NhgOrch` は `orchdaemon.cpp` で次のように生成・登録される:

```cpp
// orchdaemon.cpp L338
gNhgOrch = new NhgOrch(m_applDb, APP_NEXTHOP_GROUP_TABLE_NAME);
// L500
m_orchList = { ..., gNhgOrch, ... };
```

`NhgOrchCommon` (基底クラス) は `Orch(db, tableName)` 経由で **`ConsumerStateTable`** として `APPL_DB::NEXTHOP_GROUP_TABLE` を購読する。`Select::addSelectable()` で orchagent のメインループに登録され、Redis の `keyspace + channel` 通知 (`__keyspace` / PUBLISH による `swss::ConsumerStateTable` プロトコル) を受け取る。

### 購読テーブルとハンドラ

| 購読 DB | テーブル名 | ハンドラ | 優先度 |
|--------|------------|---------|--------|
| `APPL_DB` | `NEXTHOP_GROUP_TABLE` | `NhgOrch::doTask()` | デフォルト |

### doTask() フロー

```
ConsumerStateTable 通知受信
    └─ NhgOrch::doTask(Consumer& consumer)
            ├─ gPortsOrch->allPortsReady() チェック (未完了なら即 return)
            ├─ op == SET_COMMAND
            │       ├─ フィールド解析 (nexthop / ifname / weight / mpls_nh / seg_src / nexthop_group)
            │       ├─ is_recursive 判定
            │       ├─ NHG 数上限チェック (getMaxNhgCount())
            │       │       └─ 超過時: temporary NHG を createTempNhg() で作成
            │       ├─ 既存エントリなし → NextHopGroup::sync() → SAI create
            │       └─ 既存エントリあり → NextHopGroup::update() → SAI update
            └─ op == DEL_COMMAND
                    ├─ getRefCount() > 0 なら skip (参照カウント非ゼロ)
                    └─ NextHopGroup::remove() → SAI remove
```

## 3. SAI next_hop_group_api — 呼び出しパターン

`NhgOrch` / `NextHopGroup` は `sai_next_hop_group_api_t*` ポインタを通じて SAI を操作する:

```cpp
// nhgorch.cpp L20
extern sai_next_hop_group_api_t* sai_next_hop_group_api;
```

### 主要 SAI 呼び出し

| SAI 関数 | 発生タイミング | コードロケーション |
|----------|--------------|------------------|
| `create_next_hop_group()` | SET で新規 NHG 作成時 (`SAI_NEXT_HOP_GROUP_TYPE_ECMP`) | `nhgorch.cpp` L775 |
| `create_next_hop_group_member()` (Bulker 経由) | `syncMembers()` 内でメンバー一括追加 | `nhgorch.cpp` L913, `ObjectBulker` flush |
| `set_next_hop_group_member_attribute()` | メンバー weight 更新時 | `nhgorch.cpp` L614 |
| `remove_next_hop_group_member()` (Bulker 経由) | メンバー削除時 | `NhgCommon::remove()` 経由 |
| `remove_next_hop_group()` | DEL で NHG 全体削除時 | `NhgCommon::remove()` 経由 |

### Bulker (バッチ SAI 呼び出し)

`syncMembers()` は `ObjectBulker<sai_next_hop_group_api_t>` を使用して `create_next_hop_group_member` をバッチ処理する:

```cpp
// nhgorch.cpp L913
ObjectBulker<sai_next_hop_group_api_t> nextHopGroupMemberBulker(
    sai_next_hop_group_api, gSwitchId, gMaxBulkSize);
// ... create_entry() を繰り返し ...
nextHopGroupMemberBulker.flush();  // 一括送信
```

## 4. Observer パターン — `validateNextHop` / `invalidateNextHop`

`NhgOrch` は **Observer (被観察者)** としても機能する。`NeighOrch` が nexthop の ARP/NDP 状態変化を検知した際に以下を呼び出す:

```cpp
// nhgorch.cpp L459-499
bool NhgOrch::validateNextHop(const NextHopKey& nh_key);
bool NhgOrch::invalidateNextHop(const NextHopKey& nh_key);
```

- `validateNextHop`: 指定 nexthop を含む全 NHG を走査し、未同期メンバーを `syncMembers()` で追加 → SAI member create
- `invalidateNextHop`: 指定 nexthop を含む全 NHG を走査し、対象メンバーを SAI member remove (グループ自体は維持)

これにより、インタフェース UP/DOWN や ARP 解決/失効に連動して NHG メンバーが動的に追加・削除される。

## 5. 起動時スナップショット

orchagent 起動時、`Select::select()` ループ開始前に `ConsumerStateTable` の既存エントリが drain され `doTask()` が一括処理される (swsscommon の `Orch::doTask` スキャン機構)。これにより再起動後も APPL_DB の既存 NHG エントリが SAI に再設定される。

## 6. CRM (Critical Resource Monitor) 連携

```cpp
// nhgorch.cpp L795
gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP);
```

NHG 作成・削除のたびに CRM カウンタを更新し、ハードウェアリソース枯渇を監視する。

## 7. 参照行番号

- `orchagent/nhgorch.cpp`
  - L20: `extern sai_next_hop_group_api_t* sai_next_hop_group_api`
  - L37: `NhgOrch::doTask()`
  - L459: `NhgOrch::validateNextHop()`
  - L499: `NhgOrch::invalidateNextHop()`
  - L614: `set_next_hop_group_member_attribute()`
  - L775: `create_next_hop_group()` (SAI_NEXT_HOP_GROUP_TYPE_ECMP)
  - L795: `gCrmOrch->incCrmResUsedCounter(CRM_NEXTHOP_GROUP)`
  - L913: `ObjectBulker` によるメンバーバッチ sync
- `orchagent/orchdaemon.cpp`
  - L338: `gNhgOrch = new NhgOrch(m_applDb, APP_NEXTHOP_GROUP_TABLE_NAME)`
  - L500: `m_orchList` への登録
