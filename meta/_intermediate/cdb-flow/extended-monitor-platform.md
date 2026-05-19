# extended-monitor (eventd 拡張監視設定) — Phase H: プラットフォーム差

## 調査対象ソース

- `sonic-net/sonic-buildimage/src/sonic-eventd/src/eventd.cpp`
- `sonic-net/sonic-buildimage/src/sonic-eventd/src/eventd.h`
- `SONiC/doc/event-alarm-framework/event-alarm-framework.md`

## 主要発見事項

### 1. SAI・プラットフォーム依存なし

`eventd.cpp` 全体を調査した結果：
- `#include <sai*.h>` は存在しない
- `getenv("platform")` 呼び出しはない
- `#ifdef` によるプラットフォーム分岐は存在しない
- `gMySwitchType == "voq"` チェックもない

完全にプラットフォーム非依存の ZMQ ブローカー + Redis 書き込みデーモン。

### 2. DBConnector 呼び出し (eventd.cpp:178)

```cpp
m_counters_db = make_shared<swss::DBConnector>("COUNTERS_DB", 0, false);
```

namespace 引数なし（0 = default）。マルチ ASIC namespace 分割なし。

### 3. MAX_CACHE_SIZE 計算 (eventd.cpp:31-33)

```cpp
#define EVT_SIZE_AVG 150
#define MAX_CACHE_SIZE (MB(100) / (EVT_SIZE_AVG))
```

MB(100) = 100*1024*1024 = 104,857,600 bytes。
MAX_CACHE_SIZE = 104,857,600 / 150 ≈ 699,050 events。

### 4. get_config_data でファイルから上書き可能 (eventd.cpp:674)

```cpp
cache_max = get_config_data(string(CACHE_MAX_CNT), (int)MAX_CACHE_SIZE);
```

`/etc/eventd.json` に `cache_max_cnt` が定義されていればその値を使う。RAM 少ないプラットフォームではこの値を下げる運用が想定される。

### 5. VM での挙動差

sonic-vs では SAI が stub 実装のため、syncd が SAI イベントを生成しない。
→ syncd 関連イベント（`syncd_events_info.json` 定義分）は EVENT_DB に記録されない。
→ eventd 自体の動作（ZMQ ブローカー、COUNTERS_DB 書き込み）は変わらない。

### 6. evprofile デフォルト（HLD 3.1.5）

`/etc/evprofile/default.json` は全プラットフォーム共通パッケージに含まれる。
ベンダー固有イベントを追加する際は別ファイルを `/etc/evprofile/` に配置。
HLD にはカスタム evprofile の上書きマージ仕様は現時点で未定義。
