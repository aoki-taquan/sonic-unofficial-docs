# BUFFER_POOL — Phase A: コード由来の暗黙デフォルト調査

調査日: 2026-05-14  
対象ブランチ: chore/q67-f-phaseA-buffer-pool

## フィールド一覧

YANG: `sonic-buffer-pool.yang` (name, type, mode, size, xoff, percentage)

## 各フィールドの暗黙デフォルト・fallback

### `xoff`

- YANG: `default 0`
- 実装 (buffermgrdyn.cpp): `newSHPSize = "0"` で初期化 (L2523)。フィールドが CONFIG_DB に存在しない場合 SHP size は "0" 扱い
- **一致**: YANG default と実装 fallback は同じ `0`。乖離なし

### `size`

- YANG: default なし、optional
- 実装 (buffermgrdyn.cpp L2525-2534):
  - `size` フィールドが存在しない場合 → `bufferPool.dynamic_size = true`
  - `size` フィールドが存在する場合 → `bufferPool.dynamic_size = false`
- **動作**: `dynamic_size=true` のとき、Lua plugin (`buffer_pool_mellanox.lua`) が available_buffer から実効サイズを計算し APPL_DB に書き込む。`buffermgrdyn.cpp` は直接 APPL_DB に pool を書かない (silent defer)
- **`ingress_lossless_pool` 追加条件** (L2555-2632): `dynamic_size=true` かつ `overSubscribeRatio` が non-zero かつ SHP が size で enabled でない場合 → `dontUpdatePoolToDb=true` → APPL_DB への書き込み完全スキップ。Lua plugin の計算結果のみが APPL_DB に届く

### `type`

- YANG: `mandatory true`、enum `ingress`/`egress`/`both`
- **buffermgrdyn.cpp L2544-2549 乖離**:
  ```cpp
  if (value == buffer_value_ingress)
      bufferPool.direction = BUFFER_INGRESS;
  else
      bufferPool.direction = BUFFER_EGRESS;
  ```
  `type=both` は `BUFFER_EGRESS` として内部キャッシュに記録される (else branch)。
  ただし raw 文字列 "both" は `fvVector` 経由で APPL_DB/STATE_DB に転送されるため SAI 側では `SAI_BUFFER_POOL_TYPE_BOTH` を受け取る。
  内部キャッシュの direction が EGRESS になることで、pool が ingress 用の lossless headroom 計算に参照されなくなる可能性あり
- **bufferorch.cpp L437-441 create-only 制約**:
  既存 SAI オブジェクトへの更新時 (`sai_object != SAI_NULL_OBJECT_ID`) は `type` フィールドがスキップされる (LOG_INFO のみ)。
  YANG にはこの制約の記述なし → **YANG-impl 乖離**: 作成後に `type` を変更しても SAI には反映されない

### `mode`

- YANG: `mandatory true`、enum `static`/`dynamic`
- **bufferorch.cpp L467-471 create-only 制約**:
  既存 SAI オブジェクトへの更新時は `mode` フィールドもスキップされる (LOG_INFO のみ)。
  YANG にはこの制約の記述なし → **YANG-impl 乖離**: 作成後に `mode` を変更しても SAI には反映されない
- static model (buffermgr.cpp): `mode` はバリデーションなしで APPL_DB に転送

### `percentage`

- YANG: optional、`must (not(size))` + `must buffer_model='dynamic'`
- **buffermgrdyn.cpp**: フィールドを読み取らない。`fvVector` 経由で APPL_DB に pass-through するだけ
- **bufferorch.cpp L497-501**: 不明フィールドとして LOG_ERROR + `continue` → SAI に渡らない
  ```
  SWSS_LOG_ERROR("Unknown pool field specified:%s, ignoring", field.c_str())
  ```
- **Lua plugin (buffer_pool_mellanox.lua L458-464)**: APPL_DB の `percentage` フィールドを読み取り実効サイズを計算
  ```lua
  local percentage = tonumber(redis.call('HGET', pools_need_update[i], 'percentage'))
  if percentage ~= nil and percentage >= 0 then
      effective_pool_size = available_buffer * percentage / 100
  ```
- **dead field (bufferorch 経路)**: `percentage` は SAI に一切反映されない。Lua plugin 経由でのみ有効
- **consumer 経路依存乖離**: Mellanox/Barefoot Lua plugin を持つプラットフォームのみ有効。その他プラットフォームでは `percentage` は無視される

## 複合制約

- `size` と `percentage` の排他制約は YANG の `must` で強制されるが、buffermgrdyn.cpp では両方同時に CONFIG_DB に入っても検出されない (YANG validation が先行する前提)
- `percentage` の有効性は `DEVICE_METADATA.buffer_model='dynamic'` に依存するが、buffermgrdyn.cpp はこれを直接チェックしない

## 書き込み経路別 field 扱いマトリクス

| フィールド | buffermgr (static) | buffermgrdyn (dynamic) | bufferorch (SAI) | Lua plugin |
|-----------|-------------------|----------------------|-----------------|-----------|
| `type` | pass-through | cache (both→EGRESS) + pass-through | SAI (create-only) | — |
| `mode` | pass-through | cache + pass-through | SAI (create-only) | — |
| `size` | pass-through | dynamic_size flag 制御 | SAI_BUFFER_POOL_ATTR_SIZE | 実効サイズ計算 |
| `xoff` | pass-through | SHP 計算トリガ | SAI_BUFFER_POOL_ATTR_XOFF_SIZE | SHP size 計算 |
| `percentage` | pass-through | pass-through (未読取) | LOG_ERROR + skip | 実効サイズ計算 |

## ハードコード固定値

- `INGRESS_LOSSLESS_PG_POOL_NAME = "ingress_lossless_pool"` — 特別扱いプール名がハードコード。他プール名は xoff 設定禁止
- xoff の初期値 `"0"` (L2523)

## 出典

- `sonic-swss/cfgmgr/buffermgrdyn.cpp` L2509-2669 (handleBufferPoolTable)
- `sonic-swss/orchagent/bufferorch.cpp` L391-596 (processBufferPool)
- `sonic-swss/cfgmgr/buffermgr.cpp` L337-370 (doBufferTableTask)
- `sonic-swss/cfgmgr/buffer_pool_mellanox.lua` L455-476
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-buffer-pool.yang`
