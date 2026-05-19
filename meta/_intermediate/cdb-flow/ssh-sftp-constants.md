# ssh-sftp — Phase E constants 調査ノート

## 対象ファイル

- `sonic-host-services/scripts/hostcfgd` L32-75

## 主要定数

### ファイルパス定数

| 定数 | 値 | ソース |
|------|----|--------|
| `SSH_CONFG` | `/etc/ssh/sshd_config` | `hostcfgd:32` |
| `SSH_CONFG_TMP` | `/etc/ssh/sshd_config.tmp` | `hostcfgd:33` |

### SSH_CONFIG_NAMES

`hostcfgd:67-75` に定義。CONFIG_DB キーから sshd_config ディレクティブへのマッピング。
`Subsystem` キーが存在しないことが SFTP 非制御の根拠。

### SSH_INT_VALUES / SSH_MIN_VALUES / SSH_MAX_VALUES

`hostcfgd:62-66` に定義。SSH フィールドの型と値域を定義する。
`max_sessions` は `SSH_CONFIG_NAMES` に含まれないため PAM limits 経由で適用される。

## 結論

SFTP サブシステムに直接関係する定数はファイルパス定数 (`SSH_CONFG`, `SSH_CONFG_TMP`) と
`SSH_CONFIG_NAMES` の不在 (`Subsystem` キーなし) の 2 点。min/max 定数は間接的に SFTP
セッション挙動（タイムアウト・ポート・最大セッション数）に影響する。
