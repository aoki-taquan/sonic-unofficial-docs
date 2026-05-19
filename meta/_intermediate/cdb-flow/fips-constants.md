# fips — Phase E ハードコード定数 調査証跡

## 調査対象

- `sonic-host-services/scripts/hostcfgd` (FipsCfg クラス、L98-108, L1753-1846)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-fips.yang`

## 発見した定数

### ファイルパス定数 (hostcfgd:101-108)

```python
FIPS_CONFIG_FILE = '/etc/sonic/fips.json'
OPENSSL_FIPS_CONFIG_FILE = '/etc/fips/fips_enable'
DEFAULT_FIPS_RESTART_SERVICES = ['ssh', 'telemetry.service', 'restapi']
PROC_CMDLINE = '/proc/cmdline'
```

### カーネルパラメータ判定 (hostcfgd:1773)

```python
self.cur_enforced = 'sonic_fips=1' in kernel_cmdline or 'fips=1' in kernel_cmdline
```

### fips_enable ファイル値 (hostcfgd:1796-1809)

```python
cur_fips_enabled = '0'
# ...
expected_fips_enabled = '0'
if self.enable:
    expected_fips_enabled = '1'
if cur_fips_enabled != expected_fips_enabled:
    with open(OPENSSL_FIPS_CONFIG_FILE, 'w') as f:
        f.write(expected_fips_enabled)
```

### STATE_DB キー (hostcfgd:1792, 1821)

```python
self.state_db_conn.hset('FIPS_STATS|state', 'config_datetime', datetime.utcnow().isoformat())
timestamp = self.state_db_conn.hget('FIPS_STATS|state', 'config_datetime')
```

### YANG デフォルト (sonic-fips.yang)

```yang
leaf enable {
    type stypes:boolean_type;
    default "false";
}
leaf enforce {
    type stypes:boolean_type;
    default "false";
}
```

YANG の `default "false"` と hostcfgd `FipsCfg.__init__` の `self.enable = False` / `self.enforce = False` は一致している。
