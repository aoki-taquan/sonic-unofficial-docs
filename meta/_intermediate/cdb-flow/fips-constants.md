# FIPS ハードコード定数スキャン (Phase E)

## スキャン対象

- `sonic-host-services/scripts/hostcfgd` (FipsCfg クラス、L100-108, L1753-1846)

## 抽出定数

### ファイルパス定数 (L100-108)

```
FIPS_CONFIG_FILE = '/etc/sonic/fips.json'          # L101
OPENSSL_FIPS_CONFIG_FILE = '/etc/fips/fips_enable'  # L102
DEFAULT_FIPS_RESTART_SERVICES = ['ssh', 'telemetry.service', 'restapi']  # L103
PROC_CMDLINE = '/proc/cmdline'                       # L108
```

### OpenSSL FIPS ファイル値リテラル (L1796-1809)

```python
cur_fips_enabled = '0'         # L1796
expected_fips_enabled = '0'    # L1801
expected_fips_enabled = '1'    # L1803 (enable=True の場合)
```

### kernel コマンドライン検出文字列 (L1773)

```python
self.cur_enforced = 'sonic_fips=1' in kernel_cmdline or 'fips=1' in kernel_cmdline
```

### STATE_DB キー / フィールドリテラル

```python
self.state_db_conn.hset('FIPS_STATS|state', 'config_datetime', ...)  # L1792
timestamp = self.state_db_conn.hget('FIPS_STATS|state', 'config_datetime')  # L1821
```

## 潜在的バグ

`hostcfgd:1769` で `RESTART_SERVICES_KEY` が参照されているが、同ファイル内に定義が見当たらない:

```python
self.restart_services = conf.get(RESTART_SERVICES_KEY, [])  # L1769
```

通常環境では `/etc/sonic/fips.json` が存在しないため `read_config()` の分岐に入らず、`DEFAULT_FIPS_RESTART_SERVICES` がそのまま使用される。ただし `fips.json` が存在する環境では `NameError` が発生する可能性がある。

## CONFIG_DB / YANG で変更不可な定数まとめ

| 定数 | 値 | 変更手段 |
|------|----|---------|
| `FIPS_CONFIG_FILE` | `/etc/sonic/fips.json` | なし（ハードコード） |
| `OPENSSL_FIPS_CONFIG_FILE` | `/etc/fips/fips_enable` | なし（ハードコード） |
| `DEFAULT_FIPS_RESTART_SERVICES` | `['ssh', 'telemetry.service', 'restapi']` | `/etc/sonic/fips.json` の `restart_services` キーで上書き可 |
| `PROC_CMDLINE` | `/proc/cmdline` | なし（ハードコード） |
| FIPS ファイル値 `"0"`/`"1"` | — | なし（ハードコード） |
| STATE_DB キー `FIPS_STATS\|state` | — | なし（ハードコード） |
