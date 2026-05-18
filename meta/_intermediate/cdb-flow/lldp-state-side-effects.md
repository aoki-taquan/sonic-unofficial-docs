# lldp-state: 副次 DB 書込調査 (Phase F)

調査対象: `LLDP_ENTRY_TABLE` / `LLDP_LOC_CHASSIS` (APPL_DB)
書き手: `lldp-syncd`
読み手: `sonic-snmpagent (ieee802_1ab.py)`, `sonic-mgmt-common (lldp_app.go)`

## 調査方法

- `sonic-snmpagent/src/sonic_ax_impl/mibs/ieee802_1ab.py` 全体を精査: DB 書き込み API (`hset`, `hmset`, `ProducerStateTable`, `set`) の有無を確認
- `sonic-mgmt-common/translib/lldp_app.go` 全体を精査: `processCreate/Update/Replace/Delete` は全て `ErrNotSupported` を返す実装であり APPL_DB への書き込みは発生しないことを確認
- `sonic-buildimage/dockers/docker-lldp/lldpmgrd` を精査: APPL_DB/STATE_DB/COUNTERS_DB/ASIC_DB への書き込みが全くないことを確認

## 結果

### lldp-syncd (書き手)

`lldp-syncd` は `LLDP_ENTRY_TABLE` / `LLDP_LOC_CHASSIS` に書き込むが、他の DB テーブルへの副次書き込みは行わない。
- APPL_DB 以外への書き込みコードなし
- SAI API 呼び出しなし

### sonic-snmpagent (読み手)

`ieee802_1ab.py` は `hgetall` / `keys` / `GetTable` のみ使用。DB 書き込みコードは存在しない。
唯一の `set()` 呼び出しは Python の `set()` (集合型) であり Redis 操作ではない (L526)。

### sonic-mgmt-common lldp_app.go (読み手)

`app.appDb.GetTable()` / `app.appDb.GetEntry()` のみ。`processCreate/Update/Replace/Delete` はすべて
`ErrNotSupported` を返す stub 実装であり、CREATE/UPDATE/DELETE 操作が来ても APPL_DB を含むいかなる DB にも書き込まない。

### lldpmgrd

CONFIG_DB (`DEVICE_METADATA`, `MGMT_INTERFACE`) および APPL_DB (`PORT_TABLE`) を読み取り、
`lldpcli` コマンドを実行するが、Redis DB への書き込みは行わない（lldpd への設定反映のみ）。

## 結論

`LLDP_ENTRY_TABLE` / `LLDP_LOC_CHASSIS` の書き込み・読み取りを担当するすべてのコンポーネントは、
APPL_DB 以外への副次 DB 書き込みを一切行わない。本テーブルは純粋に read-only consumer に観測されるだけであり、
STATE_DB / COUNTERS_DB / ASIC_DB への連鎖書き込みは発生しない。
