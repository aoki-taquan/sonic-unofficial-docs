# RADIUS_SERVER — プラットフォーム差調査

Task F Phase H: `RADIUS_SERVER` テーブル適用時のプラットフォーム / 構成差を `hostcfgd` (`sonic-host-services`) から精読した結果。

## 結論

**プラットフォーム差なし** (ただし `NAS-IP-Address` 補完の軽微な依存あり — 詳細下記)。

## 根拠

### 1. multi-asic: `is_multi_npu` は AaaCfg に渡されない

- `hostcfgd` 行 2182: `self.is_multi_npu = device_info.is_multi_npu()` を取得
- 行 2185: `AaaCfg(self.config_db)` コンストラクタに `is_multi_npu` は渡されない
- `AaaCfg.__init__` (354–398) は `ConfigDBConnector` 1 個のみを保持し、`asic0..N` namespace への接続や iteration を一切しない
- RADIUS_SERVER テーブルは **host CONFIG_DB のみ** に存在。`asicN` namespace の CONFIG_DB には RADIUS 関連テーブルなし (YANG モジュール `sonic-system-radius` も host scope)
- multi-asic / VOQ chassis 環境でも RADIUS_SERVER の処理経路・結果は変わらない

### 2. MGMT_VRF_CONFIG は RADIUS_SERVER 処理に直接影響しない

- `MGMT_VRF_CONFIG` 変更 → `MgmtIfaceCfg.update_mgmt_vrf()` (`hostcfgd` 行 1645–1669)
- `update_mgmt_vrf()` が再起動するのは `chrony` / `interfaces-config` のみ。`AaaCfg.modify_conf_file()` は **呼ばれない**
- RADIUS_SERVER の `vrf` フィールド (`mgmt` / `default`) はオペレータが CLI `--use-mgmt-vrf` フラグで per-server に明示設定するもの
- `MGMT_VRF_CONFIG.mgmtVrfEnabled` から `vrf` フィールドへの自動注入機構は **存在しない**
- `MGMT_INTERFACE` 変更 → `handle_radius_source_intf_ip_chg()` 呼び出し (行 2348) — これは VRF 伝播ではなく `src_intf` IP 再解決のトリガー

### 3. PAM モジュールにプラットフォーム差なし

- `pam_radius_auth.so` は community SONiC 標準 Debian パッケージ
- `common-auth-sonic.j2` / `pam_radius_auth.conf.j2` を `platform|asic|chassis|namespace|vendor` で grep → 0 ヒット
- 条件分岐は `AAA.authentication.login` 文字列・`failthrough` / `debug` / `trace` / `statistics` ブール・サーバリストのみ
- ベンダー版 SONiC はスコープ外 (本リポジトリ: community master のみ)

### 4. VOQ chassis / line card

- 各 line card / supervisor は独立した host `hostcfgd` を保持
- それぞれが自身の host CONFIG_DB の RADIUS_SERVER テーブルを独立処理
- chassis 全体での集中 RADIUS 適用機構なし

### 5. 唯一の実質的プラットフォーム依存点: eth0 固定の NAS-IP 補完

- `nas_ip` が `RADIUS|global` 未設定の場合、`get_interface_ip("eth0")` で eth0 IP を自動補完
- 管理インタフェース名が `eth0` 以外 (例: `ma1`) のプラットフォームでは IP 解決失敗 → `NAS-IP-Address` が省略される
- これは YANG / CONFIG_DB スキーマ上の差異ではなく **ランタイム挙動の差** にとどまる
- 明示的に `RADIUS|global.nas_ip` を設定すれば回避可能

## まとめ

RADIUS_SERVER 経路は SAI を経由せず、ASIC SDK にも依存しない host-only な「Linux PAM / NSS 設定ファイル再生成」処理。multi-asic / VOQ chassis / T0–T3 等の物理構成・ASIC ベンダーに関わらず動作・適用範囲は同一。MGMT_VRF は RADIUS_SERVER の `vrf` フィールドに自動反映されず、オペレータが明示指定する設計。
