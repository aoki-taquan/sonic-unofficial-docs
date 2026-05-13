# WRED_PROFILE — 値依存挙動メモ

## ecn: enum 8 値
- ecn_none → SAI_ECN_MARK_MODE_NONE (qosorch.cpp:37)
- ecn_green → SAI_ECN_MARK_MODE_GREEN (qosorch.cpp:38)
- ecn_yellow → SAI_ECN_MARK_MODE_YELLOW (qosorch.cpp:39)
- ecn_red → SAI_ECN_MARK_MODE_RED (qosorch.cpp:40)
- ecn_green_yellow → SAI_ECN_MARK_MODE_GREEN_YELLOW (qosorch.cpp:41)
- ecn_green_red → SAI_ECN_MARK_MODE_GREEN_RED (qosorch.cpp:42)
- ecn_yellow_red → SAI_ECN_MARK_MODE_YELLOW_RED (qosorch.cpp:43)
- ecn_all → SAI_ECN_MARK_MODE_ALL (qosorch.cpp:44)
- YANG default: ecn_none

## wred_green_enable / wred_yellow_enable / wred_red_enable: true / false
- YANG default: false
- 不正文字列 → SWSS_LOG_ERROR("Invalid input specified") で破棄 (qosorch.cpp)

## *_drop_probability: 0..100 (%)
- YANG default: 100 (100% = max threshold 到達後全ドロップ)
- 0 → min threshold 到達でもドロップなし（ECN マーキングのみ使用する場合）

## *_min_threshold / *_max_threshold: uint64 (bytes)
- min threshold: この値からランダムドロップ開始
- max threshold: この値で全ドロップ (100%)
- YANG: max >= min の must 制約
- 違反 → "max threshold must be >= min threshold" エラー
- orchagent: 閾値更新の 2 フェーズ適用（min/max 逆転を防ぐため deferred リスト機構）(qosorch.cpp WredMapHandler)

Sources:
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-wred-profile.yang
- sonic-swss/orchagent/qosorch.cpp
- sonic-swss/orchagent/qosorch.h
