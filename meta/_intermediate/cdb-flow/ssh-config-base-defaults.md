# SSH_CONFIG (SSH_SERVER) base フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `SSH_SERVER|POLICIES`
Phase A: コード由来デフォルト確定

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang`
- `sonic-host-services/scripts/hostcfgd` (SshServer クラス、PamLimitsCfg クラス)

---

## フィールド別 YANG default / コード由来暗黙デフォルト

### `authentication_retries`

**YANG default**: `6` (`sonic-ssh-server.yang` L27)

```yang
leaf authentication_retries {
    default 6;
    type uint32 { range 1..100; }
}
```

- hostcfgd 実効最小値: `SSH_MIN_VALUES["authentication_retries"] = 3`（YANG range 下限 1 より厳しい）
- 値 1〜2 は YANG バリデーション通過後、hostcfgd が ERR ログを出してスキップ
- DB エントリ不在時: `set_policies()` 非実行 → sshd_config の OS デフォルト `MaxAuthTries 6` が有効

**コード由来暗黙デフォルト**: なし（YANG 宣言 `default 6` が権威）

---

### `login_timeout`

**YANG default**: `120` (`sonic-ssh-server.yang` L34)

```yang
leaf login_timeout {
    default 120;
    type uint32 { range 1..600; }
}
```

- sshd_config パラメータ: `LoginGraceTime`（秒単位、YANG/sshd 両方で一致）
- DB エントリ不在時: `LoginGraceTime 120` (OpenSSH デフォルト) が有効

**コード由来暗黙デフォルト**: なし（YANG 宣言 `default 120` が権威）

---

### `ports`

**YANG default**: `"22"` (`sonic-ssh-server.yang` L41)

```yang
leaf ports {
    default "22";
    type string {
        pattern '([1-9]|[1-9]\d{1,3}|...)(...)*';
    }
}
```

- hostcfgd: `data['ports'].split(',')` でリスト化 → `handle_ports_set()` で `Port` 行を生成
- DB エントリ不在時: sshd 組み込みデフォルト `Port 22` が有効

**コード由来暗黙デフォルト**: なし（YANG 宣言 `default "22"` が権威）

---

### `inactivity_timeout`

**YANG default**: `15` (分) (`sonic-ssh-server.yang` L51)

```yang
leaf inactivity_timeout {
    default 15;
    type uint32 { range 0..35000; }
}
```

- hostcfgd が **分→秒変換** を実施 (`× 60`):

```python
# hostcfgd L1129-1131
if key == "inactivity_timeout":
    # translate min to sec.
    value = int(value) * 60
```

- sshd_config パラメータ: `ClientAliveInterval`（秒単位）
- YANG default 15 分 → sshd_config `ClientAliveInterval 900` 秒
- `0` を設定すると `ClientAliveInterval 0`（タイムアウト無効）

**コード由来暗黙デフォルト**: 分→秒変換（×60）。YANG `default 15` は分単位。

---

### `max_sessions`

**YANG default**: `0` (無制限) (`sonic-ssh-server.yang` L57)

```yang
leaf max_sessions {
    default 0;
    type uint32 { range 0..100; }
}
```

- `SSH_CONFIG_NAMES` に存在せず `set_policies()` 内で `continue`（sshd_config 非反映）
- `PamLimitsCfg.read_max_sessions_config()` が処理:

```python
# hostcfgd L1440-1441
max_sess_cfg = ssh_server_policies.get('max_sessions', 0)
self.max_sessions = max_sess_cfg if max_sess_cfg != 0 else None
```

- `0` → `None` → PAM limits 設定なし（無制限）
- `1..100` → `/etc/security/limits.d/` に `maxlogins` として書き込み

**コード由来暗黙デフォルト**: `get('max_sessions', 0)` → `0` → `None`（PAM limits 非出力 = 無制限）

---

### `password_authentication`

**YANG default**: `true` (`sonic-ssh-server.yang` L75)

```yang
leaf password_authentication {
    type boolean;
    default true;
}
```

- hostcfgd が bool/string → `"yes"`/`"no"` に変換:

```python
# hostcfgd L1132-1143
elif key == "password_authentication":
    if isinstance(value, str):
        value = "no" if value.lower() in ["false"] else "yes"
    else:
        value = "yes" if bool(value) else "no"
```

- `"false"` → `"no"`, その他(`"true"`, 空, bool True) → `"yes"`
- DB エントリ不在時: sshd デフォルト `PasswordAuthentication yes` が有効

**コード由来暗黙デフォルト**: なし（YANG `default true` が権威）

---

### `permit_root_login`

**YANG default**: なし (`sonic-ssh-server.yang` L63-71 — `default` 宣言なし)

```yang
leaf permit_root_login {
    type enumeration {
        enum "yes"; enum "prohibit-password";
        enum "forced-commands-only"; enum "no";
    }
}
```

- DB にフィールドが存在しない場合: `set_policies()` でキーが存在しないためスキップ
- sshd の組み込みデフォルト `prohibit-password`（OpenSSH 7.7+）が有効

**コード由来暗黙デフォルト**: なし（DB 不在時は sshd 組み込みデフォルト `prohibit-password`）

---

### `ciphers`

**YANG default**: なし (leaf-list, `sonic-ssh-server.yang` L77-91)

- hostcfgd: `",".join(value)` で comma-delimited 文字列に変換して `Ciphers` に書く
- DB 不在時: sshd_config に `Ciphers` 行なし → OpenSSH 組み込みデフォルト暗号スイートが有効

**コード由来暗黙デフォルト**: なし（DB 不在時は OpenSSH デフォルト cipher suite）

---

### `kex_algorithms`

**YANG default**: なし (leaf-list, `sonic-ssh-server.yang` L92-110)

- 同上。DB 不在時: `KexAlgorithms` 行なし → OpenSSH デフォルト kex スイートが有効

**コード由来暗黙デフォルト**: なし

---

### `macs`

**YANG default**: なし (leaf-list, `sonic-ssh-server.yang` L111-131)

- 同上。DB 不在時: `MACs` 行なし → OpenSSH デフォルト MAC スイートが有効

**コード由来暗黙デフォルト**: なし

---

## 要約表

| フィールド | YANG default | コード由来暗黙デフォルト | 実効 sshd_config 値 | 根拠 |
|-----------|-------------|------------------------|-------------------|------|
| `authentication_retries` | **6** | なし | `MaxAuthTries 6` | `sonic-ssh-server.yang` L27 |
| `login_timeout` | **120** | なし | `LoginGraceTime 120` | `sonic-ssh-server.yang` L34 |
| `ports` | **`"22"`** | なし | `Port 22` | `sonic-ssh-server.yang` L41 |
| `inactivity_timeout` | **15** (分) | 分→秒変換 (×60) → **900** 秒 | `ClientAliveInterval 900` | `sonic-ssh-server.yang` L51; `hostcfgd` L1129 |
| `max_sessions` | **0** | `0` → PAM 設定なし (`None`) | PAM limits 非出力 = 無制限 | `hostcfgd` L1440-1441 |
| `password_authentication` | **`true`** | `"false"`→`"no"`, その他→`"yes"` | `PasswordAuthentication yes` | `sonic-ssh-server.yang` L75; `hostcfgd` L1132 |
| `permit_root_login` | なし | DB 不在 → sshd 組み込みデフォルト | `prohibit-password` (OpenSSH 7.7+) | `sonic-ssh-server.yang` L63-71 |
| `ciphers` | なし | DB 不在 → OpenSSH デフォルト suite | Ciphers 行なし | `sonic-ssh-server.yang` L77-91 |
| `kex_algorithms` | なし | DB 不在 → OpenSSH デフォルト suite | KexAlgorithms 行なし | `sonic-ssh-server.yang` L92-110 |
| `macs` | なし | DB 不在 → OpenSSH デフォルト suite | MACs 行なし | `sonic-ssh-server.yang` L111-131 |

---

## 注目 discrepancy

1. **`authentication_retries` の min 差異**: YANG range は `1..100` だが hostcfgd の `SSH_MIN_VALUES` では `3` が実効最小値。値 1〜2 は YANG 通過後に hostcfgd がスキップ。
2. **`inactivity_timeout` 単位変換**: YANG description は "minutes" と明記するが変換ロジック (×60) は hostcfgd 実装にのみ存在。YANG 型 `uint32` には単位情報なし。
3. **`max_sessions` の経路**: `SSH_CONFIG_NAMES` に存在しないため sshd_config 非反映。PAM limits (`/etc/security/limits.d/`) 経由で制御。OpenSSH の `MaxSessions`（チャンネル数上限）とは概念が異なる。
4. **`permit_root_login` の YANG default 欠如**: HLD では "デフォルトは OS 値 (Debian では prohibit-password)" と記載しているが YANG に `default` 宣言がない。

---

## 証拠リンク

- `sonic-buildimage:9ea932ec` `src/sonic-yang-models/yang-models/sonic-ssh-server.yang` — YANG defaults
- `sonic-host-services:c5bbbe8b` `scripts/hostcfgd` L61-75 — `SSH_INT_VALUES`, `SSH_MIN_VALUES`, `SSH_CONFIG_NAMES`
- `sonic-host-services:c5bbbe8b` `scripts/hostcfgd` L1045-1175 — `SshServer` クラス (`set_policies()`)
- `sonic-host-services:c5bbbe8b` `scripts/hostcfgd` L1418-1441 — `PamLimitsCfg.read_max_sessions_config()`
