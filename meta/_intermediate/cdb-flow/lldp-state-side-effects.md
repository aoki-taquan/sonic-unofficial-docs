# LLDP_ENTRY_TABLE / LLDP_LOC_CHASSIS 副次 DB 書込 分析 (Phase F)

生成日: 2026-05-18

## スコープ注記

`docs/reference/config-db/lldp-state.md` は **APPL_DB の `LLDP_ENTRY_TABLE` / `LLDP_LOC_CHASSIS`** を扱う。
これらのテーブルは `lldp-syncd` が唯一の書き手であり、外部からの直接書き込みは設計上不可能。
本 Phase F では「`LLDP_ENTRY_TABLE` / `LLDP_LOC_CHASSIS` への書き込みに付随して、他の DB / テーブルへ書かれる事象」を対象とする。

ソース確認範囲:

- `sonic-buildimage/dockers/docker-lldp/supervisord.conf.j2` — lldp-syncd / lldpmgrd 起動定義
- `sonic-snmpagent/src/sonic_ax_impl/mibs/ieee802_1ab.py` — SNMP Consumer (読み取り専用)
- `sonic-mgmt-common/translib/lldp_app.go` — REST/gNMI Consumer (読み取り専用)
- `sonic-buildimage/dockers/docker-lldp/lldpmgrd` — APPL_DB PortInitDone 等を読み取り、lldpcli を発行 (DB への書き込みなし)

---

## 1. APPL_DB: LLDP_ENTRY_TABLE / LLDP_LOC_CHASSIS への書き込み

`lldp-syncd` は lldpd UNIX ソケットをポーリングし、差分エントリを APPL_DB に書き込む。
これが本テーブルの「主たる書込」であり副次書込ではない。

---

## 2. STATE_DB への副次書込

`lldp-syncd` / `lldpmgrd` / `sonic-snmpagent` / `lldp_app.go` のいずれも、
`LLDP_ENTRY_TABLE` / `LLDP_LOC_CHASSIS` の更新をトリガとして **STATE_DB へ書き込む処理は存在しない**。

確認内容:
- `lldpmgrd` は STATE_DB の `PORT_TABLE` を読み取るのみ（`is_port_up()` でポート状態確認）
- `sonic-snmpagent ieee802_1ab.py` は APPL_DB を `hgetall` で読み取るのみ。SNMP ウォーク結果はプロセス内部 OID ツリーに保持され、STATE_DB / COUNTERS_DB には書き込まない
- `lldp_app.go` は APPL_DB を `GetTable` で読み取るのみ。REST/gNMI レスポンス生成に使用し、他 DB への書き込みはない

**結論: STATE_DB への副次書込は「なし」**

---

## 3. COUNTERS_DB への副次書込

LLDP 系コンポーネント (`lldp-syncd` / `lldpmgrd` / `sonic-snmpagent` / `lldp_app.go`) のいずれも
**COUNTERS_DB への書き込みを行わない**。

確認内容:
- `lldpmgrd` は `lldpcli configure` コマンド成功/失敗を syslog (`SWSS_LOG_*`) のみで記録
- `lldp-syncd` の失敗も syslog のみ。FLEX_COUNTER_DB との接続なし
- PBH / FDB 等の FLEX_COUNTER 書込経路 (`orchagent/pbhorch.cpp` 等) は LLDP とは無関係

**結論: COUNTERS_DB / FLEX_COUNTER_DB への副次書込は「なし」**

---

## 4. ASIC_DB / CONFIG_DB への副次書込

- `LLDP_ENTRY_TABLE` / `LLDP_LOC_CHASSIS` は SAI / orchagent とは無関係。ASIC_DB への副次書込は「なし」
- `lldp-syncd` / `lldpmgrd` は CONFIG_DB へ書き込まない（読み取りのみ）

**結論: ASIC_DB / CONFIG_DB への副次書込は「なし」**

---

## 5. lldp-syncd による lldpd への間接フィードバック

lldpd は `LLDP_ENTRY_TABLE` を読み取らない。lldpd が生成した LLDPDU を lldp-syncd が APPL_DB に書き込む一方向の流れのみ。フィードバックループはない。

---

## まとめ

| 副次書込先 | 有無 | 根拠 |
|-----------|-----|------|
| **STATE_DB** | なし | lldpmgrd は STATE_DB 読み取りのみ / snmpagent・lldp_app.go は書き込みなし |
| **COUNTERS_DB** | なし | lldp 系コンポーネント全てで COUNTERS_DB 書込コードなし |
| **FLEX_COUNTER_DB** | なし | 同上 |
| **ASIC_DB** | なし | lldp は SAI 非経由 (lldpd ← lldpcli のみ) |
| **CONFIG_DB** | なし | lldp-syncd / lldpmgrd は CONFIG_DB 読み取りのみ |
| **EVENT_DB** | なし | eventd との連携なし |
