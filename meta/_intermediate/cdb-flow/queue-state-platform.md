# QUEUE_COUNTER_CAPABILITIES (STATE_DB) — Phase H プラットフォーム差スキャンノート

対象テーブル: `STATE_DB / QUEUE_COUNTER_CAPABILITIES`
Consumer: `PortsOrch::initCounterCapabilities()` (`sonic-swss/orchagent/portsorch.cpp:1850-1963`)
スキャン範囲: portsorch.cpp 全行精読、flexcounterorch.cpp 確認

---

## プラットフォーム差の検出

### 1. WRED/ECN キューカウンタ — SAI sai_query_stats_capability() の結果はプラットフォーム依存

`initCounterCapabilities()` は `sai_query_stats_capability(switchId, SAI_OBJECT_TYPE_QUEUE, ...)` を呼び、返却された `sai_stat_capability_list_t` に `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` 等が含まれるかで `isSupported` を決定する。

この SAI API の実装は ASIC ベンダーの libsai 実装に依存する。

- **Broadcom (BCM) 系**: WRED/ECN カウンタをサポートする実装が一般的。クエリ結果に対応 SAI 統計が含まれる。
- **Mellanox/NVIDIA 系**: プラットフォームによって WRED ECN マーキングと WRED ドロップの一方のみサポート、あるいは全サポートのケースがある。PortsOrch に Mellanox 固有の `isMlnxPlatform()` 関数（`portsorch.cpp:689-703`）が存在するが、`initCounterCapabilities()` 自体は `isMlnxPlatform()` の分岐を持たず、SAI クエリ結果のみで判定する。
- **DPU (SmartSwitch DPU)**: `gMySwitchType == "dpu"` の場合、`initializeQueuesBulk()` がスキップされる（`portsorch.cpp:6589`）ため、queue OID リストが未初期化のまま。`initCounterCapabilities()` 自体は DPU でもスキップされないが、SAI DPU 実装が WRED/ECN キュー統計をサポートしない場合は全フラグ `"false"` となる。
- **VS (Virtual Switch)**: SAI VS 実装では `sai_query_stats_capability` が `SAI_STATUS_NOT_SUPPORTED` または SUCCESS でも空リストを返すことがある。この場合も全フラグ `"false"` となる。

evidence: `portsorch.cpp:1881-1921`

### 2. `SAI_STATUS_NOT_SUPPORTED` / `SAI_STATUS_NOT_IMPLEMENTED` の扱い

SAI 実装が `sai_query_stats_capability` 自体を未実装の場合、`SAI_STATUS_NOT_SUPPORTED` が返る。`initCounterCapabilities()` はこれを SAI クエリ失敗として扱い（`status != SAI_STATUS_SUCCESS` 分岐）、`SWSS_LOG_NOTICE` を出力して全フラグ `"false"` を確定する。

特定 ASIC が部分的に WRED をサポートする例:
- ECN マーキング（MARKED_PACKETS / MARKED_BYTES）のみサポートする場合 → WRED_DROPPED_* は `"false"`
- WRED ドロップ（DROPPED_PACKETS / DROPPED_BYTES）のみサポートする場合 → ECN_MARKED_* は `"false"`

4 つのフラグは独立して設定されるため、部分的な `"true"` / `"false"` の組み合わせが実運用上存在する。

evidence: `portsorch.cpp:1889-1920`

### 3. VoQ スイッチ — キューカウンタへの影響

`gMySwitchType == "voq"` の場合、`FlexCounterOrch::getQueueConfigurations()` は `create_only_config_db_buffers` の値に関わらず全キューを対象とする（`flexcounterorch.cpp:544-553`）。ただし `QUEUE_COUNTER_CAPABILITIES` の書き込みロジックは VoQ 分岐を持たず、SAI クエリ結果のみで決まる。VoQ 環境では System Port ごとの VOQ（Virtual Output Queue）も `queue_stat_ids` + `voq_stat_ids` で管理されるが、`QUEUE_COUNTER_CAPABILITIES` に `voq_stat_ids` に対応するキーは定義されていない。

evidence: `flexcounterorch.cpp:544-553`、`portsorch.cpp:8601-8614`

### 4. プラットフォーム無依存部分

- **書き込みロジック**: `initCounterCapabilities()` 内の 4 キー初期化 → SAI クエリ → 条件付き上書きのシーケンスはプラットフォーム分岐なし
- **キー名文字列**: `WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER` 等のリテラルはコードにハードコードされており、プラットフォームにより変わらない
- **consumer の参照方法**: `wredstat` / `portstat.py` は `isSupported` フィールドを直接 GET し、プラットフォーム識別ロジックを持たない

---

## プラットフォーム差サマリ

| プラットフォーム / 条件 | QUEUE_COUNTER_CAPABILITIES への影響 | 根拠 |
|----------------------|----------------------------------|------|
| WRED 完全サポート ASIC (BCM 等) | 4 フラグすべて `"true"` になりうる | `sai_query_stats_capability` が 4 統計を返す |
| WRED 部分サポート ASIC | ECN のみ / WRED ドロップのみ `"true"` | 返却リストに含まれる統計のみ `"true"` |
| WRED 非サポート ASIC / VS | 全フラグ `"false"` | クエリが SUCCESS でも対応統計なし、またはクエリ失敗 |
| DPU (SmartSwitch) | 全フラグ `"false"` が一般的 | DPU SAI は WRED キュー統計未対応が多い |
| VoQ スイッチ | FlexCounter 対象が全キューに拡張される（CAPABILITIES 書き込み自体はプラットフォーム差なし） | `getQueueConfigurations()` の分岐 |
