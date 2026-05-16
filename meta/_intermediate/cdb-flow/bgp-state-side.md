# BGP-STATE — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-16 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/bgp-state.md` が扱う STATE_DB テーブル
(`NEIGH_STATE_TABLE` / `BGP_PEER_CONFIGURED_TABLE`) の書き込みデーモン
(`bgpmon` / `bgpcfgd BGPPeerMgrBase`) が、STATE_DB 以外の副次 DB
(APPL_DB / COUNTERS_DB / ASIC_DB / FLEX_COUNTER_DB 等) へ書き込みを行うか。

## 走査範囲

- `.cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpmon/bgpmon.py`
- `.cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`

## 走査コマンドと結果

### 1. bgpmon.py — DB 接続先の確認

```bash
grep -n "DBConnector\|SonicV2Connector\|connect\b" bgpmon.py
```

結果:

```
48: self.db = swsscommon.SonicV2Connector()
49: self.db.connect(self.db.STATE_DB, False)
```

**STATE_DB のみ** に接続。他の DB への接続呼出は 0 件。

### 2. bgpmon.py — 副次 DB 名前空間アクセスの確認

```bash
grep -n "COUNTERS_DB\|APPL_DB\|ASIC_DB\|FLEX_COUNTER\|EVENTS_DB\|CHASSIS_APP_DB\|publish\|notify" bgpmon.py
```

結果: **マッチ 0 件**。

### 3. managers_bgp.py — DB 接続先の確認

```bash
grep -n "DBConnector\|SonicV2Connector" managers_bgp.py
```

結果:

```
286: state_db = swsscommon.DBConnector("STATE_DB", 0)
```

`update_state_db()` 内で生成される接続先は **STATE_DB のみ**。

### 4. managers_bgp.py — 副次 DB 名前空間アクセスの確認

```bash
grep -n "COUNTERS_DB\|APPL_DB\|APP_DB\|ASIC_DB\|FLEX_COUNTER\|EVENTS_DB\|CHASSIS_APP_DB\|publish\|notify" managers_bgp.py
```

結果: **マッチ 0 件**（CONFIG_DB は読み取り専用の参照のみ）。

### 5. STATE_DB テーブルの下流購読者による副次書込の確認

`NEIGH_STATE_TABLE` の下流購読者は SNMP サブエージェント
(`sonic-snmpagent/src/sonic_ax_impl/mibs/vendor/cisco/bgp4.py`) のみ。
同ファイルは `NEIGH_STATE_TABLE` を **読み取るのみ** で、他の DB への書き込みは行わない
（SNMP GET/GETNEXT 応答として MIB 値を返すだけ）。

`BGP_PEER_CONFIGURED_TABLE` の下流購読者は SDN コントローラ（外部プロセス）のみ。
STATE_DB 側から能動的に他 DB へ波及書込を行う swsscommon ハンドラは存在しない。

## 結論

`bgpmon` / `bgpcfgd BGPPeerMgrBase` は **STATE_DB にのみ書き込む**。
APPL_DB / COUNTERS_DB / ASIC_DB / FLEX_COUNTER_DB / EVENTS_DB
いずれへの副次書込も存在しない。

`NEIGH_STATE_TABLE` の下流は SNMP GET 経由の **読み取りのみ** であり、
SNMP サブエージェントが他 DB へ書き込む経路は存在しない。

## 根拠サマリ

| 検証項目 | ファイル / 行 | 結果 |
|---|---|---|
| bgpmon.py の DB 接続先 | `bgpmon.py:48-49` | STATE_DB のみ |
| bgpmon.py の副次 DB 参照 | `bgpmon.py` 全体 grep | 0 件 |
| managers_bgp.py の DB 接続先 | `managers_bgp.py:286` | STATE_DB のみ (update_state_db 内) |
| managers_bgp.py の副次 DB 参照 | `managers_bgp.py` 全体 grep | 0 件 |
| SNMP 下流が他 DB へ書き込む経路 | `sonic-snmpagent/bgp4.py` | 読み取りのみ、書込なし |
| SDN コントローラ下流 | 外部プロセス | STATE_DB 読み取りのみ |
