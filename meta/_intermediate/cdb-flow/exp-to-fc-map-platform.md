# EXP_TO_FC_MAP — Phase H プラットフォーム差異調査

## 調査対象

- `orchagent/qosorch.cpp` (sonic-swss@4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/cbf/nhgmaporch.cpp`
- `sonic-buildimage/files/build_templates/qos_config.j2`
- CBF HLD: `SONiC/doc/cbf/cbf_hld.md`

## FC サポート有無（最大のプラットフォーム差）

`EXP_TO_FC_MAP` の動作はスイッチが CBF (Class-Based Forwarding) / MPLS EXP → FC マッピングを
SAI レベルでサポートするかどうかに依存する。

### SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES

`NhgMapOrch::getMaxNumFcs()` が初回呼び出し時に
`sai_switch_api->get_switch_attribute(gSwitchId, 1, SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES)`
で取得する（`nhgmaporch.cpp:299-325`）。

| 結果 | max_num_fcs 値 | EXP_TO_FC_MAP SET 時の挙動 |
|------|---------------|--------------------------|
| SAI クエリ成功 (`SAI_STATUS_SUCCESS`) | スイッチ返値（例: テスト環境 = 63） | `fc` 値が `[0, max_num_fcs)` の範囲なら受理 |
| SAI クエリ失敗（FC 未サポートスイッチ） | `0` (固定) | 全 `fc` 値が `task_invalid_entry` で reject。`SWSS_LOG_WARN("Switch does not support FCs")` のみ出力 |

**影響**: FC 未サポートの ASIC（= `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES` 未定義）では、
`EXP_TO_FC_MAP` エントリを CONFIG_DB に書いても SAI/ASIC に一切反映されない（silent drop）。

## VoQ / DPU / SmartSwitch の影響

`handleExpToFcTable()` 実装には `gMySwitchType` のガードが存在しない。

| 環境 | 影響 | 根拠 |
|------|------|------|
| 通常（non-VoQ）NPU | 差異なし | 標準パス |
| VoQ システム | `QosOrch::doTask()` 内の VoQ 分岐（`gMySwitchType == "voq"`, `qosorch.cpp:1637,1715,1772`）は QUEUE ハンドラのみ対象。EXP_TO_FC_MAP パスに VoQ 分岐なし | 差異なし |
| DPU (SmartSwitch) | `handleExpToFcTable` には DPU ガードなし。ただし DPU では MPLS が通常使用されない | MPLS CBF は DPU 環境では事実上不使用 |

## qos_config.j2 テンプレート

汎用 `qos_config.j2` (`sonic-buildimage/files/build_templates/qos_config.j2`) に
`EXP_TO_FC_MAP` セクションは存在しない（CBF は MPLS 環境固有のためデフォルト定義なし）。

| プラットフォーム | EXP_TO_FC_MAP の初期値 |
|----------------|----------------------|
| 汎用 AZURE QoS | なし（`qos_config.j2` に定義なし） |
| MPLS 対応ベンダー固有プラットフォーム | プラットフォーム固有の j2 テンプレートに定義される場合あり |

## YANG 制約との乖離（プラットフォーム依存部分）

| フィールド | YANG パターン | 実装上限 | 差異の原因 |
|-----------|--------------|---------|-----------|
| `fc` | `"[0-7]?"` (最大 7) | `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES` 返値（例: 63） | SAI query 結果がプラットフォーム依存 |

## サマリ

| 観点 | 結果 | 根拠 |
|------|------|------|
| FC サポート有無 | **プラットフォーム依存** — `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES` クエリ結果で確定 | `nhgmaporch.cpp:299-325` |
| VoQ | 差異なし（EXP_TO_FC_MAP パスに VoQ 分岐なし） | `qosorch.cpp:1637,1715,1772` は QUEUE 専用 |
| DPU / SmartSwitch | 差異なし（実装ガードなし）、MPLS CBF は DPU では非使用 | — |
| multi-asic | 各 ASIC の orchagent が独立して CONFIG_DB を購読 | 標準 SubscriberStateTable 動作 |
| qos_config.j2 初期値 | なし（MPLS CBF は汎用デフォルトなし） | `sonic-buildimage/files/build_templates/qos_config.j2` |
