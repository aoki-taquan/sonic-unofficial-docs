# BUFFER_PG — Phase E: ハードコード定数調査

## スキャン対象ソース

| ファイル | SHA (HEAD) |
|---------|-----------|
| `sonic-swss/cfgmgr/buffermgrdyn.cpp` | HEAD |
| `sonic-swss/cfgmgr/buffermgr.cpp` | HEAD |
| `sonic-swss/orchagent/bufferorch.cpp` | HEAD |
| `sonic-swss/orchagent/portsorch.h` | HEAD |
| `sonic-swss/cfgmgr/buffermgrdyn.h` | HEAD |

---

## 検出定数一覧

### 1. PG インデックス範囲 (0–7)

- YANG `sonic-buffer-pg.yang` の `pg_num` パターン: `[0-7]((-)[0-7])?`
- `buffermgrdyn.cpp` L1336: `objectsMap = (1 << portInfo.maximum_buffer_objects[BUFFER_PG]) - 1`
  - `maximum_buffer_objects[BUFFER_PG]` は STATE_DB `BUFFER_MAX_PARAM` で実機から取得 (最大値 8 = インデックス 0–7)。
- 実装上 PG インデックスは `uint8_t` にキャストして使用 (`buffermgr.cpp` L197)。
- lossless PG は通常 `3,4`（PFC コスマップ依存; `buffers_config.j2` 参照）。

### 2. PG プロファイル名パターン

`buffermgrdyn.cpp` L481–525 `getDynamicProfileName()`:

```
pg_lossless_<speed>_<cable>           (MTU=9100 デフォルト時)
pg_lossless_<speed>_<cable>_mtu<mtu>  (非デフォルト MTU 時)
[上記] + _th<threshold>               (threshold != m_defaultThreshold 時)
[上記] + _<gearbox_model>             (gearbox モデル指定時)
[上記] + _8lane                       (Mellanox 8-lane 特殊ポート)
[上記] + _profile                     (最終サフィックス固定)
```

例: `pg_lossless_100000_5m_profile`、`pg_lossless_100000_5m_8lane_profile`

静的モード (`buffermgr.cpp` L183–184):
```
pg_lossless_<speed>_<cable>_profile
```

### 3. デフォルト MTU 定数

`buffermgrdyn.h` L15:
```c
#define DEFAULT_MTU_STR "9100"
```
MTU がこの値と一致する場合はプロファイル名に `_mtu` サフィックスが付かない。

### 4. lossless pool 名定数

`buffermgrdyn.h` L14:
```c
#define INGRESS_LOSSLESS_PG_POOL_NAME "ingress_lossless_pool"
```
`buffermgr.h` L13 にも同定義。buffermgrdyn.cpp 全域で使用。

### 5. DB テーブル名定数

| 定数 | 値 | 定義 |
|------|----|------|
| `APP_BUFFER_PG_TABLE_NAME` | `"BUFFER_PG_TABLE"` | `sonic-swss-common/common/schema.h:161` |
| `CFG_BUFFER_PG_TABLE_NAME` | `"BUFFER_PG"` (buffermgr.cpp L140 参照) | `buffermgr.cpp` ほか |

### 6. SAI 識別子

| SAI ID | 用途 | evidence |
|--------|------|---------|
| `SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE` | PG へのバッファプロファイル設定 | `bufferorch.cpp` L1425 |
| `SAI_OBJECT_TYPE_INGRESS_PRIORITY_GROUP` | PG オブジェクト型 | `bufferorch.cpp` L1458 |
| `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES` | PG xoff watermark 統計 | `portsorch.cpp` L412 |
| `SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES` | PG shared watermark 統計 | `portsorch.cpp` L413 |
| `SAI_INGRESS_PRIORITY_GROUP_STAT_DROPPED_PACKETS` | PG drop counter 統計 | `portsorch.cpp` L418 |

### 7. FlexCounter グループ名

`portsorch.h` L36–40:

| マクロ | 値 | ポーリング間隔 |
|--------|-----|--------------|
| `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_WATERMARK_STAT_COUNTER"` | 60,000 ms |
| `PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_DROP_STAT_COUNTER"` | 10,000 ms |

`flexcounterorch.cpp` L53–54:
```c
#define PG_WATERMARK_KEY  "PG_WATERMARK"
#define PG_DROP_KEY       "PG_DROP"
```
これらの `KEY` は `FLEX_COUNTER_TABLE` 上のキーとして CONFIG_DB に設定される。

---

## 主な乖離・注意点

| 定数 | 備考 |
|------|------|
| `DEFAULT_MTU_STR = "9100"` | SONiC デフォルト MTU。9100 以外のポートは profile 名に `_mtu9216` 等が付く |
| `INGRESS_LOSSLESS_PG_POOL_NAME = "ingress_lossless_pool"` | ハードコード固定。`BUFFER_POOL` テーブルのキーと一致必須 |
| PG watermark ポーリング 60,000 ms | `portsorch.cpp` L92 では数値 `60000` と文字列 `"60000"` が両方存在 (macro + numeric) |
| lossless PG インデックス (3,4) | コード上のハードコードではなく `buffers_config.j2` テンプレートに依存。HWSKU によって異なり得る |
