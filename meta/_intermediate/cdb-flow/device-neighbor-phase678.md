# DEVICE_NEIGHBOR — Phase 6/7/8 derivation & handler-branching

対象ページ: `docs/reference/config-db/device-neighbor.md`
バッチ: cdb_batch_9

---

## Phase 6: 自動派生 (minigraph.py 代入)

<!-- derivation -->

### 1. `neighbors` dict → `DEVICE_NEIGHBOR` の一括代入

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2637`

```python
results['DEVICE_NEIGHBOR'] = neighbors
```

- `neighbors` は minigraph XML の `<Neighbors>` → `<DeviceLinkBase>` タグから解析される。
- 各エントリのキーはポート名（例: `"Ethernet0"`）、値は `{'name': <peer_hostname>, 'port': <peer_port>}` の辞書。

### 2. ポートエイリアスマッピングによる正規化

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:741,747`

```python
neighbors[port_alias_map[endport]] = {'name': startdevice, 'port': startport}
neighbors[port_alias_map[startport]] = {'name': enddevice, 'port': endport}
```

- `port_alias_map` によりプラットフォーム固有のポートエイリアス（例: `fortyGigE0/0`）から sonic 内部名（例: `Ethernet0`）に変換される。
- エイリアスマップに存在しないポートはそのままのキー名で登録される（minigraph.py:649,656）。

### 3. `description` フィールドの自動付与

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2465`

```python
port['description'] = "%s:%s" % (neighbors[port_name]['name'], neighbors[port_name]['port'])
```

- `PORT` テーブルの `description` フィールドに `<peer_hostname>:<peer_port>` 形式の文字列が自動代入される。`DEVICE_NEIGHBOR` の情報から派生するクロス代入。

### 4. backend ポートの除外

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2636`

```python
del neighbors[nghbr]
```

- BackEnd ASIC トポロジにおいて内部インターコネクトポートは `neighbors` から削除される。`DEVICE_NEIGHBOR` には外部ネイバーのみが残る。

<!-- /derivation -->

---

## Phase 7: 条件付き登録

<!-- derivation -->

該当なし。

`DEVICE_NEIGHBOR` テーブルを直接 consume する swss 系 manager は存在しない。このテーブルは主に参照用途（LLDP neighbor 表示、BGP neighbor metadata チェック）で使用され、mgr/orch による能動的な処理はない。

<!-- /derivation -->

---

## Phase 8: manager メソッド内 early return / dispatch

<!-- handler-branching -->

該当なし。

`DEVICE_NEIGHBOR` テーブルを subscribe する manager（`lldpmgrd` 等）は存在するが、このテーブル自体が write される（SET/DEL イベントが発生する）ケースは minigraph.py による初期 populate のみ。実行時に CONFIG_DB から subscribe してハンドリングする早期リターン / dispatch ロジックは存在しない。

`bgpcfgd` の `BgpPeerMgr` は `DEVICE_NEIGHBOR_METADATA` テーブルを依存チェックとして参照するが（managers_bgp.py:140）、`DEVICE_NEIGHBOR` (メタデータなし) とは別テーブル。

<!-- /handler-branching -->
