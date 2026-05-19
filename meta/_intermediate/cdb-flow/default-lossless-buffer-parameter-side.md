# DEFAULT_LOSSLESS_BUFFER_PARAMETER — Phase F 副次 DB 書込 調査ノート

調査対象: `buffermgrdyn` が `DEFAULT_LOSSLESS_BUFFER_PARAMETER` を処理する際に APPL_DB / STATE_DB / APPL_STATE_DB へ発生する副次書込

## 調査コード

- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/cfgmgr/buffermgrdyn.h`

---

## 副次書込 A: APPL_DB BUFFER_PROFILE_TABLE（動的プロファイル再生成）

### トリガー条件

1. `default_dynamic_th` フィールドが変更された場合 → `m_defaultThreshold` 更新後、各 lossless PG の headroom 再計算がトリガーされる
2. `over_subscribe_ratio` が変化して SHP 有効/無効が切り替わった場合 → `refreshSharedHeadroomPool(enable_state_updated_by_ratio=true, ...)` が呼ばれ、すべての動的 lossless プロファイルを再計算

### コード経路

```
handleDefaultLossLessBufferParam() (L1978)
  ├─ default_dynamic_th 変更  → doUpdateBufferProfileForSize(profile) → updateBufferProfileToDb()
  │     → m_applBufferProfileTable.set(name, fvVector)   ← APPL_DB BUFFER_PROFILE_TABLE 書込
  │     → m_stateBufferProfileTable.set(name, fvVector)  ← STATE_DB BUFFER_PROFILE_TABLE 書込 (同時)
  └─ over_subscribe_ratio 変更 → refreshSharedHeadroomPool() (L1593)
        → need_refresh_profiles=true → calculateHeadroomSize(profile) → doUpdateBufferProfileForSize()
              → updateBufferProfileToDb()
                    → m_applBufferProfileTable.set(name, fvVector)   ← APPL_DB BUFFER_PROFILE_TABLE 書込
                    → m_stateBufferProfileTable.set(name, fvVector)  ← STATE_DB BUFFER_PROFILE_TABLE 書込
```

evidence: `buffermgrdyn.cpp L919-920` (updateBufferProfileToDb 内)

---

## 副次書込 B: APPL_DB BUFFER_POOL_TABLE（SHP 有効化/無効化時の xoff 更新）

### トリガー条件

- `over_subscribe_ratio` が変化して SHP 有効/無効が切り替わった場合のみ
- `refreshSharedHeadroomPool()` から `updateBufferPoolToDb(INGRESS_LOSSLESS_PG_POOL_NAME, pool)` が呼ばれる

### コード経路

```
refreshSharedHeadroomPool() (L1593)
  ├─ shp_enabled_by_size=true かつ pool.total_size 非ゼロ:
  │       updateBufferPoolToDb(INGRESS_LOSSLESS_PG_POOL_NAME, ingressLosslessPool)
  │         → m_applBufferPoolTable.set(name, fvVector)   ← APPL_DB BUFFER_POOL_TABLE 書込  (L1695, L885)
  │         → m_stateBufferPoolTable.set(name, fvVector)  ← STATE_DB BUFFER_POOL_TABLE 書込  (L887)
  └─ !shp_enabled_by_ratio かつ enable_state_updated_by_ratio=true かつ pool.total_size 非ゼロ:
          ingressLosslessPool.xoff = "0"
          updateBufferPoolToDb(INGRESS_LOSSLESS_PG_POOL_NAME, ingressLosslessPool)
            → m_applBufferPoolTable.set(name, fvVector)   ← APPL_DB BUFFER_POOL_TABLE 書込  (L1701-1703, L885)
            → m_stateBufferPoolTable.set(name, fvVector)  ← STATE_DB BUFFER_POOL_TABLE 書込  (L887)
```

evidence: `buffermgrdyn.cpp L1695, L1701-1703, L885, L887`

---

## 副次書込 C: STATE_DB BUFFER_POOL_TABLE および STATE_DB BUFFER_PROFILE_TABLE（常時同時書込）

`updateBufferPoolToDb()` および `updateBufferProfileToDb()` はそれぞれ APPL_DB への書込と **同時に** STATE_DB の対応テーブルへも書込む（evidence: L885-887, L919-920）。

---

## 副次書込が発生しない条件

- `default_dynamic_th` 変更のみの場合、BUFFER_POOL_TABLE への書込は発生しない（プロファイル再計算のみ）
- `over_subscribe_ratio` が同じ値のままの場合（`newRatio == m_overSubscribeRatio`）、副次書込はなし（evidence: L2015 の `if` 分岐）
- `m_portInitDone=false` の場合（起動直後）、SHP 有効化書込は保留される（evidence: L2019）
