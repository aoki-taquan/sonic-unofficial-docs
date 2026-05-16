# loopback-interface — Side-effects 調査ノート (Phase F)

調査日: 2026-05-16  
調査対象: `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/orchagent/intfsorch.cpp`

---

## 副次書込み一覧

### 1. APPL_DB / APP_INTF_TABLE（intfmgrd → AppDB Producer）

**属性ロウ SET**（`doIntfGeneralTask()` SET パス、`intfmgr.cpp:1053`）:

```
APP_INTF_TABLE|<alias>
  vrf_name = <vrf_name>
  mac_addr = <mac_addr | "00:00:00:00:00:00">
  loopback_action = <loopback_action>  # フィールドあり時のみ
```

`m_appIntfTableProducer.set(alias, data)` で Producer Channel（APPL_DB）に書く。

**IP プレフィクスロウ SET**（`doIntfAddrTask()` SET パス、`intfmgr.cpp:1137`）:

```
APP_INTF_TABLE|<alias>|<ip-prefix>
  scope = "global"   # CONFIG_DB の scope 値は無視されハードコード
  family = "IPv4" | "IPv6"
```

IPv6 link-local (`fe80::/10`) は APP_INTF_TABLE に**書かれない**（サイレントスキップ）。

**属性ロウ / IP ロウ DEL**:
- `m_appIntfTableProducer.del(alias)` — 属性ロウ削除時
- `m_appIntfTableProducer.del(appKey)` — IP ロウ削除時（`intfmgr.cpp:1088, 1161`）

---

### 2. STATE_DB / STATE_INTERFACE_TABLE（intfmgrd → StateDB）

**属性ロウ SET**（`intfmgr.cpp:1054`）:

```
STATE_INTERFACE_TABLE|<alias>
  vrf = <vrf_name>
```

`m_stateIntfTable.hset(alias, "vrf", vrf_name)` — ハッシュフィールド 1 件のみ書く。

**IP ロウ SET**（`intfmgr.cpp:1138`）:

```
STATE_INTERFACE_TABLE|<alias>|<ip-prefix>
  state = "ok"
```

`m_stateIntfTable.hset(keys[0] + "|" + keys[1], "state", "ok")` で 1 件書く。  
IPv6 link-local は STATE_INTERFACE_TABLE にも**書かれない**。

**DEL**:
- `m_stateIntfTable.del(alias)` — 属性ロウ削除時（`intfmgr.cpp:1089`）
- `m_stateIntfTable.del(keys[0] + "|" + keys[1])` — IP ロウ削除時（`intfmgr.cpp:1162`）

---

### 3. COUNTERS_DB / COUNTERS_RIF_NAME_MAP, COUNTERS_RIF_TYPE_MAP（orchagent IntfsOrch）

`addRifToFlexCounter(id, name, type)` が呼ばれるタイミング:
- `generateInterfaceMap()` タイマー（1 秒インターバル）内で `m_rifsToAdd` リストを走査し、SAI RIF ID の COUNTERS_DB へのマッピングが確定したエントリを登録（`intfsorch.cpp:1630`）

```
COUNTERS_RIF_NAME_MAP
  <alias> = <sai_object_id>   # 例: "Loopback0" -> "oid:0x60000000xxxx"

COUNTERS_RIF_TYPE_MAP
  <sai_object_id> = <rif_type>  # 例: "oid:0x60000000xxxx" -> "SAI_ROUTER_INTERFACE_TYPE_PORT"
```

`m_rifNameTable->set("", rifNameVector)` / `m_rifTypeTable->set("", rifTypeVector)` で書く（`intfsorch.cpp:1537-1538`）。

Loopback IF の場合 `port.m_type` が `Port::PHY` / `Port::LAG` / ... に当てはまらないため、`type` が空文字列になる可能性がある。ただし IntfsOrch の `setIntf` パスでは Loopback も SAI RIF 作成対象となり、`m_rifsToAdd` に積まれる。

**DEL**（`intfsorch.cpp:1560-1561`）:
```
COUNTERS_RIF_NAME_MAP  -> hdel("", name)
COUNTERS_RIF_TYPE_MAP  -> hdel("", id)
```

FLEX_COUNTER_DB へのポーリング停止（`stopFlexCounterPolling`）も同時に実行される。

---

### 4. CHASSIS_APP_DB / SYSTEM_INTERFACE_TABLE（orchagent IntfsOrch — VOQ 環境のみ）

`isChassisDbInUse()` が true の場合のみ `voqSyncAddIntf(alias)` / `voqSyncDelIntf(alias)` が呼ばれる（`intfsorch.cpp:1316-1317, 1369-1370`）。

```
CHASSIS_APP_DB / SYSTEM_INTERFACE_TABLE|<system_alias>
  oper_status = "up" | "down"
```

Loopback に対して `gPortsOrch->getPort(alias, port)` を呼ぶが、Loopback は `Port::PHY` / `Port::LAG` ではないため `port.m_system_port_info.type` 判定でスキップされる可能性が高い。通常環境（非 VOQ）では書込みは発生しない。

---

## まとめ表

| DB | テーブル | キー | フィールド | タイミング | 根拠 |
|----|---------|------|-----------|-----------|------|
| APPL_DB | `APP_INTF_TABLE` | `<alias>` | `vrf_name`, `mac_addr`, `loopback_action` | 属性ロウ SET | `intfmgr.cpp:1053` |
| APPL_DB | `APP_INTF_TABLE` | `<alias>:<ip-prefix>` | `scope="global"`, `family` | IP ロウ SET（link-local 除く） | `intfmgr.cpp:1137` |
| STATE_DB | `STATE_INTERFACE_TABLE` | `<alias>` | `vrf` | 属性ロウ SET | `intfmgr.cpp:1054` |
| STATE_DB | `STATE_INTERFACE_TABLE` | `<alias>\|<ip-prefix>` | `state="ok"` | IP ロウ SET（link-local 除く） | `intfmgr.cpp:1138` |
| COUNTERS_DB | `COUNTERS_RIF_NAME_MAP` | `""` | `<alias>=<sai_oid>` | SAI RIF 作成後 1 秒タイマー | `intfsorch.cpp:1537` |
| COUNTERS_DB | `COUNTERS_RIF_TYPE_MAP` | `""` | `<sai_oid>=<type>` | SAI RIF 作成後 1 秒タイマー | `intfsorch.cpp:1538` |
| CHASSIS_APP_DB | `SYSTEM_INTERFACE_TABLE` | `<system_alias>` | `oper_status` | SAI RIF 作成時（VOQ 環境のみ） | `intfsorch.cpp:1317` |
