# SFLOW — Phase E ハードコード定数 証跡

ソース: `sonic-swss/orchagent/sfloworch.cpp`, `sonic-swss/cfgmgr/sflowmgr.cpp`, `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-sflow.yang`

## 抽出定数一覧

| 定数名 / 意味 | 値 | 場所 |
|---|---|---|
| `sample_rate` 最小値 | `256` | `sonic-sflow.yang` L128: `range "256..8388608"` |
| `sample_rate` 最大値 | `8388608` | `sonic-sflow.yang` L128: `range "256..8388608"` |
| `collector_port` デフォルト | `6343` (UDP) | `sonic-sflow.yang` L81: `default 6343;` |
| `polling_interval` デフォルト | `20` (秒) | `sonic-sflow.yang` L163: `default 20;` |
| `polling_interval` 有効範囲 | `0` または `5..300` | `sonic-sflow.yang` L158: `range "0\|5..300"` |
| グローバル `admin_state` 初期値 | `false` (`m_gEnable = false`) | `sflowmgr.cpp` L19 コンストラクタ |
| グローバル `sample_direction` 初期値 | `"rx"` (`m_gDirection = "rx"`) | `sflowmgr.cpp` L20-21 コンストラクタ |
| `SFLOW_SESSION|all` 初期状態 | `m_intfAllConf = true` (全ポートデフォルト有効) | `sflowmgr.cpp` L18 コンストラクタ |
| `ERROR_SPEED` (ポート速度未定義) | `"error"` 文字列 | `sflowmgr.h` L13: `#define ERROR_SPEED "error"` |
| `NA_SPEED` (oper speed 非対応) | `"N/A"` 文字列 | `sflowmgr.h` L14: `#define NA_SPEED "N/A"` |
| デフォルト sampling rate | ポート oper_speed 値 (= line rate) | `sflowmgr.cpp` findSamplingRate() L385-401 |
| SAI samplepacket attribute | `SAI_SAMPLEPACKET_ATTR_SAMPLE_RATE` | `sfloworch.cpp` L26 |
| SAI API | `sai_samplepacket_api->create_samplepacket()` | `sfloworch.cpp` L29 |
| コレクタ最大数 | `2` | `sonic-sflow.yang` `max-elements 2` |

## 備考

- `sample_rate` の YANG 範囲 (`256..8388608`) はハードウェア制約に由来し、YANG モデルで enforce される。
- デフォルト sampling rate はポートの oper_speed (bit/s 単位の数値文字列) を直接使用。例: 100GbE → rate=`100000` (速度の Mbps 表現)。
- `collector_port` の 6343 は IANA 割当の sFlow UDP ポート番号。
- `agent_id` フィールドのデフォルトは YANG / ソースコードともに明示されない（オプション）。
