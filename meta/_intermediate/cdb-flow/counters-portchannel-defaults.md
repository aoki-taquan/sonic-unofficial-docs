# COUNTERS_DB PortChannel/LAG カウンタ — Phase A コード由来デフォルト調査

生成日: 2026-05-14

## 調査ソース

- `sonic-swss/orchagent/portsorch.cpp:762,8019-8022,8095` — `COUNTERS_LAG_NAME_MAP` への OID 登録
- `sonic-swss/orchagent/intfsorch.cpp:49-58,70,1527-1554` — RIF カウンタ (rifStatIds) の FlexCounter 登録
- `sonic-swss/orchagent/rif_rates.lua` — RATES テーブルへの RX_BPS/TX_BPS/RX_PPS/TX_PPS 導出
- `sonic-utilities/scripts/intfstat:63-71` — counter_names 定義 (SAI_ROUTER_INTERFACE_STAT_*)
- `sonic-swss-common/common/schema.h:219-222` — COUNTERS_PORT_NAME_MAP / COUNTERS_LAG_NAME_MAP 定数定義
- `sonic-utilities/tests/portstat_db/counters_db.json` — 実ランタイムデータ構造の確認
- `sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py:407` — SNMP の LAG counter 取得経路

---

## COUNTERS_DB PortChannel 関連テーブル構造

### 1. `COUNTERS_LAG_NAME_MAP`

```
COUNTERS_LAG_NAME_MAP|""  (hash)
  PortChannel0001 -> oid:0x60000000005a1
  PortChannel0002 -> oid:0x60000000005a2
  ...
```

**書き込み元**: `portsorch.cpp::addLag()` が `m_counterLagTable->set("", fields)` を呼ぶ。
**削除**: `portsorch.cpp::removeLag()` が `m_counterLagTable->hdel("", lag.m_alias)` を呼ぶ。

このマップは LAG 名 → SAI OID のルックアップテーブルであり、カウンタ値自体は持たない。

### 2. `COUNTERS_RIF_NAME_MAP`

```
COUNTERS_RIF_NAME_MAP|""  (hash)
  PortChannel0001 -> oid:0x60000000005a1
  PortChannel0002 -> oid:0x60000000005a2
  Ethernet20      -> oid:0x...
  Vlan1000        -> oid:0x...
  ...
```

**書き込み元**: `intfsorch.cpp::addRifToFlexCounter()` — PortChannel に IP アドレスが設定され RIF (Router Interface) が作成されたタイミングで登録。
**条件**: `PORTCHANNEL_INTERFACE` テーブルに当該 PortChannel のエントリが存在しないと RIF は作成されず、このマップにも登録されない。

### 3. `COUNTERS:<oid>` (カウンタ値テーブル)

FlexCounter が定期的に SAI から読み取り書き込む。PortChannel の RIF OID に対して以下フィールドが格納される:

| フィールド | 説明 |
|---|---|
| `SAI_ROUTER_INTERFACE_STAT_IN_PACKETS` | RIF 受信パケット数 |
| `SAI_ROUTER_INTERFACE_STAT_IN_OCTETS` | RIF 受信バイト数 |
| `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS` | RIF 受信エラーパケット数 |
| `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_OCTETS` | RIF 受信エラーバイト数 |
| `SAI_ROUTER_INTERFACE_STAT_OUT_PACKETS` | RIF 送信パケット数 |
| `SAI_ROUTER_INTERFACE_STAT_OUT_OCTETS` | RIF 送信バイト数 |
| `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS` | RIF 送信エラーパケット数 |
| `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_OCTETS` | RIF 送信エラーバイト数 |

定義箇所: `intfsorch.cpp:49-58` `rifStatIds` 配列。

### 4. `RATES:<oid>` (レート導出テーブル)

`rif_rates.lua` が FlexCounter の Lua プラグインとして動作し、`COUNTERS` から前回との差分を計算して格納。

| フィールド | 説明 | 計算式 |
|---|---|---|
| `RX_BPS` | 受信ビットレート (bytes/sec) | `(in_octets_delta) / delta * 1000` (EWMA スムージング) |
| `TX_BPS` | 送信ビットレート (bytes/sec) | `(out_octets_delta) / delta * 1000` (EWMA スムージング) |
| `RX_PPS` | 受信パケットレート (pkts/sec) | `(in_pkts_delta) / delta * 1000` (EWMA スムージング) |
| `TX_PPS` | 送信パケットレート (pkts/sec) | `(out_pkts_delta) / delta * 1000` (EWMA スムージング) |

スムージング係数 `alpha` は `RATES:RIF` の `RIF_ALPHA` フィールドから取得。
`alpha` が未設定の場合、rif_rates.lua は早期 return し `RATES` テーブルに何も書かない。

---

## コード由来暗黙デフォルト

### RATES フィールドの初期値

| フィールド | 初期値 | 挙動 |
|---|---|---|
| `RX_BPS` / `TX_BPS` / `RX_PPS` / `TX_PPS` | 存在しない (初回 FlexCounter 実行まで) | `intfstat` は `STATUS_NA` ("N/A") を表示 |
| 初回 polling 時 | `INIT_DONE = "COUNTERS_LAST"` を設定 | 前回値なしのため BPS/PPS は計算せず次回に持ち越す |
| 2回目 polling 時 | `INIT_DONE = "DONE"` を設定し EWMA を開始 | 初回 BPS/PPS 値が書き込まれる |

### カウンタ値の初期値

SAI から読み取る。HW リセット後 / 初期状態では `"0"` が格納される。
FlexCounter が polling を開始するまで `COUNTERS:<oid>` のフィールドは存在しない。
`intfstat` は欠損フィールドを `STATUS_NA` として扱う。

### RIF 未作成時のカウンタなし

PortChannel に IP アドレスが割り当てられていない場合（L2 LAG）、RIF は作成されず `COUNTERS_RIF_NAME_MAP` に登録されない。
この場合 `COUNTERS:<lag_oid>` のカウンタフィールドは存在しない。
`intfstat` でこの LAG を指定すると "Interface missing from COUNTERS_RIF_NAME_MAP" エラーになる。

### SNMP 経路の違い (member 集計)

SNMP の ifMIB (`rfc2863.py`) は PortChannel の IF カウンタを各メンバポートの `SAI_PORT_STAT_*` を合計して計算する。
これは `COUNTERS_LAG_NAME_MAP` の OID を直接参照する `intfstat` の経路（RIF ベース）と異なる。

| 経路 | 使用カウンタ | 対象 |
|---|---|---|
| `intfstat` / `show interfaces counters rif` | `SAI_ROUTER_INTERFACE_STAT_*` (RIF) | L3 PortChannel のみ |
| SNMP ifMIB | `SAI_PORT_STAT_*` の member 総和 | L2/L3 PortChannel |

---

## 主要 discrepancy

1. **L2 PortChannel に COUNTERS_RIF_NAME_MAP エントリなし**: L2 LAG は RIF が存在しないため `intfstat` で参照不可。SNMP は member 集計で間接的に統計取得できる。
2. **RATES フィールド初期欠損**: FlexCounter 初回実行後しばらく `RX_BPS` 等が `N/A` になる。alpha 未設定時は永久に `N/A`。
3. **`intfstat` の counter_names 順序**: `intfstat` は `SAI_ROUTER_INTERFACE_STAT_IN_OCTETS` を index 1 (rx_b_ok)、`SAI_ROUTER_INTERFACE_STAT_IN_PACKETS` を index 0 (rx_p_ok) として扱う。カウンタ順がコードに埋め込まれており、SAI が特定フィールドを返さない HW では N/A になる。
