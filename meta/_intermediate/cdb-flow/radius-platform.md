# RADIUS (global) — プラットフォーム差調査

生成日: 2026-05-19

Task F Phase H: `RADIUS` テーブル適用時のプラットフォーム / 構成差を `hostcfgd`
(`sonic-host-services`) から精読した結果。

## 結論

**プラットフォーム差なし** (ただし `nas_ip` 自動補完時の管理 IF 名に軽微な依存あり)。

## 根拠

### 1. multi-asic: `is_multi_npu` は RadiusCfg に渡されない

- `hostcfgd` L2182: `self.is_multi_npu = device_info.is_multi_npu()` を取得
- `AaaCfg.__init__` (L354-398) は `ConfigDBConnector` 1 個のみを保持し、`asic0..N`
  namespace への接続 / iteration を一切しない
- `RADIUS` テーブルは **host CONFIG_DB のみ** に存在。`asicN` namespace の CONFIG_DB には
  RADIUS 関連テーブルなし (`sonic-system-radius` YANG も host scope)
- multi-asic / VOQ chassis 環境でも RADIUS 処理経路・結果は変わらない

### 2. VOQ chassis / line card

- 各 line card / supervisor は独立した host `hostcfgd` を保持
- それぞれが自身の host CONFIG_DB の `RADIUS` テーブルを独立処理
- chassis 全体での集中 RADIUS 適用機構なし

### 3. PAM モジュールにプラットフォーム差なし

- `pam_radius_auth.so` は community SONiC 標準 Debian パッケージ
- `common-auth-sonic.j2` / `pam_radius_auth.conf.j2` を `platform|asic|chassis|namespace|vendor`
  で grep → 0 ヒット
- 条件分岐は `AAA.authentication.login` 文字列・`failthrough` / `debug` / `trace` /
  `statistics` ブール・サーバリストのみ
- ベンダー版 SONiC はスコープ外

### 4. MGMT_VRF_CONFIG の影響なし

- `MGMT_VRF_CONFIG` 変更 → `MgmtIfaceCfg.update_mgmt_vrf()` (L1645-1669)
- `update_mgmt_vrf()` が再起動するのは `chrony` / `interfaces-config` のみ。`RadiusCfg.modify_conf_file()` は呼ばれない
- `RADIUS|global.vrf` フィールドはオペレータが CLI で明示設定。`MGMT_VRF_CONFIG` からの自動注入なし

### 5. 唯一の実質的プラットフォーム依存点: eth0 固定の nas_ip 補完

- `nas_ip` が `RADIUS|global` 未設定の場合、`get_interface_ip("eth0")` で eth0 IP を自動補完
- 管理インタフェース名が `eth0` 以外 (例: `ma1`) のプラットフォームでは IP 解決失敗
  → `NAS-IP-Address` が省略される
- 明示的に `RADIUS|global.nas_ip` を設定すれば回避可能
- YANG / CONFIG_DB スキーマ上の差異ではなくランタイム挙動の差にとどまる

## Evidence

- `sonic-host-services/scripts/hostcfgd` L92-98 (モジュール定数)
- `hostcfgd` L354-398 (`AaaCfg.__init__`)
- `hostcfgd` L2182-2185 (is_multi_npu 取得 / AaaCfg 初期化)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-radius.yang`
