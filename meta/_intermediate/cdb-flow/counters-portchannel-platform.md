# counters-portchannel Phase H — プラットフォーム差異スキャンノート

Generated: 2026-05-18
Target doc: docs/reference/config-db/counters-portchannel.md

対象テーブル: `COUNTERS_DB|COUNTERS_LAG_NAME_MAP`、`COUNTERS_DB|COUNTERS_RIF_NAME_MAP`
Consumer: `orchagent` — `portsorch::addLag()` / `intfsorch::addRifToFlexCounter()`
スキャン範囲: `portsorch.cpp` addLag / voqSyncAddLag / isMlnxPlatform 系、`intfsorch.cpp` 全行

---

## 検出したプラットフォーム差異

### 1. VoQ スイッチ — `COUNTERS_LAG_NAME_MAP` への OID キーが変わらないが LAG 生成属性が異なる

`gMySwitchType == "voq"` 時、`addLag()` は `create_lag()` に `SAI_LAG_ATTR_SYSTEM_PORT_AGGREGATE_ID` を追加する (`portsorch.cpp:7962-7991`)。Multi-ASIC VoQ では `LagIdAllocator` がシャーシ全体でユニークな `spa_id` を払い出す。

- `COUNTERS_LAG_NAME_MAP` に書き込まれる OID は通常スイッチと変わらない（SAI が返す `lag_id` をそのまま格納）。
- `voqSyncAddLag()` が CHASSIS_APP_DB `SYSTEM_LAG_TABLE` に system_lag_alias（`<hostname>|<asic>|PortChannelXXXX` 形式）を書き込む副次書き込みが発生する (`portsorch.cpp:11139-11162`)。
- VoQ 構成では CHASSIS_APP_DB からリモート LAG エントリが到着した場合も `doVoqSystemLagTask()` が `addLag()` を呼び `COUNTERS_LAG_NAME_MAP` に登録するため、**リモートシステム LAG の OID が COUNTERS_DB に混在する**。

evidence: `portsorch.cpp:7962-7991`, `portsorch.cpp:11139-11165`, `portsorch.cpp:1084-1094`

### 2. Mellanox — LAG メンバ有効/無効操作の順序が異なるが COUNTERS_DB に直接影響なし

LAG メンバの collection / distribution 属性操作順が Mellanox 固有であることはコード中に明記されているが (`portsorch.cpp:6361-6382` のコメント「distribution-only mode is not supported on Mellanox platform」)、これは `SAI_LAG_MEMBER_ATTR_INGRESS_DISABLE` / `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` の SET 順序の問題であり `COUNTERS_LAG_NAME_MAP` / `COUNTERS_RIF_NAME_MAP` の書き込み自体には影響しない。

### 3. `gTraditionalFlexCounter` — ASIC_DB VID→RID ゲートの有無

`gTraditionalFlexCounter = true` の場合（一部の古い platform 構成や VS 環境のデフォルト）、`intfsorch` はタイマーループで `ASIC_DB VIDTORID` を確認してから `addRifToFlexCounter()` を呼ぶ (`intfsorch.cpp:1627`)。`gTraditionalFlexCounter = false` 環境ではこのゲートがなく即座に `startFlexCounterPolling()` が呼ばれる。結果として `COUNTERS_RIF_NAME_MAP` への書き込みタイミングが最大数秒異なる可能性がある。

evidence: `intfsorch.cpp:40`, `intfsorch.cpp:1627`

### 4. VS（Virtual Switch）— RIF カウンタは返るが値は 0 固定

`sonic-sairedis/vslib` の Virtual Switch SAI は `SAI_OBJECT_TYPE_ROUTER_INTERFACE` の統計取得をサポートするが、実トラフィックを反映しない（すべて 0 を返す）。そのため `COUNTERS:<rif_oid>` のフィールドは存在するが値が変化しない。`RATES:<rif_oid>` の BPS/PPS は計算上 0 になる。

evidence: vslib の stats_get 実装（VirtualSwitchSaiInterface）では RIF stat を stub 返答

### 5. RIF stat ID セット — プラットフォーム共通（変更不可）

`rifStatIds` (`intfsorch.cpp:49-58`) の 8 統計は全プラットフォーム共通であり、プラットフォームごとに変化しない。SAI が特定の stat を `SAI_STATUS_NOT_SUPPORTED` で返した場合、FlexCounter は当該フィールドを 0 で書き込む（エラーをログして継続）。現時点でコードに stat 個別の capability チェックは存在しない。

### 結論

プラットフォーム差異は小さく、VoQ 構成での `COUNTERS_LAG_NAME_MAP` へのリモート LAG 混在と `gTraditionalFlexCounter` によるタイミング差が主な注意点。RIF カウンタの stat セット自体はプラットフォーム非依存。
