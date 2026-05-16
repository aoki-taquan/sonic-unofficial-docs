# MACSEC_PROFILE — Phase C 暗黙参照抽出

**対象ページ**: `docs/reference/config-db/macsec-profile.md`
**ソース**: `sonic-swss/orchagent/macsecorch.cpp`, `sonic-swss/cfgmgr/macsecmgr.cpp`
**作成日**: 2026-05-16

## 抽出結果

### 1. PORT テーブル（`PORT.macsec` フィールド）

- **参照種別**: 読み取り（トリガー条件）
- **利用箇所**: `MACsecMgr::enableMACsec()` (`cfgmgr/macsecmgr.cpp:298,473-484`) が `CFG_PORT_TABLE` の SET イベントを購読し、`get_value(port_attr, "macsec", profile_name)` で `PORT|<ifname>` エントリの `macsec` フィールドを読み取る。このフィールドが空か存在しない場合は `disableMACsec()` へフォールバック。
- **影響**: `MACSEC_PROFILE` テーブルへのエントリ追加だけでは MACsec は有効化されない。`PORT|<ifname>` の `macsec` フィールドにプロファイル名を設定することで初めて MKA セッションが起動する。双方が揃うまで `task_need_retry` でリトライされる。

### 2. MACSEC_PROFILE → STATE_DB PORT テーブル（`isPortStateOk`）

- **参照種別**: 読み取り（起動ゲート）
- **利用箇所**: `MACsecMgr::isPortStateOk()` (`cfgmgr/macsecmgr.cpp:614-631`) が `m_statePortTable` (STATE_DB `PORT_TABLE`) を `get()` し、`state == "ok"` かつ `netdev_oper_status == "up"` の両条件を確認する。これが満たされない間は `enableMACsec()` が `task_need_retry` を返し続ける。
- **影響**: 物理リンクが UP していない（または PortsOrch の初期化が未完了の）ポートに MACsec を適用しようとした場合、MACsec の有効化がブロックされる。STATE_DB の `PORT_TABLE` への依存が暗黙的に存在する。

### 3. MACSEC_SC（APPL_DB）← MACsecOrch が処理

- **参照種別**: 受信（APPL_DB 経由）
- **利用箇所**: `MACsecOrch::doTask()` (`orchagent/macsecorch.cpp:863-891`) が `APP_MACSEC_EGRESS_SC_TABLE_NAME` / `APP_MACSEC_INGRESS_SC_TABLE_NAME` を購読。キー形式は `<port_name>:<sci>` (`cfgmgr/macsecmgr.cpp:1715` の `swss::join(':', port_name, MACsecSCI(...))`)。SC テーブルエントリが書き込まれると `taskUpdateEgressSC` / `taskUpdateIngressSC` が SAI `sai_macsec_api` でセキュリティチャネルを確立する。
- **影響**: MACSEC_PROFILE → `wpa_supplicant` (MKA) → APPL_DB `MACSEC_EGRESS_SC` / `MACSEC_INGRESS_SC` という非同期連鎖が存在する。CONFIG_DB 書き込みから SAI SC 作成までの経路は同期的ではなく、MKA 交渉が成立して初めて SC/SA がプログラムされる。

### 4. APP_PORT_TABLE（APPL_DB）—— `pfc_encryption_mode` フィールド

- **参照種別**: 読み取り（PFC ACL 設定）
- **利用箇所**: `MACsecOrch::createMACsecACLTable()` (`orchagent/macsecorch.cpp:2709-2715`) が `m_applPortTable.get(port_name, values)` で APPL_DB `PORT_TABLE` のポートエントリを取得し、`pfc_encryption_mode` フィールドを読み取って PFC ACL エントリを生成する。
- **影響**: MACsec 有効時に PFC (Priority Flow Control) の暗号化モードが APPL_DB PORT テーブルから暗黙的に取得される。このフィールドが存在しない場合はデフォルト値 (`PFC_MODE_DEFAULT`) を使用する。

## 既存ページとの整合性確認

| 既存記述 | 確認結果 |
|---------|---------|
| `PORT.macsec` フィールドでプロファイル名を参照すると説明 | `enableMACsec()` の `get_value(port_attr, "macsec", profile_name)` で確認 — 整合 |
| `macsecmgrd` が `MACSEC_PROFILE` を購読 | `CFG_MACSEC_PROFILE_TABLE_NAME` の SET/DEL ハンドラ登録で確認 — 整合 |
| MACsec SC/SA は SAI `sai_macsec_api` 経由 | `taskUpdateEgressSC` → `SAI_MACSEC_SC_ATTR_*` 属性設定で確認 — 整合 |
| `wpa_supplicant` が MKA セッションを実行 | `startWPASupplicant()` での `execl(WPA_SUPPLICANT_CMD, "-D", "macsec_sonic", ...)` で確認 — 整合 |
