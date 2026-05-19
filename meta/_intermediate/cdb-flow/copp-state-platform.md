# COPP_STATE — Phase H プラットフォーム差スキャンノート

対象テーブル: `STATE_DB COPP_GROUP_TABLE` / `COPP_TRAP_TABLE` / `COPP_TRAP_CAPABILITY_TABLE`
Consumer/Producer: `CoppOrch` (`sonic-swss/orchagent/copporch.cpp`)
スキャン範囲: copporch.cpp L240-300 (publishTrapIdsCapability), L343-365 (initDefaultTrapIds platform 分岐), L1154-1295 (getAttribsFromTrapGroup), orch.h L41-42 (定数)

---

## 検出したプラットフォーム差

### 1. Mellanox / Marvell Prestera — `trap_priority` スキップ

**箇所 1**: `initDefaultTrapIds()` — copporch.cpp L348-362
```cpp
char *platform = getenv("platform");
if (!platform || (!strstr(platform, MLNX_PLATFORM_SUBSTRING) && (!strstr(platform, MRVL_PRST_PLATFORM_SUBSTRING))))
{
    attr.id = SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY;
    attr.value.u32 = 1;
    trap_id_attrs.push_back(attr);
}
```

**箇所 2**: `getAttribsFromTrapGroup()` — copporch.cpp L1185-1195
```cpp
/* Mellanox platform doesn't support trap priority setting */
/* Marvell platform doesn't support trap priority. */
char *platform = getenv("platform");
if (!platform || (!strstr(platform, MLNX_PLATFORM_SUBSTRING) && (!strstr(platform, MRVL_PRST_PLATFORM_SUBSTRING))))
{
    attr.id = SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY,
        attr.value.u32 = (uint32_t)stoul(fvValue(*i));
    trap_id_attribs.push_back(attr);
}
```

定数値:
- `MLNX_PLATFORM_SUBSTRING = "mellanox"` (orch.h:42)
- `MRVL_PRST_PLATFORM_SUBSTRING = "marvell-prestera"` (orch.h:41)

**STATE_DB への影響**:
- `COPP_TRAP_TABLE.hw_status` の書き込みロジック自体はプラットフォーム非依存
- `trap_priority` スキップは SAI `create_hostif_trap()` の引数を変えるだけで、成功/失敗の判定は SAI 実装依存
- 成功時: `hw_status=installed` 書き込み（全プラットフォーム共通）
- 失敗時: 書き込みスキップ（全プラットフォーム共通）

### 2. `publishTrapIdsCapability()` — プラットフォーム差なし

`CoppOrch::publishTrapIdsCapability()` (copporch.cpp L240-300) はプラットフォーム環境変数を参照しない。
SAI `sai_query_attribute_enum_values_capability()` の返却値がプラットフォームごとに異なるため、`COPP_TRAP_CAPABILITY_TABLE|traps.trap_ids` の内容はプラットフォームにより変わる。
ただしこれはプラットフォームコードの分岐ではなく SAI 実装の差異による。

---

## プラットフォーム差サマリ

| 検査値 | 対象プラットフォーム | STATE_DB テーブル | 影響内容 |
|--------|------------------|-----------------|---------|
| `getenv("platform")` に `"mellanox"` 含む | Mellanox NOS | `COPP_TRAP_TABLE.hw_status` | trap_priority なしで SAI 呼び出し。hw_status 書込みロジック自体は変化なし |
| `getenv("platform")` に `"marvell-prestera"` 含む | Marvell Prestera | 同上 | 同上 |
| その他 | x86/Broadcom 等 | 同上 | `SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY=1` を含めて SAI 呼び出し |
| SAI capability クエリ結果 | 全プラットフォーム | `COPP_TRAP_CAPABILITY_TABLE` | trap_ids の内容がプラットフォームにより異なる（コード分岐ではなくSAI返却値の差）|
