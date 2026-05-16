# dscp-to-tc-map — Phase H: プラットフォーム差分

ソース: `sonic-swss/orchagent/qosorch.cpp`, `sonic-utilities/scripts/db_migrator.py`,
`sonic-buildimage/files/build_templates/qos_config.j2`,
`sonic-buildimage/device/mellanox/*/qos.json.j2`

---

## 1. SAI capability クエリによる分岐

### `querySwitchCapability(SAI_OBJECT_TYPE_SWITCH, SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP)`

`applyDscpToTcMapToSwitch()` (`qosorch.cpp:1955-1975`) は SAI を呼ぶ前に
`sai_query_attribute_capability()` でスイッチレベルへの DSCP→TC map 適用が
実装されているか確認する。

| 結果 | 挙動 |
|------|------|
| `capability.set_implemented == true` | SAI に `sai_switch_api->set_switch_attribute()` を発行 |
| `capability.set_implemented == false` または query 失敗 | **エラーなし・silent skip** で `true` を返す |

→ **SAI が `SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` をサポートしていない ASIC では
`PORT_QOS_MAP|global` の設定はノーオペレーションになる。**

---

## 2. Broadcom: スイッチレベル自動生成 (db_migrator)

`db_migrator.py:700-715` の `migrate_port_qos_map_global()`:

```python
asics_require_global_dscp_to_tc_map = ["broadcom"]
if self.asic_type not in asics_require_global_dscp_to_tc_map:
    return
```

- **Broadcom ASIC のみ** でアップグレード時に `PORT_QOS_MAP|global` を自動生成。
- 既存 `DSCP_TO_TC_MAP` テーブルの `get_keys()` で先頭 1 件を取得して設定。
- **複数マップ存在時は先頭（順序未定義）の 1 件のみ**が global に適用される。
- Mellanox / その他 ASIC ではこの自動生成は行われない（`return` で早期終了）。

---

## 3. Mellanox: AZURE_UPLINK マップと `different_dscp_to_tc_map`

Mellanox 向け `qos.json.j2` (例: `x86_64-mlnx_msn4600c-r0/Mellanox-SN4600C-C64/qos.json.j2`):

```jinja2
{% set different_dscp_to_tc_map = true %}
{%- macro generate_dscp_to_tc_map() %}
    "AZURE_UPLINK": { ... }
    "AZURE": { ... }
{%- endmacro %}
```

`qos_config.j2:438-447` の条件分岐:

```jinja2
{% if different_dscp_to_tc_map and tunnel_qos_remap_enable %}
  {% if DEVICE_METADATA['localhost']['type'] == 'LeafRouter' ... %}
      "dscp_to_tc_map": "AZURE_UPLINK"
  {% elif DEVICE_METADATA['localhost']['subtype'] == 'DualToR' ... %}
      "dscp_to_tc_map": "AZURE_UPLINK"
  {% else %}
      "dscp_to_tc_map": "AZURE"
```

| デバイスタイプ | `tunnel_qos_remap` | 適用マップ |
|---|---|---|
| LeafRouter（ToR 隣接ポート） | enabled | `AZURE_UPLINK` |
| DualToR（LeafRouter 隣接ポート） | enabled | `AZURE_UPLINK` |
| その他全ポート | enabled | `AZURE` |
| 全デバイス | disabled | `AZURE`（single map） |

---

## 4. フォールバック: `generate_dscp_to_tc_map` 未定義時

`qos_config.j2:265-332`: `generate_dscp_to_tc_map` マクロが未定義のプラットフォームでは
ハードコードされた AZURE マップがデフォルト値として埋め込まれる。

代表的なデフォルト値:

| DSCP | TC |
|------|----|
| 3, 4 | 3, 4（lossless） |
| 8 | 0（best-effort） |
| 46 | 5（EF） |
| 48 | 6（CS6/network control） |
| その他 | 1 |

Broadcom では `generate_dscp_to_tc_map_per_sku` による SKU 単位のカスタマイズもある
（`qos_config.j2:262-263`）。

---

## 5. TC 範囲の ASIC 差分

YANG 定義の `tc_type`: `uint8 range "0..15"` (`sonic-types.yang.j2:338`)。

| ASIC | 実際に受け付ける TC 範囲 | 備考 |
|------|--------------------------|------|
| Broadcom（大多数） | 0..7 | TC 8+ は SAI エラー → `task_failed` |
| Mellanox（大多数） | 0..7 | 同上 |
| 一部高性能 ASIC | 0..15 の可能性 | SAI ベンダー実装依存 |

**YANG は 0..15 を許可するが、現行 ASIC の大多数は 0..7 のみサポート。**

---

## 6. Evidence

- `qosorch.cpp:1955-1975` — `applyDscpToTcMapToSwitch` + `querySwitchCapability`
- `db_migrator.py:700-715` — Broadcom 限定 global 自動生成
- `qos_config.j2:142-170,254-263,437-447` — tunnel_qos_remap / AZURE_UPLINK 条件分岐
- `device/mellanox/.../qos.json.j2:23,160-170` — `different_dscp_to_tc_map = true`, AZURE_UPLINK macro
