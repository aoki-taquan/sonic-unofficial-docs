# DPU / ENI — Phase G 通信メカニズム 証跡

## 調査ソース

- `sonic-swss/orchagent/dash/dashenifwdorch.h`
- `sonic-swss/orchagent/dash/dashenifwdorch.cpp`
- `sonic-swss/orchagent/orch.h` (Orch2 定義)
- `sonic-swss/orchagent/orch.cpp` (addConsumer / ConsumerStateTable 生成)
- `sonic-swss/orchagent/orchdaemon.cpp` (L614-617: SmartSwitch 分岐・DashEniFwdOrch 登録)
- `sonic-swss-common/common/schema.h` (L196: APP_DASH_ENI_FORWARD_TABLE 定数)

## 書き込み側 (Producer) — APPL_DB:DASH_ENI_FORWARD_TABLE

`DashEniFwdOrch` は APPL_DB の `DASH_ENI_FORWARD_TABLE` を**読み取る**側 (consumer) であり、
このテーブルへの書き込みは `HaMgrd` が担当する (HA 設計書 `eni-based-forwarding.md:108`)。

SmartSwitch HA 構成では HaMgrd が ZMQ チャネルまたは ProducerStateTable 経由で
`DASH_ENI_FORWARD_TABLE` に ENI-to-VDPU マッピングを書き込む。

## 読み取り側 (Consumer) — DashEniFwdOrch

`DashEniFwdOrch` は `Orch2` を継承する (`dashenifwdorch.h:92`)。

```cpp
// orchdaemon.cpp:615
DashEniFwdOrch *dash_eni_fwd_orch =
    new DashEniFwdOrch(m_configDb, m_applDb, APP_DASH_ENI_FORWARD_TABLE, gNeighOrch);
```

`Orch2` コンストラクタは `Orch(db, tableName, pri)` を呼び、`Orch::addConsumer()` 内で
`ConsumerStateTable(applDb, "DASH_ENI_FORWARD_TABLE", gBatchSize, pri)` を生成する
(`orch.cpp:1186-1194`)。

`APP_DASH_ENI_FORWARD_TABLE = "DASH_ENI_FORWARD_TABLE"` (`schema.h:196`)。

### 購読フロー

```
HaMgrd
  ↓ ProducerStateTable / ZMQ → APPL_DB:DASH_ENI_FORWARD_TABLE
Redis keyspace notification (__keyspace@0__:DASH_ENI_FORWARD_TABLE|*)
  ↓
ConsumerStateTable.pops()
  ↓
Orch2::doTask(Consumer&) → addOperation() / delOperation()
  ↓
DashEniFwdOrch::addOperation() (lazyInit → DpuRegistry populate → ENI ACL 生成)
DashEniFwdOrch::delOperation() (ENI ACL 削除)
```

## NeighOrch Observer — Neighbor 変化通知

`DashEniFwdOrch` は `Observer` を実装し、コンストラクタ内で
`neighorch_->attach(this)` を呼ぶ (`dashenifwdorch.cpp:15-19`)。

Neighbor 解決・削除イベントが `NeighOrch` から発行されると、
`DashEniFwdOrch::update(SUBJECT_TYPE_NEIGH_CHANGE, cntx)` が呼ばれ
(`dashenifwdorch.cpp:31-44`)、`handleNeighUpdate()` → 影響 ENI の `fireAllRules()` が実行される。

| 通知経路 | 方向 | 用途 |
|---------|------|------|
| `neighorch_->attach(this)` (コンストラクタ) | `NeighOrch` → `DashEniFwdOrch` | Neighbor 解決イベント受信 |
| `neighorch_->detach(this)` (デストラクタ) | 購読解除 | ライフサイクル管理 |
| `handleNeighUpdate()` (L47-79) | 受信ハンドラ | Neighbor UP 時: LOCAL ENI の ACL ルール再発火 |

## ProducerStateTable 出力 (副次 DB 書込、Phase F 参照)

`EniFwdCtxBase` コンストラクタ (`dashenifwdorch.cpp:403-405`) で 3 本の
`ProducerStateTable` を生成し、APPL_DB 3 テーブルへ SET/DEL する:

| 出力テーブル | 方式 |
|------------|------|
| `APPL_DB:ACL_TABLE_TYPE_TABLE` | ProducerStateTable SET/DEL |
| `APPL_DB:ACL_TABLE_TABLE` | ProducerStateTable SET/DEL |
| `APPL_DB:ACL_RULE_TABLE` | ProducerStateTable SET/DEL |

## SmartSwitch 限定登録

`DashEniFwdOrch` は `orchdaemon.cpp:613-617` の `gMySwitchSubType == "SmartSwitch"` 分岐内でのみ
インスタンス化・登録される。通常 SONiC スイッチでは `DASH_ENI_FORWARD_TABLE` の
ConsumerStateTable 購読は発生しない。

## SELECT_TIMEOUT / ポーリング

`Orch` 基底クラスの `Select::select()` は通常 1000 ms のデフォルトタイムアウトで
ループする (orchestration loop)。`DASH_ENI_FORWARD_TABLE` への書き込みが発生した場合、
Redis keyspace notification を受信して `ConsumerStateTable` が起動し、即座に
`doTask()` が呼ばれる。タイムアウト時は何もしない。
