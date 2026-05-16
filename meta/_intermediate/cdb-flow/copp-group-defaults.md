# COPP_GROUP Phase A — コード由来の暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象ページ: `docs/reference/config-db/copp-group.md`

## エントリポイント grep 結果 (1 回限り)

```
grep -rln "COPP_GROUP" .cache/sonic-sources/ → 30 件
主要: coppmgr.cpp, copporch.cpp, sonic-copp.yang, copp_cfg.j2
```

## フィールド列挙と YANG default 対応

| フィールド | YANG default | mandatory |
|---|---|---|
| `queue` | 0 | no |
| `trap_priority` | 0 | no |
| `trap_action` | なし | yes |
| `meter_type` | なし | yes |
| `mode` | なし | yes |
| `color` | なし | no |
| `cir` | 0 | no |
| `cbs` | 0 | no |
| `pir` | なし | no (when=tr_tcm) |
| `pbs` | なし | no (when=sr_tcm/tr_tcm) |
| `green_action` | forward | no |
| `yellow_action` | forward | no (when=sr_tcm/tr_tcm) |
| `red_action` | forward | no |

## コード由来の暗黙デフォルト（主要発見）

### 1. `default` グループの `trap_action` 省略 → SAI はデフォルト動作継続

`copp_cfg.j2` の `default` グループには `trap_action` フィールドが存在しない（YANG mandatory=true だが JSON には記載なし）。`copporch.cpp::getAttribsFromTrapGroup()` は来たフィールドのみ SAI に渡す。`trap_action` 未指定の場合、SAI hostif trap のデフォルト（SAI 実装依存）が使われる。

証拠: `copp_cfg.j2` L3-9 `default` エントリに `trap_action` なし。`getAttribsFromTrapGroup` L1162-1294 は `trap_action` が来た場合のみ `trap_id_attribs` に追加。

### 2. `trap_priority` — プラットフォーム依存の silent drop

`getAttribsFromTrapGroup()` L1184-1195:
```cpp
char *platform = getenv("platform");
if (!platform || (!strstr(platform, MLNX_PLATFORM_SUBSTRING) && (!strstr(platform, MRVL_PRST_PLATFORM_SUBSTRING))))
{
    attr.id = SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY,
    attr.value.u32 = (uint32_t)stoul(fvValue(*i));
    trap_id_attribs.push_back(attr);
}
```
Mellanox (`mlnx`) または Marvell (`mrvl_prest`) プラットフォームでは `trap_priority` フィールドは CONFIG_DB に存在しても SAI に渡されない（silent drop）。他プラットフォームでは反映される。

### 3. `initDefaultTrapIds()` — `SAI_HOSTIF_TRAP_TYPE_TTL_ERROR` のハードコード動作

`copporch.cpp` L332-368:
- 起動時に `SAI_HOSTIF_TRAP_TYPE_TTL_ERROR` を `default` グループに強制登録
- `trap_priority` = 1 にハードコード（ただし Mellanox/Marvell では省略）
- `trap_action` = `SAI_PACKET_ACTION_TRAP` にハードコード
- これは CONFIG_DB の `COPP_GROUP|default` の値とは独立して実行される

### 4. `color` 省略 → SAI デフォルト (`blind` 相当)

`color` フィールドが CONFIG_DB に存在しない場合、`getAttribsFromTrapGroup()` は `SAI_POLICER_ATTR_COLOR_SOURCE` を policer_attribs に追加しない。SAI policer 作成時にデフォルト値（実装依存、通常 `SAI_POLICER_COLOR_SOURCE_BLIND`）が適用される。`policer_object` 構造体の `color` フィールドも未初期化のまま残る。

### 5. `green_action` / `yellow_action` / `red_action` の二重デフォルト

YANG default = `forward`。コード（`getAttribsFromTrapGroup()`）は省略時に SAI に渡さないため、SAI 実装のデフォルト（通常 `forward`）が使われる。YANG と SAI デフォルトは一致するが、SAI 実装が異なる場合は乖離の可能性がある。

### 6. `mergeConfig()` での NULL cfg → 全フィールド除外

`coppmgr.cpp` L218-224:
```cpp
if(fvField(it2) == "NULL")
{
    SWSS_LOG_DEBUG("Ignoring create for key %s",i.first.c_str());
    null_cfg = true;
    break;
}
```
ユーザーが `COPP_GROUP|<name>` に `NULL` フィールドを設定すると、そのキー全体が `mergeConfig()` で除外される。`m_cfg[i.first]` は設定されず、APPL_DB への書き込みも行われない。init cfg（`copp_cfg.j2`）のデフォルト値もマージされない。

### 7. `cir=0` の意味とデフォルト実効値

YANG default = 0。`cir=0` の場合 policer は rate unlimitied として SAI に渡される（`SAI_POLICER_ATTR_CIR=0` は SAI 仕様でレート無制限）。`copp_cfg.j2` の `default` グループは `cir=600` を明示しているため、デフォルトでは 600 pps 制限が適用される。

### 8. `queue4_group3` の `cir`/`cbs` プラットフォーム分岐

`copp_cfg.j2` L37-43:
```jinja2
{% if DEVICE_METADATA['localhost']['type'] is defined and 'Mgmt' in DEVICE_METADATA['localhost']['type'] %}
    "cir":"300", "cbs":"300",
{% else %}
    "cir":"100", "cbs":"100",
{% endif %}
```
管理スイッチ型デバイスでは `lldp`/`dhcp_relay` の cir/cbs が 300 pps、それ以外は 100 pps。

### 9. DEL_COMMAND → init cfg からの自動復元

`coppmgr.cpp` L898-921: COPP_GROUP エントリが削除されると、`m_coppGroupInitCfg` に存在する場合は init cfg（`copp_cfg.j2`）の値で自動再作成される。つまり、ユーザーが `sonic-db-cli CONFIG_DB del 'COPP_GROUP|queue4_group1'` しても、デーモン再起動後または次回 coppmgrd 処理時に init 値で復元される。

### 10. `policer_object` の未初期化フィールド

`createPolicer()` L632-650 で `obj.meter`, `obj.mode`, `obj.color` は `policer_attribs` に含まれる場合のみ設定される。`color` が省略された場合 `obj.color` はデフォルト初期化（`0` = `SAI_POLICER_COLOR_SOURCE_AWARE` の可能性）のまま `m_trap_group_policer_map` に保存される。後の `trapGroupUpdatePolicer()` でこの未初期化値と比較されるため、誤った「変更なし」判定が起きる可能性がある（potential bug）。

## プラットフォーム依存まとめ

| プラットフォーム | 影響フィールド | 挙動 |
|---|---|---|
| Mellanox (`mlnx`) | `trap_priority` | SAI に渡されない（silent drop） |
| Marvell Prestera (`mrvl_prest`) | `trap_priority` | SAI に渡されない（silent drop） |
| Mgmt switch type | `queue4_group3.cir/cbs` | 100 → 300 pps に変更 |
| SAI capability query 失敗時 | `trap_ids` | `default_supported_trap_ids` 固定リストにフォールバック（`neighbor_miss` が含まれない） |

## SAI fallback: supported trap IDs

`copporch.cpp` L104-151: SAI capability query が失敗した場合、`default_supported_trap_ids` の静的リストにフォールバック。このリストには `neighbor_miss` が含まれない（コメント: "This list is intended to remain static and should not be updated with new traps"）。よって古い SAI では `neighbor_miss` trap が silent drop される。
