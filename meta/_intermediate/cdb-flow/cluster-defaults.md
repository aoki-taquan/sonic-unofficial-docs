# cluster: Phase A — コード由来デフォルト調査

## 調査対象

SONiC CONFIG_DB における `cluster` フィールドのデフォルト値とコード由来挙動。  
`cluster` フィールドは独立した CONFIG_DB テーブルではなく、以下の 2 テーブルのフィールドとして存在する:
- `DEVICE_METADATA|localhost.cluster`
- `DEVICE_NEIGHBOR_METADATA|<device>.cluster`

## grep entry (1 回のみ)

```
grep -rn "ClusterName\|\"cluster\"\|'cluster'" \
  sonic-buildimage/src/sonic-config-engine/minigraph.py
```

ヒット箇所:
- L493: `cluster = None` — parse_device() ローカル初期値
- L514: `elif node.tag == str(QName(ns, "ClusterName")): cluster = node.text` — minigraph XML から取得
- L667-668: `if cluster != None: device_data['cluster'] = cluster` — DEVICE_NEIGHBOR_METADATA への書き込み (None のみ除外)
- L2170: `cluster = [...][0].get('cluster', "")` — 自ノード取得時の fallback `""`
- L2171-2172: `if cluster: results['DEVICE_METADATA']['localhost']['cluster'] = cluster` — 空文字列なら書き込みスキップ

## フィールド別デフォルト分析

### DEVICE_METADATA|localhost.cluster

| フェーズ | 値 | コード根拠 |
|---------|-----|-----------|
| YANG default | なし (YANG に `default` 文なし) | `sonic-device_metadata.yang:184-187` |
| minigraph parse_device() 初期値 | `None` | `minigraph.py:493` |
| 自ノード dict.get() fallback | `""` (空文字列) | `minigraph.py:2170` |
| 書き込み条件 | `if cluster:` — 空文字列は falsy → 書き込みスキップ | `minigraph.py:2171-2172` |
| DB に書き込まれる条件 | minigraph XML の `<ClusterName>` 要素が存在し、非空 | `minigraph.py:514` |
| 存在しない場合の実行時 fallback | フィールド自体が DB に存在しない (エントリなし) | — |

**コード由来デフォルト**: フィールドなし（省略）。消費側コードは `.get('cluster', '')` パターンで空文字列を fallback とする。

### DEVICE_NEIGHBOR_METADATA|<device>.cluster

| フェーズ | 値 | コード根拠 |
|---------|-----|-----------|
| YANG default | なし (YANG に `default` 文なし) | `sonic-device_neighbor_metadata.yang:39-42` |
| parse_device() 初期値 | `None` | `minigraph.py:493` |
| 書き込み条件 | `if cluster != None:` — `None` のみ除外。空文字列 `""` は書き込まれる | `minigraph.py:667-668` |
| 消費側 fallback | `minigraph.py:2170` で `get('cluster', "")` | `minigraph.py:2170` |

**重要な非対称性**:
- DEVICE_METADATA は `if cluster:` (truthy check) → 空文字列でも書き込みスキップ
- DEVICE_NEIGHBOR_METADATA は `if cluster != None:` (None check) → 空文字列 `""` が書き込まれる

## YANG スキーマ確認

```yang
# sonic-device_metadata.yang L184-187
leaf cluster {
    type string;
    description "The switch is a member of this cluster.";
}
# → default なし, mandatory なし → optional field

# sonic-device_neighbor_metadata.yang L39-42
leaf cluster {
    description "The switch is a member of this cluster";
    type string;
}
# → default なし, mandatory なし → optional field
```

## minigraph XML ソース

minigraph の `<Device>` 要素内の `<ClusterName>` タグから取得:

```python
# minigraph.py:514-515
elif node.tag == str(QName(ns, "ClusterName")):
    cluster = node.text
```

`<ClusterName>` タグが存在しない場合は `cluster = None` のまま。

## 書き込み入り口サマリ

| 書き込み元 | 対象テーブル | 書き込み条件 |
|-----------|------------|------------|
| `minigraph.py (sonic-cfggen)` | `DEVICE_METADATA|localhost` | `<ClusterName>` 存在 + 非空 |
| `minigraph.py (sonic-cfggen)` | `DEVICE_NEIGHBOR_METADATA|<device>` | `<ClusterName>` 存在 (None でない) |
| CLI | なし | CLI 書き込みパスなし |
| db_migrator | なし | migration 対象外 |

## 消費側コード (Direction B)

- `minigraph.py:2170`: 自ノードの cluster 名を取得し、DEVICE_METADATA に書き込む前処理で使用
- `swss_vars.j2`: `cluster` を Jinja2 変数として参照するが fallback 文字列なし (空文字列扱い)

## 結論

`cluster` フィールドは純粋に minigraph XML の `<ClusterName>` タグから派生し、コードハードコードデフォルトは存在しない。エントリが DB に存在しない場合の実行時 fallback は空文字列 `""` (消費側が `.get('cluster', '')` 使用)。
