# MGMT_INTERFACE — Phase B 書込み順依存スキャンノート

対象テーブル: `MGMT_INTERFACE`
Consumer: `hostcfgd` (`MgmtIfaceCfg`) / `interfaces-config` (`interfaces.j2`)
スキャン範囲: `sonic-host-services/scripts/hostcfgd:1608-1700, 2345-2360, 2485`; `sonic-buildimage/files/image_config/interfaces/interfaces.j2` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. MGMT_VRF_CONFIG 先行推奨 — VRF フラグが interfaces.j2 で参照される

- `interfaces.j2:9,88` は `MGMT_VRF_CONFIG['vrf_global']['mgmtVrfEnabled']` を参照して `forced_mgmt_routes` のルーティングテーブルを `default` または mgmt VRF (table 6000) に切り替える。
- `MGMT_VRF_CONFIG` が CONFIG_DB に存在しない（または `mgmtVrfEnabled != "true"`）状態で `MGMT_INTERFACE` を書き込むと、`interfaces-config` はデフォルト VRF モードで生成される。
- 後から `MGMT_VRF_CONFIG` が追加されると `mgmt_vrf_handler` → `systemctl restart interfaces-config` → 再生成で最終的に一致する。
- evidence: `hostcfgd:2352-2358`, `interfaces.j2:9,88`

### 2. SYSLOG_SERVER 暗黙依存 — 未設定時に 10.20.6.16/32 がハードコード注入

- `interfaces.j2:101-113`: `SYSLOG_SERVER` が定義されている場合は各サーバ IP への policy routing rule を mgmt table に追加。
- `SYSLOG_SERVER` が**未設定**（または空）の場合は `10.20.6.16/32` がハードコードで mgmt VRF / default table に自動注入される。
- `SYSLOG_SERVER` を後から追加すると `mgmt_intf_handler` 経由の `interfaces-config` 再起動がトリガーされないため、ハードコードルートが一時的に残留する。
- **順序依存**: `SYSLOG_SERVER` を先に設定してから `MGMT_INTERFACE` を書くことで中間状態でのハードコードルート注入を回避できる。
- evidence: `interfaces.j2:101-130`

### 3. RADIUS src_intf 解決 — MGMT_INTERFACE 変更が RADIUS 送信元 IP を再決定

- `hostcfgd:2345-2351` (`mgmt_intf_handler`):
  1. `aaacfg.handle_radius_source_intf_ip_chg(mgmt_intf_name)` — MGMT_INTERFACE の IP が変わると RADIUS の src_intf に対応する IP を再解決
  2. `aaacfg.handle_radius_nas_ip_chg(mgmt_intf_name)` — RADIUS NAS IP を再解決
  3. `mgmtifacecfg.update_mgmt_iface()` → `systemctl restart interfaces-config`
- **順序依存**: `RADIUS_SERVER.src_intf=eth0` が設定済みの状態で `MGMT_INTERFACE` の IP を変更すると自動で RADIUS 送信元 IP も更新される。
- evidence: `hostcfgd:2345-2355`

### 4. interfaces-config の再生成トリガー — 変更検知時のみ

- `MgmtIfaceCfg.update_mgmt_iface()` は `data != self.iface_config_data.get(key)` のときのみ `systemctl restart interfaces-config` を呼ぶ（変更なしの場合はスキップ）。
- **タイミング依存**: 同一の CONFIG_DB 値を繰り返し書き込んでも `interfaces-config` の再起動は発生しない（冪等）。
- evidence: `hostcfgd:1630-1647`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `MGMT_VRF_CONFIG.mgmtVrfEnabled` → `MGMT_INTERFACE` | 推奨先行 | `mgmt_vrf_handler` 後追い自動復旧 |
| 2 | `SYSLOG_SERVER` → `MGMT_INTERFACE` | 推奨先行 | ハードコード `10.20.6.16/32` 注入を回避できる |
| 3 | `MGMT_INTERFACE` 変更 → RADIUS `src_intf` 解決 | `mgmt_intf_handler` が自動トリガー | RADIUS_SERVER が先に存在していること |
| 4 | 同一値の重複書き込み | 冪等（再起動なし） | — |
