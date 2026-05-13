# VLAN_INTERFACE テーブル — 例外条件・特殊挙動

## スキーマ検証

- **VRF 変更禁止**: `intfmgr` は既存 IF の VRF 変更を `isIntfChangeVrf()` で検出し `SWSS_LOG_ERROR("%s can not change to %s directly, skipping")` を出力してエントリを破棄する[^e1]。
- **`proxy_arp` / `grat_arp` / `mpls` 値**: 不正値の場合 `SWSS_LOG_ERROR("... state is invalid")` を出力し処理を中断[^e1]。

## ignore / skip

- **インタフェース未 ready**: `isIntfStateOk()` が false の場合 `m_toSync` に残留してリトライ待ち（"Interface is not ready, skipping"）[^e1]。
- **VRF 未 ready**: VRF が STATE_DB に存在しない場合も同様にリトライ待ち[^e1]。

## デフォルト補完

- `admin_status` 省略時: `"up"` が自動補完される[^e1]。
- YANG: `nat_zone` のデフォルトは `0`、`ipv6_use_link_local_only` のデフォルトは `disable`[^e2]。

[^e1]: `sonic-swss/cfgmgr/intfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
[^e2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vlan.yang>
