# SYSLOG_CONFIG — ハードコード定数調査 (Phase E)

調査日: 2026-05-18
対象ソース:
- `sonic-host-services/scripts/hostcfgd` (L1695-1743, L2410-2415)
- `sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2`
- `sonic-buildimage/files/image_config/rsyslog/rsyslog-container.conf.j2`

## rsyslog.conf.j2 内のハードコード定数

### テンプレートフォールバック値

| 定数/フォールバック | 値 | 用途 | ソース行 |
|---|---|---|---|
| `format` フォールバック | `'standard'` | `gconf.get('format', 'standard')` — SYSLOG_CONFIG|GLOBAL が欠落 or format 未設定時 | `rsyslog.conf.j2` L51 |
| `welf_firewall_name` フォールバック | `hostname` (DEVICE_METADATA 由来) | WELF 形式時の fw 名フォールバック | `rsyslog.conf.j2` L52 |
| `severity` フォールバック (サーバ個別) | `'*'` (全 severity) | per-server severity 未設定時、さらに SYSLOG_CONFIG も未設定時 | `rsyslog.conf.j2` L92 |
| `port` フォールバック (サーバ個別) | `514` | SYSLOG_SERVER 個別エントリの `port` 未設定時 | `rsyslog.conf.j2` L89 |
| `protocol` フォールバック (サーバ個別) | `'udp'` | SYSLOG_SERVER 個別エントリの `protocol` 未設定時 | `rsyslog.conf.j2` L90 |
| `vrf` フォールバック (サーバ個別) | `'default'` | SYSLOG_SERVER 個別エントリの `vrf` 未設定時 | `rsyslog.conf.j2` L91 |

### 受信ポート (ハードコード)

| 定数 | 値 | 用途 | ソース行 |
|---|---|---|---|
| UDP syslog 受信ポート | `514` | `input(type="imudp" ... port="514")` — ホスト rsyslog の UDP 受信ポート | `rsyslog.conf.j2` L31, L33 |
| RELP syslog 受信ポート | `2514` | `input(type="imrelp" ... port="2514")` — コンテナからの RELP 受信ポート | `rsyslog.conf.j2` L42, L44 |
| ファイルパーミッション | `0640` | `$FileCreateMode 0640` | `rsyslog.conf.j2` L136 |
| ディレクトリパーミッション | `0755` | `$DirCreateMode 0755` | `rsyslog.conf.j2` L137 |
| Umask | `0022` | `$Umask 0022` | `rsyslog.conf.j2` L138 |
| スプールディレクトリ | `/var/spool/rsyslog` | `$WorkDirectory /var/spool/rsyslog` | `rsyslog.conf.j2` L144 |
| インクルードディレクトリ | `/etc/rsyslog.d/*.conf` | `$IncludeConfig /etc/rsyslog.d/*.conf` | `rsyslog.conf.j2` L149 |
| 重複抑制 | `on` | `$RepeatedMsgReduction on` | `rsyslog.conf.j2` L154 |
| omfwd キュータイプ | `LinkedList` | `queue.type="LinkedList"` | `rsyslog.conf.j2` L124 |
| omfwd キューサイズ | `20000` | `queue.size="20000"` | `rsyslog.conf.j2` L124 |
| omfwd リトライ回数 | `60` | `action.resumeRetryCount="60"` | `rsyslog.conf.j2` L124 |

## rsyslog-container.conf.j2 内のハードコード定数

| 定数 | 値 | 用途 | ソース行 |
|---|---|---|---|
| コンテナ rate_limit_interval デフォルト | `'300'` 秒 | `rate_limit_interval\|default('300')` — SYSLOG_CONFIG_FEATURE 未設定時 | L27 |
| コンテナ rate_limit_burst デフォルト | `'20000'` 件 | `rate_limit_burst\|default('20000')` — SYSLOG_CONFIG_FEATURE 未設定時 | L27 |
| RELP 転送先ポート | `2514` | `port="2514"` — ホスト rsyslog の RELP 受信ポートへの転送 | L63 |
| RELP リトライ回数 | `60` | `action.resumeRetryCount="60"` | L63 |
| RELP キュータイプ | `LinkedList` | `queue.type="LinkedList"` | L63 |
| RELP キューサイズ | `20000` | `queue.size="20000"` | L63 |
| ファイルパーミッション | `0640` | `$FileCreateMode 0640` | L70 |
| スプールディレクトリ | `/var/spool/rsyslog` | `$WorkDirectory /var/spool/rsyslog` | L77 |

## hostcfgd 内のハードコード定数

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| systemd サービス名 (config) | `'rsyslog-config'` | `systemctl restart rsyslog-config` — 設定反映サービス | `hostcfgd` L1732-1734 |
| systemd サービス名 (daemon) | `'rsyslog'` | `systemctl reset-failed rsyslog` — デーモン名 | `hostcfgd` L1732-1733 |

## 補足

- `SYSLOG_CONFIG` フィールドの YANG default (`format=standard`, `severity=notice`) は YANG バリデーション層でのみ付与される。テンプレートはこれとは独立に独自フォールバックを持つ（二重防御）。
- コンテナ側の rate_limit デフォルト `300/20000` は `SYSLOG_CONFIG|GLOBAL` とは無関係（コンテナ rsyslog は SYSLOG_CONFIG_FEATURE のみ参照）。
