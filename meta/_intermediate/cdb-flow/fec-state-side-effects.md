# fec-state Phase F — 副次 DB 書込スキャン証跡

調査日: 2026-05-19
対象: STATE_DB `PORT_TABLE` の FEC 関連フィールド（`fec`, `supported_fecs`）

## 調査ファイル
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/cfgmgr/portmgr.cpp`

---

## A. portmgrd による APPL_DB への書き写し (CONFIG_DB → APPL_DB)

`portmgr.cpp:196-214` — `doTask()` は CONFIG_DB `PORT` テーブルの変更を受け取り、
`fec` を含む全フィールドを `field_values` に積んで `writeConfigToAppDb(alias, field_values)` を呼ぶ。

```cpp
// portmgr.cpp:186-213 (抜粋)
for (auto i : kfvFieldsValues(t)) {
    if (fvField(i) == "mtu") { ... }
    else if (fvField(i) == "admin_status") { ... }
    else {
        field_values.emplace_back(i);  // fec もここに入る
    }
}
if (field_values.size()) {
    writeConfigToAppDb(alias, field_values);  // APPL_DB PORT_TABLE へ書込み
}
```

`writeConfigToAppDb` は `m_appPortTable.set(alias, field_values)` を呼ぶ (portmgr.cpp:257, 264)。
`m_appPortTable` は `ProducerStateTable(appDb, APP_PORT_TABLE_NAME)` (portmgr.cpp:21)。

結果:
- CONFIG_DB `PORT|<port>.fec` が変更されると APPL_DB `PORT_TABLE:<port>.fec` に同値が書かれる
- この APPL_DB 値が `show interfaces fec status` の **FEC Admin 列** として表示される
- STATE_DB の `fec` (oper) とは別フィールド

---

## B. FEC_ALIGNMENT_LOCK ポーリング (FLEX_COUNTER_DB + COUNTERS_DB)

`portsorch.cpp:229-234` — `port_phy_attr_ids` に `SAI_PORT_ATTR_FEC_ALIGNMENT_LOCK` が含まれる。

```cpp
const vector<sai_port_attr_t> port_phy_attr_ids = {
    SAI_PORT_ATTR_RX_SIGNAL_DETECT,
    SAI_PORT_ATTR_FEC_ALIGNMENT_LOCK,   // ← FEC 関連
    SAI_PORT_ATTR_RX_SNR
};
```

`port_phy_attr_manager` (`FlexCounterManager(PORT_PHY_ATTR_FLEX_COUNTER_GROUP, ...)`)
は `postPortInit()` / ポート初期化時に `setCounterIdList(p.m_port_id, CounterType::PORT_PHY_ATTR, ...)` を呼び、
FLEX_COUNTER_DB に `SAI_PORT_ATTR_FEC_ALIGNMENT_LOCK` を含む attr リストを登録する (portsorch.cpp:4164-4166)。

`syncd` が FLEX_COUNTER_DB のポーリング指示を受けて SAI から値を取得し COUNTERS_DB に書き込む。

結果:
- FLEX_COUNTER_DB に `PORT_PHY_ATTR:<port_oid>` エントリが設定される (FEC_ALIGNMENT_LOCK 含む)
- syncd が定期ポーリング (10000ms 間隔) → COUNTERS_DB `COUNTERS:<port_oid>` に
  `SAI_PORT_ATTR_FEC_ALIGNMENT_LOCK` の値が書き込まれる
- PortsOrch 自体が COUNTERS_DB に直接書くわけではない（syncd 経由）

---

## C. FEC エラー統計カウンタ (COUNTERS_DB 経由)

`portsorch.cpp:308-324` — `port_stat_ids` に FEC エラー統計が含まれる:

```
SAI_PORT_STAT_IF_IN_FEC_SYMBOL_ERRORS
SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_S0 .. _S15
```

`port_stat_manager` (`FlexCounterManager(PORT_STAT_COUNTER_FLEX_COUNTER_GROUP, ...)`) が
ポート登録時にこれらを含む stat ID リストを FLEX_COUNTER_DB に書き込む (portsorch.cpp:728, 4138-4155 周辺)。

結果:
- FLEX_COUNTER_DB に `COUNTERS_PORT_STAT_COUNTER:<port_oid>` で FEC エラー stat IDs が設定される
- syncd が定期ポーリング (1000ms 間隔) → COUNTERS_DB `COUNTERS:<port_oid>` に各 FEC エラーカウント書込み
- `show interfaces counters` / `sonic-clear counters` から参照される

---

## D. 直接の副次 DB 書込一覧

PortsOrch が `fec` / `supported_fecs` を STATE_DB に書く際に発生する**直接の**副次書込は存在しない。
副次的に発生するのは:

| 副次 DB | テーブル/キー | 書込主体 | 契機 | evidence |
|---------|------------|---------|-----|---------|
| APPL_DB | `PORT_TABLE:<port>` → `fec` | `portmgrd` (portmgr.cpp:196-264) | CONFIG_DB `PORT.fec` 変更時 | portmgr.cpp:21, 257 |
| FLEX_COUNTER_DB | `PORT_PHY_ATTR:<port_oid>` → attr_ids (FEC_ALIGNMENT_LOCK 含む) | `PortsOrch::port_phy_attr_manager` 経由 | postPortInit / ポート登録時 | portsorch.cpp:4164-4166 |
| COUNTERS_DB | `COUNTERS:<port_oid>` → `SAI_PORT_ATTR_FEC_ALIGNMENT_LOCK` | `syncd` (FLEX_COUNTER_DB ポーリング受け) | 10000ms 定期 | portsorch.cpp:729 |
| COUNTERS_DB | `COUNTERS:<port_oid>` → `SAI_PORT_STAT_IF_IN_FEC_*` | `syncd` | 1000ms 定期 | portsorch.cpp:308-324 |

---

## E. 直接 DB 書込がないと確認した範囲

grep 実施: `grep -n "APPL_DB\|COUNTERS_DB\|FLEX_COUNTER\|ASIC_DB" portsorch.cpp | grep -i fec` → ヒットなし

`updateDbPortOperFec()` と `initPortSupportedFecModes()` は `m_portStateTable.set()` のみを呼び、
他 DB への副次書込は行わない。
