# COPP_GROUP — Task F Phase H: プラットフォーム差分

生成日: 2026-05-16  
ソース: `sonic-swss/orchagent/copporch.cpp`、`sonic-swss/cfgmgr/coppmgr.cpp`

---

## 1. SAI hostif trap group capability クエリ

### `publishTrapIdsCapability()` (copporch.cpp L240-299)

`CoppOrch` コンストラクタから呼ばれ、起動時に 1 回だけ実行される。

```
sai_query_attribute_enum_values_capability(
    gSwitchId,
    SAI_OBJECT_TYPE_HOSTIF_TRAP,
    SAI_HOSTIF_TRAP_ATTR_TRAP_TYPE,
    &enum_values_capability)
```

- **成功時**: SAI から返ったトラップ種別リストを `supported_trap_ids` (in-memory set) に格納し、`STATE_DB.COPP_TRAP_CAPABILITY_TABLE|traps` に `trap_ids` フィールドとして書き込む。
- **失敗時 (SAI_STATUS_SUCCESS 以外)**: SWSS_LOG_NOTICE を出力し、ハードコードされた `default_supported_trap_ids` (44 種) にフォールバック。このリストは静的であり、新しいトラップ追加では更新されない設計 (`/* This list is intended to remain static */`)。

**ASIC ベンダー対応差**:  
`sai_query_attribute_enum_values_capability` は SAI 標準 API であるが、ベンダー SAI が対応していない場合は失敗する。対応ベンダー SAI であれば実際にサポートするトラップ種別のみが返る。未対応ベンダーでは `default_supported_trap_ids` にフォールバックする (copporch.cpp L265-270)。

---

## 2. `trap_priority` のプラットフォーム差

### 2-a. デフォルトトラップ初期化時 (copporch.cpp L347-359)

```cpp
char *platform = getenv("platform");
if (!platform || (!strstr(platform, MLNX_PLATFORM_SUBSTRING)
                  && (!strstr(platform, MRVL_PRST_PLATFORM_SUBSTRING))))
{
    attr.id = SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY;
    attr.value.u32 = 1;
    trap_id_attrs.push_back(attr);
}
```

- `MLNX_PLATFORM_SUBSTRING = "mellanox"` (orch.h L42)
- `MRVL_PRST_PLATFORM_SUBSTRING = "marvell-prestera"` (orch.h L41)
- **Mellanox / Marvell Prestera** では `SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY` を **設定しない**。これらプラットフォームが trap priority 設定をサポートしないため。
- **その他 ASIC** (Broadcom, Barefoot/Intel, VS 等) では priority = 1 をデフォルトとして設定し、SAI 内部デフォルト (0) による意図しないパケットトラップ挙動を回避する。

### 2-b. ユーザー設定 `trap_priority` 反映時 (copporch.cpp L1184-1194)

`parseTrapGroupAttribute()` 内で同じ platform チェックを再実施する:

```cpp
char *platform = getenv("platform");
if (!platform || (!strstr(platform, MLNX_PLATFORM_SUBSTRING)
                  && (!strstr(platform, MRVL_PRST_PLATFORM_SUBSTRING))))
{
    attr.id = SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY;
    attr.value.u32 = (uint32_t)stoul(fvValue(*i));
    trap_id_attribs.push_back(attr);
}
```

- Mellanox / Marvell Prestera では CONFIG_DB の `trap_priority` フィールドが **無視される**（SAI への属性セットが行われない）。ログ出力も行われないためサイレントスキップとなる。

---

## 3. VOQ / Chassis 差

`copporch.cpp` 全体を精査したが、VOQ (Virtual Output Queue) chassis 固有のコードパスは存在しない。CoppOrch は VOQ chassis の linecard / system port に対して追加の分岐を持たない。COPP はホスト CPU 受信トラフィックに適用され、VOQ スイッチファブリックの転送パスには依存しない。

---

## 4. 未サポートトラップのフィルタリング

`processCoppTrapGroup()` (copporch.cpp L411 周辺):

```cpp
SWSS_LOG_NOTICE("Ignoring the trap_id: %s, since not supported by vendor SAI", trap_id_str.c_str());
```

`supported_trap_ids` に含まれないトラップ ID は SAI への登録をスキップする。これにより、特定ベンダー SAI が対応していないトラップ種別を CONFIG_DB/APPL_DB に設定しても、`orchagent` がエラー終了せずスキップする設計になっている。

---

## 5. evidence まとめ

| 差分項目 | ファイル | 行番号 |
|---------|---------|--------|
| SAI capability クエリ + フォールバック | copporch.cpp | L240-299 |
| default trap priority 設定 (Mellanox/Marvell 除外) | copporch.cpp | L347-359 |
| ユーザー設定 trap_priority スキップ (Mellanox/Marvell) | copporch.cpp | L1184-1194 |
| 未サポートトラップ ID スキップ | copporch.cpp | L411 |
| platform 環境変数定義 | orch.h | L41-42 |
