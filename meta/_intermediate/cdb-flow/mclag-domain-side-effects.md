# CONFIG_DB 副次 DB 書込分析: MCLAG_DOMAIN (Phase F)

ソース: `sonic-swss/orchagent/mlagorch.cpp`, `sonic-swss/mclagsyncd/mclaglink.cpp`, `sonic-swss/fdbsyncd/fdbsync.cpp`

---

## 副次書込先サマリ

| DB | テーブル / キー | 書込トリガー | 証跡 |
|---|---|---|---|
| STATE_DB | `STATE_MCLAG_TABLE\|<domain_id>` | ICCP セッション状態変化 (iccpd→mclagsyncd) | `mclaglink.cpp:1357,1414,1460` |
| STATE_DB | `STATE_MCLAG_TABLE\|<domain_id>` (role) | ICCP ロール決定 (active/standby) | `mclaglink.cpp:1414` |
| STATE_DB | `STATE_MCLAG_TABLE\|<domain_id>` (system_mac) | システム MAC 決定時 | `mclaglink.cpp:1460` |
| STATE_DB | `STATE_MCLAG_LOCAL_INTF_TABLE\|<if_name>` | ローカル IF port_isolate 変化 | `mclaglink.cpp:1525` |
| STATE_DB | `STATE_MCLAG_REMOTE_INTF_TABLE\|<domain_id>\|<if_name>` | リモート IF oper_status 変化 | `mclaglink.cpp:1585` |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_BRIDGE_PORT:*` (読取) | peer FDB 同期のため bridge_port OID を解決 | `mclaglink.cpp:79-95` |
| APPL_DB | `FDB_TABLE\|Vlan<id>:<mac>` | iccpd からの MCLAG_FDB_OPER_ADD/DEL を受信時 | `mclaglink.cpp:512,517` |

---

## STATE_DB MCLAG_TABLE 書込詳細

`mclagsyncd` (MclagLink) は iccpd からの制御メッセージを受け取り、以下のフィールドを STATE_DB `STATE_MCLAG_TABLE|<domain_id>` に書き込む。

### oper_status フィールド

```
STATE_MCLAG_TABLE|<domain_id>  →  oper_status = "up" | "down"
```

- トリガー: iccpd が ICCP セッションの up/down を `MCLAG_MSG_TYPE_SET_ICCP_STATE` で通知
- `is_iccp_up` フラグも内部更新される
- evidence: `mclaglink.cpp` `mclagsyncdSetIccpState()` (L1319-L1365)

### role フィールド

```
STATE_MCLAG_TABLE|<domain_id>  →  role = "active" | "standby"
                                  system_mac = "<xx:xx:xx:xx:xx:xx>"
```

- トリガー: iccpd が ICCP ロールネゴシエーション完了を `MCLAG_MSG_TYPE_SET_ICCP_ROLE` で通知
- evidence: `mclaglink.cpp` `mclagsyncdSetIccpRole()` (L1367-L1421)

### system_mac フィールド単体更新

```
STATE_MCLAG_TABLE|<domain_id>  →  system_mac = "<xx:xx:xx:xx:xx:xx>"
```

- トリガー: iccpd が `MCLAG_MSG_TYPE_SET_SYSTEM_ID` で system MAC を通知
- evidence: `mclaglink.cpp` `mclagsyncdSetSystemId()` (L1423-L1484)

### DEL (ドメイン削除)

```
STATE_MCLAG_TABLE|<domain_id>  →  エントリ削除
```

- トリガー: iccpd が `MCLAG_MSG_TYPE_DEL_ICCP_INFO` で削除通知
- evidence: `mclaglink.cpp` `mclagsyncdDelIccpInfo()` (L1486-L1507)

---

## STATE_DB MCLAG_LOCAL_INTF_TABLE 書込詳細

```
STATE_MCLAG_LOCAL_INTF_TABLE|<if_name>  →  port_isolate_peer_link = "true" | "false"
```

- トリガー: MCLAG_INTERFACE に紐づくポートの port-isolation 状態変化
- evidence: `mclaglink.cpp` `setLocalIfPortIsolate()` (L1509-L1535)

---

## STATE_DB MCLAG_REMOTE_INTF_TABLE 書込詳細

```
STATE_MCLAG_REMOTE_INTF_TABLE|<domain_id>|<if_name>  →  oper_status = "up" | "down"
```

- トリガー: リモートピアの MCLAG_INTERFACE oper_status 変化を iccpd が通知
- evidence: `mclaglink.cpp` `mclagsyncdSetRemoteIfState()` (L1538-L1593)

---

## ASIC_DB bridge_port 参照

`mclagsyncd` は MCLAG ピアとの FDB エントリ同期において、ASIC_DB から SAI bridge_port OID を読み取る。

```
ASIC_STATE:SAI_OBJECT_TYPE_BRIDGE_PORT:<oid>
  SAI_BRIDGE_PORT_ATTR_PORT_ID  →  ポート OID
  SAI_BRIDGE_PORT_ATTR_TUNNEL_ID  →  トンネル OID（フォールバック）
```

- 用途: iccpd から受け取った MAC エントリのポート名を bridge_port_id に変換するため
- evidence: `mclaglink.cpp` `getBridgePortIdToAttrPortIdMap()` (L73-L96)

---

## APPL_DB FDB_TABLE 書込詳細

iccpd からの FDB ADD/DEL 通知を受け、`mclagsyncd` が APPL_DB に書き込む。

```
FDB_TABLE|Vlan<vid>:<mac>
  port  =  "<if_name>"        (ADD 時)
  type  =  "dynamic" | "dynamic_local"  (ADD 時)
```

- ADD: `MCLAG_FDB_OPER_ADD` 受信時に `p_fdb_tbl->set(fdb_key, attrs)` を実行
- DEL: `MCLAG_FDB_OPER_DEL` 受信時に `p_fdb_tbl->del(fdb_key)` を実行
- 書込後、fdbsyncd が APPL_DB を読み取り ASIC_DB へさらに転送する（orchagent 経由の sai_fdb_api）
- evidence: `mclaglink.cpp` `mclagsyncdProcessFdbEntries()` (L500-L520)

---

## MlagOrch の observer 通知 (内部 Subject/Observer)

`MlagOrch` 自身は DB に書き込まないが、以下の Subject 通知を broadcast する。

| Subject type | トリガー | 受信者 |
|---|---|---|
| `SUBJECT_TYPE_MLAG_ISL_CHANGE` | `addIslInterface()` / `delIslInterface()` | `FdbOrch` — FDB フラッシュ制御 |
| `SUBJECT_TYPE_MLAG_INTF_CHANGE` | `addMlagInterface()` / `delMlagInterface()` | `FdbOrch` — MLAG ポート判定 |

- FdbOrch はこれを受け `isMlagInterface()` / `isIslInterface()` を通じてポート down 時の FDB フラッシュをスキップ
- evidence: `mlagorch.cpp:170,187,210,231` / `fdborch.cpp:1209`

---

## ICCPd 経路まとめ

```
CONFIG_DB MCLAG_DOMAIN
  └─ mclagsyncd (MclagLink) 購読
       └─ iccpd プロセスへ CFG メッセージ転送 (Unix socket)
            ├─ ICCP セッション確立 (peer_ip:2626 TCP)
            │    └─ STATE_DB STATE_MCLAG_TABLE 書込 (oper_status / role / system_mac)
            ├─ FDB 同期 (ピア MAC 広告)
            │    └─ APPL_DB FDB_TABLE 書込 → fdbsyncd → ASIC_DB
            └─ intf 状態同期
                 └─ STATE_DB STATE_MCLAG_LOCAL/REMOTE_INTF_TABLE 書込
```
