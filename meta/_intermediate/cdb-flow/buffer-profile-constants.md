# BUFFER_PROFILE ハードコード定数 (Task F Phase E)

対象ソース:
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` / `buffermgrdyn.h`
- `sonic-swss/cfgmgr/buffermgr.cpp`
- `sonic-swss/orchagent/bufferorch.cpp` / `bufferorch.h`
- `sonic-swss/orchagent/buffer/bufferschema.h`

---

## 1. threshold_mode 値（フィールド名文字列）

| 定数名 | 値 | 定義箇所 |
|--------|-----|---------|
| `buffer_dynamic_th_field_name` | `"dynamic_th"` | `orchagent/bufferorch.h:28` |
| `buffer_static_th_field_name` | `"static_th"` | `orchagent/bufferorch.h:29` |

`dynamic_th` フィールドが存在 → `threshold_mode = "dynamic_th"` として扱う。  
`static_th` フィールドが存在 → `threshold_mode = "static_th"` として扱う。  
どちらも未指定の場合、pool の `mode` に `"_th"` を付加した文字列が `threshold_mode` として採用される (`buffermgrdyn.cpp:901,2719`)。

## 2. packet_discard_action 値

| 定数名 | 値 | 定義箇所 |
|--------|-----|---------|
| `BUFFER_PROFILE_PACKET_DISCARD_ACTION` | `"packet_discard_action"` | `orchagent/buffer/bufferschema.h:8` |
| `BUFFER_PROFILE_PACKET_DISCARD_ACTION_DROP` | `"drop"` | `orchagent/buffer/bufferschema.h:5` |
| `BUFFER_PROFILE_PACKET_DISCARD_ACTION_TRIM` | `"trim"` | `orchagent/buffer/bufferschema.h:6` |

`"trim"` 以外の値（`"drop"` を含む）は `SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP` にマップされる。  
`"trim"` は `SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP_AND_TRIM` にマップされる。  
未設定時は APPL_DB/SAI に送出されない（SAI platform default が適用）。

## 3. SAI 識別子マッピング（bufferorch.cpp L661-736）

| CONFIG_DB フィールド | SAI 属性 ID | SAI 値 |
|---------------------|------------|--------|
| `pool` | `SAI_BUFFER_PROFILE_ATTR_POOL_ID` | sai_object_id_t |
| `xon` | `SAI_BUFFER_PROFILE_ATTR_XON_TH` | uint64 (bytes) |
| `xon_offset` | `SAI_BUFFER_PROFILE_ATTR_XON_OFFSET_TH` | uint64 (bytes) |
| `xoff` | `SAI_BUFFER_PROFILE_ATTR_XOFF_TH` | uint64 (bytes) |
| `size` | `SAI_BUFFER_PROFILE_ATTR_BUFFER_SIZE` | uint64 (bytes) |
| `dynamic_th` | `SAI_BUFFER_PROFILE_ATTR_THRESHOLD_MODE` → `SAI_BUFFER_PROFILE_THRESHOLD_MODE_DYNAMIC`; `SAI_BUFFER_PROFILE_ATTR_SHARED_DYNAMIC_TH` | sai_int8_t (alpha) |
| `static_th` | `SAI_BUFFER_PROFILE_ATTR_THRESHOLD_MODE` → `SAI_BUFFER_PROFILE_THRESHOLD_MODE_STATIC`; `SAI_BUFFER_PROFILE_ATTR_SHARED_STATIC_TH` | uint64 (bytes) |
| `packet_discard_action=drop` | `SAI_BUFFER_PROFILE_ATTR_PACKET_ADMISSION_FAIL_ACTION` | `SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP` |
| `packet_discard_action=trim` | `SAI_BUFFER_PROFILE_ATTR_PACKET_ADMISSION_FAIL_ACTION` | `SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP_AND_TRIM` |

注意: `pool` および閾値モード (`SAI_BUFFER_PROFILE_ATTR_THRESHOLD_MODE`) は SAI create-only 属性。既存オブジェクトへの変更は silently スキップ (`bufferorch.cpp L655-659, L694-714`)。

## 4. headroom override 関連ハードコード

| 定数名 | 値 | 定義箇所 | 用途 |
|--------|-----|---------|------|
| `INGRESS_LOSSLESS_PG_POOL_NAME` | `"ingress_lossless_pool"` | `cfgmgr/buffermgrdyn.h:14` | headroom_type=dynamic 時にデフォルト pool として強制セット |
| `DEFAULT_MTU_STR` | `"9100"` | `cfgmgr/buffermgrdyn.h:15` | port の MTU が未設定の場合に使用されるデフォルト MTU (bytes) |
| `BUFFERMGR_TIMER_PERIOD` | `10` (秒) | `cfgmgr/buffermgrdyn.h:17` | buffermgrd のポーリング周期 |

headroom override (`headroom_type=dynamic`) 時: `pool` が未指定の場合 `INGRESS_LOSSLESS_PG_POOL_NAME` が自動補完され、`lossless=true` + `direction=BUFFER_INGRESS` が強制セットされる (`buffermgrdyn.cpp:987,2788-2794`)。

## 5. pool mode 文字列定数（bufferorch.h L22-23）

| 定数名 | 値 | 意味 |
|--------|-----|------|
| `buffer_pool_mode_dynamic_value` | `"dynamic"` | pool が dynamic shared buffer mode |
| `buffer_pool_mode_static_value` | `"static"` | pool が static threshold mode |

pool mode と threshold_mode の整合性チェックに使用。不一致時は `task_failed`。

## 6. headroom_type フィールド値

| 値 | 効果 | evidence |
|----|------|---------|
| `"dynamic"` | `dynamic_calculated=true`、`lossless=true`、`direction=BUFFER_INGRESS` を強制セット。ポートに参照されるまで APPL_DB への書き込みを defer | `buffermgrdyn.cpp:2788-2795` |
| `"static"` または未設定 | `dynamic_calculated=false`（デフォルト）。CONFIG_DB の明示値を APPL_DB にそのまま転送 | `buffermgrdyn.cpp:2692` |

---

スキャン証跡:
- `buffermgrdyn.cpp` L890-922 (`updateBufferProfileToDb`)
- `buffermgrdyn.cpp` L2671-2935 (`handleBufferProfileTable`)
- `bufferorch.cpp` L620-760 (`processBufferProfile`)
- `bufferschema.h` 全行
- `bufferorch.h` L15-35
- `buffermgrdyn.h` L14-25
