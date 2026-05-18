# ssh-server — 副次 DB 書込 (side-effects) 調査メモ

## 調査対象

`docs/reference/config-db/ssh-server.md` Phase F 追加分。
`hostcfgd` の `SshServer` クラスおよび `PamLimitsCfg` クラスが `SSH_SERVER|POLICIES` を処理する際に、DB (APPL_DB / STATE_DB / COUNTERS_DB 等) への副次書込みがあるかを調査する。

## 調査方法

`sonic-host-services/scripts/hostcfgd` の `SshServer` クラス (L1045–1175) および `PamLimitsCfg` クラス (L1418–1441)、`ssh_handler` (L2297–2299)、`HostConfigDaemon.__init__` の SSH 関連部分 (L2191–2277) を対象に、以下のキーワードで grep:
- `set(`, `hset(`, `ProducerStateTable`, `NotificationProducer`, `state_db`, `STATE_DB`, `APPL_DB`, `COUNTERS_DB`, `ASIC_DB`, `FLEX_COUNTER_DB`

## 結果

### APPL_DB 書込

`SshServer` / `PamLimitsCfg` ともに `ProducerStateTable` / `Table.set()` / `hset()` の呼び出しなし。APPL_DB への書込み 0 件。

### STATE_DB 書込

`hostcfgd` の STATE_DB 参照は `FipsCfg` (`hostcfgd` L1759–1821) と `RestartWaiter` 用 (`hostcfgd` L2160–2162) のみ。`SshServer` クラスは `state_db_conn` を保持せず、STATE_DB への書込み 0 件。

### COUNTERS_DB / FLEX_COUNTER_DB / ASIC_DB 書込

`hostcfgd` 全体に COUNTERS_DB / FLEX_COUNTER_DB / ASIC_DB 参照なし。`SshServer` は SAI を経由しないため、これら DB への書込みは発生しない。

### その他 DB 書込

LOGLEVEL_DB / ERROR_DB への書込みも `SshServer` / `PamLimitsCfg` 内には存在しない。

## 結論

CONFIG_DB `SSH_SERVER|POLICIES` の変更に伴って `hostcfgd` が副次的に書き込む DB エントリは **存在しない**。副作用はすべて Linux ホスト OS の設定ファイル書き換え（`/etc/ssh/sshd_config`、`/etc/security/limits.d/`、`/etc/pam.d/pam-limits-conf`、`/etc/security/limits.conf`）および `systemctl restart ssh` の実行に閉じる。

## evidence

- `sonic-host-services/scripts/hostcfgd` L1045–1175: `SshServer` クラス全体 — ProducerStateTable / hset / STATE_DB 参照なし
- `sonic-host-services/scripts/hostcfgd` L1418–1441: `PamLimitsCfg` クラス全体 — ProducerStateTable / hset / STATE_DB 参照なし
- `sonic-host-services/scripts/hostcfgd` L2297–2299: `ssh_handler` — ファイル書換と systemctl 呼び出しのみ
