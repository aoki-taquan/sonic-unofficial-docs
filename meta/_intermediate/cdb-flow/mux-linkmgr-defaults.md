# MUX_LINKMGR フィールド コード由来デフォルト調査メモ

調査日: 2026-05-15  
対象テーブル: CONFIG_DB `MUX_LINKMGR` (Task F Phase A — `linkmgrd` C++ ソース直当て)

## 調査対象ファイル

- `sonic-linkmgrd/src/common/MuxConfig.h` (デーモン内部既定値の本体: メンバ初期化子)
- `sonic-linkmgrd/src/DbInterface.cpp` (`processMuxLinkmgrConfigNotifiction`: フィールド → setter)
- `sonic-linkmgrd/src/common/MuxLogger.h` / `MuxLogger.cpp` (ログ重大度の既定値)
- `sonic-linkmgrd/src/LinkMgrdMain.cpp` (起動時ロギングフィルタ既定値)

`MUX_LINKMGR` は YANG 上ほぼすべてのフィールドが `default` を持たないため、CONFIG_DB に該当キーが無いときは **linkmgrd のメンバ初期化子で焼かれた値** がそのまま有効になる。本メモはその "コード由来デフォルト" を網羅する。

---

## `MUX_LINKMGR|LINK_PROBER` 系

### `interval_v4`

**コード由来デフォルト**: `100` (ms)

```cpp
// MuxConfig.h:487
uint32_t mTimeoutIpv4_msec = 100;
```

`DbInterface.cpp:1132-1133` で `interval_v4` 文字列を `setTimeoutIpv4_msec()` に渡し `mTimeoutIpv4_msec` を上書き。DB に当該フィールドが無ければ初期化子 `100` のまま。

### `interval_v6`

**コード由来デフォルト**: `1000` (ms)

```cpp
// MuxConfig.h:488
uint32_t mTimeoutIpv6_msec = 1000;
```

`DbInterface.cpp:1134-1135` (`setTimeoutIpv6_msec()`)。

### `positive_signal_count`

**コード由来デフォルト**: `1` (回)

```cpp
// MuxConfig.h:490
uint32_t mPositiveStateChangeRetryCount = 1;
```

`DbInterface.cpp:1136-1137` (`setPositiveStateChangeRetryCount()`)。1 回の連続正常受信で active 判定。

### `negative_signal_count`

**コード由来デフォルト**: `3` (回)

```cpp
// MuxConfig.h:491
uint32_t mNegativeStateChangeRetryCount = 3;
```

`DbInterface.cpp:1138-1139` (`setNegativeStateChangeRetryCount()`)。3 回連続喪失で standby 判定。

### `suspend_timer`

**コード由来デフォルト**: `500` (ms — メンバ初期化子) / 動的計算値 `(mNegativeStateChangeRetryCount + 1) * mTimeoutIpv4_msec = (3+1)*100 = 400` ms (getter)

```cpp
// MuxConfig.h:493
uint32_t mSuspendTimeout_msec = 500;

// MuxConfig.h:308 (getter は計算式優先)
inline uint32_t getSuspendTimeout_msec() const {
    return (mNegativeStateChangeRetryCount + 1) * mTimeoutIpv4_msec;
};
```

**重要な差異**: setter (`DbInterface.cpp:1140-1141`) は `mSuspendTimeout_msec` を直接書き換えるが、**getter は無視して計算式を返す** ため、CONFIG_DB の `suspend_timer` 値は実際の suspend 計算に反映されない可能性が高い (デッドストア)。

### `interval_pck_loss_count_update`

**コード由来デフォルト**: `300` (回)。下限 `50` で clamp。

```cpp
// MuxConfig.h:492
uint32_t mLinkProberStatUpdateIntervalCount = 300;

// MuxConfig.h:131 (setter は 50 を下限に clamp)
inline void setLinkProberStatUpdateIntervalCount(uint32_t interval_count) {
    mLinkProberStatUpdateIntervalCount = interval_count > 50 ? interval_count : 50;
};
```

`DbInterface.cpp:1146-1147`。`50` 未満を書き込んでも `50` に丸められる。

### `use_well_known_mac`

**コード由来デフォルト**: `true` (= `enabled` 相当、Active-Active 経路のみ)

```cpp
// MuxConfig.h:506
bool mUseWellKnownMacActiveActive = true;
```

`DbInterface.cpp:1142-1143` で `v == "enable"` の真偽を `setUseWellKnownMacActiveActive()` に渡す。  
**重要な差異**: YANG の enum は `enabled` / `disabled` だが、コード側は `v == "enable"` (末尾 `d` なし) を真と判定。CONFIG_DB に `enabled` が書かれた場合、`v == "enable"` は false になり **常に動的 MAC** が選択される (バグ扱いの可能性)。

### `src_mac`

**コード由来デフォルト**: `mEnableUseTorMac = false` (= `VlanMac` 相当)

```cpp
// MuxConfig.h:508
bool mEnableUseTorMac = false;
```

`DbInterface.cpp:1144-1145` は `processSrcMac(v == "ToRMac")` を呼ぶ (内部で `setIfUseTorMacAsSrcMac()`)。DB に `src_mac` が無ければ `mEnableUseTorMac = false` のまま → VLAN MAC を送信元に使う。

---

## `MUX_LINKMGR|TIMED_OSCILLATION`

### `oscillation_enabled`

**コード由来デフォルト**: `true`

```cpp
// MuxConfig.h:497
bool mEnableTimedOscillationWhenNoHeartbeat = true;
```

`DbInterface.cpp:1192-1197` で文字列 `"true"` / `"false"` のみ受理 (それ以外は何もしない)。

### `interval_sec`

**コード由来デフォルト**: `300` (秒)。下限 `300` で clamp (`force=true` 時のみバイパス)。

```cpp
// MuxConfig.h:498
uint32_t mOscillationTimeout_sec = 300;

// MuxConfig.h:338-344 (setter は 300 を下限に clamp、force でバイパス)
inline void setOscillationInterval_sec(uint32_t oscillationInterval_sec, bool force=false) {
    if (force || oscillationInterval_sec > 300) {
        mOscillationTimeout_sec = oscillationInterval_sec;
    } else {
        mOscillationTimeout_sec = 300;
    }
}
```

`DbInterface.cpp:1198-1203` は `force` を渡さない → CONFIG_DB に `300` 以下を書いても `300` に丸められる。

---

## `MUX_LINKMGR|MUXLOGGER`

### `log_verbosity`

**コード由来デフォルト**: `info`

```cpp
// MuxLogger.h:250
boost::log::trivial::severity_level mLevel = boost::log::trivial::info;
```

ただし `LinkMgrdMain.cpp:46` は起動時オプション用に `debug` を定数で持つ:
```cpp
static auto DEFAULT_LOGGING_FILTER_LEVEL = boost::log::trivial::debug;
```

`DbInterface.cpp:1172-1175` で動的更新 (`updateLogVerbosity(v)`)、ただし `MuxLogger::isLinkToSwssLogger()` 真の場合は SwSS ログバックエンド側に委ね無視。

---

## `MUX_LINKMGR|SERVICE_MGMT`

### `kill_radv`

**コード由来デフォルト**: linkmgrd 側に処理コードなし。

`DbInterface.cpp` の `processMuxLinkmgrConfigNotifiction` には `SERVICE_MGMT` キーの分岐が存在しない (`LINK_PROBER` / `MUXLOGGER` / `TIMED_OSCILLATION` の 3 つだけ)。`kill_radv` を消費するのは **linkmgrd ではなく `mux-cable.sh` / systemd ユニット側** のシェル / Jinja2 経路 (YANG が `default True`)。  
→ linkmgrd のメモリ上に既定値は無く、YANG 上の `default True` がコンフィグ生成系を経由して効くのみ。

---

## 要約表

| フィールド | container | コード由来デフォルト | 出典 (linkmgrd C++) | 備考 |
|-----------|-----------|---------------------|---------------------|------|
| `interval_v4` | `LINK_PROBER` | `100` ms | `MuxConfig.h:487` | — |
| `interval_v6` | `LINK_PROBER` | `1000` ms | `MuxConfig.h:488` | — |
| `positive_signal_count` | `LINK_PROBER` | `1` | `MuxConfig.h:490` | — |
| `negative_signal_count` | `LINK_PROBER` | `3` | `MuxConfig.h:491` | — |
| `suspend_timer` | `LINK_PROBER` | `500` ms (setter), 計算式 `(neg+1)*v4` (getter) | `MuxConfig.h:493,308` | setter は反映されずデッドストア疑い |
| `interval_pck_loss_count_update` | `LINK_PROBER` | `300`、下限 `50` clamp | `MuxConfig.h:492,131` | — |
| `use_well_known_mac` | `LINK_PROBER` | `true` (内部 bool) | `MuxConfig.h:506` | `v == "enable"` 判定 — YANG `enabled` と不一致 |
| `src_mac` | `LINK_PROBER` | `false` (= `VlanMac`) | `MuxConfig.h:508` | `v == "ToRMac"` で真 |
| `oscillation_enabled` | `TIMED_OSCILLATION` | `true` | `MuxConfig.h:497` | YANG `default true` と一致 |
| `interval_sec` | `TIMED_OSCILLATION` | `300` 秒、下限 `300` clamp | `MuxConfig.h:498,338` | force=false なので `300` 以下は丸め |
| `log_verbosity` | `MUXLOGGER` | `info` | `MuxLogger.h:250` | 起動 CLI 既定は `debug` (`LinkMgrdMain.cpp:46`) |
| `kill_radv` | `SERVICE_MGMT` | linkmgrd は処理せず (YANG `default True` のみ) | — | `DbInterface.cpp` に SERVICE_MGMT 分岐なし |

---

## 派生する注意点 (ページ本文への反映候補)

1. `suspend_timer` setter はあるが getter が計算式を優先 → 設定値が無視される疑い (要 verifier 裏取り)
2. `use_well_known_mac` は YANG enum `enabled` / `disabled` だがコードは `"enable"` で判定 — 文字列ミスマッチで常に false 経路
3. `interval_sec` は `300` 未満を書いても `300` に丸められる (デフォルト = 下限)
4. `interval_pck_loss_count_update` も同様に `50` を下限に clamp
5. `kill_radv` は linkmgrd 起動時のコンフィグ経路 (シェル/systemd) 専用で、linkmgrd 本体は未消費

---

## 証拠リンク

- `sonic-linkmgrd/src/common/MuxConfig.h:485-514` — private メンバ初期化子 (すべての数値・bool 既定値)
- `sonic-linkmgrd/src/common/MuxConfig.h:131` — `setLinkProberStatUpdateIntervalCount` の `50` 下限 clamp
- `sonic-linkmgrd/src/common/MuxConfig.h:308` — `getSuspendTimeout_msec` の計算式
- `sonic-linkmgrd/src/common/MuxConfig.h:338-344` — `setOscillationInterval_sec` の `300` 下限 clamp
- `sonic-linkmgrd/src/DbInterface.cpp:1120-1214` — `processMuxLinkmgrConfigNotifiction` (フィールド → setter dispatch)
- `sonic-linkmgrd/src/common/MuxLogger.h:250` — `mLevel = info`
- `sonic-linkmgrd/src/LinkMgrdMain.cpp:46` — `DEFAULT_LOGGING_FILTER_LEVEL = debug`
