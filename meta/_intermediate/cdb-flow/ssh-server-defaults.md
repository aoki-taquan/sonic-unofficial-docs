# SSH_SERVER フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `SSH_SERVER|POLICIES`

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang`
- `sonic-host-services/scripts/hostcfgd` (SshServer クラス、L1045-L1175)
- `sonic-utilities/config/main.py` (L9987-10000、CLI 書き込み)
- `sonic-host-services/tests/hostcfgd/test_ssh_server_vectors.py` (テストベクタ)

---

## フィールド別 暗黙デフォルト

### `authentication_retries`

**YANG default**: `6`（`sonic-ssh-server.yang` L27）

```yang
leaf authentication_retries {
    default 6;
    type uint32 { range 1..100; }
}
```

hostcfgd は値を DB から読み、`SSH_MIN_VALUES["authentication_retries"] = 3` / `SSH_MAX_VALUES = 100` で範囲検証して `MaxAuthTries` に書く。  
DB エントリ不在時は `set_policies()` が呼ばれないため `sshd_config` のデフォルト（`MaxAuthTries 6`）がそのまま有効。

**コード由来暗黙デフォルト**: なし（YANG 宣言 `default 6` が権威）

---

### `login_timeout`

**YANG default**: `120`（`sonic-ssh-server.yang` L34）

```yang
leaf login_timeout {
    default 120;
    type uint32 { range 1..600; }
}
```

hostcfgd の `SSH_CONFIG_NAMES["login_timeout"] = "LoginGraceTime"` で sshd_config に書く。  
DB エントリ不在時は `sshd_config` の OpenSSH デフォルト（`LoginGraceTime 120`）が有効。

**コード由来暗黙デフォルト**: なし（YANG 宣言 `default 120` が権威）

---

### `ports`

**YANG default**: `"22"`（`sonic-ssh-server.yang` L41）

```yang
leaf ports {
    default "22";
    type string { pattern '...' }
}
```

hostcfgd の `set_policies()` で `data['ports'] = data['ports'].split(',')` → `handle_ports_set()` で `Port` 行を sshd_config に反映。  
DB エントリ不在時は sshd の組み込みデフォルト port 22 が有効。

**コード由来暗黙デフォルト**: なし（YANG 宣言 `default "22"` が権威）

---

### `inactivity_timeout`

**YANG default**: `15`（`sonic-ssh-server.yang` L51）

```yang
leaf inactivity_timeout {
    default 15;
    type uint32 { range 0..35000; }
}
```

hostcfgd L1129-1131: `inactivity_timeout` は分単位を秒に変換して `ClientAliveInterval` に書く：

```python
if key == "inactivity_timeout":
    value = int(value) * 60
```

**単位変換**: DB の 15（分）→ sshd_config の `ClientAliveInterval 900`（秒）。

`ClientAliveCountMax` の対応フィールドは CONFIG_DB にない（hostcfgd が書かないため OpenSSH デフォルト 3 が有効）。

**コード由来暗黙デフォルト**: `0` を指定すると `ClientAliveInterval 0`（不活動タイムアウト無効）。YANG `default 15` → 実効値 `900` 秒。

---

### `max_sessions`

**YANG default**: `0`（`sonic-ssh-server.yang` L57）

```yang
leaf max_sessions {
    default 0;
    type uint32 { range 0..100; }
}
```

hostcfgd L1144-1145: `max_sessions` は `SSH_CONFIG_NAMES` に存在せず、`set_policies()` で `continue` される（sshd_config に直接書かれない）。

代わりに `PamLimitsCfg`（hostcfgd L1418-1441）が `read_max_sessions_config()` で読み込み、`/etc/security/limits.d/` の PAM limits 設定を生成する。

```python
max_sess_cfg = ssh_server_policies.get('max_sessions', 0)
self.max_sessions = max_sess_cfg if max_sess_cfg != 0 else None
```

**コード由来暗黙デフォルト**: `0` は `None` に変換 → PAM limits に `max sessions` 設定を出力しない（無制限）。

---

### `password_authentication`

**YANG default**: `true`（`sonic-ssh-server.yang` L75）

```yang
leaf password_authentication {
    type boolean;
    default true;
}
```

hostcfgd L1132-1143: 文字列/bool を `yes`/`no` に変換して `PasswordAuthentication` に書く：

```python
elif key == "password_authentication":
    if isinstance(value, str):
        value = "no" if value.lower() in ["false"] else "yes"
    else:
        value = "yes" if bool(value) else "no"
```

**変換ロジック**: DB 値 `"false"` → `"no"`、それ以外 (`"true"`, 空など) → `"yes"`。

**コード由来暗黙デフォルト**: なし（YANG `default true` が権威。DB 不在時は sshd デフォルト `PasswordAuthentication yes` が有効）。

---

### `permit_root_login`

**YANG default**: なし（`sonic-ssh-server.yang` L63-71 — `default` 宣言なし）

```yang
leaf permit_root_login {
    type enumeration {
        enum "yes"; enum "prohibit-password";
        enum "forced-commands-only"; enum "no";
    }
}
```

hostcfgd は値をそのまま `PermitRootLogin` に書く。  
DB にフィールドが存在しない場合、`set_policies()` でキーが存在しないため書き込みがスキップされる。

**コード由来暗黙デフォルト**: フィールド不在時は sshd の OpenSSH デフォルト `prohibit-password` が有効。SONiC CONFIG_DB に書かれない限り制御されない。

---

### `ciphers`

**YANG default**: なし（leaf-list、デフォルト宣言なし）

hostcfgd L1139-1140:

```python
elif key in ["ciphers", "kex_algorithms", "macs"]:
    value = ",".join(value)
```

`Ciphers` に comma-delimited 文字列として書く。  
DB にフィールドが存在しない場合はスキップ → OpenSSH の組み込みデフォルト cipher suite が有効。

**コード由来暗黙デフォルト**: なし（DB 不在時は OpenSSH 組み込みデフォルト）。

---

### `kex_algorithms`

**YANG default**: なし（leaf-list）

同上。DB 不在時は `KexAlgorithms` が sshd_config に書かれず OpenSSH デフォルトが有効。

---

### `macs`

**YANG default**: なし（leaf-list）

同上。DB 不在時は `MACs` が sshd_config に書かれず OpenSSH デフォルトが有効。

---

## 要約表

| フィールド | YANG default | コード由来暗黙デフォルト | sshd_config パラメータ | 備考 |
|-----------|-------------|------------------------|----------------------|------|
| `authentication_retries` | `6` | なし | `MaxAuthTries` | |
| `login_timeout` | `120` (秒) | なし | `LoginGraceTime` | |
| `ports` | `"22"` | なし | `Port` | |
| `inactivity_timeout` | `15` (分) | 分→秒変換（×60） | `ClientAliveInterval` | 15分 → 900秒 |
| `max_sessions` | `0` | `0` → PAM 設定なし（無制限） | PAM limits | sshd_config 非反映 |
| `password_authentication` | `true` | `"false"` → `"no"`、その他 → `"yes"` | `PasswordAuthentication` | |
| `permit_root_login` | なし | DB 不在 → OpenSSH デフォルト `prohibit-password` | `PermitRootLogin` | |
| `ciphers` | なし | DB 不在 → OpenSSH デフォルト | `Ciphers` | |
| `kex_algorithms` | なし | DB 不在 → OpenSSH デフォルト | `KexAlgorithms` | |
| `macs` | なし | DB 不在 → OpenSSH デフォルト | `MACs` | |

---

## 注目すべき discrepancy

1. **`inactivity_timeout` 単位変換**: DB は分、sshd_config は秒。YANG の description は "minutes" だが、変換ロジックは hostcfgd 内部にのみ存在。
2. **`max_sessions` は sshd_config に反映されない**: `SSH_CONFIG_NAMES` に存在せず `continue` でスキップ。代わりに PAM limits (`/etc/security/limits.d/`) に書かれる。
3. **`permit_root_login` の YANG default なし**: OpenSSH のデフォルト (`prohibit-password`) が暗黙的に有効になる。

---

## 証拠リンク

- `sonic-ssh-server.yang` — YANG default 宣言
- `hostcfgd` L61-75 — `SSH_INT_VALUES`, `SSH_MIN_VALUES`, `SSH_MAX_VALUES`, `SSH_CONFIG_NAMES`
- `hostcfgd` L1045-1175 — `SshServer` クラス（`set_policies()`, `policies_update()`, `modify_conf_file()`）
- `hostcfgd` L1418-1441 — `PamLimitsCfg.read_max_sessions_config()`
- `test_ssh_server_vectors.py` L8-16 — `default_values` テストベクタ（全フィールドのデフォルト値確認）
