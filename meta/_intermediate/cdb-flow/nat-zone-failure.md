# nat-zone — Phase D failure 調査メモ

## 調査対象
- `sonic-swss/cfgmgr/natmgr.cpp` — `setMangleIptablesRules` / `doNatIpInterfaceTask`
- `sonic-swss/orchagent/intfsorch.cpp` — `setRouterIntfsNatZoneId`

## natmgr 側の失敗挙動

### setMangleIptablesRules 失敗
- `swss::exec()` が非0 を返した場合: `SWSS_LOG_ERROR("Command '...' failed with rc %d")` してから `false` を返す
- **呼び出し元が戻り値を無視**: `natmgr.cpp:7551` / `natmgr.cpp:7583` では返値チェックなし
- キャッシュ (`m_natZoneInterfaceInfo`) は更新される → kernel との乖離が発生
- 次回イベントでは同値と判定されて再試行不可

## intfsorch 側の失敗挙動

### setRouterIntfsNatZoneId 失敗
- SAI STATUS != SUCCESS: `SWSS_LOG_ERROR("Failed to set router interface ... NAT Zone Id ...")` → `handleSaiSetStatus` に委譲
- RIF 未存在 (m_rif_id == 0): `SWSS_LOG_WARN` して `true` 返却 (silent skip)
- Port.m_nat_zone_id は設定失敗時でも更新済みのため再試行が行われない可能性あり

## 共通の特徴
- STATE_DB への障害記録なし
- 両コンポーネントともに自動回復メカニズムなし
