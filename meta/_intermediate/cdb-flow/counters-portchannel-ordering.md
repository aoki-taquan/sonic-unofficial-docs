# counters-portchannel Phase B — 書込み順依存スキャンノート

Generated: 2026-05-18
Target doc: docs/reference/config-db/counters-portchannel.md

対象テーブル: `COUNTERS_DB COUNTERS_LAG_NAME_MAP` / `COUNTERS_RIF_NAME_MAP` / `COUNTERS:<oid>` / `RATES:<oid>`
Consumer: `portsorch` (addLag/removeLag) + `intfsorch` (addRifToFlexCounter / doTask(SelectableTimer))
スキャン範囲: `portsorch.cpp:762-767, 8019-8022, 8095`, `intfsorch.cpp:70-81, 1296-1310, 1527-1553, 1598-1637`

---

## 検出した順序依存・タイミング依存

### 1. SAI LAG 作成 → COUNTERS_LAG_NAME_MAP 書き込み

`addLag()` (`portsorch.cpp:7941`) は `sai_lag_api->create_lag()` が成功してから `m_counterLagTable->set("", fields)` (`portsorch.cpp:8022`) で `COUNTERS_LAG_NAME_MAP` にエントリを書き込む。

**順序依存**: SAI 作成が先行必須。`create_lag()` が失敗すると `COUNTERS_LAG_NAME_MAP` にエントリは書かれない。consumer が `intfstat` / SNMP 経由で LAG OID を参照する場合、マップ不在により「Interface missing」エラーになる。

evidence: `portsorch.cpp:7994-8003, 8019-8022`

### 2. SAI LAG 削除後に COUNTERS_LAG_NAME_MAP から即時削除

`removeLag()` は `sai_lag_api->remove_lag()` 成功後、`m_counterLagTable->hdel("", lag.m_alias)` (`portsorch.cpp:8095`) でマップエントリを削除する。

**順序依存（削除側）**: 参照カウントが非ゼロ / メンバーが残存 / VLAN メンバーあり / bridge_port 残存のいずれかの場合、`removeLag()` が false を返しマップ削除も発生しない。CONFIG_DB から LAG を削除しても参照カウント解消まで古い OID がマップに残存する。

evidence: `portsorch.cpp:8049-8072, 8095`

### 3. PORTCHANNEL_INTERFACE SET → COUNTERS_RIF_NAME_MAP 書き込み（タイマー非同期）

`intfsorch` が PORTCHANNEL_INTERFACE の SET を受信して `addRouterIntf()` を実行すると (`intfsorch.cpp:1296-1310`)、SAI RIF 作成成功後にポートを `m_rifsToAdd` キューに追加する。実際の `COUNTERS_RIF_NAME_MAP` 書き込みは `doTask(SelectableTimer&)` (`intfsorch.cpp:1598-1637`) が `UPDATE_MAPS_SEC` 後に `addRifToFlexCounter()` を呼ぶまで遅延する。

**順序依存（非同期）**: SET から `COUNTERS_RIF_NAME_MAP` への書き込みまでタイマー遅延がある。`intfstat` / FlexCounter がタイマー満了前にポーリングすると該当 OID のカウンタが N/A になる。

evidence: `intfsorch.cpp:1310, 1598-1637`

### 4. `gTraditionalFlexCounter` モードでの VID→RID 解決待ち

`gTraditionalFlexCounter = true`（syncd traditional mode）の場合、`doTask(SelectableTimer&)` は `m_vidToRidTable->hget("", id, value)` が成功するまで `m_rifsToAdd` を消費しない (`intfsorch.cpp:1627`)。ASIC_DB `VIDTORID` テーブルに RIF の VID→RID マッピングが存在しない間は `COUNTERS_RIF_NAME_MAP` への書き込みが行われない。

**順序依存（TFC モード固有）**: VID→RID 解決完了 → `COUNTERS_RIF_NAME_MAP` 書き込みの順が強制。次回タイマー満了で自動リトライされるため手動介入は不要。

evidence: `intfsorch.cpp:73-75, 1627-1631`

### 5. PortsOrch コンストラクタでの空エントリ初期化

`PortsOrch` コンストラクタ (`portsorch.cpp:767`) は orchagent 起動時に `m_counterLagTable->set("", defaultLagFv)` で空の FieldValueTuple を書き込み `COUNTERS_LAG_NAME_MAP` ハッシュを初期化する。以降の `addLag()` / `removeLag()` がフィールドを追加・削除する。

**順序依存（起動時）**: 起動直後にマップを参照すると空ハッシュが返る中間状態がある。個別 LAG の OID は `addLag()` 呼び出し後にのみ登録される。

evidence: `portsorch.cpp:764-767`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | SAI LAG 作成成功 → COUNTERS_LAG_NAME_MAP 書き込み | 強制先行 | SAI 失敗時はマップ不在。intfstat でエラー |
| 2 | LAG 参照カウント = 0 → COUNTERS_LAG_NAME_MAP hdel | 強制先行（削除側） | 参照カウント非ゼロの間は古い OID が残存 |
| 3 | PORTCHANNEL_INTERFACE SET → COUNTERS_RIF_NAME_MAP（タイマー遅延） | 非同期（UPDATE_MAPS_SEC 後） | タイマー満了前の参照は N/A |
| 4 | VID→RID 解決（ASIC_DB VIDTORID）→ COUNTERS_RIF_NAME_MAP（TFC モードのみ） | 強制先行（TFC 固有） | 次回タイマーで自動リトライ |
| 5 | PortsOrch コンストラクタ空初期化 → 個別 LAG OID 登録 | 起動固定順序 | 起動直後は空ハッシュが返る中間状態あり |
