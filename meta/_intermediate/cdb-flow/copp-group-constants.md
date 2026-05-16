# COPP_GROUP Phase E — ハードコード定数調査

## 調査対象ファイル

- `sonic-swss/orchagent/copporch.h`
- `sonic-swss/orchagent/copporch.cpp`
- `sonic-swss/orchagent/orch.h`
- `sonic-buildimage/files/image_config/copp/copp_cfg.j2`

## 発見した定数一覧

### copporch.h (L23)

```cpp
#define HOSTIF_TRAP_COUNTER_FLEX_COUNTER_GROUP "HOSTIF_TRAP_FLOW_COUNTER"
```

FlexCounter グループ名。COUNTERS_DB の flex counter グループ識別子。CONFIG_DB と無関係だが orchagent 内部で固定値として使われる。

### copporch.cpp (L37)

```cpp
#define FLEX_COUNTER_UPD_INTERVAL 1
```

FlexCounter 更新タイマー間隔 = **1 秒**。`SelectableTimer` の `timespec.tv_sec` に使われる。

### copporch.cpp (L184–187)

```cpp
const string default_trap_group = "default";
const vector<sai_hostif_trap_type_t> default_trap_ids = {
    SAI_HOSTIF_TRAP_TYPE_TTL_ERROR
};
```

- デフォルトグループ名は文字列リテラル `"default"` で固定。
- デフォルト trap ID リストは `TTL_ERROR` のみ。CONFIG_DB の値に依らず `initDefaultTrapIds()` で強制登録される。

### copporch.cpp (L189)

```cpp
const uint HOSTIF_TRAP_COUNTER_POLLING_INTERVAL_MS = 10000;
```

HostIF trap カウンタのポーリング間隔 = **10,000 ms (10 秒)**。FlexCounterManager に渡される。

### copporch.cpp (L357)

```cpp
attr.value.u32 = 1;  // trap_priority for TTL_ERROR
```

`initDefaultTrapIds()` 内。`TTL_ERROR` の `SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY` を **1** にハードコード。
ただし Mellanox (`mlnx`) / Marvell (`marvell-prestera`) では `trap_priority` 設定をスキップ。

### orch.h (L41–42)

```cpp
#define MRVL_PRST_PLATFORM_SUBSTRING "marvell-prestera"
#define MLNX_PLATFORM_SUBSTRING      "mellanox"
```

プラットフォーム判定文字列。`platform` 環境変数と `strstr` で比較される。

### copp_cfg.j2 — デフォルトグループ定数

| グループ名 | queue | cir (pps) | cbs (pps) | trap_action | trap_priority |
|-----------|-------|-----------|-----------|-------------|---------------|
| `default` | 0 | 600 | 600 | (未設定) | (未設定) |
| `queue4_group1` | 4 | 6000 | 6000 | trap | 4 |
| `queue4_group2` | 4 | 600 | 600 | copy | 4 |
| `queue4_group3` | 4 | 100 (Mgmt: 300) | 100 (Mgmt: 300) | trap | 4 |
| `queue1_group1` | 1 | 6000 | 6000 | trap | 1 |
| `queue1_group2` | 1 | 600 | 600 | trap | 1 |
| `queue1_group3` | 1 | 200 | 200 | trap | 1 |
| `queue2_group1` | 2 | 1000 | 1000 | trap | 1 |

`queue4_group3` は Jinja2 で `DEVICE_METADATA.localhost.type` に `'Mgmt'` が含まれる場合のみ `cir=cbs=300`、それ以外は `100`。

### 補足: field 名文字列（copporch.h L26–46）

フィールド名は C++ `const string` として定義されており、変更は再ビルドが必要。CONFIG_DB のキー名がこれと一致しない場合は `parseTrapGroupAttribute()` で `task_failed` となる。

## 結論

主なハードコード定数:
1. デフォルトグループ名 `"default"` → 削除不可（orchagent がハードコードで保護）
2. TTL_ERROR trap priority = `1`（Mellanox/Marvell を除く）
3. FlexCounter ポーリング = 10 秒
4. FlexCounter 更新タイマー = 1 秒
5. プラットフォーム判定文字列 `"mellanox"` / `"marvell-prestera"`
6. `copp_cfg.j2` の pps 値 (100 / 200 / 300 / 600 / 1000 / 6000)
