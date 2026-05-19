# FLEX_COUNTER_TABLE|PG_WATERMARK — Phase H プラットフォーム差スキャンノート

Generated: 2026-05-19
Target doc: docs/reference/config-db/pg-watermark.md

対象エントリ: `CONFIG_DB FLEX_COUNTER_TABLE|PG_WATERMARK`
Consumer: `FlexCounterOrch::doTask()`, `PortsOrch` PG watermark manager, `WatermarkOrch::doTask()`
スキャン範囲: `orchagent/flexcounterorch.cpp` 全行、`orchagent/portsorch.cpp` PG watermark 関連、`sonic-buildimage/src/sonic-config-engine/minigraph.py:58,2740`

---

## 検出したプラットフォーム差

### 1. 管理デバイス — minigraph による強制 disable

`minigraph.py:58` の `mgmt_disabled_counters = ["PG_WATERMARK", "QUEUE_WATERMARK", ...]` リストが管理デバイス判定時に参照される。`minigraph.py:2740` 付近で管理デバイスに対し `FLEX_COUNTER_TABLE|PG_WATERMARK: {"FLEX_COUNTER_STATUS": "disable"}` が CONFIG_DB に書き込まれる。

これは minigraph 再生成のたびに適用されるため、`counterpoll watermark enable` で一時的に上書きしても minigraph 再生成で元に戻る。

### 2. SAI カウンタ対応差 — ASIC 依存

- `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES`: headroom バッファ（XOFF）非サポート ASIC では 0 または `SAI_STATUS_NOT_SUPPORTED`
- `SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES`: ほとんどの ASIC でサポート。`vs` プラットフォームでは 0 固定

FlexCounter Manager は SAI エラーを orchagent エラーとして伝播しないため、ASIC 非対応でも orchagent ログにエラーは出ない（syncd 内で吸収）。

### 3. VoQ / ファブリック / DASH — 影響なし

- `flexcounterorch.cpp` の `gMySwitchType == "voq"` 分岐は QUEUE グループの BUFFER_QUEUE 取得ロジック（`getQueueConfigurations()`）にのみ存在。PG_WATERMARK ハンドラパス（`flexcounterorch.cpp:258-270`）に VoQ 依存コードなし。
- `gFabricPortsOrch` のファブリックポート QUEUE カウンタ追加処理（`flexcounterorch.cpp:291-294`）は QUEUE グループ専用。PG_WATERMARK は対象外。
- DASH/SmartSwitch 系 orch 参照（`flexcounterorch.cpp:299-347`）は ENI/DASH_METER/HA_SET グループ専用。
- Gearbox 追加処理（`flexcounterorch.cpp:204-212`）は PORT/MACSEC グループ専用。

### 4. multi-asic

各 ASIC namespace で orchagent が独立起動し、自 namespace の CONFIG_DB および FLEX_COUNTER_DB を参照する。PG watermark カウンタは ASIC ごとに独立して収集・書き込みされる。

---

## サマリ

| プラットフォーム | 影響 | 根拠 |
|---------------|------|------|
| 管理デバイス | minigraph が `disable` を強制書き込み | `minigraph.py:58,2740` |
| SAI 非対応 ASIC (XOFF_ROOM) | ウォーターマーク値が常時 0 または N/A | `portsorch.cpp:410-414` |
| VoQ シャーシ | 影響なし | `flexcounterorch.cpp` PG_WATERMARK パスに VoQ 分岐なし |
| ファブリックポート | 影響なし | PG は ingress PG 専用、ファブリックポートに PG なし |
| DASH / SmartSwitch | 影響なし | DASH 系コードパスは PG_WATERMARK ハンドラ外 |
| Gearbox | 影響なし | PORT/MACSEC グループ専用処理 |
| multi-asic | ASIC ごとに独立収集 | namespace 分離 |
