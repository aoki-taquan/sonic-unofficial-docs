# APPL_DB MCLAG/ICCP — Phase B 書込み順依存スキャンノート

対象テーブル: APPL_DB `MCLAG_FDB_TABLE` / `ISOLATION_GROUP_TABLE` / `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `LAG_TABLE` / `PORT_TABLE` / `INTF_TABLE`
書込主体: `mclagsyncd` (`sonic-swss/mclagsyncd/`)
上流: `iccpd` (`sonic-buildimage/src/iccpd/`)
スキャン範囲: `mclaglink.cpp` 全 IPC ハンドラ、`mclag_csm.c` / `mlacp_link_handler.c` のロール確定・状態遷移

---

## 検出した順序依存・タイミング依存

### 1. PORT / PORTCHANNEL / VLAN 先行（必須先行・自動回復ほぼなし）

- `mclagsyncd` が書く APPL_DB エントリは key やフィールド値として PORT / PORTCHANNEL / VLAN のオブジェクト名を文字列で保持する（Phase C cross-refs 参照）。
  - `MCLAG_FDB_TABLE` key: `Vlan<vid>:<mac>`、`port` フィールドに PortChannel/Port 名（`mclaglink.cpp:465-521`）。
  - `ISOLATION_GROUP_TABLE.PORTS` / `.MEMBERS`: PortChannel 名カンマ区切り（`mclaglink.cpp:237,258,274`）。
  - `LAG_TABLE` / `PORT_TABLE` key: PortChannel / Ethernet 名 prefix で振り分け（`mclaglink.cpp:407,416`）。
  - `INTF_TABLE` key: INTERFACE / VLAN_INTERFACE / PORTCHANNEL_INTERFACE のいずれか同名 IF（`mclaglink.cpp:435-461`）。
- これらの参照先 `PORT` / `PORTCHANNEL` / `VLAN` / `VLAN_MEMBER` が CONFIG_DB に未登録の場合、下流 orchagent (`fdborch` / `isolationGroupOrch` / `aclOrch` / `portsOrch` / `intfsOrch` / `lagOrch`) が `m_portsOrch->getPort()` などで解決失敗し `task_need_retry` 扱いになる。orchagent は次の `SELECT_TIMEOUT=1000ms` tick で再試行を続けるため最終的には自動回復する場合があるが、`mclagsyncd` 自身はフィードバックを受けない。
- **順序依存**: MCLAG を意図する PortChannel・所属 VLAN・MCLAG ピアリンク用 Port を **先に** CONFIG_DB に書き、`portsOrch` の `allPortsReady()` が true になってから `MCLAG_DOMAIN` / `MCLAG_INTERFACE` を SET するのが安全。
- evidence: `sonic-swss/mclagsyncd/mclaglink.cpp:407,416,465-521,237,274`, `sonic-swss/orchagent/orchdaemon.cpp:23,959`

### 2. `MCLAG_DOMAIN` の SET → iccpd ICCP セッション up → ロール確定 → `INTF_TABLE.mac_addr`（厳密順）

- `setIntfMac()` (`mclaglink.cpp:435-462`) は iccpd からの `MCLAG_MSG_TYPE_SET_INTF_MAC` を受けて `INTF_TABLE|<if>.mac_addr` を SET する。
- iccpd 側ではロール (active/standby) と system_mac が確定した後でしか `MCLAG_MSG_TYPE_SET_INTF_MAC` を送らない（`mlacp_link_handler.c` の各 send は `MLACP(csm).current_state != MLACP_STATE_EXCHANGE` を early-return：L145, L209, L1202, L1255, L1315 等）。
- mclagsyncd 側でも ICCP セッション up を示す `is_iccp_up = is_oper_up` の代入は `mclagsyncdSetIccpState()` 末尾 (`mclaglink.cpp:1355`) で行われ、これより前に来た `MCLAG_MSG_TYPE_SET_ISOLATION_GROUP` が op_len==0 で到達した場合は `p_iso_grp_tbl->del("MCLAG_ISO_GRP")` 経路に入る（`mclaglink.cpp:233-247`）。
- **順序依存**: ロール確定前の状態で `INTF_TABLE` への書込みは発生しない。ロール確定前に MCLAG_INTERFACE を消すと iccpd 側で MAC 復元送信が抑止され、`intfOrch` 経由のシステム MAC 上書きが取りこぼされる可能性がある。
- evidence: `mclaglink.cpp:435-462, 1355, 1920-1921`, `iccpd/src/mlacp_link_handler.c:145,209,1202,1255,1315`

### 3. ICCP セッション up 状態 (`is_iccp_up`) による ISOLATION_GROUP の SET/DEL 分岐

- `ISOLATION_GROUP_TABLE|MCLAG_ISO_GRP` の書込みは `is_iccp_up` の値で意味が変わる:
  - `is_iccp_up == true` かつ `op_len == 0`（全リモート IF down）: `MEMBERS=""` でエントリ保持 (`mclaglink.cpp:233-241`)。
  - `is_iccp_up == false`: エントリ自体を `del("MCLAG_ISO_GRP")` (`mclaglink.cpp:244-247`)。
  - 通常時: PortChannel のみを残した `MEMBERS` で `set(...)` (`mclaglink.cpp:251-281`)。
- `is_iccp_up` は `mclagsyncdSetIccpState()` の末尾でのみ更新される (`mclaglink.cpp:1355`)。**ICCP up 通知より前** に届いた isolation メッセージは「is_iccp_up==false」分岐で DEL 扱いになる（実運用では iccpd 側で順序が制御されているため通常発生しないが、メッセージ取りこぼし・再送時に観測されうる）。
- **順序依存**: iccpd 側で `MCLAG_MSG_TYPE_SET_ICCP_STATE(up)` を `MCLAG_MSG_TYPE_SET_ISOLATION_GROUP` より先に送る順序が暗黙の前提。
- evidence: `mclaglink.cpp:233-281, 1355`

### 4. `LAG_TABLE.learn_mode` の SET → ICCP up 後の `"hardware"` 戻し（厳密順）

- MCLAG 起動時、`mclagsyncd` はリモート側 PortChannel の MAC 学習を `"disable"` に落とすメッセージを iccpd から受け、APPL_DB `LAG_TABLE.learn_mode="disable"` を書く（`mclaglink.cpp:393-407`、`MCLAG_SUB_OPTION_TYPE_MAC_LEARN_DISABLE`）。
- ICCP セッション確立後、ロール確定・MAC 同期完了に伴って iccpd は `MCLAG_SUB_OPTION_TYPE_MAC_LEARN_ENABLE` を送り、`learn_mode="hardware"` に戻す。
- **順序依存**: `LAG_TABLE.learn_mode` は中間状態（空 / 別値）を取らず、必ず `"disable" → "hardware"` の遷移を経る。CONFIG_DB を直接いじって PortChannel を再構成する場合、ICCP 切断 → 再 EXCHANGE の間は学習が hardware に戻らないため、ピア間で MAC が見えない時間が生じる。
- evidence: `mclaglink.cpp:393-407`

### 5. `LAG_TABLE.traffic_disable` はロール確定後しか書かれない

- `mclagsyncdSetTrafficDisable()` (`mclaglink.cpp:1300-1310`) は `MCLAG_MSG_TYPE_SET_TRAFFIC_DIST_DISABLE` / `_ENABLE` を受けて `traffic_disable` を `"true"` / `"false"` で書く。
- iccpd は active ロール確定 + 系統 down 検出時に `disable=true` を送り、リカバリで `false` に戻す（`mlacp_link_handler.c:1430-1437` 系の `MLACP_STATE_EXCHANGE` ガード）。
- **順序依存**: フィールド不在 = `lagOrch` のデフォルト `"false"`（分散有効）。`traffic_disable=true` を観測する前に PortChannel を削除すると、SAI 側に「分散無効」の残骸が残る可能性がある（消費側 `portsOrch` の `task_failed` パスで `task_need_retry` にならないため）。
- evidence: `mclaglink.cpp:1300-1310`, `mlacp_link_handler.c:1430-1437`

### 6. DEL 順序: `MCLAG_DOMAIN` 先 DEL → iccpd 切断 → STATE_DB 自動 cleanup

- CONFIG_DB `MCLAG` (MCLAG_DOMAIN) を DEL すると `mclagsyncd` は `processMclagDomainCfg()` で iccpd に削除を通知し、iccpd 側で `mclagsyncdDelIccpInfo()` 経由の `del(<mlag_id>)` が `STATE_MCLAG_TABLE` に向けて出る (`mclaglink.cpp:1480-1505`)。
- APPL_DB 側の `MCLAG_FDB_TABLE` / `INTF_TABLE.mac_addr` / `LAG_TABLE.learn_mode` は **iccpd からの明示 DEL メッセージがない限り残る**。`MCLAG_FDB_TABLE` は iccpd が `del_remote_static_mac_address()` 経由で個別 DEL するため、ICCP セッション切断後にしか APPL_DB から消えない。
- **順序依存**: 「`MCLAG_INTERFACE` を残したまま `MCLAG_DOMAIN` を DEL → 直後に `PORTCHANNEL` を DEL」順序にすると、`MCLAG_FDB_TABLE` の残骸が消費側 `fdborch` の retry ループに残る。`MCLAG_INTERFACE` を先に DEL してから `MCLAG_DOMAIN` を DEL する順序が安全。
- evidence: `mclaglink.cpp:1480-1505, 655-892`

### 7. `mclagsyncd` 起動順 — `DEVICE_METADATA.mac` 先行必須

- `mclagsyncdFetchSystemMacFromConfigdb()` (`mclaglink.cpp:127-128`) は起動直後 `accept()` 前に呼ばれ、`CONFIG_DB|DEVICE_METADATA|localhost.mac` を読む。空なら `SWSS_LOG_ERROR` で `m_system_mac` 空のまま続行。
- 外側 `while(1)` の retry で再 fetch する経路はあるが、ICCP up 通知をすでに送出した iccpd と再ハンドシェイクするまで system_mac は空になる。
- **順序依存**: `DEVICE_METADATA|localhost.mac` の書込みが `mclagsyncd` 起動より後ろにずれると、初期 ICCP セッションで `system_mac` 空伝播の事故が起きうる。
- evidence: `mclaglink.cpp:127-128`, `mclagsyncd.cpp:44-121`

---

## 緩和策まとめ

| 操作 | 推奨順 | 根拠 |
|---|---|---|
| MCLAG 構築 | `PORT` / `VLAN` / `VLAN_MEMBER` / `PORTCHANNEL` / `PORTCHANNEL_MEMBER` → `MCLAG_DOMAIN` → `MCLAG_INTERFACE` / `MCLAG_UNIQUE_IP` | 依存 1, 2 |
| MCLAG 解体 | `MCLAG_INTERFACE` / `MCLAG_UNIQUE_IP` → `MCLAG_DOMAIN` → `PORTCHANNEL` | 依存 6 |
| `DEVICE_METADATA.mac` 変更 | `mclagsyncd` 停止 → CONFIG_DB 更新 → `mclagsyncd` 再起動 | 依存 7 |
| 学習モード手動切替 | iccpd 側操作のみ。APPL_DB 直書きは非推奨 | 依存 4 |

## 自動回復可否

- 依存 1（PORT/PORTCHANNEL/VLAN 先行）: `task_need_retry` で部分自動回復。
- 依存 2-5（ICCP up / ロール確定）: 自動回復は iccpd の再 EXCHANGE 経由のみ。途中で `mclagsyncd` 再起動が走ると全エントリ再生成。
- 依存 6-7（DEL / system_mac）: 自動回復なし。手動再起動 or 明示 SET 必要。
