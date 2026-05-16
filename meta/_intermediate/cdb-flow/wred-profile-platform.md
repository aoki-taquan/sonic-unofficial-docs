# WRED_PROFILE — Phase H: プラットフォーム差 (SAI capability / vendor / VoQ chassis)

## 調査対象ソース

- `sonic-net/sonic-swss` orchagent/qosorch.cpp — `WredMapHandler::convertFieldValuesToAttributes()` (L585-762)、`WredMapHandler::addQosItem()` (L784-860)、`QosOrch::applyWredProfileToQueue()` (L1708-1750)、`QosOrch::handleQueueTable()` (L1752-1940)
- `sonic-net/sonic-buildimage` files/build_templates/qos_config.j2 — AZURE_LOSSLESS テンプレート (L486-506)

## 結論サマリ

WRED_PROFILE の SAI 呼び出しにはプラットフォーム識別文字列による静的分岐（`BRCM_PLATFORM_SUBSTRING` / `MLNX_PLATFORM_SUBSTRING` 等）は存在しない。ただし以下の 2 種のプラットフォーム差が確認される:

1. **VoQ chassis (`gMySwitchType == "voq"`)**: `applyWredProfileToQueue()` および `handleQueueTable()` のキー解析ロジックが分岐する
2. **一部ベンダー SAI の min/max threshold 順序制約**: `convertFieldValuesToAttributes()` の 2 フェーズ適用機構がこれを吸収する（明示的プラットフォーム識別なし）

SAI capability の動的照会（`querySwitchCapability` / `sai_query_attribute_capability`）は WRED_PROFILE に対しては実施されない。ECN マーキングモード・WRED カラー設定の全属性は能力照会なしで直接 SAI に渡される。

---

## 差異 1: VoQ chassis — `applyWredProfileToQueue()` のキュー ID 解決

`qosorch.cpp:1708-1750`

| 条件 | キュー ID 取得方法 | 効果 |
|------|------------------|------|
| `gMySwitchType == "voq"` | `gPortsOrch->getPortVoQIds(port)` で VoQ ID リストを取得し `queue_ids[queue_ind]` を使用 | SAI 属性 `SAI_QUEUE_ATTR_WRED_PROFILE_ID` を **VoQ** に設定する |
| それ以外（通常スイッチ / multi-asic / DPU 等） | `port.m_queue_ids[queue_ind]` を使用 | SAI 属性 `SAI_QUEUE_ATTR_WRED_PROFILE_ID` を **物理キュー** に設定する |

VoQ chassis では QUEUE テーブルのキーが `{hostname}|{asic}|{port}|{queue_index}` の 4 トークン形式になり、orchagent は `gMyHostName` / `gMyAsicName` と比較してローカル ASIC のポートかを判定してから VoQ ID を使う（`qosorch.cpp:1790-1798`）。非ローカルポートへの WRED 適用はスキップされる。

## 差異 2: VoQ chassis — `handleQueueTable()` のキー解析

`qosorch.cpp:1772-1810`

| 条件 | QUEUE キーフォーマット | 解析ロジック |
|------|----------------------|-------------|
| `gMySwitchType == "voq"` | `{hostname}\|{asic}\|{port}\|{index}` (4 トークン必須) | 4 トークン未満は `task_invalid_entry` で即破棄 |
| それ以外 | `{port}\|{index}` (2 トークン必須) | 2 トークン以外は `task_invalid_entry` |

VoQ 環境では WRED プロファイルを QUEUE に紐付ける際に hostname / ASIC 名の照合が追加で行われる。ローカル ASIC でないキーはポート解決に失敗する（`gPortsOrch->getPort()` が false を返す）ため WRED bind がスキップされる。

## 差異 3: ベンダー SAI の min/max threshold 順序制約（明示的分岐なし）

`qosorch.cpp:596-629`（コメント）、`qosorch.cpp:636-694`（実装）

> "Setting WRED profile can fail in case the current min threshold is greater than the new max threshold for any color at any time, **on some vendor's platforms**."

コメント内に「一部ベンダーの SAI は 1 回の SET 操作で整合性を検証するため、min > max の過渡状態が発生するとエラーを返す」と記されている。対象ベンダーの明示はなし（プラットフォーム識別文字列不使用）。

対策として `convertFieldValuesToAttributes()` は **2 フェーズ属性適用** を実装する:

```
Phase 1: 逆転を起こさない属性を通常リストへ追加
Phase 2: 逆転を起こす属性を deferred リストへ退避

→ SAI SET 順: [通常リスト全属性] → [deferred リスト全属性]
```

これにより「現在 min=1M, max=2M → 新 min=3M, max=4M」の変更も:
1. まず max=4M を SET（逆転なし: min=1M < max=4M）
2. 次に min=3M を SET（逆転なし: min=3M < max=4M）

と安全に適用できる。プラットフォームを問わず全環境でこの 2 フェーズ機構が有効である（ベンダー分岐なし）。

## 差異 4: SAI capability 照会なし（WRED_PROFILE 固有の照会は実施されない）

`qosorch.cpp` 全体 grep: `querySwitchCapability` は `applyDscpToTcMapToSwitch()` (L1955-1960) のみで使用されており、WRED_PROFILE / WRED 属性に対しては SAI capability 動的照会を一切行わない。

| SAI 属性 | 照会方法 | 未対応時の挙動 |
|----------|---------|---------------|
| `SAI_WRED_ATTR_ECN_MARK_MODE` | 照会なし。`ecn_map.at()` で値変換後に直接 SAI SET | ASIC が非対応の場合 `sai_wred_api->create_wred()` がエラーを返す → エントリ破棄 |
| `SAI_WRED_ATTR_{GREEN/YELLOW/RED}_ENABLE` | 照会なし | 同上 |
| `SAI_WRED_ATTR_*_{MIN/MAX}_THRESHOLD` | 照会なし | 同上 |
| `SAI_WRED_ATTR_*_DROP_PROBABILITY` | 照会なし | 同上 |
| `SAI_WRED_ATTR_WEIGHT` | 照会なし（常に 0 を固定注入） | 同上 |

実質的な ASIC 対応差は SAI ライブラリ側（各ベンダーの `libsai`）で吸収される。SAI がエラーを返した場合にのみ orchagent がエントリを破棄する（ログ: `"Failed to create wred profile: %d"`）。

## 差異 5: generate_wred_profiles マクロ — プラットフォーム別 WRED テンプレート生成

`sonic-buildimage/files/build_templates/qos_config.j2:486-506`

```jinja
{% if generate_wred_profiles is defined %}
    {{ generate_wred_profiles() }}
{% else %}
    "AZURE_LOSSLESS": { ... }
{% endif %}
```

| 条件 | 動作 |
|------|------|
| プラットフォーム j2 テンプレートが `generate_wred_profiles` マクロを定義している | プラットフォーム固有 WRED プロファイル（カスタム閾値・ECN 設定）を生成。`AZURE_LOSSLESS` を置換する場合あり |
| マクロ未定義（デフォルト） | 固定値の `AZURE_LOSSLESS` プロファイルを生成（min=1MiB/max=2MiB/prob=5%/ecn=ecn_all） |

このマクロ実装は各プラットフォームの hwsku ディレクトリ以下の `qos.json.j2` が担う。community SONiC の標準プラットフォーム（例: Celestica / EdgeCore / Dell / Arista ベース）がそれぞれ独自の WRED 閾値を定義できる。

## スキャン証跡

- `WredMapHandler::convertFieldValuesToAttributes()` L585-762 全行読了
- `WredMapHandler::addQosItem()` L784-860 全行読了
- `WredMapHandler::removeQosItem()` L864-874 確認
- `QosOrch::applyWredProfileToQueue()` L1708-1750 全行読了
- `QosOrch::handleQueueTable()` L1752-1940 全行読了
- `qosorch.cpp` 全体 `querySwitchCapability` / `sai_query` grep: WRED 関連 0 ヒット
- `qosorch.cpp` 全体 `platform` / `BRCM` / `MLNX` / `vendor` grep: WRED 関連 0 ヒット（コメント 2 件のみ）
- `gMySwitchType` 使用箇所: L1637 / L1715 / L1772 の 3 箇所（すべて `"voq"` 比較）
- `qos_config.j2:486-506` `generate_wred_profiles` マクロ確認
