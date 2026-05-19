# NTP_GLOBAL — Phase E: ハードコード定数スキャンノート

対象ページ: `docs/reference/config-db/ntp-global.md`
ソース参照: `meta/_intermediate/cdb-flow/ntp-constants.md`

---

## 検出したハードコード定数

### hostcfgd NtpCfg — chrony 操作

- `CHRONY_RESTART = ['systemctl', 'restart', 'chrony']` (`hostcfgd:1280`)
  — NTP 設定変更のたびに発行。SIGHUP による設定リロードは採用されない。

### ファイルパス (chrony-config.sh / chrony.conf.j2)

- `/etc/chrony/chrony.conf` — `chrony-config.sh:9`
- `/etc/chrony/chrony.keys` — `chrony-config.sh:10-11`
- `keyfile /etc/chrony/chrony.keys` — `chrony.conf.j2:127` でハードコード

### NTP UDP ポート (caclmgrd)

- ポート: **123** UDP — `caclmgrd:98`。CONFIG_DB に対応フィールドなし。
- `multi_asic_ns_to_host_fwd: False` — `caclmgrd:99`

### chrony ポーリングデフォルト (非管理)

- `minpoll` 6 (= 64 秒)、`maxpoll` 10 (= 1024 秒) — CONFIG_DB / YANG に対応フィールドなし

---

## evidence

- `sonic-host-services/scripts/hostcfgd` L1280
- `sonic-host-services/scripts/caclmgrd` L95-100
- `sonic-buildimage/files/image_config/chrony/chrony.conf.j2` L127
- `sonic-buildimage/files/image_config/chrony/chrony-config.sh` L9-11
