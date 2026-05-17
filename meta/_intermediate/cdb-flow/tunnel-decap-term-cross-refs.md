# TUNNEL_DECAP_TERM_TABLE — Phase C 暗黙参照 (cross-table refs) 調査メモ

調査日: 2026-05-17
対象ファイル:
- `sonic-swss/orchagent/tunneldecaporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/routeorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/vnetorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/orchdaemon.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/tunnelmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## YANG leafref

`TUNNEL_DECAP_TERM_TABLE` は APPL_DB のテーブルであり YANG 定義対象外。leafref は存在しない。以下はすべて実装レベルの暗黙参照。

---

## 暗黙参照 (実装レベル)

### 1. APPL_DB.TUNNEL_DECAP_TABLE — 親トンネルの存在確認 (読み取り)

- **参照先テーブル**: `APPL_DB.TUNNEL_DECAP_TABLE`
- **参照方向**: 読み取り（メモリ内 `tunnelTable` map で間接参照）
- **参照元**: `doDecapTunnelTermTask()` L392: `bool tunnel_exists = (tunnelTable.find(tunnel_name) != tunnelTable.end());`
- **機構**: TUNNEL_DECAP_TERM_TABLE の SET/DEL イベント処理時に、同一 `tunnel_name` の TUNNEL_DECAP_TABLE エントリが tunnelTable (orchagent メモリ内キャッシュ) に存在するか確認する。存在しなければ unhandledDecapTerms に保留し、TUNNEL_DECAP_TABLE 作成完了後に自動フラッシュされる。
- **条件**: 全 SET/DEL イベント処理時
- **副作用**: 親トンネルが不在の場合は永続スキップでなく保留 (unhandledDecapTerms)。LOG_NOTICE が出るが機能的問題なし (L520: `"tunnel doesn't exist, added to unhandled list."`)
- evidence: `tunneldecaporch.cpp:392, 511-521, 1497-1519`

### 2. STATE_DB.TUNNEL_DECAP_TERM_TABLE — モニタリングミラー (書き込み)

- **参照先テーブル**: `STATE_DB.TUNNEL_DECAP_TERM_TABLE` (STATE_TUNNEL_DECAP_TERM_TABLE_NAME = "TUNNEL_DECAP_TERM_TABLE")
- **参照方向**: 書き込み（APPL_DB への SAI 反映成功後にミラー書き込み）
- **参照元**: `addDecapTunnelTermEntry()` L998: `setDecapTunnelTermStatus(...)` → `stateTunnelDecapTermTable->set(key, fv)`
- **機構**: SAI `create_tunnel_term_table_entry()` 成功後に STATE_DB へ同じ key/fields を書き込む。`src_ip` / `subnet_type` は空でない場合のみ書き込まれる (L1551-1558)。DEL 時は `removeDecapTunnelTermStatus()` で STATE_DB のエントリも削除 (L1563-1567)。
- **条件**: SAI create/remove 成功時
- **副作用**: SAI 失敗時は STATE_DB に書き込まれないため、STATE_DB が「実際に SAI 設定された term の一覧」として機能する。
- evidence: `tunneldecaporch.cpp:998, 1539-1567`

### 3. RouteOrch — VIP route 登録時の自動書き込み (書き込み元)

- **参照先テーブル**: `APPL_DB.TUNNEL_DECAP_TERM_TABLE` (本テーブル)
- **参照方向**: 書き込み (`ProducerStateTable::set()`)
- **参照元**: `RouteOrch::createVipRouteSubnetDecapTerm()` (routeorch.cpp L3220-3235)、`RouteOrch::removeVipRouteSubnetDecapTerm()` (routeorch.cpp L3238-3251)
- **機構**: VIP subnet decap ルートが追加されるとき RouteOrch が `m_appTunnelDecapTermProducer.set(key, {{"term_type","MP2MP"},{"subnet_type","vip"}})` を直接 APPL_DB に書き込む。RouteOrch が TUNNEL_DECAP_TERM_TABLE の書き込み元の一つであることに注意。書き込み前に `gTunneldecapOrch->getSubnetDecapConfig().enable` を確認し、false の場合はスキップする (L3223)。
- **条件**: VIP ルート追加 (subnet decap enable=true かつ VIP prefix の場合)
- **副作用**: `m_SubnetDecapTermsCreated` set で重複書き込みを防止している (L3224)。RouteOrch 側の削除は `removeVipRouteSubnetDecapTerm()` が APPL_DB から DEL する。
- evidence: `routeorch.cpp:53, 3220-3251`

### 4. VNetRouteOrch — VNet VIP route 登録時の自動書き込み (書き込み元)

- **参照先テーブル**: `APPL_DB.TUNNEL_DECAP_TERM_TABLE` (本テーブル)
- **参照方向**: 書き込み (`ProducerStateTable::set()`)
- **参照元**: `VNetRouteOrch::createSubnetDecapTerm()` (vnetorch.cpp L1563-1578)、`VNetRouteOrch::removeSubnetDecapTerm()` (vnetorch.cpp L1581-1594)
- **機構**: VNet VIP ルート追加時に `app_tunnel_decap_term_producer_.set(key, {{"term_type","MP2MP"},{"subnet_type","vip"}})` を書き込む。RouteOrch と同様、`getSubnetDecapConfig().enable` を確認し false ならスキップ (L1566)。`subnet_decap_terms_created_` で重複防止 (L1566)。
- **条件**: VNet VIP ルート追加 (subnet decap enable=true かつ VNet prefix の場合)
- **副作用**: RouteOrch と VNetRouteOrch が同一 prefix の term を二重書き込みしないように、それぞれ独立した `*_created_` set で管理している。
- evidence: `vnetorch.cpp:734, 1563-1594`

### 5. SubnetDecapConfig — subnet decap 設定の参照 (読み取り)

- **参照先テーブル**: `CONFIG_DB.SUBNET_DECAP`（`subnetDecapConfig` 構造体を経由）
- **参照方向**: 読み取り（`gTunneldecapOrch->getSubnetDecapConfig()` または `subnetDecapConfig` メンバー直接参照）
- **参照元**: `doDecapTunnelTermTask()` L472-509: subnet decap term の `enable` / `src_ip` / `src_ip_v6` を参照してエントリを採否決定
- **機構**: `is_subnet_decap_term` が true のとき `subnetDecapConfig.enable` が false → 永続スキップ。`enable` が true でも `src_ip` / `src_ip_v6` が空 → 永続スキップ。
- **条件**: tunnel_name が `subnetDecapConfig.tunnel` または `subnetDecapConfig.tunnel_v6` に一致する term の処理時
- **副作用**: SUBNET_DECAP が後から更新されても、すでにスキップされた term はキューから消えているため自動再処理されない（運用上は SUBNET_DECAP を先に設定すること）。
- evidence: `tunneldecaporch.cpp:393-394, 472-509`

---

## 参照関係サマリ

```
APPL_DB.TUNNEL_DECAP_TERM_TABLE（書き込み: tunnelmgrd / swssconfig / RouteOrch / VNetRouteOrch）
  ├─ [読み取り] APPL_DB.TUNNEL_DECAP_TABLE (tunnelTable メモリキャッシュ)
  │              → 親トンネル存在確認。不在なら unhandledDecapTerms に保留
  ├─ [読み取り] CONFIG_DB.SUBNET_DECAP (subnetDecapConfig)
  │              → subnet decap term の採否決定。enable=false / src_ip 未設定なら永続スキップ
  ├─ [書き込み] STATE_DB.TUNNEL_DECAP_TERM_TABLE
  │              → SAI create 成功後にモニタリングミラーを書き込み
  ├─ [書き込み元] RouteOrch (routeorch.cpp)
  │              → VIP ルート追加時に subnet_type=vip の MP2MP term を自動書き込み
  └─ [書き込み元] VNetRouteOrch (vnetorch.cpp)
                 → VNet VIP ルート追加時に subnet_type=vip の MP2MP term を自動書き込み
```

---

## Evidence

- `tunneldecaporch.cpp:35, 392-521, 998, 1539-1567`
- `routeorch.cpp:53, 3220-3251`
- `vnetorch.cpp:734, 1563-1594`
- `orchdaemon.cpp:343-348`
