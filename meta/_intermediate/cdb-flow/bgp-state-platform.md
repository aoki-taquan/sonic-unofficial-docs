# bgp-state Phase H — BGP_PEER_CONFIGURED_TABLE プラットフォーム差分調査

調査日: 2026-05-16
調査対象:
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpmon/bgpmon.py`
- `sonic-snmpagent/src/sonic_ax_impl/mibs/vendor/cisco/bgp4.py`

---

## 結論: BGP_PEER_CONFIGURED_TABLE にプラットフォーム差分は存在しない

`BGP_PEER_CONFIGURED_TABLE` を書き込む `BGPPeerMgrBase.update_state_db()`（managers_bgp.py L271–304）
には `switch_type`・`sub_role`・`DEVICE_METADATA.localhost.type` による分岐が**一切存在しない**。

`NEIGH_STATE_TABLE` を書き込む `bgpmon.py` についても同様に platform 分岐は存在しない。
ただし SNMP サブエージェント（sonic-snmpagent）が `NEIGH_STATE_TABLE` を読み取る際には
**マルチ ASIC 対応として全 namespace の STATE_DB を横断収集する**という動作上の差異が存在する。

---

## 根拠詳細

### 1. managers_bgp.py — update_state_db の完全コード

```python
def update_state_db(self, vrf, nbr, data, op):
    if (vrf == "default"):
        key = nbr
    else:
        key = vrf + "|" + nbr
    try:
        state_db = swsscommon.DBConnector("STATE_DB", 0)
        state_peer_table = swsscommon.Table(state_db, swsscommon.STATE_BGP_PEER_CONFIGURED_TABLE_NAME)
        if (op == "SET"):
            state_peer_table.set(key, list(sorted(data.items())))
        elif (op == "DEL"):
            (status, fvs) = state_peer_table.get(key)
            if status == True:
                state_peer_table.delete(key)
        ...
    except Exception as e:
        log_err("Update of state db failed for peer '(%s)' with error: %s" % (key, str(e)))
        return False
```

- `switch_type` 参照: **なし**
- `sub_role` 参照: **なし**
- `DEVICE_METADATA.type` 条件分岐: **なし**

grep 確認:
- `switch_type` in managers_bgp.py → **0 件**
- `sub_role` in managers_bgp.py → **0 件**
- `is_chassis` in managers_bgp.py → **0 件**

`localhost/type` は deps リスト（L120）に依存キーとして登録されているが、
これは swsscommon の依存性ガード（「そのキーが DB に存在するまで handler をブロック」する
仕組み）として利用されているだけであり、値による動作切り替えには使われていない。

---

### 2. bgpmon.py — NEIGH_STATE_TABLE 書き込みの platform 差分

```python
# L49–51 __init__
self.db.connect(self.db.STATE_DB, False)
self.pipe = swsscommon.RedisPipeline(self.db.get_redis_client(self.db.STATE_DB))
self.db.delete_all_by_pattern(self.db.STATE_DB, "NEIGH_STATE_TABLE|*")
```

- 1 つの固定 STATE_DB 接続（namespace 指定なし → デフォルト namespace のみ）
- 接続時にプラットフォーム種別を参照せず
- platform 向け分岐コードなし

---

### 3. SNMP サブエージェント — マルチ ASIC 差分（動作上の差異のみ）

`sonic-snmpagent/src/sonic_ax_impl/mibs/vendor/cisco/bgp4.py` L22, L29–30:

```python
self.db_conn = Namespace.init_namespace_dbs()
Namespace.connect_all_dbs(self.db_conn, mibs.STATE_DB)
self.neigh_state_map = Namespace.dbs_keys_namespace(self.db_conn, mibs.STATE_DB, "NEIGH_STATE_TABLE|*")
```

マルチ ASIC 構成では `Namespace.init_namespace_dbs()` が全 namespace（asic0, asic1, …）の
STATE_DB 接続リストを返し、`dbs_keys_namespace()` で全 namespace の
`NEIGH_STATE_TABLE|*` を横断収集する。

これは **SNMP 読み取り側の動作**であり、`NEIGH_STATE_TABLE` 自体のスキーマ・フィールドに
変化はない。書き込み側（bgpmon.py）は各 ASIC コンテナ内で独立して動作し、
それぞれの namespace 内 STATE_DB に書き込む。

---

## プラットフォーム差分まとめ

| テーブル | 書き込み元 | switch_type / sub_role 分岐 | マルチ ASIC 対応 |
|---------|-----------|---------------------------|----------------|
| `NEIGH_STATE_TABLE` | bgpmon.py | **なし** | bgpmon は各 ASIC コンテナ内で独立動作。SNMP 読み取り時に全 namespace 横断収集 |
| `BGP_PEER_CONFIGURED_TABLE` | managers_bgp.py `update_state_db` | **なし** | bgpcfgd は各 ASIC コンテナ内で独立動作。読み取り側 (SDN コントローラ等) の挙動はスコープ外 |

---

## ソース証跡

| ファイル | 行 | 内容 |
|---------|----|------|
| `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | L271–304 | `update_state_db` — platform 分岐なし |
| `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | L119–120 | `localhost/type` を deps に登録（値参照なし） |
| `src/sonic-bgpcfgd/bgpmon/bgpmon.py` | L49–51 | STATE_DB 接続（固定、namespace 指定なし） |
| `sonic-snmpagent/src/sonic_ax_impl/mibs/vendor/cisco/bgp4.py` | L22, L29–30 | マルチ ASIC 全 namespace 横断収集 |
