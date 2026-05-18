# dscp-to-fc-map — Phase H: プラットフォーム差分

ソース: `sonic-swss/orchagent/qosorch.cpp`,
`sonic-swss/orchagent/cbf/nhgmaporch.cpp`,
`sonic-buildimage/files/build_templates/cbf_config.j2`

調査日: 2026-05-18

---

## 1. プラットフォーム識別方法

`DscpToFcMapHandler` は `getenv("platform")` / `MLNX_PLATFORM_SUBSTRING` による分岐を**一切持たない**。
`gMySwitchType` (VoQ 分岐) も使用しない。
唯一の実装差は SAI capability query (`SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES`) 経由で生じる。

---

## 2. SAI capability — FC 非対応 ASIC での全エントリ reject

`NhgMapOrch::getMaxNumFcs()` (`nhgmaporch.cpp:299-324`) は初回呼び出し時に
`sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr)` で
`SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES` を取得する。

| SAI 戻り値 | `max_num_fcs` | `DSCP_TO_FC_MAP` への影響 |
|---|---|---|
| `SAI_STATUS_SUCCESS` | `attr.value.u8`（通常 8〜64） | FC 0..`max_num_fcs-1` が有効 |
| それ以外 (NOT_SUPPORTED 等) | **0** | 全 FC 値が `fc >= 0` 条件で reject → `task_invalid_entry` |

FC 非対応 ASIC では SAI map オブジェクトが一切作成されない（silent drop + ERROR ログのみ）。

---

## 3. cbf_config.j2 — CBF マップはプラットフォーム共通テンプレート

`sonic-buildimage/files/build_templates/cbf_config.j2` の AZURE マップは全 ASIC 共通で
64 エントリを定義する。プラットフォーム固有 `cbf.json.j2` による上書きは可能だが、
community master 公開分では Mellanox / Broadcom 固有の `cbf.json.j2` が存在しない
（`device/<vendor>/<hwsku>/cbf.json.j2` 形式）。

---

## 4. Evidence

- `qosorch.cpp:1039-1094` — `DscpToFcMapHandler::convertFieldValuesToAttributes`
  (platform 分岐なし、`max_num_fcs` による FC 上限チェックのみ)
- `nhgmaporch.cpp:299-324` — `NhgMapOrch::getMaxNumFcs`
  (`SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES` query + fallback=0)
- `cbf_config.j2:1-69` — AZURE マップ全 64 エントリ（プラットフォーム共通）
