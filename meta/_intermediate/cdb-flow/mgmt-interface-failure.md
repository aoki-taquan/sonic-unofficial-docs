# mgmt-interface — Phase D failure-behavior 調査ノート

## 調査対象

- `sonic-swss/cfgmgr/intfmgr.cpp` — `IntfMgr::setIntfIp()`, `doIntfAddrTask()`, `doIntfGeneralTask()`
- `sonic-host-services/scripts/hostcfgd` — `MgmtIfaceCfg`, `mgmt_intf_handler`

## 主要発見

### IP 設定失敗パス (`setIntfIp` / `intfmgr.cpp:78-133`)

- IPv4 `ip address add/del` 失敗: `SWSS_LOG_ERROR` のみ。リトライなし。
- IPv6 `ip address add` 失敗 (1 回目): `sysctl net.ipv6.conf.<alias>.disable_ipv6=0` でフラグ再有効化してリトライ。
- IPv6 フラグ有効化失敗: 即時 `return`（IP 設定断念）。
- IPv6 リトライも失敗: `SWSS_LOG_ERROR` のみ。
- `doIntfAddrTask()` は全経路で `true` を返す（`intfmgr.cpp:1170`）→ エントリはキューから除去、**自動リトライなし**。

### インターフェース未 ready の場合のリトライ

- `isIntfStateOk(alias)` または `isIntfCreated(alias)` が false の場合: `doIntfAddrTask` は `false` を返しエントリをキューに保持。Consumer ポーリング (100ms) で再試行する。
- これが唯一の自動リトライ経路。

### VRF バインド失敗 (`ip link set <alias> master <vrf>`)

- `SWSS_LOG_ERROR` のみ。VRF バインド未完のまま続行。

### hostcfgd 経路の失敗

- `MgmtIfaceCfg.update_mgmt_iface()` → `systemctl restart interfaces-config` の発行自体は Popen 相当。
- `interfaces-config.sh` 内の `sonic-cfggen` 失敗や `systemctl restart networking` 失敗はログに出るが hostcfgd は例外をキャッチせず続行（Python subprocess check=False に準ずる挙動）。

## マーカー変換経緯

元ファイルでは `<!-- failure-behavior -->` / `<!-- /failure-behavior -->` マーカーが使われていたため、
Phase B-H スキャン (`<!-- failure -->`) で未対応と検出されていた。
本 Phase D 作業で標準マーカー `<!-- failure -->` / `<!-- /failure -->` に統一した。
