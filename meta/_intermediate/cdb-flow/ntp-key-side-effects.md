# NTP_KEY — 副次ファイル書込 (Phase F)

生成日: 2026-05-19

## 調査対象

- `sonic-host-services/scripts/hostcfgd` (`NtpCfg.ntp_srv_key_update`)
- `sonic-buildimage/files/image_config/chrony/chrony.keys.j2`
- `sonic-buildimage/files/image_config/chrony/chrony.conf.j2`
- `sonic-buildimage/files/image_config/chrony/chrony-config.sh`

## 結論サマリ

- APPL_DB / STATE_DB への副次書込: **0 件**
- 主副次ファイル書込: `/etc/chrony/chrony.keys`（NTP_KEY テーブル全件を sonic-cfggen で展開）
- 副次ファイル書込: `/etc/chrony/chrony.conf`（chrony restart のたびに再生成）
- `NTP_KEY.trusted` フィールドは `chrony.keys.j2` で参照されない（dead field 確認済）

## 証跡

### hostcfgd:1396-1402

```python
try:
    run_cmd(self.CHRONY_RESTART, True, True)
except Exception:
    syslog.syslog(syslog.LOG_ERR, f'NtpCfg: Failed to restart '
                                  'chrony service')
    return
```

`CHRONY_RESTART = ['systemctl', 'restart', 'chrony']` (`hostcfgd:1280`)。
DB への書込なし。

### chrony-config.sh:10-11

```bash
sonic-cfggen -d -t /usr/share/sonic/templates/chrony.keys.j2 > /etc/chrony/chrony.keys
chmod o-r /etc/chrony/chrony.keys
```

### chrony.keys.j2:8-17

```jinja2
{% set trusted_arr = [] -%}
{% for server in NTP_SERVER if NTP_SERVER[server].trusted == 'yes' and
                               NTP_SERVER[server].resolve_as -%}
    {% set _ = trusted_arr.append(NTP_SERVER[server].resolve_as) -%}
{% endfor -%}
{% set trusted_str = ' ' ~ trusted_arr|join(',') -%}
{% for keyid in NTP_KEY if NTP_KEY[keyid].type and NTP_KEY[keyid].value -%}
{{ keyid }} {{ NTP_KEY[keyid].type | upper }} {{ NTP_KEY[keyid].value | b64decode }}{{ trusted_str }}
{% endfor -%}
```

`NTP_KEY.trusted` は参照されず、dead field であることを確認。
