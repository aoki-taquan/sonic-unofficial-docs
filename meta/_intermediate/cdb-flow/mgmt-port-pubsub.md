# MGMT_PORT — Phase G: CONFIG_DB Subscribe 機構 (通信メカニズム) 調査ノート

対象ページ: `docs/reference/config-db/mgmt-port.md`
調査日: 2026-05-18

---

## 調査目的

MGMT_PORT テーブルの CONFIG_DB 購読（subscribe）メカニズムを確認する。
実装が polling 型か event-driven 型かを分類する。

---

## 調査結果

### hostcfgd の subscribe 登録一覧

ソース: `sonic-host-services/scripts/hostcfgd L2452-2526`

```python
self.config_db.subscribe('MGMT_INTERFACE', make_callback(self.mgmt_intf_handler))  # L2485
self.config_db.subscribe(swsscommon.CFG_MGMT_VRF_CONFIG_TABLE_NAME,
                         make_callback(self.mgmt_vrf_handler))  # L2496-2497
```

**`MGMT_PORT` テーブルへの subscribe 登録は存在しない。**

hostcfgd は `MGMT_INTERFACE` (L2485) と `MGMT_VRF_CONFIG` (L2496) を購読するが、
`MGMT_PORT` テーブルへの `config_db.subscribe()` 呼び出しは全コードを grep しても
見つからない。

### mgmt_oper_status.py — polling 型読み取り

ソース: `sonic-buildimage/files/image_config/monit/mgmt_oper_status.py:12-57`

```python
db = SonicV2Connector(use_unix_socket_path=True)
db.connect('CONFIG_DB')
db.connect('STATE_DB')
mgmt_ports_keys = db.keys(db.CONFIG_DB, 'MGMT_PORT|*')
```

- `SonicV2Connector` を使った**一回限りの読み取り（one-shot）**。`listen()` / `subscribe()` は呼ばない。
- monit デーモンによって**定期的に呼び出される**（polling モデル）。
- CONFIG_DB の `MGMT_PORT|*` を全件スキャンし、STATE_DB `MGMT_PORT_TABLE|<port>` へ差分コピーする。

### MGMT_PORT が購読されない理由

MGMT_PORT テーブルのフィールド（`speed`, `autoneg`, `mtu`, `admin_status`, `alias`）は
Phase A 調査で確認済みの通り大部分が "dead write"（コンシューマが ethtool 等を発行しない）。
唯一の実効処理は `mgmt_oper_status.py` による STATE_DB への反映であり、
これはイベント駆動ではなく polling で十分なため、event-driven な subscribe は実装されていない。

### 通信メカニズムまとめ

| コンポーネント | 機構 | テーブル | 方向 |
|---|---|---|---|
| `hostcfgd` | `ConfigDBConnector.subscribe()` (event-driven) | `MGMT_INTERFACE`, `MGMT_VRF_CONFIG` | 読み取り → 処理 |
| `mgmt_oper_status.py` | `SonicV2Connector.keys()` + `get_all()` (one-shot polling) | `MGMT_PORT|*` | 読み取り → STATE_DB 書込 |
| `lldpd.conf.j2` | 起動時テンプレート展開（静的） | `MGMT_PORT[].alias` | 読み取り（起動時のみ） |
| `sonic-snmpagent` | SNMP GET 要求時の on-demand 読み取り | `MGMT_PORT[].alias` | 読み取り（要求時） |

---

## 結論

`MGMT_PORT` テーブルには event-driven な CONFIG_DB subscribe consumer が存在しない。
変化の検知は monit による `mgmt_oper_status.py` の定期実行（polling）に限られる。
Phase G ブロックはこの「subscribe 不在・polling 型」の実態を記述する。
