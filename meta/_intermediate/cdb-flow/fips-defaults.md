# FIPS フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `FIPS`

## 調査対象ファイル

- `sonic-host-services/scripts/hostcfgd` (`FipsCfg` クラス, L1753-1846)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-fips.yang`

---

## フィールド別 暗黙デフォルト

### `enable` (FIPS|global)

**コード由来デフォルト**: `False` (boolean)

```python
# hostcfgd:1759-1761  (FipsCfg.__init__)
def __init__(self, state_db_conn):
    self.enable = False
    self.enforce = False
```

`load()` 内で DB 値を取得する際にも `'false'` が fallback:

```python
# hostcfgd:1781-1782
self.enforce = is_true(common_config.get('enforce', 'false'))
self.enable  = self.enforce or is_true(common_config.get('enable', 'false'))
```

→ DB に `enable` キーが存在しない場合、`False` 扱い。`update_noneenforce_config()` (L1795-) で `expected_fips_enabled = '0'` となり `/etc/fips/fips_enable` に `0` が書かれる。

### `enforce` (FIPS|global)

**コード由来デフォルト**: `False` (boolean)

```python
# hostcfgd:1760
self.enforce = False
```

`load()` での fallback も `'false'`（上記 L1781）。`update_enforce_config()` (L1838-) で bootloader `set_fips(image, False)` 相当となり、grub kernel cmdline に `sonic_fips=1` / `fips=1` が付加されない。

### 派生属性: `enable = enforce or enable`

**重要な実装上のセマンティクス**: hostcfgd は `enforce=true` のときは `enable` の DB 値に関わらず `self.enable = True` を強制する (L1782):

```python
self.enable = self.enforce or is_true(common_config.get('enable', 'false'))
```

→ `enforce=true, enable=false` の組み合わせは実質 `enable=true` として動作する（value-behavior マトリクス末行「意味がない」と整合）。

### `restart_services`

**コード由来デフォルト**: `['ssh', 'telemetry.service', 'restapi']`

```python
# hostcfgd:103
DEFAULT_FIPS_RESTART_SERVICES = ['ssh', 'telemetry.service', 'restapi']

# hostcfgd:1762
self.restart_services = DEFAULT_FIPS_RESTART_SERVICES
```

`/etc/sonic/fips.json` が存在する場合は `read_config()` (L1765-1769) で `conf.get(RESTART_SERVICES_KEY, [])` に上書きされる（ファイル不在時はモジュール定数を使用）。これは CONFIG_DB フィールドではなく hostcfgd 内部の挙動だが、FIPS 切替時に再起動されるサービス一覧の出所として記録。

---

## 早期 return 条件

`load(data={})` (L1775-1779) で `data.get('global', {})` が空の場合は何もせず return:

```python
common_config = data.get('global', {})
if not common_config:
    syslog.syslog(syslog.LOG_INFO, f'FipsCfg: skipped the FIPS config, the FIPS setting is empty.')
    return
```

→ `FIPS|global` エントリが CONFIG_DB に**まったく存在しない**場合、`update()` は呼ばれず、`/etc/fips/fips_enable` は触られない。実効デフォルトは「OS の現状維持」（前回起動時の状態）。

---

## YANG default 文との比較

`sonic-fips.yang` には `enable` / `enforce` の `default` 文は明示されていない（boolean leaf のみ）。hostcfgd 側のコード由来 fallback (`'false'`) が実質的なデフォルトを決定する。

---

## まとめ

| フィールド | YANG default | コード由来 fallback | 実効デフォルト (未設定時) |
|-----------|--------------|---------------------|----------------------------|
| `enable`  | なし | `False` (`__init__`) / `'false'` (`load`) | `False` → `/etc/fips/fips_enable = 0` |
| `enforce` | なし | `False` (`__init__`) / `'false'` (`load`) | `False` → bootloader 未設定 |

特殊則: `enable = enforce or enable_db` のため `enforce=true` は `enable` を必ず引き上げる。
