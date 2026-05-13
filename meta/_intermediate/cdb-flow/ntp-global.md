# CONFIG_DB 例外条件分析: NTP_GLOBAL (NTP|global)

## Consumer

- `hostcfgd` / `ntpcfgd` (`sonic-utilities`): `NTP` テーブル (key = `global`) を購読し、`/etc/chrony/chrony.conf` (または ntpd.conf) へ設定を反映。

## 例外条件

### 1. vrf = "mgmt" かつ mgmtVrfEnabled が false → YANG must 制約違反
- ソース: `sonic-ntp.yang` — `must "(current() != 'mgmt') or (/mvrf:sonic-mgmt_vrf/mvrf:MGMT_VRF_CONFIG/mvrf:vrf_global/mvrf:mgmtVrfEnabled = 'true')"` / `error-message "Must condition not satisfied. Try enable Management VRF."`。
- MGMT_VRF_CONFIG で `mgmtVrfEnabled = true` を先に設定しないと、`vrf = mgmt` は YANG バリデーションで拒否される。

### 2. vrf の許可値は "mgmt" または "default" のみ
- ソース: `sonic-ntp.yang` — `pattern "mgmt|default"`。それ以外の VRF 名は YANG バリデーションで拒否。

### 3. src_intf が存在しないインターフェースを参照 → YANG leafref 違反
- ソース: `sonic-ntp.yang` — `src_intf` は PORT / PORTCHANNEL / LOOPBACK_INTERFACE / MGMT_PORT への leafref または "eth0" パターン。登録されていないインターフェース名は YANG で拒否される。

### 4. authentication のデフォルト = "disabled"
- ソース: `sonic-ntp.yang` — `default disabled`。省略時は NTP 認証なしで動作。

### 5. dhcp のデフォルト = "enabled"
- ソース: `sonic-ntp.yang` — `default enabled`。DHCP 配布の NTP サーバが優先して使用される。

### 6. admin_state のデフォルト = "enabled"
- ソース: `sonic-ntp.yang` — `default enabled`。エントリが空でも NTP クライアントは動作する。
