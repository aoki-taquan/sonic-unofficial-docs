# SRV6_MY_SIDS — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-17
ソース: `sonic-swss/orchagent/srv6orch.cpp` / `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py`
主要関数: `Srv6Orch::createUpdateMysidEntry`, `Srv6Orch::deleteMysidEntry`, `SRv6Mgr::sids_set_handler`, `SRv6Mgr::sids_del_handler`

---

## 概要

`SRV6_MY_SIDS` テーブルへの書込みは **2 つの独立した処理パス** で副次書込みを引き起こす。

1. **bgpcfgd パス**: `SRv6Mgr` が FRR (zebra/bgpd) に vtysh コマンドを発行する
2. **Srv6Orch パス**: `Srv6Orch` が APP_DB を介して SAI / ASIC, COUNTERS_DB, CRM を更新する

CONFIG_DB 自身への書き戻しは発生しない。

---

## 1. bgpcfgd パス（SRv6Mgr → FRR）

### SET 時（`sids_set_handler`）

`managers_srv6.py:88-94` で `cfg_mgr.push_list()` に以下の vtysh コマンドを積む:

```
segment-routing
 srv6
  static-sids
   sid <ip_prefix> locator <locator_name> behavior <action> [vrf <decap_vrf>]
```

- `decap_vrf` が `"default"` の場合 `vrf` オプションは省略される (`managers_srv6.py:91-93`)
- コマンドは非同期で FRR に投入される（`cfg_mgr.push_list` は即時ではなく flush 時に一括実行）

### DEL 時（`sids_del_handler`）

`managers_srv6.py:127-131` で前回 SET 時のコマンド文字列を `directory` から取得し、`no ` を前置して発行:

```
segment-routing
 srv6
  static-sids
   no sid <ip_prefix> locator <locator_name> behavior <action> [vrf <decap_vrf>]
```

存在しない SID の削除要求はサイレント skip (`managers_srv6.py:122-124`、`log_warn` のみ)。

---

## 2. Srv6Orch パス（APPL_DB → SAI / ASIC）

`Srv6Orch` は `APP_SRV6_MY_SID_TABLE`（APP_DB）を `m_mysidTable`（`srv6orch.cpp:104`）でサブスクライブし、
エントリを `createUpdateMysidEntry()` / `deleteMysidEntry()` で処理する。

### SET 時の副次書込み

| 副次 DB / API | キー / 操作 | 条件 | ソース |
|-------------|-----------|------|--------|
| SAI / `sai_srv6_api` | `create_my_sid_entry(&entry, attrs)` | 新規エントリ | `srv6orch.cpp:1606` |
| SAI / `sai_srv6_api` | `set_my_sid_entry_attribute(VRF_ID, oid)` | `decap_vrf` 更新時 | `srv6orch.cpp:1619` |
| SAI / `sai_srv6_api` | `set_my_sid_entry_attribute(NH_ID, oid)` | `adj` 更新時 | `srv6orch.cpp:1628` |
| SAI / `sai_router_intfs_api` | `create_router_interface` (loopback RIF) | `decap_dscp_mode` 指定時のみ | `srv6orch.cpp:505` |
| SAI / `sai_tunnel_api` | `create_tunnel` (IPinIP tunnel) | `decap_dscp_mode` 指定時のみ | `srv6orch.cpp:538` |
| SAI / `sai_tunnel_api` | `create_tunnel_term_table_entry` | `decap_dscp_mode` 指定時のみ | `srv6orch.cpp:1561` |
| CRM | `incCrmResUsedCounter(CRM_SRV6_MY_SID_ENTRY)` | 新規エントリ | `srv6orch.cpp:1612` |
| COUNTERS_DB / `COUNTERS_SRV6_NAME_MAP` | `hset("", sid_key, counter_oid)` | カウンタ有効時のみ | `srv6orch.cpp:199` |
| FlexCounter タイマー | `m_counter_update_timer->start()` | カウンタ有効かつ pending 空 → 空でなくなった時 | `srv6orch.cpp:204-207` |

`decap_dscp_mode` が指定された場合（`mySidTunnelRequired()` が true）、IPinIP Tunnel オブジェクトは **DSCP モードごとに 1 個共有**され、SID ごとに新規作成されない（`createMySidIpInIpTunnel` は同一 dscp_mode の tunnel を再利用する）。

### DEL 時の副次書込み

| 副次 DB / API | キー / 操作 | 条件 | ソース |
|-------------|-----------|------|--------|
| SAI / `sai_srv6_api` | `remove_my_sid_entry(&entry)` | 常時 | `srv6orch.cpp:1669` |
| CRM | `decCrmResUsedCounter(CRM_SRV6_MY_SID_ENTRY)` | 常時 | `srv6orch.cpp:1675` |
| COUNTERS_DB / `COUNTERS_SRV6_NAME_MAP` | `hdel("", sid_key)` | カウンタ有効時のみ | `srv6orch.cpp:223` |
| FLEX_COUNTER_DB | `clearCounterIdList(counter_oid)` | カウンタ有効かつ VID→RID 解決済み | `srv6orch.cpp:229` |
| SAI / `sai_tunnel_api` | `remove_tunnel_term_table_entry` | `tunnel_term_entry != NULL` | `srv6orch.cpp:1698` |
| SAI / `sai_tunnel_api` | `remove_tunnel` (IPinIP, refcount=0 の時) | `tunnel_term_entry != NULL` | `srv6orch.cpp:1704` |
| SAI / `sai_router_intfs_api` | `remove_router_interface` (loopback RIF, refcount=0) | `tunnel_term_entry != NULL` | `srv6orch.cpp:deinitIpInIpTunnel` |
| VRFOrch refcount | `decreaseVrfRefCount(dt_vrf)` | `mySidVrfRequired(endBehavior)` == true | `srv6orch.cpp:1683` |
| NeighOrch refcount | `decreaseNextHopRefCount(nexthop, 1)` | `mySidNextHopRequired(endBehavior)` == true | `srv6orch.cpp:1689` |

---

## 3. in-memory 副作用（Srv6Orch 内部）

- `srv6_my_sid_table_[key]` — SET 時にキャッシュ登録、DEL 時に `erase()` (`srv6orch.cpp:1652, 1711`)
- `m_pendingSRv6MySIDEntries` — nexthop 未解決時の保留リスト (`srv6orch.cpp:1524-1542`)
  - Neighbor ADD イベント受信で自動再インストール (`srv6orch.cpp:1224-1260`)

---

## フロー概要

```
CONFIG_DB SRV6_MY_SIDS|<locator>|<prefix>
  ├─► bgpcfgd SRv6Mgr::sids_set_handler
  │    └─► cfg_mgr.push_list → FRR vtysh (segment-routing srv6 static-sids sid ...)
  └─► APP_DB APP_SRV6_MY_SID_TABLE (fpmsyncd 等 or bgpcfgd 経由)
        └─► Srv6Orch::createUpdateMysidEntry
              ├─ [dscp_mode指定] SAI create_router_interface (loopback RIF)
              ├─ [dscp_mode指定] SAI create_tunnel (IPinIP)
              ├─ [dscp_mode指定] SAI create_tunnel_term_table_entry
              ├─ SAI create_my_sid_entry / set_my_sid_entry_attribute
              ├─ CRM incCrmResUsedCounter(CRM_SRV6_MY_SID_ENTRY)
              └─ [カウンタ有効] COUNTERS_DB COUNTERS_SRV6_NAME_MAP hset(sid_key, counter_oid)
                    └─ 1秒タイマー後: FLEX_COUNTER_DB setCounterIdList
```

---

## 注記

- CONFIG_DB / STATE_DB への書き戻しは発生しない。
- APPL_DB への直接書込みも発生しない（`Srv6Orch` は APPL_DB を読むのみ）。
- bgpcfgd パスと Srv6Orch パスは独立して動作する。CONFIG_DB 変更が両パスに伝播するかはシステム構成依存。
- IPinIP トンネルの SAI オブジェクトは `decap_dscp_mode` 値ごとに 1 つ共有される（参照カウントで管理）。
