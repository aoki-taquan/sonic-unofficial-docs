# COUNTERS_DB RIF カウンタ — Phase H プラットフォーム制約スキャンノート

対象テーブル: `COUNTERS_DB / COUNTERS_RIF_NAME_MAP`, `COUNTERS_RIF_TYPE_MAP`, `COUNTERS:<oid>`, `RATES:<oid>`
Consumer/Writer: `IntfsOrch` (`sonic-swss/orchagent/intfsorch.cpp`)
スキャン範囲: `intfsorch.cpp` 全行・`flexcounterorch.cpp` RIF ブランチ・`intfsorch.h`

---

## 検出したプラットフォーム依存・SAI Capability 差異

### 1. VoQ シャーシ vs 非 VoQ — インタフェース処理パスの分岐

- `gMySwitchType == "voq"` かつ `isChassisDbInUse()` のとき `IntfsOrch` コンストラクタ (`intfsorch.cpp:102-108`) でシャーシ向けの追加 subscriber (`CHASSIS_APP_SYSTEM_INTERFACE_TABLE_NAME`) が登録される。
- VoQ 環境では `addRouterIntfs()` 成功後に `voqSyncAddIntf()` が呼ばれ、ローカル RIF の情報を `CHASSIS_APP_DB / SYSTEM_INTERFACE_TABLE` に同期する (`intfsorch.cpp:1314-1317`)。
- リモートシステムポートの RIF SET が届いた場合 (`isRemoteSystemPortIntf()`)、`doTask(Consumer)` は通常の `setIntf()` / `addRouterIntfs()` を呼ばず oper_status の NeighOrch 通知のみ行う (`intfsorch.cpp:881-893`)。
  - **影響**: リモートシステムポートには `COUNTERS_RIF_NAME_MAP` エントリが作成されず、FLEX_COUNTER_DB への登録も行われない。`intfstat` でリモート RIF のカウンタは表示されない。
- evidence: `intfsorch.cpp:102-108`, `intfsorch.cpp:881-893`, `intfsorch.cpp:1314-1317`, `intfsorch.cpp:1640-1666`

### 2. RIF タイプ別の SAI OID 解決 — PHY / LAG / VLAN / SUBPORT / SYSTEM

- `addRifToFlexCounter()` を呼ぶ `doTask(SelectableTimer&)` ではポートタイプ (`Port::PHY`, `Port::LAG`, `Port::VLAN`, `Port::SUBPORT`, `Port::SYSTEM`) に応じて `type` 文字列を切り替える (`intfsorch.cpp:1609-1626`)。
- `Port::SYSTEM` は VoQ シャーシ専用で `SAI_ROUTER_INTERFACE_TYPE_PORT` 扱いとなり、`COUNTERS_RIF_TYPE_MAP` に `"SAI_ROUTER_INTERFACE_TYPE_PORT"` として書き込まれる。
- `Port::SUBPORT`（VLAN サブインタフェース）は `SAI_ROUTER_INTERFACE_TYPE_SUB_PORT` として登録される。SAI がサブポートタイプの統計取得をサポートしない場合、`COUNTERS:<oid>` フィールドは syncd ポーリング時に 0 のまま更新されないことがある（プラットフォーム依存）。
- `addRouterIntfs()` の SAI 属性設定 (`intfsorch.cpp:1210-1248`) でも同じ型分岐があり、`Port::PHY`/`Port::SYSTEM` は `SAI_ROUTER_INTERFACE_ATTR_PORT_ID`、`Port::LAG` は `m_lag_id`、`Port::VLAN` は `m_vlan_info.vlan_oid` を使用する。
- evidence: `intfsorch.cpp:1609-1626`, `intfsorch.cpp:1210-1248`

### 3. SAI_ROUTER_INTERFACE_STAT_* の未サポートフィールド

- `rifStatIds[]` (`intfsorch.cpp:49-59`) に列挙された `SAI_ROUTER_INTERFACE_STAT_*` 全件が FLEX_COUNTER_DB に登録される。
- SAI 実装がそのプラットフォームで一部フィールドをサポートしない場合、syncd は当該フィールドをスキップしてポーリング結果を書かない（または常に 0 を返す）。
  - 例: 一部 ASIC では `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_OCTETS` / `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_OCTETS` が未サポートで COUNTERS_DB に存在しない。
  - `intfstat` はフィールドが存在しない場合に `0` として表示するが、値の「存在しない」と「ゼロ」を区別しない。
- evidence: `intfsorch.cpp:49-59`, `intfsorch.cpp:1543-1548`

### 4. `gTraditionalFlexCounter` — SAI モードによる登録パスの差異

- `gTraditionalFlexCounter = true`（旧モード）: ASIC_DB `VIDTORID` テーブルへの RIF OID 登録が syncd によって完了するまで、`doTask(SelectableTimer&)` の 1 秒 tick ごとに登録を試みる (`intfsorch.cpp:1627-1636`)。ハードウェア初期化が遅い環境（大規模シャーシ等）では複数 tick の遅延が生じる。
- `gTraditionalFlexCounter = false`（新 rpc モード）: VIDTORID チェックをスキップし SAI RIF 作成直後の次 tick で `addRifToFlexCounter()` を呼ぶ。初期カウンタ統計がより早く収集開始される。
- evidence: `intfsorch.cpp:1627-1636`, `intfsorch.h:40`

### 5. NAT ゾーン ID — NAT 対応プラットフォーム限定

- `gIsNatSupported` が `true` の場合のみ `addRouterIntfs()` で `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` が SAI 属性に追加される (`intfsorch.cpp:1287-1294`)。
- NAT 非対応プラットフォームでは `nat_zone_id` フィールドは SAI に渡されず、COUNTERS_DB への影響もない（カウンタ ID リストは変わらない）。
- evidence: `intfsorch.cpp:1287-1294`

### 6. MPLS 対応プラットフォーム限定

- `port.m_mpls == true` のとき `addRouterIntfs()` で `SAI_ROUTER_INTERFACE_ATTR_ADMIN_MPLS_STATE` が SAI 属性に追加される (`intfsorch.cpp:1278-1284`)。
- MPLS 非対応プラットフォームでは SAI がこの属性をリジェクトする可能性があり、その場合 `create_router_interface()` がエラーを返して RIF 作成が失敗し COUNTERS_DB へのエントリが作成されない。
- evidence: `intfsorch.cpp:1278-1284`, `intfsorch.cpp:1297-1305`

### 7. LoopBack インタフェース — RIF カウンタなし

- `alias.find("Loopback")` で判定 (`is_lo = !alias.compare(0, strlen(LOOPBACK_PREFIX), LOOPBACK_PREFIX)`)。Loopback インタフェースは `setIntf()` で処理されるが `addRouterIntfs()` は呼ばれず `m_rifsToAdd` に積まれない (`intfsorch.cpp:688`)。
- **影響**: LoopBack RIF は COUNTERS_RIF_NAME_MAP にエントリが作成されず `intfstat` に表示されない。これはプラットフォーム依存ではなくアーキテクチャ的な設計（LoopBack は ASIC レベルでは RIF を持たない）。
- evidence: `intfsorch.cpp:688-689`

---

## プラットフォーム差異サマリ

| # | 差異 | 対象 | 影響 |
|---|------|------|------|
| 1 | VoQ シャーシ: リモートシステムポート RIF は COUNTERS_DB 未登録 | VoQ 環境 | `intfstat` でリモート RIF のカウンタ表示なし |
| 2 | RIF タイプ (SUBPORT 等) による SAI 統計サポート差 | ASIC 依存 | 未サポートフィールドは COUNTERS_DB 不在または常 0 |
| 3 | `SAI_ROUTER_INTERFACE_STAT_*` 部分サポート | ASIC 依存 | 特定エラーカウンタが非表示になる場合あり |
| 4 | `gTraditionalFlexCounter` モード: VIDTORID 完了まで登録遅延 | old-mode 環境 | 起動後数秒間カウンタが空になる場合あり |
| 5 | NAT ゾーン ID: NAT 非対応 ASIC では SAI 属性スキップ | NAT 非対応 | カウンタ収集への直接影響なし |
| 6 | MPLS 属性: MPLS 非対応 ASIC では `create_router_interface` 失敗リスク | MPLS 非対応 | RIF 未作成 → COUNTERS_DB エントリなし |
| 7 | LoopBack インタフェース: RIF カウンタ対象外（アーキ設計） | 全プラットフォーム | LoopBack は `intfstat` に表示されない |
