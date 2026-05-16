# SSH_SERVER 書込み順依存 (Phase B)

生成日: 2026-05-15  
対象ページ: `docs/reference/config-db/ssh-server.md`  
調査コミット: sonic-host-services `c5bbbe8b07b96f078fa4b761316627404b01bd04`

---

## 1. 書込み経路（入り口）

| 経路 | 呼び出し | キー |
|------|---------|------|
| CLI `config ssh inactivity-timeout` | `config_db.mod_entry("SSH_SERVER", "POLICIES", {...})` | `POLICIES` |
| CLI `config ssh max-sessions` | `config_db.mod_entry("SSH_SERVER", "POLICIES", {...})` | `POLICIES` |
| 将来: REST/gNMI | 未実装（YANG 定義済みのため将来対応可能） | — |
| minigraph / ビルド時デフォルト | なし | — |

両 CLI コマンドとも `mod_entry` によるフィールド単位の部分更新。  
`POLICIES` キーに既存エントリがあれば merge、なければ新規作成。

---

## 2. 消費側の起動順序（ordering）

```
hostcfgd 起動
  │
  ├─ __init__
  │   ├─ PamLimitsCfg.__init__() + update_config_file()   # L2191-2192
  │   │   └─ get_table('SSH_SERVER') → read_max_sessions_config()
  │   │       ※ SSH_SERVER が存在しなくても KeyError を catch してスキップ
  │   └─ SshServer.__init__()                              # L2201
  │       └─ policies = {} のみ。ファイル書き込みなし
  │
  ├─ load(init_data)   # L2232 以降
  │   ├─ wait_till_system_init_done()  # systemd target 待機
  │   ├─ sshscfg.load(ssh_server)     # L2265
  │   │   ├─ policies_update('POLICIES', data, modify_conf=False)
  │   │   └─ modify_conf_file()
  │   │       └─ set_policies(ssh_policies)
  │   │           ├─ copy2(sshd_config → sshd_config.tmp)
  │   │           ├─ フィールドごとに modify_single_file_inplace
  │   │           ├─ sshd -T -f sshd_config.tmp  (検証)
  │   │           │   ├─ OK  → rename tmp→本番、systemctl restart ssh
  │   │           │   └─ NG  → remove tmp、ロールバック・ログのみ
  │   │           └─ ※ max_sessions は continue でスキップ
  │   └─ pamLimitsCfg.update_config_file()  # L2277（2 回目）
  │       └─ read_max_sessions_config() → render_conf_file()
  │           └─ limits.d/ に maxlogins 書き込み
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

1. `SshServer.load()` → `set_policies()` が sshd_config を更新 (`systemctl restart ssh`)
2. `pamLimitsCfg.update_config_file()` (2 回目) が `/etc/security/limits.d/` を更新

この 2 ステップは **常に順序固定**。  
`max_sessions` が sshd_config 側でスキップされているため、`PamLimitsCfg` の後実行が必須。  
逆順にすると PAM limits が古い `max_sessions` 値（初回 `__init__` 時点の値）で確定してしまう。

### 3-2. ランタイム更新の原子性欠如

`ssh_handler` は `sshscfg.policies_update()` と `pamLimitsCfg.update_config_file()` を**逐次呼び出し**（トランザクションなし）。  
sshd_config 更新成功 → PAM limits 更新失敗（例: ディスクフル）の場合、sshd_config と PAM limits の設定が不整合になる可能性がある。

### 3-3. sshd 検証ゲート

`sshd -T -f <tmp>` が非ゼロの場合は **sshd_config への書き込みをロールバック**し、以降の `systemctl restart ssh` もスキップ。  
この検証は `set_policies()` 末尾で全フィールド変換完了後に実行される。  
フィールド単位のロールバックは行われない（すべて適用 or すべて棄却）。

### 3-4. 起動時の `max_sessions` 二重読み込み

`PamLimitsCfg.update_config_file()` は `__init__` 時（L2192）と `load()` 末尾（L2277）の計 2 回実行される。  
初回時点で `SSH_SERVER` エントリが存在しなければ PAM limits はデフォルト状態のまま残る。  
`sshscfg.load()` 完了後の 2 回目呼び出しで確定値に更新される。  
→ 起動直後の短時間は `max_sessions` 設定が有効でない可能性がある。

### 3-5. `DEVICE_METADATA|localhost` との関係

`PamLimitsCfg.update_config_file()` は `SSH_SERVER|POLICIES` と `DEVICE_METADATA|localhost` の **両方** が存在しない場合に早期 return する（L1430）。  
`SSH_SERVER|POLICIES` のみ設定して `DEVICE_METADATA|localhost` が存在しない場合は PAM limits が更新されない。  
通常の SONiC デプロイでは `DEVICE_METADATA|localhost` は必ず存在するため実害はないが、ミニマル構成での注意点。

---

## 4. フィールドごとの書込み先と依存関係

| フィールド | 書込み先 | 依存関係 |
|-----------|---------|---------|
| `authentication_retries` | `/etc/ssh/sshd_config` (`MaxAuthTries`) | なし（即時反映、sshd 再起動） |
| `login_timeout` | `/etc/ssh/sshd_config` (`LoginGraceTime`) | なし |
| `ports` | `/etc/ssh/sshd_config` (`Port`) | `handle_ports_set()` 経由で行挿入位置に依存（既存 `Port` 行の位置） |
| `inactivity_timeout` | `/etc/ssh/sshd_config` (`ClientAliveInterval`) | 分→秒変換が必須（hostcfgd 内部変換） |
| `max_sessions` | `/etc/security/limits.d/` (PAM `maxlogins`) | `PamLimitsCfg.update_config_file()` が後続で実行される必要あり |
| `password_authentication` | `/etc/ssh/sshd_config` (`PasswordAuthentication`) | boolean→yes/no 変換が必須 |
| `permit_root_login` | `/etc/ssh/sshd_config` (`PermitRootLogin`) | なし |
| `ciphers` | `/etc/ssh/sshd_config` (`Ciphers`) | leaf-list → comma-delimited 変換 |
| `kex_algorithms` | `/etc/ssh/sshd_config` (`KexAlgorithms`) | leaf-list → comma-delimited 変換 |
| `macs` | `/etc/ssh/sshd_config` (`MACs`) | leaf-list → comma-delimited 変換 |

---

## 5. evidence

- `sonic-host-services/scripts/hostcfgd` L1045-1161 (`SshServer` クラス)
- `sonic-host-services/scripts/hostcfgd` L1410-1475 (`PamLimitsCfg` クラス)
- `sonic-host-services/scripts/hostcfgd` L2190-2277 (`HostConfigDaemon.load`)
- `sonic-host-services/scripts/hostcfgd` L2297-2299 (`ssh_handler`)
- `sonic-host-services/scripts/hostcfgd` L2478 (`subscribe('SSH_SERVER', ...)`)
- `sonic-utilities/config/main.py` L9979-10000 (CLI `config ssh`)
