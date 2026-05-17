# SERIAL_CONSOLE / SSH_SERVER — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-host-services/scripts/hostcfgd`
  - ref: c5bbbe8b07b96f078fa4b761316627404b01bd04
- `sonic-buildimage/files/image_config/cli_sessions/tmout-env.sh.j2`

---

## 1. sshd_config ファイルパス定数 (hostcfgd L32-33)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `SSH_CONFG` | `/etc/ssh/sshd_config` | sshd 設定ファイル。`set_policies()` が直接書き換える | hostcfgd L32 |
| `SSH_CONFG_TMP` | `/etc/ssh/sshd_config.tmp` | `SSH_CONFG + ".tmp"` として動的生成。`sshd -T` 検証後に `os.rename()` で本ファイルに置換 | hostcfgd L33 |

---

## 2. PAM limits / Linux limits ファイルパス定数 (hostcfgd L81-84)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PAM_LIMITS_CONF_TEMPLATE` | `/usr/share/sonic/templates/pam_limits.j2` | `max_sessions > 0` 時に展開する PAM limits Jinja2 テンプレート | hostcfgd L81 |
| `LIMITS_CONF_TEMPLATE` | `/usr/share/sonic/templates/limits.conf.j2` | `/etc/security/limits.conf` 生成テンプレート | hostcfgd L82 |
| `PAM_LIMITS_CONF` | `/etc/pam.d/pam-limits-conf` | PAM limits 設定出力先。`PamLimitsCfg.render_conf_file()` が上書き | hostcfgd L83 |
| `LIMITS_CONF` | `/etc/security/limits.conf` | PAM limits の `limits.conf` 出力先 | hostcfgd L84 |

---

## 3. SSH フィールド検証定数 (hostcfgd L61-75)

### SSH_INT_VALUES — 整数型フィールド名リスト

```python
SSH_INT_VALUES = ["authentication_retries", "login_timeout", "inactivity_timeout", "max_sessions"]
```
hostcfgd L61。このリスト内のフィールドは `int()` 変換 + `SSH_MIN_VALUES` / `SSH_MAX_VALUES` 範囲チェックが行われる。

### SSH_MIN_VALUES — 最小値マップ

| フィールド | 最小値 | YANG range | ソース |
|-----------|--------|-----------|--------|
| `authentication_retries` | `3` | `1..100` (YANG) | hostcfgd L62 |
| `login_timeout` | `1` | `1..600` (YANG) | hostcfgd L62 |
| `ports` | `1` | N/A (YANG string) | hostcfgd L62 |
| `inactivity_timeout` | `0` | `0..35000` (YANG) | hostcfgd L63 |
| `max_sessions` | `0` | `0..100` (YANG) | hostcfgd L63 |

> **注意**: `authentication_retries` の hostcfgd コード最小値は **3** だが、YANG `range 1..100` は 1 以上を許容する。コードが YANG より厳しい下限を課している。

### SSH_MAX_VALUES — 最大値マップ

| フィールド | 最大値 | YANG range | ソース |
|-----------|--------|-----------|--------|
| `authentication_retries` | `100` | `1..100` (YANG) | hostcfgd L64 |
| `login_timeout` | `600` | `1..600` (YANG) | hostcfgd L64 |
| `ports` | `65535` | N/A (YANG string) | hostcfgd L65 |
| `inactivity_timeout` | `35000` | `0..35000` (YANG) | hostcfgd L65 |
| `max_sessions` | `100` | `0..100` (YANG) | hostcfgd L65 |

---

## 4. SSH_CONFIG_NAMES — sshd_config ディレクティブ名マッピング (hostcfgd L67-75)

| CONFIG_DB フィールド | sshd_config ディレクティブ | ソース |
|---------------------|--------------------------|--------|
| `authentication_retries` | `MaxAuthTries` | hostcfgd L68 |
| `login_timeout` | `LoginGraceTime` | hostcfgd L69 |
| `ports` | `Port` | hostcfgd L70 |
| `inactivity_timeout` | `ClientAliveInterval` | hostcfgd L71 |
| `permit_root_login` | `PermitRootLogin` | hostcfgd L72 |
| `password_authentication` | `PasswordAuthentication` | hostcfgd L73 |
| `ciphers` | `Ciphers` | hostcfgd L74 |
| `kex_algorithms` | `KexAlgorithms` | hostcfgd L74 |
| `macs` | `MACs` | hostcfgd L75 |

> `max_sessions` は `SSH_CONFIG_NAMES` に含まれない。`set_policies()` 内でこのマップを参照するため、`max_sessions` は sshd_config に書かれず PAM limits 経路にのみ反映される。

---

## 5. tmout-env.sh.j2 ハードコードデフォルト

| 値 | 用途 | ソース |
|----|------|--------|
| `900` (秒) | `SERIAL_CONSOLE|POLICIES.inactivity_timeout` が DB 不在または 0 未満のときのフォールバック値 (= 15分 = YANG default 15 × 60) | tmout-env.sh.j2 L2 |

---

## 6. 注目すべきコード-YANG 乖離

| 項目 | YANG | hostcfgd コード | 影響 |
|------|------|----------------|------|
| `authentication_retries` 最小値 | `range 1..100` | `SSH_MIN_VALUES["authentication_retries"] = 3` | YANG で 1 または 2 を設定しても hostcfgd がエラーログを出して適用を拒否する |
| `max_sessions` sshd 反映 | YANG leaf (uint32) | `SSH_CONFIG_NAMES` に含まれない | sshd_config の `MaxSessions` には反映されない (PAM limits のみ) |
