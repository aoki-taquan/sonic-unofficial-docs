# SSH_SERVER 失敗挙動マトリクス (Phase D)

生成日: 2026-05-18
対象ページ: `docs/reference/config-db/ssh-config.md`
調査コミット: sonic-host-services `c5bbbe8b07b96f078fa4b761316627404b01bd04`

---

## 調査対象コード箇所

- `sonic-host-services/scripts/hostcfgd` L1045-1165 (`SshServer` クラス)
- `sonic-host-services/scripts/hostcfgd` L1410-1478 (`PamLimitsCfg` クラス)
- `sonic-host-services/scripts/hostcfgd` L2297-2299 (`ssh_handler`)

---

## SET 処理の失敗経路

### SshServer.set_policies() 内の失敗

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `ports` フォーマットが int 型（文字列でない） | `handle_ports_set()` L1094 | LOG_ERR のみ・`set_policies()` が `return` → sshd_config 変更なし | `LOG_ERR: "port num value {} in wrong format"` | `hostcfgd:L1097` |
| `ports` 値が `1..65535` 範囲外 | `handle_ports_set()` L1096-1100 | LOG_ERR のみ・`set_policies()` が `return` → sshd_config 変更なし | `LOG_ERR: "Ssh port {} out of range"` | `hostcfgd:L1100` |
| `authentication_retries`/`login_timeout`/`inactivity_timeout`/`max_sessions` が SSH_INT_VALUES 範囲外 | `set_policies()` L1121-1124 | `continue` でそのフィールドをスキップ（他フィールドの適用は継続）| `LOG_ERR: "Ssh {} {} out of range"` | `hostcfgd:L1123-1124` |
| 未知のキーが ssh_policies に含まれる | `set_policies()` L1148 | `LOG_ERR` のみ・そのフィールドをスキップ（他フィールドは適用継続） | `LOG_ERR: "Failed to update sshd config file - wrong key {}"` | `hostcfgd:L1148` |
| `sshd -T -f <tmp>` バリデーション失敗（設定文法エラー） | `set_policies()` L1150-1159 | `os.remove(SSH_CONFG_TMP)` → sshd_config 変更なし（全フィールドロールバック） | `LOG_ERR: "Failed to update sshd config file - sshd -T returned {} with error {}"` | `hostcfgd:L1159` |
| `systemctl restart ssh` 失敗 | `run_cmd()` L126-131 | LOG_ERR のみ・sshd_config は更新済みだが sshd デーモンは旧設定で稼働 | `LOG_ERR: "Failed to update sshd config file"` | `hostcfgd:L1157` |

### PamLimitsCfg.render_conf_file() 内の失敗

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| jinja2 テンプレートレンダリング例外（テンプレートファイル不在・権限エラー等） | `render_conf_file()` L1475-1478 | 例外捕捉・PAM limits ファイル未更新 | `LOG_ERR: "modify pam_limits config file failed with exception: {}"` | `hostcfgd:L1476-1478` |
| PAM limits ファイル (`LIMITS_CONF`) への書き込み `IOError` | `render_conf_file()` L1468-1472 | 例外が上記 `except Exception` に捕捉・LOG_ERR | 同上 | `hostcfgd:L1469-1472` |

---

## 失敗時の全体的な挙動まとめ

1. **ports の範囲外 / フォーマット誤り** → `set_policies()` が即 `return`。`SSH_CONFG_TMP` はコピー済み状態で残る可能性あり（`return` 前に `remove` はしない）。ただし `os.rename` が実行されないため `sshd_config` 本番は変更されない。

2. **整数フィールドの範囲外 / 未知キー** → フィールド単位で `continue` / `LOG_ERR` してスキップ。他フィールドは適用継続。`sshd -T` ゲートは通過するため、部分的な設定変更が sshd_config に書き込まれる可能性がある。

3. **`sshd -T` バリデーション失敗** → `os.remove(SSH_CONFG_TMP)` で tmp ファイル削除・全フィールドロールバック。`sshd_config` 本番は変更なし。sshd は現行設定で継続稼働。

4. **`systemctl restart ssh` 失敗** → `sshd_config` は更新済み。sshd は次回の外部再起動 or 再起動要因発生まで旧設定で稼働する不整合状態となる。

5. **`PamLimitsCfg` 失敗（jinja2 エラー等）** → `/etc/security/limits.conf` 未更新。PAM の `max_sessions` 制限は古い値（またはシステムデフォルト）で継続する。`SshServer` 処理が成功している場合は sshd_config のみ更新済みで設定不整合となる。

---

## DEL 処理の挙動

`SSH_SERVER|POLICIES` エントリが DEL された場合、`ssh_handler` は `data = {}` で `policies_update` を呼ぶ。`self.policies = {}` となり `modify_conf_file()` は `len(ssh_policies) > 0` が False のため `set_policies()` を呼ばない。sshd_config は変更されない（最後に適用された設定が残る）。

---

## evidence

- `sonic-host-services/scripts/hostcfgd` L1094-1100 (`handle_ports_set`)
- `sonic-host-services/scripts/hostcfgd` L1110-1159 (`set_policies`)
- `sonic-host-services/scripts/hostcfgd` L1421-1478 (`PamLimitsCfg.update_config_file`, `render_conf_file`)
- `sonic-host-services/scripts/hostcfgd` L2297-2299 (`ssh_handler`)
