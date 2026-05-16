# SSH_SERVER|POLICIES 書込み順依存 (Phase B)

生成日: 2026-05-16  
対象ページ: `docs/reference/config-db/ssh-config-base.md`  
調査コミット: sonic-host-services `c5bbbe8b07b96f078fa4b761316627404b01bd04`

---

## 1. 書込み経路（入り口）

| 経路 | 呼び出し | キー |
|------|---------|------|
| CLI `config ssh-server ...` | `config_db.mod_entry("SSH_SERVER", "POLICIES", {...})` | `POLICIES` |
| minigraph / ビルド時デフォルト | なし | — |
| REST/gNMI | 未実装（YANG 定義済みのため将来対応可能） | — |

`SSH_SERVER|POLICIES` は他 CONFIG_DB テーブルへの leafref・外部キー参照をもたないため、
**書き込み前に先行必須テーブルは存在しない**。

---

## 2. 消費側の起動順序（hostcfgd）

```
hostcfgd 起動
  │
  ├─ __init__
  │   ├─ PamLimitsCfg.__init__() + update_config_file()   # L2191-2192
  │   │   └─ get_table('SSH_SERVER') → read_max_sessions_config()
  │   │       ※ SSH_SERVER が存在しなくても KeyError を catch してスキップ
  │   └─ SshServer.__init__()                              # L2201
  │       └─ policies = {} のみ。sshd_config は変更しない
  │
  ├─ wait_till_system_init_done()  # systemd target 待機
  │
  ├─ sshscfg.load(ssh_server)   # L2265
  │   ├─ policies_update('POLICIES', data, modify_conf=False)
  │   └─ modify_conf_file()
  │       └─ set_policies(ssh_policies)
  │           ├─ copy2(sshd_config → sshd_config.tmp)
  │           ├─ フィールドごとに modify_single_file_inplace で行内置換/追記
  │           ├─ sshd -T -f sshd_config.tmp  (検証)
  │           │   ├─ OK  → rename tmp→本番, systemctl restart ssh
  │           │   └─ NG  → remove tmp (ロールバック), ERR ログのみ
  │           └─ ※ max_sessions は continue でスキップ（PAM 管理）
  │
  ├─ pamLimitsCfg.update_config_file()   # L2277 (2 回目)
  │   └─ read_max_sessions_config() → limits.d/ に maxlogins 書き込み
  │
  └─ register_callbacks()   # L2456
      └─ subscribe('SSH_SERVER', ssh_handler)  # L2478
          └─ ssh_handler(key, op, data)
              ├─ sshscfg.policies_update(key, data)   ← sshd_config 更新
              └─ pamLimitsCfg.update_config_file()    ← PAM limits 更新
```

---

## 3. 先行テーブル依存

| テーブル | 要否 | 理由 |
|---------|------|------|
| `DEVICE_METADATA\|localhost` | 任意（実質必須） | `PamLimitsCfg.update_config_file()` は `SSH_SERVER` と `DEVICE_METADATA` の両方が存在しない場合に早期 return（L1430）。`DEVICE_METADATA` がない場合 PAM limits が更新されない。通常の SONiC デプロイでは常に存在 |
| その他 CONFIG_DB テーブル | なし | `SshServer.set_policies()` は外部 OID 参照なし |

---

## 4. 更新フロー上の注意点

### sshd 検証ゲート

`sshd -T -f <tmp>` が非ゼロの場合は tmp を削除してロールバック。`systemctl restart ssh` はスキップ。
フィールド単位のロールバックは行われない（全フィールド適用 or 全棄却）。

### max_sessions の二段階更新

`max_sessions` は `SSH_CONFIG_NAMES` に含まれず `set_policies()` 内でスキップされる。
代わりに `PamLimitsCfg.update_config_file()` が後続で `limits.d/` に書き込む。
このため ssh_handler 内では sshd_config 更新 → PAM limits 更新の順序が固定されている。

### 起動直後の max_sessions 空白期間

`PamLimitsCfg.update_config_file()` は `__init__` 時（L2192）と `load()` 末尾（L2277）の 2 回実行される。
`sshscfg.load()` 完了前の初回呼び出し時点では `SSH_SERVER` が未処理のため、
初回のみ古い（またはデフォルト）値が PAM limits に書かれる。
2 回目呼び出しで確定値に上書きされる。

---

## 5. evidence

- `sonic-host-services/scripts/hostcfgd` L1045-1161 (`SshServer` クラス)
- `sonic-host-services/scripts/hostcfgd` L1410-1475 (`PamLimitsCfg` クラス)
- `sonic-host-services/scripts/hostcfgd` L2190-2277 (`HostConfigDaemon.load`)
- `sonic-host-services/scripts/hostcfgd` L2297-2299 (`ssh_handler`)
- `sonic-host-services/scripts/hostcfgd` L2478 (`subscribe('SSH_SERVER', ...)`)
