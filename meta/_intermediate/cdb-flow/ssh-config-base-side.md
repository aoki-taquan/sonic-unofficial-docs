# ssh-config-base — Phase F 副次 DB 書込 調査証跡

対象テーブル: `SSH_SERVER|POLICIES`
調査日: 2026-05-19
調査者: Claude (batch)

## 調査方針

`hostcfgd` の `SshServer` クラスおよび `PamLimitsCfg` クラスが CONFIG_DB `SSH_SERVER` テーブルへの変更を受けて
APPL_DB / STATE_DB / COUNTERS_DB 等の他 DB テーブルに書き込みを行うかを確認する。

## grep 結果

```
# SshServer クラス範囲 (L1020-1170) で DB 書込系関数を検索
grep -n "set(\|hset(\|Producer\|Notification\|publish\|APPL_DB\|STATE_DB" hostcfgd | awk 'NR>=1020 && NR<=1170'
→ 0 ヒット

# PamLimitsCfg クラス範囲 (L1410-1490) で同様検索
→ 0 ヒット
```

## 結論

`SshServer` および `PamLimitsCfg` は他 DB への書き込みを一切行わない。
副作用はすべて Linux ホスト OS のファイル書換に閉じる:

- `/etc/ssh/sshd_config` — `set_policies()` が一時ファイル経由で書換 + `systemctl restart ssh`
- `/etc/security/limits.conf` — `PamLimitsCfg.render_conf_file()` が Jinja2 テンプレート経由で書換
- `/etc/pam.d/pam-limits-conf` — 同上

STATE_DB への書込は `RestartWaiter` と `FipsCfg` のみが使用しており、SSH 処理パスには存在しない。
