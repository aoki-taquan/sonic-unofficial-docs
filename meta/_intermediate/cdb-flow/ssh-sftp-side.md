# ssh-sftp — 副次 DB 書込 (side-effects) 調査メモ

## 調査対象

`docs/reference/config-db/ssh-sftp.md` Phase F 追加分。
`SSH_SFTP` テーブルは存在せず、SFTP サブシステムは OS テンプレート固定（CONFIG_DB 管理外）。
`SSH_SERVER|POLICIES` を処理する `SshServer` / `PamLimitsCfg` が Subsystem sftp に関して副次 DB 書込みを行うかを確認する。

## 調査方法

`sonic-host-services/scripts/hostcfgd` の `SshServer` クラス (L1045–1175) および `PamLimitsCfg` クラス (L1418–1441) を対象に、以下のキーワードで grep:
- `set(`, `hset(`, `ProducerStateTable`, `NotificationProducer`, `state_db`, `STATE_DB`, `APPL_DB`, `COUNTERS_DB`, `ASIC_DB`, `FLEX_COUNTER_DB`

## 結果

### APPL_DB 書込

`SshServer` / `PamLimitsCfg` ともに `ProducerStateTable` / `Table.set()` / `hset()` の呼び出しなし。APPL_DB への書込み 0 件。SFTP サブシステムそのものは `SSH_CONFIG_NAMES` 外のため `SshServer.set_policies()` の処理対象外。

### STATE_DB 書込

`hostcfgd` の STATE_DB 参照は `FipsCfg` (L1759–1821) と `RestartWaiter` 用 (L2160–2162) のみ。`SshServer` は `state_db_conn` を保持せず、STATE_DB への書込み 0 件。SFTP 状態を STATE_DB に通知する経路は存在しない。

### COUNTERS_DB / FLEX_COUNTER_DB / ASIC_DB 書込

`hostcfgd` 全体に COUNTERS_DB / FLEX_COUNTER_DB / ASIC_DB 参照なし。SFTP は SAI を経由しないため、これら DB への書込みは発生しない。

### その他 DB 書込

LOGLEVEL_DB / ERROR_DB への書込みも `SshServer` / `PamLimitsCfg` 内には存在しない。

## 結論

`SSH_SFTP` テーブルは存在せず、`Subsystem sftp` 行は OS テンプレートで常時固定。
CONFIG_DB 操作に起因する副次 DB 書込みは **一切存在しない**。
SFTP サブシステムの状態変化（有効・無効）が DB に反映される経路もない。
副作用は `/etc/ssh/sshd_config` テンプレートの静的存在にのみ依存し、CONFIG_DB・DB 系には一切波及しない。

## evidence

- `sonic-host-services/scripts/hostcfgd` L67–75: `SSH_CONFIG_NAMES` に `Subsystem` キーなし — `SshServer.set_policies()` は SFTP 行を処理対象外とする
- `sonic-host-services/scripts/hostcfgd` L1045–1175: `SshServer` クラス全体 — ProducerStateTable / hset / STATE_DB 参照なし
- `sonic-host-services/scripts/hostcfgd` L1418–1441: `PamLimitsCfg` クラス全体 — ProducerStateTable / hset / STATE_DB 参照なし
