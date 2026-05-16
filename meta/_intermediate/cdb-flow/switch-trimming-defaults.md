# SWITCH_TRIMMING フィールド暗黙デフォルト調査メモ

調査日: 2026-05-16
対象テーブル: CONFIG_DB `SWITCH_TRIMMING`

## 調査対象ファイル

- `sonic-swss/orchagent/switchorch.cpp` (`SwitchOrch::setSwitchTrimming`, `doCfgSwitchTrimmingTableTask`)
- `sonic-swss/orchagent/switch/trimming/helper.cpp` (`SwitchTrimmingHelper::parseTrimSize/Dscp/Tc/Queue`, `parseTrimConfig`, `validateTrimConfig`)
- `sonic-swss/orchagent/switch/trimming/container.h` (`SwitchTrimming` 構造体 — 各サブフィールドの `is_set = false` 初期値)
- `sonic-swss/orchagent/switch/trimming/capabilities.h` / `.cpp` (`SwitchTrimmingCapabilities`)
- `sonic-swss/orchagent/switch/trimming/schema.h` (`SWITCH_TRIMMING_DSCP_VALUE_FROM_TC = "from-tc"`, `SWITCH_TRIMMING_QUEUE_INDEX_DYNAMIC = "dynamic"`)
- `sonic-swss/orchagent/portsorch.cpp` (`nvda_port_trim_drop.lua`, `DROPPED_TRIM_PACKETS` / `TX_TRIM_PACKETS` カウンタ統合のみ — フィールド既定値処理は無し)

---

## フィールド別 暗黙デフォルト

### `size`

**コード由来デフォルト**: なし (フィールド省略時は SAI 属性送信なし)

- `SwitchTrimming.size.is_set` のデフォルトは `false` (container.h L18)。
- `parseTrimSize()` (helper.cpp L62–84) は明示値があるときのみ `is_set = true` をセット。
- `setSwitchTrimming()` (switchorch.cpp L1087–1108) は `if (trim.size.is_set)` で囲まれた経路でのみ `SAI_SWITCH_ATTR_PACKET_TRIM_SIZE` を発行。省略時は SAI 設定変更なし → **SAI 既存値 or SAI ベンダーデフォルト** が有効。
- ASIC 既存値と CONFIG_DB が乖離していた場合は SET 拒否 (`return false` + `"ASIC and CONFIG DB are diverged"`).

### `dscp_value`

**コード由来デフォルト**: なし。ただし parser 内部で *暗黙のモード自動設定* あり。

- `parseTrimDscp()` (helper.cpp L86–127) は値ごとに 2 通りの内部状態を構築する:
  - `value == "from-tc"` (case-insensitive, `boost::algorithm::to_lower_copy`) →
    `cfg.dscp.mode.value = SAI_PACKET_TRIM_DSCP_RESOLUTION_MODE_FROM_TC`, `cfg.dscp.mode.is_set = true` のみ (DSCP 値は未設定)。
  - 数値 (0..63) → `cfg.dscp.value` をセット後、`cfg.dscp.mode.value = SAI_PACKET_TRIM_DSCP_RESOLUTION_MODE_DSCP_VALUE` を**自動付与** (helper.cpp L123)。
- 範囲外 (`<0` or `>63`) は `LOG_ERROR` + `false` でエントリ全破棄。
- フィールド省略時は `dscp.mode.is_set = false` のまま → switchorch.cpp L1109 の if 文を通らず SAI 属性発行なし。

### `tc_value`

**コード由来デフォルト**: なし。

- `parseTrimTc()` (helper.cpp L129–151) は明示値のみ受理 (`tc.is_set = true`)。
- `dscp.mode == DSCP_VALUE` (`isSymDscpMode == true`) のとき `setSwitchTrimming()` は TC を SAI に送らず `SWSS_LOG_WARN("Skip setting switch trimming TC value for symmetric DSCP mode")` (switchorch.cpp L1190) と記録する。
- `dscp_value=from-tc` を使う場合のみ TC が SAI へ反映される。
- TC 値の上限は capability 由来 (`SAI_SWITCH_ATTR_QOS_MAX_NUMBER_OF_TRAFFIC_CLASSES`)。`validateTrimTcCap()` 失敗時は SET 拒否。

### `queue_index`

**コード由来デフォルト**: なし。ただし parser 内部で mode 自動付与あり。

- `parseTrimQueue()` (helper.cpp L153–185):
  - `value == "dynamic"` (case-insensitive) →
    `cfg.queue.mode.value = SAI_PACKET_TRIM_QUEUE_RESOLUTION_MODE_DYNAMIC`, `cfg.queue.mode.is_set = true`、index は未設定。
  - 数値 → `cfg.queue.index.value` セット後、`cfg.queue.mode.value = SAI_PACKET_TRIM_QUEUE_RESOLUTION_MODE_STATIC` を**自動付与** (helper.cpp L181–182)。
- フィールド省略時は `queue.mode.is_set = false` のまま → SAI 属性発行なし。

### 検証ガード (`validateTrimConfig`)

少なくとも `size` / `dscp.mode` / `tc` / `queue.mode` のいずれかが `is_set` でなければ `LOG_ERROR("Validation error: missing valid fields")` + `false` (helper.cpp L233–246)。全フィールド空のエントリは破棄される。

---

## capability 不在時の挙動

`SwitchTrimmingCapabilities` (capabilities.cpp L142–179):

- 構築時 (`SwitchTrimmingCapabilities()`) で全 `isAttrSupported = false` から開始し、SAI の `query_attribute_capability` 成功時のみ `true` に昇格させる。
- `isSwitchTrimmingSupported()` は次の全てが `true` のときだけ `true`:
  - `trimCap.size.isAttrSupported`
  - `trimCap.dscp.mode.isAttrSupported`
  - `trimCap.queue.mode.isAttrSupported`
  - `isDscpValueModeSupported` が `true` の場合のみ `trimCap.dscp.isAttrSupported` も要求
  - `isFromTcModeSupported` が `true` の場合のみ `trimCap.tc.isAttrSupported` も要求
  - `isStaticModeSupported` が `true` の場合のみ `trimCap.queue.index.isAttrSupported` も要求
- `setSwitchTrimming()` 冒頭 (switchorch.cpp L1081–1085) で `!isSwitchTrimmingSupported()` の場合は `SWSS_LOG_WARN("Switch trimming configuration is not supported: skipping ...")` をログして **`return true`** で抜ける (SAI 書き込みなしでも成功扱い)。
- enum capability (`isEnumSupported`) が `false` のときは `validateTrimDscpModeCap` / `validateTrimQueueModeCap` が常に `true` を返し検証スキップ (capabilities.cpp L185–188, L232–235)。

> **挙動まとめ**: ASIC が packet trimming 非対応の場合、`SWITCH_TRIMMING|GLOBAL` への SET はエラーにならず黙って no-op。`STATE_DB` 側 capability テーブルでサポート有無を確認するのが運用上正しい (`writeCapabilitiesToDb` 経由)。

---

## 要約表

| フィールド | コード由来デフォルト | 省略時の SAI 挙動 | fallback 源 |
|-----------|-------------------|-----------------|------------|
| `size` | なし | SAI 属性発行なし → SAI ベンダー既定/既存値保持 | `container.h:18` `is_set = false` |
| `dscp_value` | なし (parser が DSCP_VALUE / FROM_TC モードを値から自動派生) | `dscp.mode.is_set = false` で SAI 属性発行なし | `helper.cpp:123, 99` |
| `tc_value` | なし (symmetric DSCP モード時は省略推奨) | TC 属性発行なし。symmetric mode 中は明示しても **skip + WARN** | `helper.cpp:141, switchorch.cpp:1190` |
| `queue_index` | なし (parser が STATIC / DYNAMIC モードを値から自動派生) | `queue.mode.is_set = false` で SAI 属性発行なし | `helper.cpp:165, 181` |
| capability 不在時 | — | `setSwitchTrimming()` 全体が WARN ログのみで **成功扱い** (no-op) | `switchorch.cpp:1081–1085` |

---

## 証拠リンク (ref: sonic-swss@4305596156d70e9797e8a881b3d19b46de0bce0d)

- `orchagent/switchorch.cpp:1066–1304` — `setSwitchTrimming()` 本体
- `orchagent/switchorch.cpp:1081–1085` — capability 不在で WARN + return true
- `orchagent/switchorch.cpp:1190` — symmetric DSCP モード時の TC スキップ WARN
- `orchagent/switch/trimming/container.h:16–53` — 各サブフィールド `is_set = false` 既定
- `orchagent/switch/trimming/helper.cpp:62–185` — parseTrim{Size,Dscp,Tc,Queue}
- `orchagent/switch/trimming/helper.cpp:233–246` — `validateTrimConfig` (全空エントリ破棄)
- `orchagent/switch/trimming/capabilities.cpp:142–179` — `isSwitchTrimmingSupported`
- `orchagent/switch/trimming/schema.h:5,10` — `"from-tc"` / `"dynamic"` リテラル
- `orchagent/portsorch.cpp:802,857` — Nvidia 専用 lua plugin + trim カウンタ統合のみ (フィールド既定処理なし)
