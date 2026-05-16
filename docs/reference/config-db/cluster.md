---
title: cluster フィールド (DEVICE_METADATA / DEVICE_NEIGHBOR_METADATA)
description: "SONiC CONFIG_DB における cluster フィールド — DEVICE_METADATA|localhost と DEVICE_NEIGHBOR_METADATA|<device> に共通する所属クラスタ名フィールドのリファレンス。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-device_metadata.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-device_neighbor_metadata.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-config-engine/minigraph.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - DEVICE_METADATA
    - DEVICE_NEIGHBOR_METADATA
  cli: []
  yang:
    - sonic-device_metadata
    - sonic-device_neighbor_metadata
---

# cluster フィールド

## 概要

SONiC の [CONFIG_DB](../../reference/glossary.md#term-config_db) には独立した `CLUSTER` テーブルは存在しない。「cluster」概念は以下の 2 テーブルのフィールドとして実装されている[^1]。

| テーブル | キー | フィールド | 意味 |
|---------|------|-----------|------|
| `DEVICE_METADATA` | `localhost` | `cluster` | 自ノードの所属クラスタ名 |
| `DEVICE_NEIGHBOR_METADATA` | `<device_hostname>` | `cluster` | 隣接デバイスの所属クラスタ名 |

クラスタ名は **minigraph XML の `<ClusterName>` 要素**から派生し、`sonic-cfggen` / `minigraph.py` がデバイス起動時に CONFIG_DB へ書き込む。典型値は `"AAA00PrdStr00"` のようなデータセンター内の論理グループ識別子。

## key 構造

```text
DEVICE_METADATA|localhost
DEVICE_NEIGHBOR_METADATA|<device_hostname>
```

## フィールド詳細

| フィールド | 型 | YANG default | 実行時 fallback | 説明 |
|-----------|----|-------------|----------------|------|
| `cluster` | string | なし | `""` (空文字列) | 所属クラスタ名。minigraph の `<ClusterName>` から派生 |

## 暗黙デフォルト・コード由来挙動

<!-- defaults -->

### cluster フィールドの書き込み条件の非対称性

`cluster` フィールドには YANG `default` 文が存在しない (optional フィールド)。書き込み挙動はテーブルによって異なる。

#### DEVICE_METADATA|localhost.cluster

```python
# minigraph.py:2170-2172
cluster = [devices[key] for key in devices if key.lower() == hostname.lower()][0].get('cluster', "")
if cluster:                                            # truthy check — 空文字列はスキップ
    results['DEVICE_METADATA']['localhost']['cluster'] = cluster
```

- minigraph XML に `<ClusterName>` が**存在しない**場合: `get('cluster', "")` により `""` が得られ、`if cluster:` が False → **フィールドを書き込まない**
- `<ClusterName>` が**存在し非空**の場合のみ書き込まれる
- DB にフィールドが存在しない場合の消費側 fallback: 空文字列 `""` (`.get('cluster', '')` パターン)

#### DEVICE_NEIGHBOR_METADATA|<device>.cluster

```python
# minigraph.py:662-668
(_, _, _, _, name, hwsku, d_type, deployment_id, cluster, d_subtype, slice_type) = parse_device(device)
device_data = {}
if cluster != None:                                    # None check — 空文字列 "" は書き込まれる
    device_data['cluster'] = cluster
```

```python
# minigraph.py (parse_device):493,514-515
cluster = None                                        # 初期値 None
elif node.tag == str(QName(ns, "ClusterName")):
    cluster = node.text                               # XML タグが存在すれば text を代入 (空文字列の場合も代入)
```

- `<ClusterName>` タグが**存在しない**場合: `cluster = None` のまま → `if cluster != None:` が False → 書き込まない
- `<ClusterName>` タグが**存在し空文字列**の場合: `cluster = ""` → `if cluster != None:` が True → 空文字列 `""` が書き込まれる (DEVICE_METADATA と挙動が異なる)
- `<ClusterName>` タグが**存在し非空**の場合: 値を書き込む

#### 非対称性のまとめ

| テーブル | 書き込み条件 | 空文字列の扱い |
|---------|------------|--------------|
| `DEVICE_METADATA|localhost` | `if cluster:` (truthy) | 書き込まない |
| `DEVICE_NEIGHBOR_METADATA|<dev>` | `if cluster != None:` (None check) | 書き込む (`""`) |

### YANG スキーマ

```yang
# sonic-device_metadata.yang:184-187
leaf cluster {
    type string;
    description "The switch is a member of this cluster.";
}

# sonic-device_neighbor_metadata.yang:39-42
leaf cluster {
    description "The switch is a member of this cluster";
    type string;
}
```

両 YANG モデルとも `default` 文なし、`mandatory` 文なし → optional フィールド。

<!-- /defaults -->

## 書き込み入り口 (Direction A)

対象テーブル: `DEVICE_METADATA` / `DEVICE_NEIGHBOR_METADATA` の `cluster` フィールド

### minigraph / sonic-cfggen

- `sonic-cfggen -m /etc/sonic/minigraph.xml -d` — `<ClusterName>` タグが存在する場合に書き込み
  - ソース: `sonic-buildimage/src/sonic-config-engine/minigraph.py`

### CLI

- なし (CLI から `cluster` フィールドを直接書き込む手段は提供されていない)

### REST / gNMI (sonic-mgmt-common)

- なし

### db_migrator

- なし (migration 対象外)

### ビルド時デフォルト

- なし

### ランタイム注入

- なし

## 消費側 (Direction B)

| 消費元 | 参照箇所 | 使用目的 |
|-------|---------|---------|
| `minigraph.py:2170` | `get('cluster', "")` | 自ノード cluster 名を DEVICE_METADATA に書き込む前処理 |
| `swss_vars.j2` | Jinja2 変数参照 | template 展開 (存在しない場合は空文字列) |

## 関連 CONFIG_DB / YANG / CLI

- 親テーブル: [`DEVICE_METADATA`](./device-metadata.md)、[`DEVICE_NEIGHBOR_METADATA`](./device-neighbor-metadata.md)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-device_metadata`、`sonic-device_neighbor_metadata`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`DEVICE_METADATA`](./device-metadata.md)
- CONFIG_DB: [`DEVICE_NEIGHBOR_METADATA`](./device-neighbor-metadata.md)
- [YANG](../../reference/glossary.md#term-yang): `sonic-device_metadata`
- [YANG](../../reference/glossary.md#term-yang): `sonic-device_neighbor_metadata`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-device_metadata.yang` L184-187, `sonic-device_neighbor_metadata.yang` L39-42. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-device_metadata.yang>

<!-- ops-hint -->
## 運用ヒント

### cluster 名の確認

```bash
# 自ノードの cluster 名確認
sonic-db-cli CONFIG_DB hget 'DEVICE_METADATA|localhost' cluster

# 隣接デバイスの cluster 名確認 (例: ARISTA01T1)
sonic-db-cli CONFIG_DB hget 'DEVICE_NEIGHBOR_METADATA|ARISTA01T1' cluster
```

### cluster 名が設定されない場合

minigraph XML に `<ClusterName>` タグが存在しない構成では、フィールドが DB に存在しない。`hget` の結果が空になるが、これは正常。消費側コードは空文字列として処理する。

<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | テーブル | 挙動 |
|------|---------|------|
| `<ClusterName>` タグなし | `DEVICE_METADATA` | フィールドを書き込まない (`if cluster:` False) |
| `<ClusterName>` タグなし | `DEVICE_NEIGHBOR_METADATA` | フィールドを書き込まない (`cluster = None`, `if cluster != None:` False) |
| `<ClusterName>` タグあり・空文字列 | `DEVICE_METADATA` | 書き込まない (truthy check で "" はスキップ) |
| `<ClusterName>` タグあり・空文字列 | `DEVICE_NEIGHBOR_METADATA` | 空文字列 `""` を書き込む (None check のため通過) |

> **Evidence**: `sonic-buildimage` `src/sonic-config-engine/minigraph.py:493,514-515,662-668,2170-2172`
<!-- /cdb-exceptions -->
