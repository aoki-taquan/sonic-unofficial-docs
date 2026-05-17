# sflow-session-platform — Phase H: SFLOW_SESSION プラットフォーム差分

対象ページ: `docs/reference/config-db/sflow-session.md`
調査ソース: `sonic-swss/cfgmgr/sflowmgr.cpp`, `sonic-swss/orchagent/sfloworch.cpp`, `sonic-swss/orchagent/orchdaemon.cpp`
調査日: 2026-05-17

---

## 調査方針

以下のキーワードで全ソースを精読:
- `platform` / `sub_platform` / `getenv` (静的プラットフォーム比較)
- `sai_query_attribute_capability` / `query_attribute_enum_capability` (動的 capability 照会)
- `SAI_SAMPLEPACKET_ATTR_TYPE` / `SAI_SWITCH_ATTR_SAMPLEPACKET` (SAI 機能宣言)
- `voq` / `chassis` / `dpu` / `smartswitch` (特殊ハードウェアモード)

---

## 結果: プラットフォーム差分なし（静的比較・動的照会とも存在しない）

### sflowmgr.cpp

- `getenv("platform")` / `getenv("sub_platform")` の呼び出し: **なし**
- プラットフォーム名文字列比較 (`broadcom`, `mellanox`, etc.): **なし**
- VOQ chassis 分岐 (`is_chassis()` 相当): **なし**
- SmartSwitch / DPU 分岐 (`switch_type == "dpu"`): **なし**
- sflowmgrd は Linux userspace デーモンであり、OS 機能（`service hsflowd restart/stop`）のみ呼び出す。
  ハードウェア差異は SAI 層（orchagent/SflowOrch）が完全に吸収する。

### sfloworch.cpp

- `sai_query_attribute_capability` 呼び出し: **なし**
- `SAI_SWITCH_ATTR_SUPPORTED_*` capability 照会: **なし**
- `getenv("platform")` / `getenv("sub_platform")` の呼び出し: **なし**
- VOQ / DPU 分岐: **なし**
- SflowOrch は SAI `sai_samplepacket_api->create_samplepacket()` と `sai_port_api->set_port_attribute()` を
  プラットフォーム非依存の固定シーケンスで呼び出す。

### 使用する SAI 属性（固定、capability 照会なし）

| SAI API / 属性 | 用途 |
|---------------|------|
| `sai_samplepacket_api->create_samplepacket()` | サンプリングレートごとにセッション作成 |
| `sai_samplepacket_api->remove_samplepacket()` | セッション削除 |
| `SAI_PORT_ATTR_INGRESS_SAMPLEPACKET_ENABLE` | rx / both 方向のポートサンプリング有効化 |
| `SAI_PORT_ATTR_EGRESS_SAMPLEPACKET_ENABLE` | tx / both 方向のポートサンプリング有効化 |
| `SAI_SAMPLEPACKET_ATTR_SAMPLE_RATE` | サンプリングレート（sai_uint32_t）|

いずれも `sai_query_attribute_capability()` での事前照会を行わずに直接呼び出す。
SAI が `SAI_STATUS_NOT_SUPPORTED` や `SAI_STATUS_FAILURE` を返した場合は
`handleSaiCreateStatus` / `handleSaiSetStatus` / `handleSaiRemoveStatus` 経由でログ出力し
`it++; continue` でイベントをスキップするが、フォールバック経路（software sFlow 等）は存在しない。

---

## ASIC ベンダー別傾向（経験則）

sfloworch.cpp 自体はベンダー文字列を参照しないが、SAI 実装の典型的なハードウェアサンプリング対応状況:

| ASIC / プラットフォーム | hardware sFlow サポート | 備考 |
|---|---|---|
| broadcom (Trident3 / Tomahawk) | あり | SAI samplepacket API 実装済み |
| broadcom-dnx (Jericho / Qumran) | 機種依存 | DNX SAI で一部 samplepacket 制限あり |
| mellanox (Spectrum) | あり | Spectrum / Spectrum-2/3/4 で SAI samplepacket 対応 |
| barefoot (Tofino) | 通常なし | P4 ベースのため標準 SAI samplepacket 未実装が多い |
| cisco-8000 (Silicon One) | あり | SAI samplepacket 実装済み |
| marvell-prestera | 機種依存 | SAI 実装次第 |
| vs (Virtual Switch) | **なし** | libsai が samplepacket 未実装。sfloworch は SAI エラーをログ出力してスキップするのみ |

!!! note
    vs (仮想スイッチ) では `create_samplepacket` が SAI_STATUS_NOT_IMPLEMENTED を返すため
    ASIC_DB への反映が行われない。hsflowd / sflowmgrd の userspace 処理は正常動作するが
    ハードウェアサンプリングは機能しない。

---

## 結論

SFLOW_SESSION テーブル処理のプラットフォーム差分は **ゼロ**。
- sflowmgrd: OS の `hsflowd` サービス制御のみ（プラットフォーム非依存）
- SflowOrch: SAI samplepacket API を固定シーケンスで呼び出す（capability 照会なし）
- 差異は SAI 実装層（ASIC SDK）に完全に委譲される。SAI がエラーを返した場合はログ出力 + スキップ（フォールバックなし）
