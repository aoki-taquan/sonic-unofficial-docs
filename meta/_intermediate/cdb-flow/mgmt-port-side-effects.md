# MGMT_PORT テーブル — 副次 DB 書込スキャンノート (Phase F)

調査日: 2026-05-18
調査対象:
- `sonic-buildimage/files/image_config/monit/mgmt_oper_status.py`
- `sonic-host-services/scripts/hostcfgd` (MgmtIfaceCfg クラス)
- `sonic-swss/cfgmgr/portmgrd.cpp`
- `sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py`

---

## 結論

`MGMT_PORT` エントリの SET/DEL に起因してコードが副次的に書き込む DB は **STATE_DB の `MGMT_PORT_TABLE`** のみ。APPL_DB・ASIC_DB・COUNTERS_DB・FLEX_COUNTER_DB への書込みは一切存在しない。

---

## grep 調査結果

| 調査対象 | grep キーワード | ヒット有無 | 備考 |
|---------|----------------|-----------|------|
| `hostcfgd` (MgmtIfaceCfg 全体) | `set(`/`Producer`/`Notification` + `APPL_DB` | **0 件** | `MgmtIfaceCfg.update_mgmt_iface()` / `update_mgmt_vrf()` は `systemctl restart` のみ発行 |
| `mgmt_oper_status.py` | `db.set(` | **1 種** | `db.set(db.STATE_DB, ...)` のみ。APPL_DB への書込みなし |
| `portmgrd.cpp` | MGMT_PORT への subscribe | **0 件** | `CFG_PORT_TABLE_NAME`（= `"PORT"`）のみ購読。MGMT_PORT は処理対象外 |
| `sonic_ax_impl/mibs/__init__.py` | CONFIG_DB / STATE_DB への `set(` | **0 件** | 読み取り専用。SNMP は DB に書き込まない |

---

## STATE_DB への書込み詳細

### MGMT_PORT_TABLE — フィールド同期

`mgmt_oper_status.py` は monit によって定期的に呼び出され、以下の書込みを実行する。

```
STATE_DB MGMT_PORT_TABLE|<port>
  <field>  ← CONFIG_DB MGMT_PORT|<port> の各フィールドを差分コピー
  oper_status ← /sys/class/net/<port>/operstate から取得（up / down / unknown）
```

- CONFIG_DB `MGMT_PORT|*` に存在する全フィールド（`oper_status` を除く）を STATE_DB へ同期。
- `oper_status` は CONFIG_DB ではなく `/sys/class/net/<port>/operstate` の実測値から設定。
- 差分更新（フィールドが STATE_DB に存在しない、または値が異なる場合のみ `db.set()` を発行）。
- MGMT_PORT エントリが CONFIG_DB に存在しない場合は STATE_DB への書込みを行わない（`mgmt_oper_status.py:16-19`）。

### DEL 時の挙動

`MGMT_PORT` エントリが DEL されると `db.keys(CONFIG_DB, 'MGMT_PORT|*')` が空を返す。
`mgmt_oper_status.py` は STATE_DB をクリアせず `LOG_DEBUG` を出力して正常終了する。
→ **STATE_DB に古い `MGMT_PORT_TABLE` エントリが残存するゴースト状態**になる（monit の次回実行でも CONFIG_DB が空なら同様）。

---

## 副次書込サマリ

| 副次 DB | テーブル | 書込条件 | ソース |
|---------|---------|---------|--------|
| STATE_DB | `MGMT_PORT_TABLE\|<port>` | `mgmt_oper_status.py` が monit 定期実行される都度（CONFIG_DB にエントリが存在する場合） | `mgmt_oper_status.py:30-34, 39-44` |
| APPL_DB | なし | — | — |
| ASIC_DB | なし | — | portmgrd は MGMT_PORT 非購読 |
| COUNTERS_DB | なし | — | — |
| FLEX_COUNTER_DB | なし | — | — |
