# LLDP_ENTRY_TABLE / LLDP_LOC_CHASSIS — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-buildimage/dockers/docker-lldp/lldpmgrd` (PORT_INIT_TIMEOUT, FAILED_CMD_TIMEOUT, RETRY_LIMIT, SELECT_TIMEOUT_MS)
- `sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2` (portidsubtype ifname, pause)
- `sonic-buildimage/dockers/docker-lldp/supervisord.conf.j2` (プロセス起動順序 priority)
- `sonic-snmpagent/src/sonic_ax_impl/mibs/ieee802_1ab.py` (time_mark=0 OID インデックス定数)

---

## 1. lldpmgrd タイムアウト / リトライ定数 (lldpmgrd L33-35, L291)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PORT_INIT_TIMEOUT` | `300` 秒 | PortInitDone / PortConfigDone を受信しないまま経過した場合に lldpd を強制 resume するタイムアウト | lldpmgrd L33 |
| `FAILED_CMD_TIMEOUT` | `6` 秒 | lldpcli コマンド失敗後の次回リトライまでのバックオフ最小間隔 | lldpmgrd L34 |
| `RETRY_LIMIT` | `5` 回 | lldpcli コマンド失敗時の最大リトライ回数。超過すると当該ポートの LLDP 設定を断念 | lldpmgrd L35 |
| `SELECT_TIMEOUT_MS` | `10000` ms (= 10 秒) | Redis Pub/Sub select() のポーリング間隔。CONFIG_DB / APPL_DB 変更を 10 秒以内に検出 | lldpmgrd L291 |

---

## 2. lldpd.conf.j2 のハードコード設定 (lldpd.conf.j2 L31-33)

| 設定 | 値 | 用途 | ソース |
|------|----|------|--------|
| `configure lldp portidsubtype ifname` | `ifname` (グローバル) | 全ポートのデフォルト portid を MAC アドレスではなくインタフェース名 (ifname) に固定。後続 lldpmgrd が `portidsubtype local` (alias) で上書きするまでの初期値 | lldpd.conf.j2 L31 |
| `pause` | — | 起動直後は LLDPDU 送出を停止。lldpmgrd が PortInitDone + PortConfigDone 受信後に `lldpcli resume` するまで LLDPDU は送出されない | lldpd.conf.j2 L33 |

---

## 3. supervisord.conf.j2 のプロセス起動優先度 (supervisord.conf.j2 L46-102)

| プログラム | priority | 起動待機条件 | 役割 |
|-----------|---------|------------|------|
| `rsyslogd` | 1 | (なし) | syslog デーモン |
| `start` | 2 | `rsyslogd:running` | 初期化スクリプト |
| `lldpd` | 3 | `start:exited` | open-lldp デーモン本体 |
| `waitfor_lldp_ready` | 3 | `lldpd:running` | lldpd UNIX ソケット待機 |
| `lldp-syncd` | 4 | `waitfor_lldp_ready:exited` | APPL_DB 書き込みデーモン |
| `lldpmgrd` | 5 | `lldp-syncd:running` | CONFIG_DB 変化検知 → lldpcli 制御 |

priority 値は supervisord の起動順序制御に使用。lldp-syncd は lldpd UNIX ソケットが ready になるまで開始しないため、`LLDP_ENTRY_TABLE` / `LLDP_LOC_CHASSIS` への書き込みは lldpd 起動完了後にのみ開始する。

---

## 4. lldpmgrd のポート処理ハードコード動作 (lldpmgrd L156, L144-145)

| 定数 / 動作 | 値 | 用途 | ソース |
|------------|-----|------|--------|
| `portidsubtype local` (lldpcli コマンド) | `"local"` | ポート up 時、lldpcli に `configure ports <port_name> lldp portidsubtype local <alias>` を発行。alias 未設定時はポート名を alias として使用 | lldpmgrd L156 |
| inband / recirc / backplane ポートをスキップ | `inband_prefix()` / `recirc_prefix()` / `backplane_prefix()` | これらプレフィックスで始まるポートは LLDP 設定対象外。`generate_pending_lldp_config_cmd_for_port()` が早期 return | lldpmgrd L144-145 |
| `hostname` 優先順位 | `chassis_hostname` > `hostname` | `DEVICE_METADATA|localhost` の `chassis_hostname` が存在すれば優先使用。不在時は `hostname` | lldpmgrd L253 |

---

## 5. sonic-snmpagent の OID インデックス定数 (ieee802_1ab.py L453)

| 定数 / 動作 | 値 | 用途 | ソース |
|------------|-----|------|--------|
| `time_mark` (SNMP OID インデックス要素) | `0` (ハードコード) | lldpRemTable の OID インデックスは `(timeMark, ifIndex, remIndex)` の 3 要素。Multi-ASIC 環境で同一 ifIndex が複数の timeMark で重複するのを避けるため、timeMark を常に `0` として OID を構築する。`lldp_rem_time_mark` フィールドの実際の値は OID 計算に使用されない | ieee802_1ab.py L453 |

---

## 特記事項

1. **`PORT_INIT_TIMEOUT` の強制 resume**: 300 秒 (5 分) を経過すると `port_init_done` / `port_config_done` が強制的に `True` に設定され、`lldpcli resume` が実行される。ポートが未初期化でも LLDPDU を送出し始めるため、不完全な TLV (alias 未設定 port ID 等) が対向ノードに伝達される可能性がある。
2. **`portidsubtype` の 2 段階設定**: `lldpd.conf.j2` でグローバルに `ifname` を設定し、その後 lldpmgrd がポートごとに `local` (alias) で上書きする。ポートが up になるまで lldpcli コマンドが実行されないため、リンクアップ前は `ifname` ベースの portid が LLDPDU に含まれる。
3. **FAILED_CMD_TIMEOUT と RETRY_LIMIT の組合せ**: 1 回失敗から 6 秒後に再試行、最大 5 回まで。6 回目の失敗 (= `RETRY_LIMIT` 超過) で当該ポートの LLDP 設定更新を断念し、ログ出力のみ。その後ポート up/down が再発生するまで再試行しない。

---

## 出典

- `sonic-net/sonic-buildimage/dockers/docker-lldp/lldpmgrd` L33-35, L144-145, L156, L253, L291
- `sonic-net/sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2` L31-33
- `sonic-net/sonic-buildimage/dockers/docker-lldp/supervisord.conf.j2` L46-102
- `sonic-net/sonic-snmpagent/src/sonic_ax_impl/mibs/ieee802_1ab.py` L453
