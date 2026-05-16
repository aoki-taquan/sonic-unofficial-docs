# SSH_SERVER フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: CONFIG_DB `SSH_SERVER`

## 調査対象ファイル

- `sonic-host-services/scripts/hostcfgd` (SshServer クラス, PamLimitsCfg クラス)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang`
- `sonic-buildimage/src/sonic-yang-models/doc/Configuration.md` (SSH_SERVER 節)
- `sonic-net/SONiC/doc/ssh_config/ssh_config.md` (HLD)

---

## テーブル構造

```
SSH_SERVER|POLICIES
```

key は `POLICIES` 固定 (singleton)。

---

## フィールド別 暗黙デフォルト

### `authentication_retries`

**YANG default**: `6`

```yang
# sonic-ssh-server.yang:27
leaf authentication_retries {
    default 6;
    type uint32 { range 1..100; }
}
```

**hostcfgd バリデーション**: `SSH_MIN_VALUES["authentication_retries"] = 3`, `SSH_MAX_VALUES["authentication_retries"] = 100`  
(注: YANG range は 1..100, hostcfgd min は 3 — 差異あり。YANG が緩く hostcfgd が厳しい)

**コード由来デフォルト**: `SshServer.__init__` では `self.policies = {}` (空 dict)。  
DB に `POLICIES` キーが存在しない場合 `load()` が `self.policies = {}` をセット → `set_policies()` は呼ばれない → `/etc/ssh/sshd_config` の OS 値 (Debian デフォルト: `MaxAuthTries 6`) がそのまま有効。  
つまり CONFIG_DB に未設定でも実効値は `6` (OS sshd_config の Debian デフォルト) となる。

**sshd_config マッピング**: `MaxAuthTries`  
(hostcfgd:67: `SSH_CONFIG_NAMES["authentication_retries"] = "MaxAuthTries"`)

---

### `login_timeout`

**YANG default**: `120`

```yang
# sonic-ssh-server.yang:34
leaf login_timeout {
    default 120;
    type uint32 { range 1..600; }
}
```

**hostcfgd バリデーション**: min=1, max=600 (YANG と一致)

**コード由来デフォルト**: YANG/OS デフォルト `120` 秒。未設定時は OS の `LoginGraceTime 120` が有効。

**sshd_config マッピング**: `LoginGraceTime`  
(hostcfgd:68: `SSH_CONFIG_NAMES["login_timeout"] = "LoginGraceTime"`)

---

### `ports`

**YANG default**: `"22"`

```yang
# sonic-ssh-server.yang:41-48
leaf ports {
    default "22";
    type string {
        pattern '([1-9]|[1-9]\d{1,3}|[1-5]\d{4}|...)(,...)*';
    }
}
```

**hostcfgd バリデーション**: min=1, max=65535 (各ポート番号)

**コード由来デフォルト**: OS デフォルト `Port 22`。  
`policies_update()` で `data['ports'].split(',')` によってコンマ区切り文字列をリストに変換する。

**sshd_config マッピング**: `Port` (複数行に展開)  
(hostcfgd:69: `SSH_CONFIG_NAMES["ports"] = "Port"`)

---

### `inactivity_timeout`

**YANG default**: `15`

```yang
# sonic-ssh-server.yang:52
leaf inactivity_timeout {
    default 15;
    type uint32 { range 0..35000; }
}
```

**hostcfgd 変換**: 分 → 秒に変換して sshd_config に書く。

```python
# hostcfgd:1129-1131
if key == "inactivity_timeout":
    value = int(value) * 60
```

**コード由来デフォルト**: `15` 分 (= `900` 秒)。未設定時は OS の `ClientAliveInterval` 値。  
`PamLimitsCfg.read_max_sessions_config()` では `max_sessions` のみを扱い、`inactivity_timeout` は `SshServer.set_policies()` 経由で処理される。

**sshd_config マッピング**: `ClientAliveInterval` (単位: 秒)  
(hostcfgd:70: `SSH_CONFIG_NAMES["inactivity_timeout"] = "ClientAliveInterval"`)

---

### `max_sessions`

**YANG default**: `0` (0 = 無制限)

```yang
# sonic-ssh-server.yang:59
leaf max_sessions {
    default 0;
    type uint32 { range 0..100; }
}
```

**hostcfgd 実装**: `SshServer.set_policies()` では `max_sessions` を `continue` でスキップ (`SSH_CONFIG_NAMES` に含まれない)。

```python
# hostcfgd:1144-1146
elif key in ['max_sessions']:
    # Ignore, these parameters handled in other modules
    continue
```

`PamLimitsCfg` が PAM limits.conf.j2 経由で `/etc/security/limits.conf` に `* - maxsyslogins <N>` を書き込む。  
`PamLimitsCfg.read_max_sessions_config()` のデフォルト: `ssh_server_policies.get('max_sessions', 0)` → 0 → `self.max_sessions = None` (無制限)。

```python
# hostcfgd:1440-1441
max_sess_cfg = ssh_server_policies.get('max_sessions', 0)
self.max_sessions = max_sess_cfg if max_sess_cfg != 0 else None
```

**コード由来デフォルト**: `0` (None = 無制限)。pam_limits 経由 (sshd_config 非経由)。

---

### `permit_root_login`

**YANG default**: なし (default 文なし)

```yang
# sonic-ssh-server.yang:63-71
leaf permit_root_login {
    description "Specifies whether root can log in using ssh.";
    type enumeration {
        enum "yes";
        enum "prohibit-password";
        enum "forced-commands-only";
        enum "no";
    }
}
```

**Configuration.md 記載**: Default value: `"prohibit-password"` (但し YANG に default 文なし — ドキュメントのみ)

**コード由来デフォルト**: `SshServer` クラスに `permit_root_login` のフォールバック値はない。  
DB に未設定の場合、`set_policies()` は呼ばれるが `permit_root_login` キーが存在しない → OS sshd_config の `PermitRootLogin` 値がそのまま有効。  
Debian デフォルト: `prohibit-password`。

**sshd_config マッピング**: `PermitRootLogin`  
(hostcfgd:71: `SSH_CONFIG_NAMES["permit_root_login"] = "PermitRootLogin"`)

---

### `password_authentication`

**YANG default**: `true`

```yang
# sonic-ssh-server.yang:75
leaf password_authentication {
    type boolean;
    default true;
}
```

**hostcfgd 変換**:

```python
# hostcfgd:1132-1137
elif key == "password_authentication":
    if isinstance(value, str):
        value = "no" if value.lower() in [ "false" ] else "yes"
    else:
        value = "yes" if bool(value) else "no"
```

bool/string → "yes"/"no" に変換して sshd_config に書き込む。

**コード由来デフォルト**: YANG default `true` → "yes"。未設定時は OS の `PasswordAuthentication` 値。

**sshd_config マッピング**: `PasswordAuthentication`

---

### `ciphers`

**YANG default**: なし (leaf-list, default 文なし)

```yang
# sonic-ssh-server.yang:77-91
leaf-list ciphers {
    type enumeration { ... }
}
```

**hostcfgd 変換**:

```python
# hostcfgd:1138-1140
elif key in [ "ciphers", "kex_algorithms", "macs" ]:
    value = ",".join(value)
```

list → コンマ区切り文字列に変換。

**コード由来デフォルト**: なし。DB に未設定の場合、OS sshd_config の `Ciphers` 行がそのまま使われる (OpenSSH デフォルト暗号スイート)。

**sshd_config マッピング**: `Ciphers`

---

### `kex_algorithms`

**YANG default**: なし (leaf-list, default 文なし)

**コード由来デフォルト**: なし。OS sshd_config の `KexAlgorithms` がそのまま有効。

**sshd_config マッピング**: `KexAlgorithms`

---

### `macs`

**YANG default**: なし (leaf-list, default 文なし)

**コード由来デフォルト**: なし。OS sshd_config の `MACs` がそのまま有効。

**sshd_config マッピング**: `MACs`

---

## 要約表

| フィールド | YANG default | コード由来 fallback | hostcfgd MIN/MAX | sshd_config キー |
|-----------|-------------|-------------------|-----------------|-----------------|
| `authentication_retries` | `6` | なし (OS デフォルト 6) | 3 / 100 | `MaxAuthTries` |
| `login_timeout` | `120` | なし (OS デフォルト 120s) | 1 / 600 | `LoginGraceTime` |
| `ports` | `"22"` | なし (OS デフォルト 22) | 1 / 65535 | `Port` |
| `inactivity_timeout` | `15` | なし (OS デフォルト) | 0 / 35000 | `ClientAliveInterval` (分→秒変換) |
| `max_sessions` | `0` | `get('max_sessions', 0)` → None (無制限) | 0 / 100 | — (pam_limits 経由) |
| `permit_root_login` | なし | なし (OS 値: prohibit-password) | — | `PermitRootLogin` |
| `password_authentication` | `true` | なし (OS デフォルト yes) | — | `PasswordAuthentication` |
| `ciphers` | なし | なし (OS 暗号スイート) | — | `Ciphers` |
| `kex_algorithms` | なし | なし (OS kex スイート) | — | `KexAlgorithms` |
| `macs` | なし | なし (OS MAC スイート) | — | `MACs` |

---

## 特記事項

1. **DB 未設定時の挙動**: `SSH_SERVER|POLICIES` が CONFIG_DB に存在しない場合、`SshServer.load()` は `self.policies = {}` をセットし `set_policies()` を呼ばない。`/etc/ssh/sshd_config` は変更されず、OS インストール時の Debian デフォルト値が有効となる。

2. **authentication_retries の min 差異**: YANG range は `1..100` だが hostcfgd の `SSH_MIN_VALUES["authentication_retries"] = 3` が実効最小値。1〜2 は YANG を通過するが hostcfgd がログ ERR を出してスキップする。

3. **max_sessions のルーティング**: `max_sessions` は `SshServer.set_policies()` ではスキップされ、`PamLimitsCfg` が `/etc/security/limits.conf` の `maxsyslogins` に書き込む二重ルーティング構造。

4. **permit_root_login の YANG default 欠如**: HLD (ssh_config.md) では「デフォルトは OS 値 (Debian では prohibit-password)」と記載されているが、YANG に `default` 文がないため YANG レベルでは未設定時は OS のまま。

5. **inactivity_timeout の単位変換**: CONFIG_DB には分単位で格納。sshd_config には秒単位 (×60) で書かれる。

---

## 証拠リンク

- `sonic-host-services:c5bbbe8b` `scripts/hostcfgd:61-75` — SSH_INT/MIN/MAX/CONFIG_NAMES 定数
- `sonic-host-services:c5bbbe8b` `scripts/hostcfgd:1045-1161` — `SshServer` クラス全体
- `sonic-host-services:c5bbbe8b` `scripts/hostcfgd:1438-1441` — `PamLimitsCfg.read_max_sessions_config()`
- `sonic-buildimage:9ea932ec` `src/sonic-yang-models/yang-models/sonic-ssh-server.yang` — YANG defaults
- `sonic-net/SONiC:doc/ssh_config/ssh_config.md` — HLD (permit_root_login デフォルト言及)
