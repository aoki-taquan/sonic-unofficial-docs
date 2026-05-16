# LLDP — Phase B 書込み順依存スキャンノート

対象テーブル: `LLDP|GLOBAL`, `LLDP_PORT|<ifname>`
Consumer: `lldpmgrd` (`sonic-buildimage/dockers/docker-lldp/lldpmgrd`)
スキャン範囲: lldpmgrd 全行精読、lldpd.conf.j2、supervisord.conf.j2、sonic-lldp.yang 参照

---

## 検出した順序依存・タイミング依存

### 1. PORT テーブルへの leafref（LLDP_PORT 書き込み先行条件）

- `sonic-lldp.yang` L107-110: `LLDP_PORT_LIST.ifname` は `sonic-port/PORT/PORT_LIST/name` への leafref。
- mgmt-framework (sonic-mgmt-common) 経由で YANG バリデーションが有効な場合、対応する `PORT|<ifname>` エントリが CONFIG_DB に存在しないと `LLDP_PORT|<ifname>` への SET が leafref 違反で拒否される。
- 直接 `sonic-db-cli` / `redis-cli` で書き込む場合はバリデーションをスキップできるが、その後 `lldpmgrd` が `lldpcli configure ports <ifname>` を実行した際に linux netdev が存在しないためコマンドが失敗する。
- 順序依存: `PORT|<ifname>` が先に存在すること。
- evidence: `sonic-lldp.yang:107-110`

### 2. APP_DB PORT テーブルの PortInitDone / PortConfigDone 待機

- `lldpmgrd.run()` L296-342: `PortInitDone` および `PortConfigDone` イベントを APPL_DB の PORT テーブルから受信するまで `lldpcli resume` を発行しない。
- 起動直後は lldpd が `pause` 状態（lldpd.conf.j2 末尾の `pause` ディレクティブ）。`PortInitDone` + `PortConfigDone` を両方受信した後（または PORT_INIT_TIMEOUT=300 秒タイムアウト後）に `lldpcli resume` を発行して LLDP パケット送信を開始する。
- **LLDP_PORT のポート設定は resume 前でも pending_cmds に積まれるが、linux netdev が up になるまで実際の `lldpcli configure ports` はスキップされる**。
- 順序依存: `PortInitDone` / `PortConfigDone` が APPL_DB に届く前は LLDP PDU 送出なし。
- evidence: `lldpmgrd:259-273`, `lldpmgrd:296-342`, `lldpd.conf.j2:末尾`

### 3. netdev oper_status=up が LLDP_PORT 適用の先行条件

- `lldpmgrd.process_pending_cmds()` L176: `is_port_up(port_name)` が False の場合、ポートの `lldpcli configure ports` コマンドをスキップしてリトライ待機する。
- `is_port_up()` は STATE_DB の `PORT_TABLE|<ifname>.netdev_oper_status` を参照する。
- ポートが物理的にリンクアップするまで `LLDP_PORT` の設定（alias / portid subtype）は lldpd に反映されない。
- 順序依存: `STATE_DB: PORT_TABLE|<ifname>.netdev_oper_status = "up"` が LLDP_PORT 設定反映の前提。
- evidence: `lldpmgrd:116-134`, `lldpmgrd:168-204`

### 4. DEVICE_METADATA が lldpd 起動時ホスト名の先行条件

- `lldpd.conf.j2` L末尾: 起動時に `configure system hostname {{ DEVICE_METADATA['localhost']['hostname'] }}` を設定する。
- `lldpmgrd` は `DEVICE_METADATA` テーブルの変更を CONFIG_DB から購読し (`lldp_process_device_table_event`)、`hostname` / `chassis_hostname` の変化を `lldpcli configure system hostname` に反映する。
- `LLDP|GLOBAL` の `system_name` フィールドはこの hostname とは独立して管理される（CLI `config lldp global sysdescr` 等から書き込まれる）。
- 順序依存: 起動時の hostname は `DEVICE_METADATA|localhost.hostname` が先に書き込まれている必要あり。ランタイム変更は後追いで自動反映。
- evidence: `lldpmgrd:247-256`, `lldpd.conf.j2:22`

### 5. MGMT_INTERFACE が Management Address TLV の先行条件

- `lldpd.conf.j2` L4-14: 起動時に `MGMT_INTERFACE` テーブルから IPv4/IPv6 アドレスを取り出し `configure system ip management pattern` を設定する。
- `lldpmgrd` は `MGMT_INTERFACE` テーブルの変更も購読し (`lldp_process_mgmt_info_change`)、アドレス変化を lldpd にリアルタイム反映する。
- `supp_mgmt_address_tlv=false`（デフォルト）の場合、Management Address TLV が送信されるが、`MGMT_INTERFACE` が存在しない場合は Management Address が設定されないため TLV に管理アドレスが含まれない。
- 順序依存: Management Address TLV を正しく送出したい場合、`MGMT_INTERFACE|<ifname>|<prefix>` が先に書き込まれている必要あり。
- evidence: `lldpmgrd:206-245`, `lldpd.conf.j2:4-14`

### 6. RETRY_LIMIT による失敗ポートの自動放棄

- `lldpmgrd.process_pending_cmds()` L193-200: `lldpcli` コマンドが RETRY_LIMIT=5 回失敗した場合、ポートを pending_cmds から除去してリトライを停止する。
- 失敗後に `PORT|<ifname>` の状態が改善されても pending_cmds からは除去済みのため、再度 APPL_DB から PORT イベントが来るまで再設定されない。
- 順序依存: 誤設定（存在しない port alias 等）によるコマンド失敗 5 回でポート設定が永続的にスキップされる点に注意。
- evidence: `lldpmgrd:192-200`

### 7. lldpmgrd / lldp-syncd / lldpd 起動順序（supervisord 依存）

- `supervisord.conf.j2` の priority / dependent_startup_wait_for チェーン:
  1. `rsyslogd` (priority=1)
  2. `start.sh` (priority=2, rsyslogd:running 待ち)
  3. `lldpd` (priority=3, start:exited 待ち)
  4. `waitfor_lldp_ready` (priority=3, lldpd:running 待ち)
  5. `lldp-syncd` (priority=4, waitfor_lldp_ready:exited 待ち)
  6. `lldpmgrd` (priority=5, lldp-syncd:running 待ち)
- **lldpd が起動し UNIX ソケットが ready になる前に lldpmgrd が `lldpcli` を呼び出すことはない**。
- CONFIG_DB への書き込み自体はいつでも可能だが、lldpd コンテナが起動するまで設定は反映されない。
- 順序依存: lldpd コンテナ起動 → lldp-syncd 起動 → lldpmgrd 起動の順序は supervisord が保証。
- evidence: `supervisord.conf.j2:46-102`

### 8. LLDP|GLOBAL → LLDP_PORT の設定階層

- YANG grouping `lldp_mode_config` を `LLDP|GLOBAL` と `LLDP_PORT|<ifname>` の両方が uses する。
- `LLDP|GLOBAL.enabled=false` でシステム全体を無効化できるが、ポート単位の `LLDP_PORT|<ifname>.enabled` とは独立して `lldpcli` に送られる（競合時は lldpd 内部の優先度で解決）。
- 現実装では `lldpmgrd` が `LLDP|GLOBAL` の変更を直接 `lldpcli configure` に変換する部分は lldpmgrd コードに明示されていない（lldpd.conf.j2 の起動時設定 + CLI 経由が主経路）。
- 順序依存: `LLDP|GLOBAL` → `LLDP_PORT` の順で書き込むことで、グローバル設定がポート設定より先に lldpd に届く（ただし lldpd 内部で適切に上書きされるため順序違反の即時障害は軽微）。
- evidence: `sonic-lldp.yang:24-41`, `lldpmgrd:247-273`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 強度 | 緩和策 |
|---|----------|------|------|--------|
| 1 | PORT 存在 → LLDP_PORT SET | 強制先行（YANG バリデーション有効時） | 強 | CLI / yang validation なしの直書きは通過するが lldpcli 失敗 |
| 2 | PortInitDone + PortConfigDone → lldpcli resume | 強制先行（300 秒タイムアウトで緩和） | 強 | タイムアウト後は強制 resume |
| 3 | netdev oper_status=up → LLDP_PORT 反映 | 先行必須（up になるまでスキップ） | 強 | up 後に自動再試行（RETRY_LIMIT=5 まで） |
| 4 | DEVICE_METADATA.hostname → lldpd 起動 | 起動時先行必須（ランタイム変更は後追い可） | 中 | lldpmgrd がランタイム変更を自動反映 |
| 5 | MGMT_INTERFACE → Management Address TLV 送出 | 先行推奨（なければ管理 IP なしで送出） | 中 | アドレス追加後に lldpmgrd が自動反映 |
| 6 | RETRY_LIMIT 超過後の再設定 | PORT イベント再発生が必要 | 注意 | 失敗 5 回で pending から除去 |
| 7 | lldpd → lldp-syncd → lldpmgrd 起動順序 | supervisord が保証 | 強 | dependent_startup チェーン |
| 8 | LLDP\|GLOBAL → LLDP_PORT 書込み順 | 推奨（違反しても即時障害は軽微） | 弱 | lldpd 内部で競合解決 |
