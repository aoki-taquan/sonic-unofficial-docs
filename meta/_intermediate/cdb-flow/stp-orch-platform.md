# stp-orch — Phase H platform 分析

## 調査対象ファイル
- `orchagent/stporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/stporch.h`
- `cfgmgr/stpmgr.h` / `cfgmgr/stpmgr.cpp`

## ASIC 依存の SAI 属性

### 初期化時 SAI 照会 (stporch.cpp:28-40)
`StpOrch::StpOrch()` がコンストラクタで `sai_switch_api->get_switch_attribute()` を呼び出す:

1. `SAI_SWITCH_ATTR_DEFAULT_STP_INST_ID` → `m_defaultStpId`
   - ASIC が保持するデフォルト STP インスタンス OID
   - VLAN を STP インスタンスから切り離す際に「デフォルトに戻す」操作で使用
   - 取得失敗時は未初期化のまま (silent failure)

2. `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` → `m_maxStpInstance`
   - ASIC がサポートする最大 STP インスタンス数 (ASIC ベンダーごとに異なる)
   - `updateMaxStpInstance()` で `max_stp_instances - 1` を `STATE_DB STP|GLOBAL.max_stp_inst` に書き込む
   - stpmgrd は STATE_DB ポーリングでこの値を読み取り、インスタンス上限として使用

### 取得失敗時のフォールバック (stpmgr.cpp:1407-1410)
SAI 取得失敗 → STATE_DB 書き込みが行われない → stpmgrd が 60 秒ポーリング後タイムアウト →
`STP_DEFAULT_MAX_INSTANCES = 255` (`stpmgr.h:38`) にフォールバック

## ブリッジポート依存

### SAI STP ポート作成 (stporch.cpp:209-257)
`addStpPort()` は `port.m_bridge_port_id` が有効であることを前提とする:
- `SAI_STP_PORT_ATTR_BRIDGE_PORT` に `port.m_bridge_port_id` を設定
- bridge_port_id が `SAI_NULL_OBJECT_ID` の場合はエラーとなり SAI NULL を返す
- **802.1D ブリッジモード (1D bridge) が有効でないポートでは STP ポート作成不可**

### SAI STP ポート状態の制約 (stporch.cpp:316-352)
SAI は 3 状態のみサポート:
- `SAI_STP_PORT_STATE_BLOCKING`
- `SAI_STP_PORT_STATE_LEARNING`
- `SAI_STP_PORT_STATE_FORWARDING`

STP の DISABLED(0) / LISTENING(2) は `SAI_STP_PORT_STATE_BLOCKING` に圧縮マップ。
これは SAI 仕様上の制約であり、特定 ASIC 固有ではなく SAI API 全体の制約。

## SAI API セット
- `sai_stp_api->create_stp()` — STP インスタンス作成
- `sai_stp_api->remove_stp()` — STP インスタンス削除
- `sai_stp_api->create_stp_port()` — STP ポート作成
- `sai_stp_api->remove_stp_port()` — STP ポート削除
- `sai_stp_api->set_stp_port_attribute()` — STP ポート状態更新
- `sai_vlan_api->set_vlan_attribute(SAI_VLAN_ATTR_STP_INSTANCE)` — VLAN への STP インスタンス割り当て

## ASIC ベンダーによる差異
`StpOrch` は `aclorch.cpp` のような平文プラットフォーム文字列比較を**行わない**。
ASIC 差異はすべて SAI 抽象レイヤ経由で吸収:
- `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` の返却値がベンダーごとに異なる
- SAI_STATUS_SUCCESS 以外が返った場合 = ASIC が STP をサポートしない or SAI 実装不完全

## VS (Virtual Switch) での動作
`StpOrch` 初期化時の SAI 照会で `SAI_STATUS_SUCCESS` を受け取れない可能性があるが、
`SWSS_LOG_NOTICE("StpOrch initialization failure")` を出力してそのまま続行する。
stpmgrd 側で 255 フォールバックが効くため VS 環境では機能制限なしに動作確認可能。
