# MACSEC_PROFILE — 副次 DB 書込・外部副作用分析 (Phase F)

- ソース: `sonic-swss/cfgmgr/macsecmgr.cpp`、`sonic-swss/orchagent/macsecorch.cpp`
- 対象テーブル: `CONFIG_DB:MACSEC_PROFILE`

---

## 1. ファイルシステム副作用

### `/etc/wpa_supplicant.conf`

`macsecmgrd::startWPASupplicant()` が `fork()` + `execl()` で `/sbin/wpa_supplicant` を起動する際、
コンパイル時マクロ `WPA_CONF = "/etc/wpa_supplicant.conf"` をコンフィグファイルとして指定する。

```cpp
// macsecmgr.cpp L715
exit(execl(
    WPA_SUPPLICANT_CMD,
    WPA_SUPPLICANT_CMD,
    "-s",
    "-D", "macsec_sonic",
    "-g", sock.c_str(),
    NULL));
// ※ -c /etc/wpa_supplicant.conf は wpa_supplicant のデフォルトパスとして参照
```

- **書き込みなし**: `macsecmgrd` 自身はこのファイルを変更しない。
- MKA パラメータ（CAK/CKN/priority 等）は `wpa_cli set_network <id> <key> <value>` でランタイム注入される。

---

## 2. APPL_DB への書き込み

`macsecmgrd` は APPL_DB に直接書き込まない。APPL_DB への書き込みは `macsecorch` が担う。

### macsecorch が Consumer として購読する APPL_DB テーブル

```cpp
// macsecorch.cpp L872-L890
{{APP_MACSEC_PORT_TABLE_NAME, SET_COMMAND},    &MACsecOrch::taskUpdateMACsecPort},
{{APP_MACSEC_PORT_TABLE_NAME, DEL_COMMAND},    &MACsecOrch::taskDeleteMACsecPort},
{{APP_MACSEC_EGRESS_SC_TABLE_NAME, SET_COMMAND},   &MACsecOrch::taskUpdateEgressSC},
{{APP_MACSEC_EGRESS_SC_TABLE_NAME, DEL_COMMAND},   &MACsecOrch::taskDeleteEgressSC},
{{APP_MACSEC_INGRESS_SC_TABLE_NAME, SET_COMMAND},  &MACsecOrch::taskUpdateIngressSC},
{{APP_MACSEC_INGRESS_SC_TABLE_NAME, DEL_COMMAND},  &MACsecOrch::taskDeleteIngressSC},
{{APP_MACSEC_EGRESS_SA_TABLE_NAME, SET_COMMAND},   &MACsecOrch::taskUpdateEgressSA},
{{APP_MACSEC_EGRESS_SA_TABLE_NAME, DEL_COMMAND},   &MACsecOrch::taskDeleteEgressSA},
{{APP_MACSEC_INGRESS_SA_TABLE_NAME, SET_COMMAND},  &MACsecOrch::taskUpdateIngressSA},
{{APP_MACSEC_INGRESS_SA_TABLE_NAME, DEL_COMMAND},  &MACsecOrch::taskDeleteIngressSA},
```

これらのテーブルには `wpa_supplicant` / `macsec_sonic` ドライバが MKA セッション確立時に書き込み、
`macsecorch` が変更を検知して SAI オブジェクトを操作する。

---

## 3. STATE_DB への書き込み

`macsecorch` が SAI MACsec オブジェクト作成に成功すると STATE_DB へ書き込む。

```cpp
// macsecorch.cpp L633-L637
m_state_macsec_port(state_db, STATE_MACSEC_PORT_TABLE_NAME),
m_state_macsec_egress_sc(state_db, STATE_MACSEC_EGRESS_SC_TABLE_NAME),
m_state_macsec_ingress_sc(state_db, STATE_MACSEC_INGRESS_SC_TABLE_NAME),
m_state_macsec_egress_sa(state_db, STATE_MACSEC_EGRESS_SA_TABLE_NAME),
m_state_macsec_ingress_sa(state_db, STATE_MACSEC_INGRESS_SA_TABLE_NAME),
```

| STATE_DB テーブル | set() 呼び出し箇所 | del() 呼び出し箇所 |
|-----------------|-----------------|-----------------|
| `STATE_MACSEC_PORT_TABLE` | L1535 (MACsec ポート有効化後) | L1792 (無効化時) |
| `STATE_MACSEC_EGRESS_SC_TABLE` | L2039 (Egress SC 作成後) | L2161 (SC 削除時) |
| `STATE_MACSEC_INGRESS_SC_TABLE` | L2043 (Ingress SC 作成後) | L2165 (SC 削除時) |
| `STATE_MACSEC_EGRESS_SA_TABLE` | L2371 (Egress SA 作成後、SAK ロールオーバー毎) | L2433 (SA 削除時) |
| `STATE_MACSEC_INGRESS_SA_TABLE` | L2376 (Ingress SA 作成後、SAK ロールオーバー毎) | L2437 (SA 削除時) |

---

## 4. STATE_DB 参照（読み取りのみ）

`macsecmgrd::isPortStateOk()` が `STATE_PORT_TABLE` を読み取り、ポート ready 状態を確認する。書き込みなし。

```cpp
// macsecmgr.cpp L274
m_statePortTable(stateDb, STATE_PORT_TABLE_NAME)

// macsecmgr.cpp L622-L626
if (m_statePortTable.get(port_name, temp)
    && get_value(temp, "state", state)
    && state == "ok"
    && get_value(temp, "netdev_oper_status", oper_status)
    && oper_status == "up")
```

ポートが未 ready の場合は `task_need_retry` を返し、ポーリングを継続する。

---

## 5. プロセス副作用

| プロセス | 操作 | 条件 |
|---------|------|------|
| `/sbin/wpa_supplicant` | `fork()` + `execl()` で子プロセス起動 | `enableMACsec()` 時 |
| `/sbin/wpa_supplicant` | `SIGINT` 送信 + `waitpid()` で終了 | `disableMACsec()` / MACsec 無効化時 |
| `/sbin/wpa_cli` | 複数回 `exec()` 呼び出し（set_network パラメータ注入） | `configureMACsec()` 内 |

UDS ソケット `/var/run/wpa_supplicant/<port_name>` が通信路として使われる。

---

*Generated: 2026-05-16 | Source commit: sonic-swss/cfgmgr/macsecmgr.cpp (HEAD)*
