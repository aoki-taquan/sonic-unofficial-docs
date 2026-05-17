# LDAP_SERVER — Phase H プラットフォーム差 調査証跡

調査日: 2026-05-17
対象ソース:
- `sonic-net/sonic-host-services/scripts/hostcfgd`
- `sonic-net/sonic-host-services/scripts/ldap.py`
- `sonic-net/sonic-buildimage/files/build_templates/sonic_debian_extension.j2`
- `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-ldap.yang`

---

## 調査方針

LDAP_SERVER テーブルの処理において、以下の軸でプラットフォーム依存性を調査した:

1. multi-asic (`is_multi_npu`)
2. VOQ chassis / supervisor / line card
3. SmartSwitch / DPU
4. ASIC ベンダー固有 PAM モジュール
5. MGMT_VRF / MGMT_INTERFACE の影響
6. ビルド時 platform 条件分岐

---

## 1. multi-asic: `is_multi_npu` は AaaCfg に渡されない

`hostcfgd` 行 2182 で `self.is_multi_npu = device_info.is_multi_npu()` を取得する。
しかし行 2185 の `self.aaacfg = AaaCfg(self.config_db)` には渡されない。

`AaaCfg.__init__` (`hostcfgd:354-393`) は `ConfigDBConnector` 1 個のみを保持し、
`asic0..N` namespace への接続や iteration を一切しない。

`LDAP_SERVER` / `LDAP|global` テーブルは host CONFIG_DB のみに置かれ、
`asicN` namespace の CONFIG_DB には存在しない。

→ **multi-asic でも動作は同一。namespace 差分なし。**

## 2. VOQ chassis / supervisor / line card

`hostcfgd` ソース全体を `chassis`, `supervisor`, `linecard` で grep → ゼロヒット。

VOQ chassis の各 line card / supervisor は独立した host `hostcfgd` を持ち、
それぞれが自身の host CONFIG_DB の LDAP_SERVER テーブルを処理する。
chassis 全体での集中適用機構は存在しない。

→ **VOQ chassis でも動作は同一。オペレータが各 host に同一設定を流す運用前提。**

## 3. SmartSwitch / DPU

`AaaCfg` クラスに `has_per_dpu_scope` や `num_dpus` を参照する箇所なし。
SmartSwitch 固有の LDAP 処理分岐は存在しない。

→ **SmartSwitch / DPU でも動作は同一。**

## 4. ビルド時 platform 条件分岐

`sonic_debian_extension.j2` の LDAP 関連インストール部分 (行 304-315) を確認:

```
# Install pam-ldap, nss-ldap, ldap-utils
sudo LANG=C DEBIAN_FRONTEND=noninteractive chroot $FILESYSTEM_ROOT apt-get -y install \
    libnss-ldapd \
    libpam-ldapd \
    ldap-utils

# add networking.service dependancy to nslcd
sudo LANG=C chroot $FILESYSTEM_ROOT sed -i '/# Required-Start:/ s/$/ networking.service/' /etc/init.d/nslcd

# nslcd disable default
sudo LANG=C chroot $FILESYSTEM_ROOT systemctl stop nslcd.service
sudo LANG=C chroot $FILESYSTEM_ROOT systemctl mask nslcd.service
```

この部分に `{% if sonic_asic_platform == ... %}` 等の条件分岐は存在しない。
`libnss-ldapd` / `libpam-ldapd` / `nslcd` は全プラットフォーム共通でインストールされ、
デフォルトで masked 状態に設定される。

→ **ビルド時 platform 条件なし。**

## 5. MGMT_VRF / MGMT_INTERFACE の影響

`mgmt_vrf_handler` (`hostcfgd:2352-2353`) は `MgmtIfaceCfg.update_mgmt_vrf()` のみを呼ぶ。
`AaaCfg.modify_conf_file()` は呼ばれない。

LDAP_SERVER テーブルには RADIUS の `vrf` フィールドに相当するフィールドが存在しない
（YANG `sonic-system-ldap.yang` に `vrf` リーフなし）。
nslcd は VRF 対応の起動オプションを持たず、
VRF バインドはシステムレベル (`ip vrf exec`) での起動で対応するが、
hostcfgd はこれを自動化しない。

`mgmt_intf_handler` (`hostcfgd:2345-2350`) は RADIUS の NAS-IP 再解決を行うが、
LDAP に対する同等処理は存在しない。

→ **MGMT_VRF / MGMT_INTERFACE は LDAP_SERVER 処理に直接影響しない。**

## 6. PAM モジュール差異

`common-auth-sonic.j2` / `nslcd.conf.j2` テンプレートに `platform`, `asic`, `chassis`,
`namespace`, `vendor` キーワードなし（grep 確認済み）。

`nslcd.conf.j2` の固定値:
- `uid nslcd`, `gid nslcd` — 全プラットフォーム共通
- `tls_cacertfile /etc/ssl/certs/ca-certificates.crt` — 全プラットフォーム共通
- `nss_initgroups_ignoreusers ALLLOCAL` — 全プラットフォーム共通
- `nss_min_uid 1000` — 全プラットフォーム共通

→ **PAM / nslcd 設定にプラットフォーム差なし。**

## 7. IPv6 サーバアドレス処理

`ldap.py:47-53` で `ipaddress.ip_address(ip).version == 6` を判定し、
IPv6 アドレスを `[fdfd:...]` 形式でブラケット表記に変換する。
これはプラットフォーム差ではなくアドレスファミリに応じた処理であり、
全プラットフォームで同一ロジックが適用される。

---

## 結論

**プラットフォーム差なし**。

LDAP_SERVER / LDAP|global 処理は host 単位で適用され、
ASIC 種別・multi-asic / VOQ chassis 構成・SmartSwitch DPU・ベンダー固有 PAM モジュールに依存しない。
ビルド時も全プラットフォーム共通で libnss-ldapd / nslcd がインストールされる。
