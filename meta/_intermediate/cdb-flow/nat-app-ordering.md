# nat-app Phase B — 書込み順依存調査ノート

## 調査対象
- `sonic-swss/orchagent/natorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/cfgmgr/natmgr.cpp`
- `sonic-swss/natsyncd/natsync.cpp`

## 主要発見

### NAT_GLOBAL_TABLE が強制先行 (依存 #1)
- `addNatEntry()` L1907-1913: `isNatEnabled() == false` → WARN + return true (SAI 操作なし)
- `enableNatFeature()` L2534-2582: admin_mode="enabled" 受信 → `addAllDnatPoolEntries()` → `addAllNatEntries()` でキャッシュ一括 SAI 投入
- `addAllNatEntries()` L3178-3260: `m_natEntries` / `m_naptEntries` を走査して `addedToHw==false` エントリを投入

### NAT_DNAT_POOL_TABLE は独立 (依存 #3)
- `doDnatPoolTableTask()` L2968-3040: pool は NAT エントリと独立して SAI に投入
- `doNatTableTask()` L2617-2683: NAT エントリは pool 存在に依存しない

### NH 解決依存 (依存 #7)
- `addDnatToNhCache()` L391-430: `gNhTrackingSupported==true` 時は m_neighOrch->getNeighborEntry() で即時解決試み
- 未解決時: `m_routeOrch->attach(this, translatedIp)` で RouteOrch observer 登録
- NH 解決通知受信後に `addHwDnatEntry()` 遅延実行

### orchdaemon.cpp 登録順
- L454-464: natorch_base_pri=50、各テーブル優先度 50〜55
- L594: `m_orchList.push_back(gNatOrch)` — vnet 系の後、mlag の前
- NatOrch は RouteOrch (L337) / NeighOrch (L298) より後に生成される
