# lldp-state — Phase B 書込み順依存スキャンノート

対象テーブル: `APPL_DB: LLDP_ENTRY_TABLE|<ifname>`, `APPL_DB: LLDP_LOC_CHASSIS`
Consumer/Producer: `lldp-syncd` (writer), `sonic-snmpagent` / `sonic-mgmt-common` (readers)
スキャン範囲: `supervisord.conf.j2`, `lldpmgrd`, `ieee802_1ab.py`, `lldp_app.go`

---

## 検出した順序依存・タイミング依存

### 1. lldpd 起動 → lldp-syncd 起動の先行条件

- `supervisord.conf.j2`:
  - `lldpd` (priority=3): `start:exited` 待ち
  - `waitfor_lldp_ready` (priority=3): `lldpd:running` 待ち
  - `lldp-syncd` (priority=4): `waitfor_lldp_ready:exited` 待ち
  - `lldpmgrd` (priority=5): `lldp-syncd:running` 待ち
- lldpd の UNIX ソケットが ready になるまで lldp-syncd は起動しない。
- 順序依存: lldpd 起動 → waitfor_lldp_ready 完了 → lldp-syncd 起動 → APPL_DB 書き込み開始。
- evidence: `supervisord.conf.j2:46-102`

### 2. LLDP PDU 受信 → LLDP_ENTRY_TABLE エントリ出現

- lldp-syncd は lldpctl の JSON 出力を polling して差分を APPL_DB に反映する。
- `LLDP_ENTRY_TABLE|<ifname>` エントリが現れるのは、対向ノードからの LLDP PDU を lldpd が受信した後。
- polling 周期により PDU 受信から APPL_DB 反映まで数秒の遅延がある。
- 順序依存: LLDP PDU 受信 → lldp-syncd ポーリング → APPL_DB 書き込み。
- evidence: `supervisord.conf.j2:lldp-syncd program block`

### 3. LLDP_LOC_CHASSIS は PDU 受信前から書き込まれる

- `LLDP_LOC_CHASSIS` はローカル chassis 情報を保持するため、lldp-syncd 起動後に lldpctl でローカル情報を取得して書き込まれる。
- PDU 受信イベントに依存せず、lldpd 起動後から利用可能。
- 順序依存: lldpd 起動 → lldp-syncd 起動 → LLDP_LOC_CHASSIS 書き込み。

### 4. lldpcli resume 前は自ノード LLDPDU 送出なし（間接影響）

- `lldpmgrd` が `PortInitDone` + `PortConfigDone` を APPL_DB から受信するまで lldpd は pause 状態（最大 300 秒待機、または PORT_INIT_TIMEOUT 超過で強制 resume）。
- pause 中は自ノードの LLDPDU が送出されないため、対向ノードが自ノードの情報を `LLDP_ENTRY_TABLE` に書き込めない。
- LLDP_ENTRY_TABLE/LLDP_LOC_CHASSIS の読み取り自体には影響しないが、自ノードが対向に見えるまでに最大 300 秒かかる可能性がある。
- evidence: `lldpmgrd:259-273`, `lldpmgrd:296-342`

### 5. エントリ削除タイミング (TTL / リンクダウン)

- lldpd の hold time = hello_time × multiplier（デフォルト 30 × 4 = 120 秒）。
- TTL 切れ時は lldpd が lldp-syncd に通知し、lldp-syncd が `LLDP_ENTRY_TABLE|<ifname>` を APPL_DB から DEL する。
- ポートがリンクダウンした場合も同様にエントリが削除される。
- sonic-snmpagent は削除後の次回 SNMP walk では当該エントリを返さない。

### 6. APPL_DB 再起動時の一時空ウィンドウ

- lldp コンテナ再起動時、lldp-syncd 再起動後に lldpd 全エントリを再スキャンして APPL_DB を再書き込みする。
- 再書き込みが完了するまでの短期間、`LLDP_ENTRY_TABLE` が空になる可能性がある。
- SNMP polling がこのウィンドウに当たると空結果を返す。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 強度 | 備考 |
|---|----------|------|------|------|
| 1 | lldpd 起動 → lldp-syncd 起動 | 強制先行 | 強 | supervisord dependent_startup が保証 |
| 2 | LLDP PDU 受信 → LLDP_ENTRY_TABLE エントリ | 先行必須 | 強 | polling 遅延あり（数秒） |
| 3 | lldpd 起動 → LLDP_LOC_CHASSIS 書き込み | 先行必須 | 強 | PDU 受信不要、lldp-syncd 起動後に即書き込み |
| 4 | lldpcli resume → 自ノード LLDPDU 送出 | 間接影響 | 中 | 最大 300 秒の遅延 |
| 5 | TTL/リンクダウン → エントリ DEL | 自動（lldpd 管理） | — | sonic-snmpagent は次回 walk で反映 |
| 6 | コンテナ再起動 → 再書き込み完了 | 一時空ウィンドウ | 注意 | 数秒〜数十秒の空白期間あり |
