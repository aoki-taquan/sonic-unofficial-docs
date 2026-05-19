# NTP_GLOBAL — Phase F: 副次 DB 書込・ファイル書込スキャンノート

対象ページ: `docs/reference/config-db/ntp-global.md`
ソース参照: `meta/_intermediate/cdb-flow/ntp-side-effects.md`

---

## APPL_DB / STATE_DB への副次書込

**0 件。** NTP_GLOBAL 変更は APPL_DB / STATE_DB への書込を行わない。

## ファイルシステム書込

| 書込先 | 操作 | 条件 |
|--------|------|------|
| `/etc/chrony/chrony.conf` | 上書き生成 | ブート時 + `systemctl restart chrony` ごと |
| `/etc/chrony/chrony.keys` | 上書き生成 + `chmod o-r` | 同上 |

CONFIG_DB 変更 → hostcfgd `NtpCfg` → `systemctl restart chrony` → `ExecStartPre: chrony-config.sh` → 両ファイル再生成。

NTP_GLOBAL フィールドの主な chrony.conf 反映:
- `authentication == 'enabled'` → `keyfile` ディレクティブ追加
- `src_intf` (非 mgmt) → `bindacqaddress <ip>` 追加
- `vrf == 'mgmt'` → `bindacqaddress` 抑止
- `admin_state` → **反映なし** (dead field)

## evidence

- `sonic-buildimage/files/image_config/chrony/chrony.conf.j2`
- `sonic-buildimage/files/image_config/chrony/chrony-config.sh` L9-11
- `sonic-host-services/scripts/hostcfgd` L1280,1325,1357,1398
