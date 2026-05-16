# SYSLOG_CONFIG_FEATURE フィールド暗黙デフォルト調査メモ

調査日: 2026-05-16
対象テーブル: CONFIG_DB `SYSLOG_CONFIG_FEATURE`

## 調査対象ファイル

- `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py` (`ContainerConfigDaemon` / `SyslogHandler`)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-syslog.yang` (YANG `default` 文の有無)

参照 SHA: `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd` (sonic-buildimage master)

なお、本テーブルの handler は従来 `hostcfgd` 経由とされていたが、master 実体は per-container 常駐の `containercfgd` (旧呼称: hostcfgd の syslog handler 機能を分離) が CONFIG_DB を購読し、自 container の rsyslog を直接再構成する。`sonic-host-services/scripts/` 配下に SYSLOG_CONFIG_FEATURE 直接ハンドラは無く、当該フィールドの暗黙デフォルトは全て containercfgd 側に集約されている。

---

## フィールド別 暗黙デフォルト

### `rate_limit_interval` (SYSLOG_CONFIG_FEATURE|<service>)

**コード由来デフォルト**: `'0'` (文字列)

```python
# containercfgd.py:143
new_interval = '0' if not data else data.get(SYSLOG_RATE_LIMIT_INTERVAL, '0')
```

判定経路:

- エントリ自体が無い (`data` が falsy) → `'0'`
- エントリは存在するが `rate_limit_interval` キーが無い → `data.get(..., '0')` で `'0'`
- いずれも `rsyslog.conf` の `$SystemLogRateLimitInterval` 0 設定に変換され、**rate-limit 機能オフ** として動作する

YANG 側 (`sonic-syslog.yang` L162-164) には `default` 文が無いため、`config load_minigraph` / `db_migrator` 経路ではフィールド未充填となり、上記コード分岐が事実上のデフォルト源になる。

### `rate_limit_burst` (SYSLOG_CONFIG_FEATURE|<service>)

**コード由来デフォルト**: `'0'` (文字列)

```python
# containercfgd.py:144
new_burst = '0' if not data else data.get(SYSLOG_RATE_LIMIT_BURST, '0')
```

判定経路は `rate_limit_interval` と同じ。

`interval=0`/`burst=0` の組合せは rsyslog 側で「インターバル 0 ＝ rate limit 機能オフ」の意味になるため、結果として burst 値は無視される。逆に interval > 0 で burst を省略すると `'0'` 適用 → 全ドロップとなるため、両フィールドはセットで設定すべき。

### `severity` の扱い

**本テーブルには `severity` フィールドは存在しない**。

ページ本文に明記の通り、SYSLOG_CONFIG_FEATURE は rate-limit 専用テーブル。`severity` は親テーブル `SYSLOG_CONFIG` 側に存在し、YANG default は `notice` (`sonic-syslog.yang` L186)。SYSLOG_CONFIG_FEATURE 経路では severity フォールバックは発生せず、各 container の rsyslog がそのままグローバル severity を継承する。

---

## 起動時フォールバック

`SyslogHandler.__init__` は起動時に `parse_syslog_conf()` を呼び、`/etc/rsyslog.conf` から現在値を読み取って `self.current_interval` / `self.current_burst` を初期化する。

```python
# containercfgd.py:163-184
def parse_syslog_conf(self):
    interval = '0'
    burst = '0'
    # ... regex match against rsyslog.conf
    return interval, burst
```

ファイルに該当行が見つからなかった場合も `'0'` を採用 (L169-170)。つまり「rsyslog.conf に rate-limit 行なし＋CONFIG_DB エントリなし」の状態でも、`current_interval=='0'` と `new_interval=='0'` が一致するため `update_syslog_config()` は最終的に「変更なし」と判定して `rsyslogd` 再起動をスキップする (L146-148 のキャッシュ比較)。

---

## 要約表

| フィールド | コード由来デフォルト | fallback 源 | YANG default |
|-----------|-------------------|------------|--------------|
| `rate_limit_interval` | `'0'` | `containercfgd.py:143` `data.get(..., '0')` | なし |
| `rate_limit_burst` | `'0'` | `containercfgd.py:144` `data.get(..., '0')` | なし |
| `severity` | — (フィールド不存在) | 親 `SYSLOG_CONFIG.severity` (default `notice`) を rsyslog レベルで継承 | n/a |

---

## 証拠リンク

- `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py` L21-22, L98-184 (`SyslogHandler` 全体) @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-syslog.yang` L162-217 (`SYSLOG_CONFIG_FEATURE_LIST`) @ 同 SHA
