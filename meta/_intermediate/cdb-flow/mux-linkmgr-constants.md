# mux-linkmgr Phase E — ハードコード定数

source: `sonic-linkmgrd/src/common/MuxConfig.h`, `sonic-linkmgrd/src/common/MuxLogger.h`, `sonic-linkmgrd/src/LinkMgrdMain.cpp`, `sonic-linkmgrd/src/DbInterface.h`

## MuxConfig.h — C++ メンバ初期化子によるデフォルト定数

```cpp
// sonic-linkmgrd/src/common/MuxConfig.h:486-508
uint8_t  mNumberOfThreads                     = 5;       // linkmgrd 内部スレッド数
uint32_t mTimeoutIpv4_msec                    = 100;     // IPv4 ICMP heartbeat 間隔 (ms)
uint32_t mTimeoutIpv6_msec                    = 1000;    // IPv6 ICMP heartbeat 間隔 (ms)
uint32_t mRxTimeoutIpv4_msec                  = 300;     // IPv4 受信タイムアウト (ms)
uint32_t mPositiveStateChangeRetryCount       = 1;       // active 判定に必要な連続受信回数
uint32_t mNegativeStateChangeRetryCount       = 3;       // standby 判定に必要な連続喪失回数
uint32_t mLinkProberStatUpdateIntervalCount   = 300;     // パケットロス統計更新間隔 (heartbeat 回数単位、下限 50 で clamp)
uint32_t mSuspendTimeout_msec                 = 500;     // ICMP 停止タイマ初期値 (ms、getter は (neg+1)*interval_v4 を計算で返す)
uint32_t mMuxStateChangeRetryCount            = 1;       // MuxState 変更リトライ回数
uint32_t mLinkStateChangeRetryCount           = 1;       // LinkState 変更リトライ回数

bool     mEnableTimedOscillationWhenNoHeartbeat = true;  // タイマー駆動オシレーション有効 (= oscillation_enabled デフォルト)
uint32_t mOscillationTimeout_sec              = 300;     // オシレーション間隔 (秒、下限 300 で clamp)

bool     mEnableSwitchoverMeasurement         = false;   // 切替オーバーヘッド計測モード (-m フラグ)
uint32_t mDecreasedTimeoutIpv4_msec           = 10;      // 切替計測時の短縮 IPv4 間隔 (ms)

uint32_t mMuxReconciliationTimeout_sec        = 10;      // warmboot リコンシリエーション待機タイムアウト (秒)

bool     mEnableDefaultRouteFeature           = false;   // デフォルトルートなし時に heartbeat 停止する機能 (-d フラグ)
bool     mUseWellKnownMacActiveActive         = true;    // Active-Active 時 well-known MAC 使用フラグ
bool     mEnableUseTorMac                     = false;   // ToR MAC を送信元 MAC として使用 (src_mac=ToRMac 時 true)
```

### clamp 制約

| フィールド | setter 内の clamp 式 | 出典 |
|---|---|---|
| `mLinkProberStatUpdateIntervalCount` | `interval_count > 50 ? interval_count : 50` | `MuxConfig.h:131` |
| `mOscillationTimeout_sec` | `force=false` の場合 `300` 以下は `300` に丸め | `MuxConfig.h:338-342` |

## MuxLogger.h — ログレベルデフォルト

```cpp
// sonic-linkmgrd/src/common/MuxLogger.h:250
boost::log::trivial::severity_level mLevel = boost::log::trivial::info;
```

コード上の内部デフォルトは `info`。

## LinkMgrdMain.cpp — CLI 起動時デフォルト

```cpp
// sonic-linkmgrd/src/LinkMgrdMain.cpp:46
static auto DEFAULT_LOGGING_FILTER_LEVEL = boost::log::trivial::debug;
```

`linkmgrd` 起動時の CLI デフォルトは `debug`。`log_verbosity` フィールドが CONFIG_DB に設定されていない場合、`MuxLogger` 内部では `info` が初期値だが、CLI 引数なしで起動した場合は `debug` フィルタが適用される。

## DbInterface.h — DB テーブル名定数

```cpp
// sonic-linkmgrd/src/DbInterface.h:51-63
#define MUX_CABLE_INFO_TABLE                 "MUX_CABLE_INFO"
#define LINK_PROBE_STATS_TABLE_NAME          "LINK_PROBE_STATS"
#define APP_FORWARDING_STATE_COMMAND_TABLE_NAME   "FORWARDING_STATE_COMMAND"
#define APP_FORWARDING_STATE_RESPONSE_TABLE_NAME  "FORWARDING_STATE_RESPONSE"
#define APP_PEER_HW_FORWARDING_STATE_TABLE_NAME   "HW_FORWARDING_STATE_PEER"
#define STATE_PEER_HW_FORWARDING_STATE_TABLE_NAME "HW_MUX_CABLE_TABLE_PEER"
#define STATE_ICMP_ECHO_SESSION_TABLE_NAME   "ICMP_ECHO_SESSION_TABLE"
#define APP_ICMP_ECHO_SESSION_TABLE_NAME     "ICMP_ECHO_SESSION_TABLE"
#define STATE_MUX_SWITCH_CAUSE_TABLE_NAME    "MUX_SWITCH_CAUSE"
```

## IcmpPayload.h — ICMP バッファサイズ定数

```cpp
// sonic-linkmgrd/src/link_prober/IcmpPayload.h:39
#define MUX_MAX_ICMP_BUFFER_SIZE  9100   // ICMP パケットバッファ最大サイズ (bytes)
```

## 注意事項

- `mUseWellKnownMacActiveActive = true` は YANG enum `enabled`/`disabled` に対し、コードは `v == "enable"` (末尾 `d` なし) で比較するため、YANG どおり `"enabled"` を書いても常に `false` 評価になる（実装バグ疑い）。詳細は `mux-linkmgr.md` defaults セクション参照。
- `mSuspendTimeout_msec = 500` は setter の初期値だが、getter (`getSuspendTimeout_msec()`) は `(mNegativeStateChangeRetryCount + 1) * mTimeoutIpv4_msec = (3+1)*100 = 400ms` を計算で返す。setter 値はデッドストアの疑いがある。
