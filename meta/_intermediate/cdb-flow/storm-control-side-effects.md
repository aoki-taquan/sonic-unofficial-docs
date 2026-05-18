# PORT_STORM_CONTROL テーブル — Phase F 副次 DB 書込・外部テーブル連動

対象テーブル: `CONFIG_DB PORT_STORM_CONTROL`
Consumer: `PolicerOrch::handlePortStormControlTable()` / `doTask()` (`sonic-swss/orchagent/policerorch.cpp`)
スキャン範囲: `policerorch.cpp` 全行（589 行）

---

## 調査結果サマリー

`PolicerOrch::handlePortStormControlTable()` は CONFIG_DB `PORT_STORM_CONTROL` の SET / DEL を処理するが、
**STATE_DB・APPL_DB・COUNTERS_DB への明示的な書込みは一切存在しない**。

副次的な変化は以下の 2 系統に分類される:

1. **ASIC_DB（SAI API 経由）**: syncd を介した ASIC 操作
2. **PolicerOrch 内部状態**: `m_syncdPolicers` / `m_policerRefCounts` の更新

---

## 1. ASIC_DB — SAI API 経由の副次書込

`handlePortStormControlTable()` は直接 ASIC_DB の Redis テーブルへ書き込まない。
SAI API 呼び出しを行い、`syncd` が SAI 操作を ASIC_DB へ反映する。

### SET パス（新規作成）

| SAI API | 操作 | 影響するリソース | evidence |
|---------|------|----------------|----------|
| `sai_policer_api->create_policer()` | SAI policer オブジェクト生成 | ASIC 内 policer リソース | `policerorch.cpp:227-238` |
| `sai_port_api->set_port_attribute()` | ポートに policer OID をアタッチ | `SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID` / `SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID` / `SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID` | `policerorch.cpp:278-286` |

storm_type が `broadcast` / `unknown-unicast` / `unknown-multicast` に応じてアタッチ先 SAI 属性が分岐する:

```cpp
// policerorch.cpp:204-220
if (storm_type == storm_broadcast)
    port_attr.id = SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID;
else if (storm_type == storm_unknown_unicast)
    port_attr.id = SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID;
else if (storm_type == storm_unknown_mcast)
    port_attr.id = SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID;
```

### SET パス（更新）

| SAI API | 操作 | 影響するリソース | evidence |
|---------|------|----------------|----------|
| `sai_port_api->set_port_attribute()` (SAI_NULL_OBJECT_ID) | 既存 policer を一時デタッチ | ポートの storm control が一時解除 | `policerorch.cpp:278-286` |
| `sai_policer_api->set_policer_attribute()` | CIR 更新（`SAI_POLICER_ATTR_CIR` のみ） | ASIC policer の CIR 値 | `policerorch.cpp:257-263` |
| `sai_port_api->set_port_attribute()` (policer_id) | 更新後 policer を再アタッチ | ポートの storm control 再有効化 | `policerorch.cpp:278-286` |

### DEL パス

| SAI API | 操作 | 影響するリソース | evidence |
|---------|------|----------------|----------|
| `sai_port_api->set_port_attribute()` (SAI_NULL_OBJECT_ID) | ポートから policer をデタッチ | ポートの storm control 解除 | `policerorch.cpp:344-347` |
| `sai_policer_api->remove_policer()` | SAI policer オブジェクト削除 | ASIC 内 policer リソース解放 | `policerorch.cpp:349-361` |

---

## 2. PolicerOrch 内部状態 — Orch 内 map の更新

STATE_DB / APPL_DB ではなく PolicerOrch のプロセス内 map が更新される。
他の Orch や DB consumer から直接観測できない「内部副次状態」として記録する。

| map | 操作 | タイミング |
|-----|------|-----------|
| `m_syncdPolicers[storm_policer_name]` | SET（新規）: policer_id 登録 | `create_policer()` 成功後（L239） |
| `m_policerRefCounts[storm_policer_name]` | SET（新規）: 0 で初期化 | 同上（L240） |
| `m_syncdPolicers[storm_policer_name]` | DEL: erase | `remove_policer()` 成功後（L368） |
| `m_policerRefCounts[storm_policer_name]` | DEL: erase | 同上（L369） |

storm control 専用の policer は `m_policerRefCounts = 0` で固定される（他の POLICER テーブル経由の policer と異なり、参照カウントのインクリメント操作が存在しない）。

---

## 3. CONFIG_DB・STATE_DB・APPL_DB への書込なし

スキャン結果: `policerorch.cpp` に `m_cfgDb`・`m_stateDb`・`m_applDb` への `hset`・`hdel`・`del` 呼び出しは存在しない。

storm control の適用結果はオペレータが `show interface storm-control` コマンドで確認できるが、
この情報は STATE_DB ではなく **ASIC の SAI ポート属性を読み戻す**方式で取得される。

---

## 参照関係サマリー（副次書込）

```
PORT_STORM_CONTROL SET
  |- create_policer()   → ASIC_DB (syncd 経由 SAI)
  |- set_port_attribute → ASIC_DB (ポート policer アタッチ)
  `- m_syncdPolicers[]  → PolicerOrch 内部 map

PORT_STORM_CONTROL DEL
  |- set_port_attribute → ASIC_DB (policer デタッチ)
  |- remove_policer()   → ASIC_DB (policer 削除)
  `- m_syncdPolicers[]  → PolicerOrch 内部 map (erase)

STATE_DB 書込: なし
APPL_DB 書込: なし
COUNTERS_DB 書込: なし
```
