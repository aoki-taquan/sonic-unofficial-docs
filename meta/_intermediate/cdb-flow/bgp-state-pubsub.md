# BGP_PEER_CONFIGURED_TABLE (STATE_DB) — Phase G: 通信メカニズム / Pub-Sub

## 調査対象

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`
- `sonic-swss-common/common/table.h`

## BGP_PEER_CONFIGURED_TABLE の書き込みメカニズム

`BGP_PEER_CONFIGURED_TABLE` は **STATE_DB への一方向書き込み専用テーブル** であり、通知チャンネルへの PUBLISH や ProducerStateTable は使用しない。

### 書き込み経路

`BGPPeerMgrBase.update_state_db()` (managers_bgp.py L271-303) が直接 `swsscommon.Table` 経由で STATE_DB へ書き込む:

```python
state_db = swsscommon.DBConnector("STATE_DB", 0)
state_peer_table = swsscommon.Table(state_db, swsscommon.STATE_BGP_PEER_CONFIGURED_TABLE_NAME)
if op == "SET":
    state_peer_table.set(key, list(sorted(data.items())))
elif op == "DEL":
    state_peer_table.delete(key)
```

`swsscommon.Table.set()` は Redis `HSET` を発行する。`swsscommon.Table` は **ProducerStateTable ではない** ため、専用通知チャンネル (`BGP_PEER_CONFIGURED_TABLE_CHANNEL@<db_id>`) への PUBLISH は行わない。

Redis の keyspace notification (`__keyspace@6__:BGP_PEER_CONFIGURED_TABLE|*`) は Redis サーバー設定次第で発火するが、SONiC の通常構成では **STATE_DB に対して keyspace event は無効** であり、購読者は存在しない。

### 呼び出し元

| コードパス | op |
|-----------|-----|
| `BGPPeerMgrBase.set_handler()` (L239) — ネイバー追加 / 管理状態変更 | `"SET"` |
| `BGPPeerMgrBase.set_handler()` (L353, L443) — 動的ピア追加 | `"SET"` |
| `BGPPeerMgrBase.del_handler()` (L487) — ネイバー削除 | `"DEL"` |
| `config reload` (sonic-utilities/config/main.py L1613) — 全削除 | (直接 DEL) |

## 購読者の調査結果

コード調査の結果、`BGP_PEER_CONFIGURED_TABLE` を **アクティブに購読するデーモンは存在しない**。

### 根拠

1. `managers_bgp.py` 内に `subscribe`・`psubscribe`・`keyspace`・`notify` を含む記述はゼロ件 (grep 確認済み)
2. `swsscommon.Table` は通知チャンネルを持たない (ProducerStateTable / ConsumerStateTable ペアではない)
3. HLD (`Bgpcfgd-dyn-peer-modification-support.md §1.1`) の記述は「SDN コントローラが **ポーリング** でテーブル有無を確認する」設計を明示している

### 利用パターン (ポーリング)

| 利用者 | アクセス方法 | 目的 |
|--------|------------|------|
| SDN コントローラ | `HGETALL BGP_PEER_CONFIGURED_TABLE|<key>` または `EXISTS` 相当のポーリング | bgpcfgd が FRR への設定投入を完了したことの確認 |
| `show` コマンド系 | `sonic-db-cli STATE_DB keys 'BGP_PEER_CONFIGURED_TABLE|*'` など | デバッグ / オペレーション確認 |

CLI の `show bgp` 系コマンドは `NEIGH_STATE_TABLE` (bgpmon 書き込み) を主に参照し、`BGP_PEER_CONFIGURED_TABLE` を直接参照するコマンドは通常運用では存在しない。

## まとめ

| 項目 | 内容 |
|------|------|
| 書き込み | `bgpcfgd BGPPeerMgrBase.update_state_db()` が `swsscommon.Table.set()/delete()` で直接 HSET/DEL |
| 通知チャンネル | **なし** — ProducerStateTable 非使用 |
| keyspace notification | STATE_DB では通常無効のため事実上 **なし** |
| 購読デーモン | **なし** — アクティブ購読者は存在しない |
| 消費パターン | SDN コントローラによる **ポーリング**、または `show` 系コマンドによる手動確認 |
