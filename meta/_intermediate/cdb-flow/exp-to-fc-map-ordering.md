# EXP_TO_FC_MAP — 書込み順依存分析

## consumer 一覧

| consumer | 用途 | ソースパス |
|---|---|---|
| orchagent / qosorch.cpp | EXP→FC マップの SAI オブジェクト生成・適用 | sonic-swss/orchagent/qosorch.cpp:1132-1213 |
| orchagent / handlePortQosMapTable | PORT_QOS_MAP.exp_to_fc_map からの逆参照解決 | sonic-swss/orchagent/qosorch.cpp:2046-2134 |

## 書込み順依存

### SET 時の順序制約

| # | 依存 | 方向 | 挙動 |
|---|------|------|------|
| 1 | `EXP_TO_FC_MAP|<name>` SAI 作成 → `PORT_QOS_MAP|<port>` SET | 強制先行 | `resolveFieldRefValue()` が未解決で `task_need_retry`（自動再試行）|
| 2 | `EXP_TO_FC_MAP|<name>` 作成 → FC 値の `max_num_fcs` 問い合わせ完了 | 暗黙先行 | `NhgMapOrch::getMaxNumFcs()` が `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES` を SAI 問い合わせで取得。初回呼び出しまで `max_num_fcs = -1`（未初期化）のため、SAI API 準備前に呼ぶと全エントリ reject |
| 3 | EXP 値は 0..7 の整数文字列のみ | 必須形式 | `stoi()` で変換。非整数や範囲外（負数・8以上）は `task_invalid_entry`（エントリ全体が reject） |

> **推奨順序（SET）**: SAI 起動完了後 → `EXP_TO_FC_MAP|<name>` → `PORT_QOS_MAP|<port>` の `exp_to_fc_map` フィールド設定

### DEL 時の順序制約

| # | 依存 | 方向 | 挙動 |
|---|------|------|------|
| 1 | `PORT_QOS_MAP|<port>` の `exp_to_fc_map` 参照解除 → `EXP_TO_FC_MAP|<name>` DEL | 強制先行 | 参照中は `isObjectBeingReferenced()` が true → `m_pendingRemove=true` + `task_need_retry` ロック（qosorch.cpp:181-186） |
| 2 | pending_remove 解消 → SET（再書き込み）可能 | 強制先行 | pending_remove 中の SET は即 `task_need_retry` を返す（qosorch.cpp:136-139） |

> **推奨順序（DEL）**: `PORT_QOS_MAP|<port>` の `exp_to_fc_map` フィールド削除 → `EXP_TO_FC_MAP|<name>` DEL

> **Evidence**: `qosorch.cpp:124-201` (QosMapHandler::processWorkItem), `qosorch.cpp:2046-2134` (handlePortQosMapTable), `qosorch.cpp:1132-1213` (ExpToFcMapHandler)
