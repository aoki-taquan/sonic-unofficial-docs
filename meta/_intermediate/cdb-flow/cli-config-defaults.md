# SERIAL_CONSOLE / SSH_SERVER — Phase A: コード由来の暗黙デフォルト調査

調査日: 2026-05-14
対象テーブル: CONFIG_DB `SERIAL_CONSOLE|POLICIES` / `SSH_SERVER|POLICIES`

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-serial-console.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang`
- `sonic-buildimage/files/image_config/cli_sessions/tmout-env.sh.j2`
- `sonic-buildimage/files/image_config/cli_sessions/serial-config.sh`
- `sonic-host-services/scripts/hostcfgd` (SerialConsoleCfg, SshServer クラス)
- `sonic-utilities/config/main.py` (serial_console / ssh グループ CLI)
- `sonic-utilities/show/main.py` (show serial_console / show ssh)

---

## SERIAL_CONSOLE テーブル フィールド別 暗黙デフォルト

### `inactivity_timeout`

**YANG default**: `15`（`sonic-serial-console.yang` L19、単位: 分）

```yang
leaf inactivity_timeout {
    description "Serial console inactivity timeout in minutes; 0 disables the timeout.";
    type int32 { range "0..35000"; }
    default 15;
}
```

- `tmout-env.sh.j2` が DB 値を読み込み、**分→秒変換** (×60) して `TMOUT` 環境変数に書き込む
  - DB `15` → `TMOUT=900`（秒）→ シリアルコンソール自動ログアウト
- DB エントリ不在時は Jinja2 テンプレートがデフォルト `inactivity_timeout_sec = 900`（15分相当）を使用
- `show serial_console` は DB エントリ不在時に `'900 <default>'` を表示 (show/main.py L2883) — 単位は秒表示だが DB 値は分単位

**コード由来暗黙デフォルト**: `tmout-env.sh.j2` がデフォルト 900 秒 (15 分) を直接コードに持つ。DB 値 `0` を指定すると `TMOUT=0`（タイムアウト無効）。

**discrepancy**: `show serial_console` のフォールバック表示 `'900 <default>'` は秒単位表示だが、DB に設定する値は分単位。ユーザーが `show` コマンドと `config` コマンドで単位が異なることに気づかない UI 乖離がある。

### `sysrq_capabilities`

**YANG default**: `disabled`（`sonic-serial-console.yang` L26、stypes:admin_mode）

```yang
leaf sysrq_capabilities {
    type stypes:admin_mode;
    description "Enable or disable Linux SysRq key capabilities on the serial console.";
    default disabled;
}
```

- `serial-config.sh` が `SERIAL_CONSOLE|POLICIES` の `sysrq_capabilities` を直接 redis CLI で読み取り、`enabled` なら `/proc/sys/kernel/sysrq` に `1` を書く
- `sysrq-sysctl.conf.j2` テンプレートも sysctl 永続設定として `/etc/sysctl.d/95-sysrq-sysctl.conf` に書き込む
- hostcfgd `SerialConsoleCfg.update_serial_console_cfg()` が変化を検知して `serial-config.service` を再起動
- DB 値 `enabled` → Linux SysRq 有効 (`/proc/sys/kernel/sysrq=1`)
- DB 値 `disabled` (デフォルト) → `/proc/sys/kernel/sysrq=0`

**コード由来暗黙デフォルト**: なし（YANG `default disabled` が権威）。

---

## SSH_SERVER テーブル フィールド別 暗黙デフォルト

### `authentication_retries`

**YANG default**: `6`（`sonic-ssh-server.yang` L27）

hostcfgd が `MaxAuthTries` に書き込む。DB エントリ不在時は OpenSSH デフォルト（`MaxAuthTries 6`）が有効。

**コード由来暗黙デフォルト**: なし（YANG `default 6` が権威）。

### `login_timeout`

**YANG default**: `120` 秒（`sonic-ssh-server.yang` L34）

hostcfgd が `LoginGraceTime` に書き込む。DB エントリ不在時は OpenSSH デフォルト（`LoginGraceTime 120`）が有効。

**コード由来暗黙デフォルト**: なし（YANG `default 120` が権威）。

### `ports`

**YANG default**: `"22"`（`sonic-ssh-server.yang` L41）

hostcfgd の `handle_ports_set()` が `Port` 行を sshd_config に書き込む。DB エントリ不在時は sshd デフォルト port 22 が有効。

**コード由来暗黙デフォルト**: なし（YANG `default "22"` が権威）。

### `inactivity_timeout`

**YANG default**: `15` 分（`sonic-ssh-server.yang` L51）

hostcfgd L1129-1131 が **分→秒変換** (×60) して `ClientAliveInterval` に書き込む:

```python
if key == "inactivity_timeout":
    value = int(value) * 60
```

- DB `15` → `ClientAliveInterval 900`（秒）
- DB `0` → `ClientAliveInterval 0`（タイムアウト無効）
- `ClientAliveCountMax` は CONFIG_DB にフィールドなし → OpenSSH デフォルト 3 が有効
- `show ssh` のフォールバック表示は `'900 <default>'`（show/main.py L2903）— SERIAL_CONSOLE と同じ表示単位乖離

**コード由来暗黙デフォルト**: 分→秒変換ロジック（×60）が hostcfgd 内部に存在。実効値 900 秒。

### `max_sessions`

**YANG default**: `0`（`sonic-ssh-server.yang` L57）

hostcfgd の `SSH_CONFIG_NAMES` マップに存在しないため `set_policies()` 内でスキップされる（sshd_config 非反映）。代わりに `PamLimitsCfg.read_max_sessions_config()` が PAM limits (`/etc/security/limits.d/`) を生成する:

```python
max_sess_cfg = ssh_server_policies.get('max_sessions', 0)
self.max_sessions = max_sess_cfg if max_sess_cfg != 0 else None
```

- DB `0` → `None` → PAM limits に設定なし（無制限）
- DB `>0` → `/etc/security/limits.d/` の `maxlogins` 設定に反映

**コード由来暗黙デフォルト**: `0` → PAM 設定なし（無制限）。sshd_config の `MaxSessions` には反映されない（隠れた実装詳細）。

### `password_authentication`

**YANG default**: `true`（`sonic-ssh-server.yang` L75）

hostcfgd L1132-1143 が文字列/bool を `yes`/`no` に変換して `PasswordAuthentication` に書き込む:

```python
elif key == "password_authentication":
    if isinstance(value, str):
        value = "no" if value.lower() in ["false"] else "yes"
    else:
        value = "yes" if bool(value) else "no"
```

- DB 値 `"false"` (小文字) → `"no"`
- DB 値 `"true"` / `"True"` / その他非 false 文字列 → `"yes"`
- DB 値なし → sshd デフォルト `PasswordAuthentication yes` が有効

**コード由来暗黙デフォルト**: なし。ただし文字列比較ロジックに注意（`"False"` は `"yes"` に変換される — 大文字小文字 bug）。

### `permit_root_login`

**YANG default**: なし（`sonic-ssh-server.yang` L63-71 — `default` 宣言なし）

DB にフィールドが存在しない場合、hostcfgd のキーループでスキップされ sshd_config に書かれない。OpenSSH のデフォルト `prohibit-password` が暗黙的に有効。

**コード由来暗黙デフォルト**: DB 不在 → OpenSSH デフォルト `prohibit-password` が実効値。

### `ciphers` / `kex_algorithms` / `macs`

**YANG default**: なし（leaf-list — デフォルト宣言なし）

hostcfgd L1139-1140 がカンマ区切り文字列に変換して `Ciphers` / `KexAlgorithms` / `MACs` に書き込む。DB 不在時は OpenSSH 組み込みデフォルトが有効（sshd_config に行が書かれない）。

---

## 要約表

### SERIAL_CONSOLE|POLICIES

| フィールド | YANG default | DB 単位 | 実効値 | コード由来暗黙デフォルト |
|-----------|-------------|---------|-------|------------------------|
| `inactivity_timeout` | `15` (分) | 分 | `TMOUT=900` 秒 | `tmout-env.sh.j2` がデフォルト 900 秒を内包 |
| `sysrq_capabilities` | `disabled` | enum | `/proc/sys/kernel/sysrq=0` | なし |

### SSH_SERVER|POLICIES

| フィールド | YANG default | sshd_config パラメータ | コード由来暗黙デフォルト |
|-----------|-------------|----------------------|------------------------|
| `authentication_retries` | `6` | `MaxAuthTries` | なし |
| `login_timeout` | `120` (秒) | `LoginGraceTime` | なし |
| `ports` | `"22"` | `Port` | なし |
| `inactivity_timeout` | `15` (分) | `ClientAliveInterval` (秒×60) | 分→秒変換ロジック |
| `max_sessions` | `0` | PAM limits のみ (`MaxSessions` 非反映) | `0` → PAM 設定なし |
| `password_authentication` | `true` | `PasswordAuthentication` | `"False"` → `"yes"` 変換 bug |
| `permit_root_login` | なし | `PermitRootLogin` | DB 不在 → OpenSSH デフォルト `prohibit-password` |
| `ciphers` | なし | `Ciphers` | DB 不在 → OpenSSH デフォルト |
| `kex_algorithms` | なし | `KexAlgorithms` | DB 不在 → OpenSSH デフォルト |
| `macs` | なし | `MACs` | DB 不在 → OpenSSH デフォルト |

---

## 注目すべき discrepancy

1. **`inactivity_timeout` 単位乖離**: SERIAL_CONSOLE / SSH_SERVER ともに DB 値は分単位、実効値は秒単位（×60変換）。`show` コマンドのフォールバック表示 `'900 <default>'` は秒単位で混乱を招く。
2. **`max_sessions` は sshd_config 非反映**: `SSH_CONFIG_NAMES` に登録されずスキップ。PAM limits に反映される（隠れた実装詳細）。
3. **`password_authentication` の `"False"`**: 大文字始まり `"False"` は `"yes"` に変換される（hostcfgd L1133: `value.lower() in ["false"]`）。これは bug ではなく Python の `.lower()` で解消されるが、`"FALSE"` も同様に正しく動作する。
4. **`permit_root_login` の YANG default なし**: OpenSSH デフォルト (`prohibit-password`) が暗黙的に有効になる。

---

## 証拠リンク

| 証拠 | ファイル | 行 |
|-----|---------|---|
| SERIAL_CONSOLE YANG default 15 (分) | sonic-serial-console.yang | L19 |
| SERIAL_CONSOLE YANG default disabled | sonic-serial-console.yang | L26 |
| tmout-env default 900 sec | tmout-env.sh.j2 | L2 |
| tmout-env 分→秒変換 | tmout-env.sh.j2 | L6 |
| serial-config.sh sysrq | serial-config.sh | L8-12 |
| hostcfgd SerialConsoleCfg | hostcfgd | L2013-2042 |
| hostcfgd serial_console_config_handler | hostcfgd | L2438-2440 |
| SSH_SERVER YANG defaults | sonic-ssh-server.yang | L27,34,41,51,57,75 |
| hostcfgd inactivity_timeout ×60 | hostcfgd | L1129-1131 |
| hostcfgd max_sessions PAM | hostcfgd | L1418-1441 |
| hostcfgd password_authentication 変換 | hostcfgd | L1132-1143 |
| show serial_console フォールバック | show/main.py | L2883-2884 |
| show ssh フォールバック | show/main.py | L2903-2904 |
