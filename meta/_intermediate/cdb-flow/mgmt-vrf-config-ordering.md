# mgmt-vrf-config — Phase B 書込み順依存スキャンノート

対象テーブル: `MGMT_VRF_CONFIG`
Consumer: `vrfmgrd` (`sonic-swss/cfgmgr/vrfmgr.cpp`) / `hostcfgd` MgmtIfaceCfg (`sonic-host-services/scripts/hostcfgd`)
スキャン範囲: vrfmgr.cpp 全行精読、hostcfgd MgmtIfaceCfg.load()/update_mgmt_vrf() 精読

---

## 検出した順序依存・タイミング依存

### 1. vrfmgr: MGMT_VRF_CONFIG 有効化 → STATE_VRF_OBJECT_TABLE 登録 → 依存テーブル DEL が unblock

- `vrfmgr.cpp` の DEL 処理は `m_stateVrfTable.get(vrfName, temp)` で STATE_VRF_TABLE に "mgmt" エントリが存在するかを確認した後、さらに `isVrfObjExist(vrfName)`（STATE_VRF_OBJECT_TABLE を参照）で orchagent がオブジェクトを削除するまでループ待機する（`vrfmgr.cpp:331-335`）。
- **順序依存 (DEL)**: `MGMT_VRF_CONFIG` を無効化する場合、orchagent が STATE_VRF_OBJECT_TABLE から "mgmt" エントリを削除するまで vrfmgr は `delLink()` を実行しない（待機ループ）。orchagent の処理が完了しないと kernel VRF netdev が残存し続ける。
- **順序依存 (SET)**: `MGMT_VRF_CONFIG|vrf_global` に `mgmtVrfEnabled=true` を書き込む場合、`m_stateVrfTableMap` に "mgmt" エントリが既に存在する場合は SET がスキップされる（重複 SET 無効化、`vrfmgr.cpp:263-265`）。再度有効化したい場合は DEL → SET の順序が必要。
- evidence: `sonic-swss/cfgmgr/vrfmgr.cpp:263-265`, `vrfmgr.cpp:328-346`

### 2. vrfmgr: setLink("mgmt") は hostcfgd に委任 — kernel netdev 作成順序

- `setLink("mgmt")` は通常 VRF と異なり `ip link add` を実行しない。テーブル ID 6000 を内部 map に登録するのみ（`vrfmgr.cpp:176-183`）。
- **実際の kernel VRF netdev 作成は hostcfgd の `interfaces-config` restart が担う**（責務分離）。
- **順序依存**: `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled=true` を書き込んだ後、vrfmgr が `setLink` を完了しても、hostcfgd の `update_mgmt_vrf()` が `interfaces-config` を restart するまで実際の `mgmt` VRF netdev はカーネルに存在しない。つまり vrfmgr が APP_VRF_TABLE に "mgmt" を publish する時点でカーネル netdev が未作成という中間状態が発生しうる。
- evidence: `vrfmgr.cpp:176-183`, `hostcfgd:1660-1662`

### 3. hostcfgd: chrony stop → interfaces-config restart → chrony start の順序強制

- `update_mgmt_vrf()` (`hostcfgd:1659-1662`) は固定の順序でサービスを操作する:
  1. `systemctl stop chrony`
  2. `systemctl restart interfaces-config`
  3. `systemctl start chrony`
- **順序依存**: `interfaces-config` restart が `eth0` を `mgmt` VRF に所属させる際、chrony が先に停止していないと chrony が旧 VRF (デフォルト VRF) のソケットを保持したままになる。この順序は強制であり、設定変更で変更不可。
- **タイミング依存**: `systemctl restart interfaces-config` が完了するまで `systemctl start chrony` は待機される（`run_cmd` の呼び出しは同期的）。interfaces-config が失敗した場合、`subprocess.CalledProcessError` が発生してその後の `chrony start` はスキップされ、chrony が停止したままになる。
- evidence: `hostcfgd:1658-1666`

### 4. hostcfgd: NTP (chrony) は MGMT_VRF_CONFIG 有効化後でなければ mgmt VRF で起動しない

- chrony が `mgmt` VRF 内で bind するためには `interfaces-config` restart 後に chrony を `start` する必要がある（上記 #3 の順序）。
- **順序依存**: `NTP|global.vrf = "mgmt"` が設定されていても、`MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled = false` の状態では chrony は `mgmt` VRF で起動できない。YANG must 制約 (`sonic-ntp.yang`) により CLI レベルで reject されるが、CONFIG_DB を直接書き込む場合は bypass される。
- evidence: `hostcfgd:1660-1662`, sonic-ntp.yang must (NTP.vrf must ../../../MGMT_VRF_CONFIG/vrf_global/mgmtVrfEnabled = 'true')

### 5. hostcfgd: mgmtVrfEnabled 変化なし → silent drop（重複書き込み無視）

- `update_mgmt_vrf()` は `enabled == self.mgmt_vrf_enabled` の場合に即 return する（`hostcfgd:1653`）。
- **順序依存**: 同じ値（`true`→`true` または `false`→`false`）を再書き込みしても `interfaces-config` restart は発生しない。意図的に再起動させたい場合は一度異なる値に変更してから戻す必要がある。
- **silent drop**: エラーログなし。管理者が意図しない場合でも無音でスキップされる。
- evidence: `hostcfgd:1652-1654`

### 6. hostcfgd: mgmtVrfEnabled=true 時の eth0 デフォルトルート削除

- `update_mgmt_vrf()` は `enabled == 'true'` の場合に追加で `/proc/net/route` を確認し、`eth0` のデフォルトルート (metric 202) を削除する (`hostcfgd:1672-1693`)。
- **順序依存**: この処理は `interfaces-config` restart 後（上記 #3 の手順 2 完了後）に行われる。`interfaces-config` が eth0 を mgmt VRF に移動させた後にデフォルトルートが残存していれば削除する補足処理。
- **タイミング依存**: `/proc/net/route` に eth0 エントリが存在しない場合 (`CalledProcessError`) は WARNING ログのみで処理を中断する（`hostcfgd:1688-1691`）。eth0 ルートの残存はレースコンディションで変動するため、失敗しても致命的とはならない。
- evidence: `hostcfgd:1672-1693`

### 7. vrfmgr: non-warm-restart 時の起動順序 — 既存 mgmt VRF は保護される

- `VrfMgr` コンストラクタ（`vrfmgr.cpp:63-94`）は `ip -d link show type vrf` で既存カーネル VRF を列挙し、non-warm-restart の場合は `ip link del` で削除するが、`vrfName == "mgmt"` のみスキップして保護する。
- **順序依存 (起動時)**: `swss` コンテナ起動時に既存の `mgmt` VRF netdev が残存していても vrfmgr はそれを削除しない。CONFIG_DB から `mgmtVrfEnabled=true` の SET が届いた時点で `m_vrfTableMap` への登録のみ行い、netdev 作成は hostcfgd に委任する（double-create 防止）。
- evidence: `vrfmgr.cpp:73-79`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | SET 後 STATE_VRF_OBJECT_TABLE → DEL が unblock | DEL 待機ループ | orchagent 完了待ち（ポーリング） |
| 2 | vrfmgr setLink → hostcfgd interfaces-config → kernel mgmt netdev 作成 | 順次非同期 | 中間状態あり；APP_VRF_TABLE 登録と kernel netdev は別タイミング |
| 3 | stop chrony → restart interfaces-config → start chrony | 固定強制順序 | 途中失敗で chrony 停止のまま残存 |
| 4 | MGMT_VRF_CONFIG=true → NTP vrf=mgmt | 先行必須 | YANG reject (CLI)；DB 直書きは bypass |
| 5 | 同値再書き込み → silent drop | 即時スキップ | 意図的再起動には値変更が必要 |
| 6 | interfaces-config 完了 → eth0 デフォルトルート削除 | 順次 | 削除失敗は WARNING のみ；非致命的 |
| 7 | swss 起動時 mgmt VRF 保護 | 起動時スキップ | double-create 防止；hostcfgd が master |
