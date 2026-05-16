# SSH_SERVER (ssh-config) 書込み順依存 (Phase B)

生成日: 2026-05-16  
対象ページ: `docs/reference/config-db/ssh-config.md`  
調査コミット: sonic-host-services `c5bbbe8b07b96f078fa4b761316627404b01bd04`

---

## 1. 書込み経路（入り口）

| 経路 | 呼び出し | キー |
|------|---------|------|
| CLI `config ssh-server set <field> <value>` | `config_db.mod_entry("SSH_SERVER", "POLICIES", {...})` | `POLICIES` |
| ビルド時デフォルト / minigraph | なし（`SSH_SERVER|POLICIES` のビルド時注入なし） | — |
| REST / gNMI | 未実装（YANG 定義済みのため将来対応可能） | — |

すべての CLI コマンドは `mod_entry` によるフィールド単位の部分更新。  
`POLICIES` キーに既存エントリがあれば merge、なければ新規作成。

---

## 2. 消費側の起動順序（ordering）

```
hostcfgd 起動
  │
  ├─ __init__
  │   ├─ PamLimitsCfg.__init__() + update_config_file()   # L2191-2192
  │   │   └─ get_table('SSH_SERVER') → read_max_sessions_config()
  │   │       ※ SSH_SERVER が存在しなければ早期 return
  │   └─ SshServer.__init__()                              # L2201
  │       └─ self.policies = {}  のみ。ファイル書き込みなし
  │
  ├─ load(init_data)   # L2232 以降
  │   ├─ wait_till_system_init_done()  # systemd target 待機
  │   ├─ sshscfg.load(ssh_server)     # L2265
  │   │   ├─ policies_update('POLICIES', data, modify_conf=False)
  │   │   └─ modify_conf_file()
  │   │       └─ set_policies(ssh_policies)
  │   │           ├─ copy2(sshd_config → sshd_config.tmp)
  │   │           ├─ フィールドごとに modify_single_file_inplace
  │   │           │   ※ ports は handle_ports_set() 経由
  │   │           │   ※ max_sessions は continue でスキップ
  │   │           ├─ sshd -T -f sshd_config.tmp  (バリデーション)
  │   │           │   ├─ OK  → rename tmp→本番、systemctl restart ssh
  │   │           │   └─ NG  → remove tmp、ロールバック・syslog ERR のみ
  │   └─ pamLimitsCfg.update_config_file()  # L2277（2 回目）
  │       └─ read_max_sessions_config() → render_conf_file()
  │           └─ /etc/security/limits.conf に maxsyslogins 書き込み
  │
  └─ register_callbacks()   # L2456
      └─ subscribe('SSH_SERVER', ssh_handler)  # L2478
          └─ ssh_handler(key, op, data)        # L2297-2299
              ├─ sshscfg.policies_update(key, data)   ← sshd_config 更新
              └─ pamLimitsCfg.update_config_file()    ← PAM limits 更新
```

---

## 3. 書込み順依存の要点

### 3-1. 起動時の二段階更新

1. `SshServer.load()` → `set_policies()` が `/etc/ssh/sshd_config` を更新 → `systemctl restart ssh`
2. `pamLimitsCfg.update_config_file()` (2 回目) が `/etc/security/limits.conf` を更新

この 2 ステップは**常に順序固定**（L2265 の後に L2277）。  
`max_sessions` は `set_policies()` 内で `continue` されるため、`PamLimitsCfg` の後実行が必須。

### 3-2. 起動直後の PAM limits 未確定ウィンドウ

`PamLimitsCfg.update_config_file()` は `__init__` 時（L2191）と `load()` 末尾（L2277）の計 2 回実行される。  
初回実行時に `SSH_SERVER` エントリが不在なら PAM limits はデフォルト状態のまま。  
`sshscfg.load()` 完了後の 2 回目で確定値に更新される。  
→ **起動直後の短時間は `max_sessions` 制限が有効でない可能性がある**。

### 3-3. ランタイム更新の原子性欠如

`ssh_handler` は `sshscfg.policies_update()` と `pamLimitsCfg.update_config_file()` を**逐次呼び出し**（トランザクションなし）。  
sshd_config 更新成功 → PAM limits 更新失敗（ディスクフル等）の場合、両設定が不整合になる可能性がある。

### 3-4. sshd 検証ゲート（全フィールド一括）

`sshd -T -f <tmp>` が非ゼロを返す場合は tmp ファイルを削除し `systemctl restart ssh` をスキップ。  
この検証は全フィールド変換完了後に実行されるため、**フィールド単位のロールバックはなく、すべて適用 or すべて棄却**。

### 3-5. `DEVICE_METADATA|localhost` との連動

`PamLimitsCfg.update_config_file()` は `SSH_SERVER|POLICIES` と `DEVICE_METADATA|localhost` の両エントリが存在しない場合に早期 return する（L1430）。  
ミニマル構成で `DEVICE_METADATA|localhost` が不在の場合、`max_sessions` が設定されていても PAM limits は更新されない。  
通常の SONiC デプロイでは `DEVICE_METADATA|localhost` は必ず存在するため実害なし。

---

## 4. フィールドごとの書込み先と処理順

| フィールド | 書込み先 | 処理パス | 備考 |
|-----------|---------|---------|------|
| `authentication_retries` | `/etc/ssh/sshd_config` (`MaxAuthTries`) | `set_policies()` → `modify_single_file_inplace` | 範囲チェック後、SSH_CONFIG_NAMES マッピング |
| `login_timeout` | `/etc/ssh/sshd_config` (`LoginGraceTime`) | 同上 | |
| `ports` | `/etc/ssh/sshd_config` (`Port`) | `handle_ports_set()` 経由 | 既存 `Port` 行削除 → 行挿入位置依存 |
| `inactivity_timeout` | `/etc/ssh/sshd_config` (`ClientAliveInterval`) | 同上 + 分→秒変換 | `value = int(value) * 60` |
| `max_sessions` | `/etc/security/limits.conf` (`maxsyslogins`) | `PamLimitsCfg.update_config_file()` | `set_policies()` 内で `continue` されスキップ |
| `password_authentication` | `/etc/ssh/sshd_config` (`PasswordAuthentication`) | boolean→yes/no 変換後に `modify_single_file_inplace` | |
| `permit_root_login` | `/etc/ssh/sshd_config` (`PermitRootLogin`) | `modify_single_file_inplace` | |
| `ciphers` | `/etc/ssh/sshd_config` (`Ciphers`) | leaf-list → comma-delimited 変換後 | |
| `kex_algorithms` | `/etc/ssh/sshd_config` (`KexAlgorithms`) | 同上 | |
| `macs` | `/etc/ssh/sshd_config` (`MACs`) | 同上 | |

---

## 5. evidence

- `sonic-host-services/scripts/hostcfgd` L67-76 (`SSH_CONFIG_NAMES` dict)
- `sonic-host-services/scripts/hostcfgd` L1110-1161 (`SshServer.set_policies`)
- `sonic-host-services/scripts/hostcfgd` L1410-1475 (`PamLimitsCfg.read_max_sessions_config`)
- `sonic-host-services/scripts/hostcfgd` L2191-2277 (`HostConfigDaemon.__init__` / `load`)
- `sonic-host-services/scripts/hostcfgd` L2297-2299 (`ssh_handler`)
- `sonic-host-services/scripts/hostcfgd` L2478 (`subscribe('SSH_SERVER', ssh_handler)`)
