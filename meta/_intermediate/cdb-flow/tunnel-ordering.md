# TUNNEL — Phase B: 書込み順依存調査

対象テーブル: `TUNNEL|<mux_tunnel>`
Consumer: `tunnelmgrd` (`sonic-swss/cfgmgr/tunnelmgr.cpp`)、`tunneldecaporch` (`sonic-swss/orchagent/tunneldecaporch.cpp`)
スキャン範囲: `doTunnelTask()`, `doLpbkIntfTask()`, `doPeerSwitchTask()`, `addDecapTunnel()`, `addDecapTunnelTermEntry()`
Evidence: sonic-swss sha `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 検出した順序依存・タイミング依存

### 1. PEER_SWITCH 先行必須（Linux kernel tunnel 作成）

`doTunnelTask()` は `m_peerIp` が空の場合、`configIpTunnel()` をスキップして
`SWSS_LOG_NOTICE("Peer/Remote IP not configured")` を出力し return する。

- `m_peerIp` は `doPeerSwitchTask()` が `PEER_SWITCH` テーブルの `address_ipv4` を受け取った時に設定される。
- `TUNNEL` SET が `PEER_SWITCH` より先に来ると、tunnelmgrd は Linux kernel に
  `ip tunnel add tun0 mode ipip local <dst_ip> remote <peer_ip>` を実行できない。
- **重要**: `PEER_SWITCH` 設定後の自動再処理は行われない。`PEER_SWITCH` 設定後に `TUNNEL` を再 SET する必要がある。
- evidence: `tunnelmgr.cpp` L258-261

**推奨順序**:
```
SET PEER_SWITCH|<peer_name>  address_ipv4=<peer_ip>
--- その後 ---
SET TUNNEL|MuxTunnel0  tunnel_type=IPINIP  src_ip=<peer_ip>  dst_ip=<local_ip>  ...
```

### 2. LOOPBACK_INTERFACE|Loopback3 先行推奨（kernel tunnel IP 付与）

`doLpbkIntfTask()` は `LOOPBACK_INTERFACE` テーブルを購読し、`Loopback3` の IP prefix を
`m_loopbackIpCache` に収集する。`tunnelmgrd` は Linux kernel トンネル IF (`tun0`) の
ローカル IP を `Loopback3` から取得する (`LOOPBACK_SRC = "Loopback3"` ハードコード)。

- `LOOPBACK_INTERFACE|Loopback3` の prefix が未設定のまま `TUNNEL` SET が来ると、
  `tun0` へのアドレス付与がスキップされる。
- `Loopback3` が後から設定された場合は `m_tunnelCache` が空でなければ遅延付与される。
- evidence: `tunnelmgr.cpp` L19 (`LOOPBACK_SRC = "Loopback3"`), L339, L405

**推奨順序**:
```
SET LOOPBACK_INTERFACE|Loopback3|<ip_prefix>  ""
--- その後 ---
SET TUNNEL|MuxTunnel0  ...
```

### 3. DSCP_TO_TC_MAP 先行必須（decap_dscp_to_tc_map 使用時）

`tunneldecaporch.cpp` が `gQosOrch->resolveTunnelQosMap()` を呼ぶ際、
指定した map 名が未作成の場合は `task_need_retry` を返し、当該 TUNNEL エントリの処理が
無限リトライ状態に陥る。

- `decap_dscp_to_tc_map` フィールドに指定した `DSCP_TO_TC_MAP|<name>` を先に作成してから `TUNNEL` SET を行うこと。
- evidence: `tunneldecaporch.cpp` L215-221

```
SET DSCP_TO_TC_MAP|<map_name>  ...
--- その後 ---
SET TUNNEL|MuxTunnel0  decap_dscp_to_tc_map=<map_name>  ...
```

### 4. TC_TO_PRIORITY_GROUP_MAP 先行必須（decap_tc_to_pg_map 使用時）

`decap_tc_to_pg_map` フィールドも同様に `gQosOrch->resolveTunnelQosMap()` で OID 解決される。
未作成の場合は `task_need_retry` で無限待機。evidence: `tunneldecaporch.cpp` L230-236

### 5. SAI 内部呼び出し順序 (`addDecapTunnel`)

`TUNNEL` SET を受けた `tunneldecaporch` は `addDecapTunnel()` 内で以下の順序で SAI オブジェクトを作成する。

| SAI ステップ | SAI API | 依存リソース | evidence |
|------------|---------|------------|---------|
| 1. Overlay RIF 作成 | `sai_router_intfs_api->create_router_interface()` | `gVirtualRouterId` (デフォルト VRF OID)。`SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID` に設定 | `tunneldecaporch.cpp` L741-753 |
| 2. トンネル基本属性 | tunnel_attrs push: TYPE, OVERLAY_INTERFACE (ステップ1 OID), UNDERLAY_INTERFACE (gUnderlayIfId) | ステップ 1 の overlayIfId が必要 | `tunneldecaporch.cpp` L763-780 |
| 3. ECN/TTL/DSCP モード | DECAP_ECN_MODE, ENCAP_ECN_MODE, DECAP_TTL_MODE, DECAP_DSCP_MODE を push | ecn/ttl/dscp フィールド値。create-only 属性のため初回のみ有効 | `tunneldecaporch.cpp` L782-829 |
| 4. DSCP_TO_TC_MAP 付与 | `SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` push | `dscp_to_tc_map_id != SAI_NULL_OBJECT_ID` 時のみ。ステップ 3 で OID 解決済みが条件 | `tunneldecaporch.cpp` L831-837 |
| 5. TC_TO_PG_MAP 付与 | `SAI_TUNNEL_ATTR_DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP` push | `tc_to_pg_map_id != SAI_NULL_OBJECT_ID` 時のみ | `tunneldecaporch.cpp` L839-845 |
| 6. トンネル作成 | `sai_tunnel_api->create_tunnel()` | ステップ 1-5 の tunnel_attrs を一括送信 | `tunneldecaporch.cpp` L849 |
| 7. Decap Term Entry 作成 | `sai_tunnel_api->create_tunnel_term_table_entry()` | ステップ 6 の `tunnel_id` と `gVirtualRouterId` が必要。`SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_VR_ID` に gVirtualRouterId を設定 | `tunneldecaporch.cpp` L922, L979 |

**重要**: ステップ 4/5 の QoS map は `addDecapTunnel()` 呼び出し前の `doTask()` ループ内で
`task_need_retry` チェックが行われる (L290)。未解決の場合は `addDecapTunnel()` 自体が呼ばれない。

### 6. VRF (gVirtualRouterId) の暗黙依存

`addDecapTunnel()` (L741) と `addDecapTunnelTermEntry()` (L922) の両方が `gVirtualRouterId` を参照する。

- `gVirtualRouterId` は orchagent 起動時に `intfsOrch` が初期化するデフォルト VRF の OID。
- CONFIG_DB の `VRF` テーブル (ユーザー定義 VRF) とは異なり、ハードコードでデフォルト VRF が使われる。
- `tunneldecaporch` は VRF 別トンネル作成をサポートしない（デフォルト VRF 固定）。
- orchagent が正常起動し `gVirtualRouterId` が設定済みであることが前提。

### 7. ecn_mode / encap_ecn_mode は create-only（変更不可）

`tunneldecaporch.cpp` L168-183 / L793-798:

- `ecn_mode` / `encap_ecn_mode` は SAI `create-only` 属性。
- 既存トンネルに対してこれらフィールドを変更する SET を送ると `valid=false` となり、
  **SET 操作全体（他のフィールドを含む）が無効化**される。
- 変更が必要な場合は `DEL → SET`（トンネル削除後の再作成）が必要。

**DEL → SET が必要なケース**:
```
DEL TUNNEL|MuxTunnel0
--- 再作成 ---
SET TUNNEL|MuxTunnel0  ecn_mode=<new_value>  ...
```

### 8. CONFIG_DB TUNNEL → APPL_DB TUNNEL_DECAP_TABLE の依存チェーン

`tunnelmgrd` が CONFIG_DB `TUNNEL` を受け取ってから APPL_DB `TUNNEL_DECAP_TABLE` を書く。
`tunneldecaporch` は APPL_DB エントリを受けて SAI オブジェクトを作成する。

- **依存チェーン**:
  `CONFIG_DB TUNNEL SET` → tunnelmgrd → `APPL_DB TUNNEL_DECAP_TABLE SET` → tunneldecaporch → SAI
- APPL_DB への投影は tunnelmgrd が処理するまで発生しない（直接 APPL_DB を書かないこと）。

### 9. allPortsReady() ゲート（orchagent 側）

`tunneldecaporch` の `doTask()` は `gPortsOrch->allPortsReady()` が false の間は処理をスキップする。
PORT テーブルの初期化完了前に APPL_DB `TUNNEL_DECAP_TABLE` が届いても Consumer キューに留まる。

---

## SET 操作の推奨順序（起動時・設定初期化時）

```
1. PORT / PORTCHANNEL 初期化完了（orchdaemon が自動管理、allPortsReady() = true になるまで待機）
2. LOOPBACK_INTERFACE|Loopback3|<ip_prefix>  ""      — kernel tunnel IP ソース (LOOPBACK_SRC ハードコード)
3. PEER_SWITCH|<peer_name>  address_ipv4=<peer_ip>   — tunnelmgrd が m_peerIp を取得
4. QoS map 関連テーブル（decap_dscp_to_tc_map / decap_tc_to_pg_map 使用時）
   SET DSCP_TO_TC_MAP|<name>  ...
   SET TC_TO_PRIORITY_GROUP_MAP|<name>  ...
5. TUNNEL|MuxTunnel0  tunnel_type=IPINIP  src_ip=<peer_ip>  dst_ip=<local_ip>
                       dscp_mode=uniform  ecn_mode=copy_from_outer  ttl_mode=uniform
                       decap_dscp_to_tc_map=<map>  decap_tc_to_pg_map=<pg_map>
   → SAI 内部順序: overlay RIF (gVirtualRouterId) → create_tunnel (DSCP_TO_TC_MAP OID付き) → create_tunnel_term_table_entry
```

---

## DEL 操作の安全順序

```
1. MUX_CABLE の依存エントリを先に削除（MUX_CABLE は TUNNEL を参照）
2. TUNNEL|MuxTunnel0 DEL
   → tunnelmgrd が APPL_DB TUNNEL_DECAP_TABLE を DEL
   → tunneldecaporch が SAI DEL 順: tunnel_term_table_entry → tunnel → overlay RIF
3. PEER_SWITCH DEL（TUNNEL DEL の後）
```

---

## 順序依存サマリ

| # | 依存関係 | 強度 | 緩和策 |
|---|----------|------|--------|
| 1 | `PEER_SWITCH` SET → `TUNNEL` SET | **必須**（自動再処理なし） | `PEER_SWITCH` 後に再 SET |
| 2 | `LOOPBACK_INTERFACE\|Loopback3` → `TUNNEL` SET | 推奨（遅延付与あり） | 後から届けば `m_tunnelCache` 経由で付与 |
| 3 | `DSCP_TO_TC_MAP` SET → `TUNNEL` SET | **必須**（`task_need_retry` ループ） | QoS map 先行 SET |
| 4 | `TC_TO_PRIORITY_GROUP_MAP` SET → `TUNNEL` SET | **必須**（`task_need_retry` ループ） | QoS map 先行 SET |
| 5 | `gVirtualRouterId` 初期化 → overlay RIF 作成 → `create_tunnel` | **必須**（SAI 内部順序） | orchagent 正常起動が前提 |
| 6 | `create_tunnel` → `create_tunnel_term_table_entry` | **必須**（SAI 内部順序） | `addDecapTunnel()` 内で自動 |
| 7 | `ecn_mode` / `encap_ecn_mode` 変更: DEL → SET | **必須**（SET だけでは valid=false） | DEL → SET で再作成 |
| 8 | `CONFIG_DB TUNNEL` → `APPL_DB TUNNEL_DECAP_TABLE` | 自動（tunnelmgrd が処理） | 直接 APPL_DB 書き込み不可 |
| 9 | `allPortsReady()` 完了 → tunneldecaporch 処理 | 強制先行（自動調停） | orchdaemon 管理 |

---

*生成日: 2026-05-16*
*スキャン対象: sonic-swss sha `4305596156d70e9797e8a881b3d19b46de0bce0d`*
