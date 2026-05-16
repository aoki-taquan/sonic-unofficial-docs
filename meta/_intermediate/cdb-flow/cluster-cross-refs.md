# cluster フィールド — Phase C cross-refs 調査メモ

## 調査対象

`DEVICE_METADATA|localhost.cluster` および `DEVICE_NEIGHBOR_METADATA|<device>.cluster`

## 暗黙参照の調査結果

### DEVICE_METADATA との共同書き込み

`minigraph.py` の `parse_minigraph_meta()` は同一パスで以下フィールドを `DEVICE_METADATA|localhost` に書き込む。`cluster` は `deployment_id`、`chassis_hostname`、`slice_type` と同一 Python スコープで処理される（minigraph.py:2164-2176）。

| フィールド | 書き込み条件 | 依存関係 |
|-----------|------------|---------|
| `deployment_id` | `is not None` check | cluster と独立 |
| `chassis_hostname` | chassis構成時 | cluster と独立 |
| `cluster` | truthy check | 上記と独立 |
| `slice_type` | 非空かつ chassis 構成 | cluster と独立 |

### DEVICE_NEIGHBOR_METADATA との共同書き込み

`parse_devices()` (minigraph.py:804-826) で `cluster`・`deployment_id`・`hwsku`・`type` 等を同一 `device_data` dict に格納してから `devices[name] = device_data` とする。並列依存はない。

### daemon / 消費側の参照状況

| コンポーネント | cluster 参照 | 備考 |
|-------------|------------|------|
| `orchagent` | なし | `switch_type`/`mac`/`switch_id` のみ参照 |
| `bgpcfgd` | なし | `type`/`subtype` のみ参照 |
| `swss_vars.j2` | なし | `cluster` フィールドは Jinja2 展開に含まれない |
| `nbrmgrd` | なし | `switch_type` のみ参照 |
| `intfmgrd` | なし | `switch_type` のみ参照 |

### CHASSIS_APP_DB との関係

`cluster` フィールドは CONFIG_DB (`DEVICE_METADATA` / `DEVICE_NEIGHBOR_METADATA`) にのみ存在する。
CHASSIS_APP_DB への伝播コードは確認されない（minigraph.py 全体を grep して該当なし）。
VOQ 構成の `SYSTEM_NEIGH` / `SYSTEM_PORT` 等も `cluster` を参照しない。

### sonic-bgp-global.yang の rr_cluster_id との混同注意

`sonic-bgp-global.yang` に `rr_cluster_id`（BGP Route Reflector Cluster ID）と `ibgp_equal_cluster_length` フィールドが存在するが、これらは `BGP_GLOBALS` テーブルのフィールドであり、`DEVICE_METADATA.cluster` / `DEVICE_NEIGHBOR_METADATA.cluster` とは無関係。

## 結論

`cluster` フィールドを消費する daemon は存在しない（metadata-only フィールド）。
minigraph.py が XML から書き込む唯一の入り口であり、読み出し側は `minigraph.py:2170` の自己参照のみ。
cross-refs セクションでは「暗黙参照なし」と「BGP rr_cluster_id との混同注意」を明記する。

## Evidence

- `sonic-buildimage/src/sonic-config-engine/minigraph.py:493,515,524,662-668,806-813,2164-2176`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_metadata.yang:184-187`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_neighbor_metadata.yang:39-42`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-global.yang:115,406`（rr_cluster_id は別物）
- `sonic-buildimage/files/build_templates/swss_vars.j2`（cluster 参照なし確認）
