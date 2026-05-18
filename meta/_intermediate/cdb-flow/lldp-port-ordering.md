# LLDP_PORT — Phase F 書込み順依存スキャンノート

対象テーブル: `LLDP_PORT|<ifname>`
Consumer: `lldpmgrd` (`sonic-buildimage/dockers/docker-lldp/lldpmgrd`)
スキャン範囲: lldpmgrd 全行精読、sonic-lldp.yang、supervisord.conf.j2 参照

---

## 検出した順序依存・タイミング依存

### 1. PORT テーブルへの leafref（LLDP_PORT 書き込みの先行条件）

- `sonic-lldp.yang` L107-110: `LLDP_PORT_LIST.ifname` は `sonic-port/PORT/PORT_LIST/name` への leafref。
- mgmt-framework 経由の YANG バリデーション有効時、`PORT|<ifname>` が先に CONFIG_DB に存在しないと `LLDP_PORT|<ifname>` の SET が leafref 違反で拒否される。
- 直接 redis-cli / sonic-db-cli で書く場合はバリデーションをスキップできるが、後続の `lldpcli configure ports <ifname>` が linux netdev 不在で失敗する。
- 順序: `PORT|<ifname>` → `LLDP_PORT|<ifname>`（先行必須）
- evidence: `sonic-lldp.yang:107-110`

### 2. STATE_DB の netdev_oper_status=up が LLDP_PORT 反映の先行条件

- `lldpmgrd.process_pending_cmds()` L176: `is_port_up(port_name)` が False の場合、ポートの lldpcli コマンドをスキップして 10 秒ループに戻す。
- `is_port_up()` は `STATE_DB: PORT_TABLE|<ifname>.netdev_oper_status` を参照 (lldpmgrd:116-134)。
- `LLDP_PORT` への書き込みは CONFIG_DB に即座に書けるが、対応ポートの linux netdev が up になるまで lldpd に設定が反映されない。
- ポートが up になると自動で lldpcli が発行されるが、RETRY_LIMIT=5 回失敗すると pending_cmds から除去され再 PORT イベントが来るまで再設定されない。
- 順序: `STATE_DB PORT_TABLE|<ifname>.netdev_oper_status = "up"` → `lldpcli configure ports <ifname>` 発行
- evidence: `lldpmgrd:116-134`, `lldpmgrd:168-204`

### 3. APPL_DB PortInitDone + PortConfigDone → lldpcli resume

- `lldpmgrd.run()` L296-342: `PortInitDone` および `PortConfigDone` の両イベントを受信するまで `lldpcli resume` を発行しない。
- 起動直後は lldpd が `pause` 状態（lldpd.conf.j2 末尾 `pause` ディレクティブ）。LLDP_PORT の設定 (pending_cmds) は pending_cmds に積まれるが、resume 前は LLDP PDU が送出されない。
- PORT_INIT_TIMEOUT=300 秒を超過すると強制 resume する。
- 順序: `PortInitDone` + `PortConfigDone` → LLDP PDU 送出開始
- evidence: `lldpmgrd:259-273`, `lldpmgrd:296-342`

### 4. lldpmgrd は LLDP_PORT テーブルを直接購読しない（構造的特性）

- `lldpmgrd.run()` L300-310: 購読対象は `APPL_DB PORT_TABLE`、`CONFIG_DB MGMT_INTERFACE`、`CONFIG_DB DEVICE_METADATA` のみ。`CONFIG_DB LLDP_PORT` テーブルは購読していない。
- `LLDP_PORT` の `enabled` / `mode` フィールドは lldpcli には変換されない（dead field）。lldpmgrd が lldpcli に渡すのは `PORT.alias` と `PORT.description` のみ。
- LLDP_PORT 書き込みのタイミングは lldpmgrd に影響しない（CONFIG_DB に蓄積されるのみ）。
- evidence: `lldpmgrd:300-310`

---

## 順序依存サマリ

| # | 依存関係 | 強度 | 備考 |
|---|----------|------|------|
| 1 | `PORT\|<ifname>` → `LLDP_PORT\|<ifname>` | 強（YANG バリデーション有効時は必須） | 直書きはスキップ可だが lldpcli 失敗 |
| 2 | `STATE_DB netdev_oper_status=up` → lldpcli 発行 | 強（up まで自動スキップ） | up 後自動再試行、RETRY_LIMIT=5 超過で silent drop |
| 3 | `PortInitDone`+`PortConfigDone` → LLDP PDU 送出 | 強（300 秒タイムアウトで緩和） | resume 前は PDU 送出なし |
| 4 | LLDP_PORT.enabled/mode は lldpcli に非変換 | 構造的特性（dead field） | lldpmgrd は LLDP_PORT を購読しない |
