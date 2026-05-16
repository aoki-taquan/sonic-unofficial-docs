# DEVICE_NEIGHBOR_METADATA — Phase A: コード由来暗黙デフォルト調査

## 調査日時
2026-05-14

## ソース確認ファイル

| ファイル | 役割 |
|---------|------|
| `src/sonic-yang-models/yang-models/sonic-device_neighbor_metadata.yang` | YANG 定義 |
| `src/sonic-config-engine/minigraph.py` | 唯一の書き込み入り口（`parse_device()` + `parse_png()`） |
| `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | 主消費者（BGP セッション生成） |
| `sonic-utilities/pfcwd/main.py` | `type` フィールドによる server-facing 判定 |
| `sonic-utilities/show/interfaces/__init__.py` | `show interfaces neighbor expected` コマンド |
| `files/build_templates/buffers_config.j2` | バッファ設定生成テンプレート |
| `files/build_templates/qos_config.j2` | QoS 設定生成テンプレート |
| `scripts/db_migrator.py` | EdgeZoneAggregator ケーブル長移行 |

## フィールド別デフォルト・挙動分析

### `name` (key)
- **YANG default**: なし（required key）
- **minigraph 由来**: `<Hostname>` XML ノード値
- **silent drop**: `None` の場合、`devices[name]` の name が None になるが、その後のフィルタリング（`key.lower() != hostname.lower()`）で KeyError が起きうる（未ガード）

### `hwsku`
- **YANG default**: なし（optional）
- **minigraph 由来**: `<HwSku>` XML ノード値。ノードが存在しない場合は `None` となり `device_data` に追加されない（silent drop）
- **消費側**: bgpcfgd テンプレート・バッファテンプレートで参照されるが、欠落時はテンプレート側で未定義扱い（エラーにならない場合が多い）

### `cluster`
- **YANG default**: なし（optional）
- **minigraph 由来**: `<ClusterName>` XML ノード値。ノード欠落時は `None` → `device_data` に追加されない（silent drop）
- **消費側**: `minigraph.py:2170` で `cluster = [devices[key] for key if key.lower() == hostname.lower()][0].get('cluster', "")` — 自ノードの cluster 取得時は **`""` (空文字列) がデフォルト fallback**

### `lo_addr`
- **YANG default**: なし（optional）
- **minigraph 由来**: `<Address><IPPrefix>` テキスト値。ノード欠落時 `None` → `device_data` に追加されない
- **消費側 (show interfaces)**: `lo_addr` キーが存在しない場合、文字列 `'None'` を表示（`'None'` リテラル — Python None ではなく文字列）
- **消費側 (bgpcfgd)**: `minigraph.py:472` で `peer_lo_addr_str = devices[peer_hostname]["lo_addr"]` — `lo_addr` キーが存在しない場合 `KeyError` で死亡（隣接ルータからの lo_addr 取得時）
- **消費側 (buffers_config.j2:cable_length)**: `lo_addr` は直接参照されない

### `lo_addr_v6`
- **YANG default**: なし（optional）
- **minigraph 由来**: `<AddressV6><IPPrefix>` テキスト値。ノード欠落時 `None` → silent drop
- **消費側 (bgpcfgd)**: `managers_bgp.py:2839` で `if 'lo_addr_v6' in devices[neighbor]` を先にチェック → KeyError ガードあり

### `mgmt_addr`
- **YANG default**: なし（optional）
- **minigraph 由来**: `<ManagementAddress><IPPrefix>` テキスト値。ノード欠落時 `None` → silent drop
- **消費側 (show interfaces)**: キー不在時は文字列 `'None'` を表示

### `mgmt_addr_v6`
- **YANG default**: なし（optional）
- **minigraph 由来**: `<ManagementAddressV6><IPPrefix>` テキスト値。ノード欠落時 silent drop

### `type`
- **YANG default**: なし（optional、string 型、enum 制約なし）
- **minigraph 由来**: `<ElementType>` XML ノードテキスト、またはノード属性 `xsi:type` のフォールバック（`parse_device:521`）。両方欠落なら `None` → silent drop
- **消費側 (pfcwd)**: `neighbor['type'].lower() == 'server'` — キー不在の場合 `KeyError` → pfcwd 起動シーケンス中断（`pfcwd/main.py:104`）。キーが存在しても値が `None` なら `AttributeError`
- **消費側 (buffers_config.j2)**: `neighbor_role = neighbor.type` — neighbor.type が None/未定義でも jinja2 は文字列化するため `'None'` として処理 → `'edgezoneaggregator'` / `'asic'` 比較が False になるだけで silent fallback
- **消費側 (qos_config.j2)**: `'ToRRouter' in neighbor_info.type` — `type` が None だとエラー
- **消費側 (db_migrator)**: `v.get("type") == "EdgeZoneAggregator"` — `get()` 使用のため欠落時は安全に `None` 返し
- **消費側 (show interfaces)**: キー不在時は文字列 `'None'` を表示
- **大文字小文字制約**: `pfcwd` は `.lower()` で比較 → 大文字小文字は問わない。`buffers_config.j2` は `| lower` フィルタで正規化。`bgpcfgd`/`qos_config.j2` は大文字小文字を区別（`in` 演算子）

### `deployment_id`
- **YANG default**: なし（uint32、optional）
- **minigraph 由来**: `<DeploymentId>` XML ノードテキスト（文字列として格納）。ノード欠落時 `None` → silent drop
- **消費側 (bgpcfgd)**: `managers_bgp.py:135-137` — `self.check_deployment_id` フラグが constants に基づく。フラグ有効時は DEVICE_METADATA.localhost.deployment_id を参照（DEVICE_NEIGHBOR_METADATA の deployment_id は直接参照されない）
- **dead field 候補**: bgpcfgd が直接 DEVICE_NEIGHBOR_METADATA の `deployment_id` を読む実装が確認されない

### `slice_type`
- **YANG default**: なし（optional、string 型）
- **minigraph 由来**: `<AssociatedSliceStr>` ノードテキストに `"AZNG_Production"` が含まれる場合のみ `"AZNG_Production"` が格納（それ以外は `None` → silent drop）
- **ハードコード固定値**: 値は必ず `"AZNG_Production"` のみ（`minigraph.py:518-519`）。他の文字列は書き込まれない
- **消費側**: YANG では string 型だが、実装上の格納値は `"AZNG_Production"` 固定

### `resource_type`
- **YANG default**: なし（optional、string 型）
- **minigraph 由来**: YANG には定義されているが、`parse_device()` の実装では `resource_type` を XML から読み出す処理がない（`parse_meta()` で `DEVICE_METADATA.localhost.resource_type` として読み出しているが、DEVICE_NEIGHBOR_METADATA には書き込まれていない）
- **dead field**: YANG に定義があるが、minigraph パーサが DEVICE_NEIGHBOR_METADATA のエントリに `resource_type` を書き込まないため、実質的に空

### `subtype` (YANG 外フィールド)
- **YANG**: 定義なし
- **minigraph 由来**: `parse_device()` で `<SubType>` ノードから読み出し、`device_data['subtype']` に書き込む（`minigraph.py:681-682`）
- **YANG-実装 discrepancy**: YANG モデルに存在しないフィールドが実際の CONFIG_DB には書き込まれる

## 複合必須制約

- `name` は key として必須。YANG `length 1..255` 制約あり
- それ以外のフィールドはすべて YANG 上 optional（`mandatory` 文なし）
- bgpcfgd で `data["name"] not in neigmeta` チェック（`managers_bgp.py:221`）: BGP_NEIGHBORの `name` フィールドが DEVICE_NEIGHBOR_METADATA のキーとして存在しないと BGP peer 追加が延期される

## 経路依存乖離

- **single-ASIC** vs **multi-ASIC**: `minigraph.py:2638-2641`
  - single-ASIC: 自ホスト以外の全デバイスが DEVICE_NEIGHBOR_METADATA に格納
  - multi-ASIC（asic_name 指定あり）: DEVICE_NEIGHBOR に出現する neighbor のみを格納 → 隣接していないデバイスのメタデータは欠落する

## ハードコード固定値

| フィールド | 値 | 箇所 |
|-----------|-----|------|
| `slice_type` | `"AZNG_Production"` のみ | `minigraph.py:519` |
| `EDGEZONE_AGG_CABLE_LENGTH` | `"40m"` | `db_migrator.py:771`（CABLE_LENGTH への副作用） |

## 書き込み順依存

- minigraph パーサは XML の `<Devices>` セクションを全走査後にエントリを確定する。XML での出現順は関係なし
- bgpcfgd は `check_neig_meta` フラグが True の場合、DEVICE_NEIGHBOR_METADATA が directory に到達するまで BGP peer 追加を延期する（依存関係登録済みのため到達後に自動再処理）

## まとめ

| フィールド | 暗黙デフォルト/挙動 | カテゴリ |
|-----------|-------------------|---------|
| `name` | key 必須、欠落時 silent KeyError リスク | 複合必須制約 |
| `hwsku` | 欠落時 silent drop | silent drop |
| `cluster` | 自ノード取得時は `""` フォールバック | YANG default 外 fallback |
| `lo_addr` | 欠落時 silent drop / show では `'None'` 文字列 / bgpcfgd で KeyError リスク | silent drop + consumer 依存 |
| `lo_addr_v6` | 欠落時 silent drop / bgpcfgd はガードあり | silent drop |
| `mgmt_addr` | 欠落時 silent drop / show では `'None'` 文字列 | silent drop |
| `mgmt_addr_v6` | 欠落時 silent drop | silent drop |
| `type` | 欠落時 pfcwd でKeyError / qos_config.j2 でエラー / show では `'None'` 文字列 | dead-field-like + 消費者依存 |
| `deployment_id` | 欠落時 silent drop / DEVICE_NEIGHBOR_METADATA の値は bgpcfgd 非使用 | dead field 候補 |
| `slice_type` | `"AZNG_Production"` 固定値のみ書き込まれる | ハードコード固定値 |
| `resource_type` | YANG 定義あるが minigraph が書き込まない | dead field / YANG-実装 discrepancy |
| `subtype` | YANG 外フィールド。minigraph が `<SubType>` から書き込む | YANG-実装 discrepancy |
