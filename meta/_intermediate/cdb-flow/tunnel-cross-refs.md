# TUNNEL テーブル — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/tunnel.md`
解析日: 2026-05-15
根拠ソース:
- `sonic-swss/cfgmgr/tunnelmgr.cpp` (sha 4305596)
- `sonic-swss/orchagent/tunneldecaporch.cpp` (sha 4305596)
- `sonic-swss/orchagent/muxorch.cpp` (sha 4305596)
- `sonic-swss/orchagent/qosorch.cpp` (sha 4305596)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-tunnel.yang` (sha 9ea932e)

---

## 目的

`TUNNEL` エントリが CONFIG_DB に書かれたとき、`tunnelmgrd` および `tunneldecaporch` が
**暗黙的に** 参照・依存する他テーブルのキー / フィールドを網羅する。
YANG 明示 leafref（`src_ip` → `PEER_SWITCH.address_ipv4`）に加え、
実装コードのみに現れる「暗黙 leafref 相当」の依存を列挙し、`<!-- cross-refs -->` ブロックに変換する。

---

## 1. PEER_SWITCH テーブル (YANG leafref + 実装依存)

### 参照箇所

YANG leafref (`sonic-tunnel.yang` L50-52):
```yang
type leafref {
    path "/ps:sonic-peer-switch/ps:PEER_SWITCH/ps:PEER_SWITCH_LIST/ps:address_ipv4";
}
```

実装 (`tunnelmgr.cpp` L112, L127, L252-258):
```cpp
m_cfgPeerTable(cfgDb, CFG_PEER_SWITCH_TABLE_NAME),
...
m_peerIp = fvValue(j);    // PEER_SWITCH テーブルから取得
...
tunInfo.remote_ip = m_peerIp;
if (!m_peerIp.empty() && !configIpTunnel(tunInfo))
    ...
else if (m_peerIp.empty())
    SWSS_LOG_NOTICE("Peer/Remote IP not configured");
```

### 依存内容

| TUNNEL フィールド | 参照先テーブル | 参照先フィールド | 参照タイミング | 結果 |
|---|---|---|---|---|
| `src_ip` | `PEER_SWITCH` | `address_ipv4` | TUNNEL SET 処理時 | 未登録 IP は YANG leafref 違反で CONFIG_DB 書き込み拒否 |

### 特記事項

- `PEER_SWITCH.address_ipv4` が設定される前に TUNNEL SET が来ると、`m_peerIp` が空 → Linux kernel tunnel 未作成。
- 自動再処理なし。PEER_SWITCH 設定後に TUNNEL を再 SET する必要がある。

---

## 2. LOOPBACK_INTERFACE テーブル (実装ハードコード依存)

### 参照箇所

`tunnelmgr.cpp` L19, L339, L405:
```cpp
#define LOOPBACK_SRC "Loopback3"
...
if (alias == LOOPBACK_SRC && !m_tunnelCache.empty())  // L339
...
auto it = m_intfCache.find(LOOPBACK_SRC);             // L405
```

### 依存内容

| 参照先テーブル | 参照先フィールド | 条件 | 結果 |
|---|---|---|---|
| `LOOPBACK_INTERFACE\|Loopback3` | prefix (IP アドレス) | 常時（ハードコード） | `tun0` のローカル IP ソース。`Loopback3` の prefix SET より TUNNEL SET が先に来ると kernel tunnel IF へのアドレス付与が遅延 |

### 特記事項

- `LOOPBACK_SRC = "Loopback3"` はハードコード定数（CONFIG_DB 非連動）。変更不可。
- `Loopback3` の prefix が後から届いてもキャッシュ経由で tunnel アドレスが付与される（`tunnelmgr.cpp` L339 以降）。
- 推奨順序: `LOOPBACK_INTERFACE|Loopback3|<ip>` SET → PEER_SWITCH SET → TUNNEL SET。

---

## 3. QoS マップテーブル (実装依存 — 暗黙 leafref)

### 参照箇所

`tunneldecaporch.cpp` L215-272 (QosOrch::resolveTunnelQosMap 呼び出し):
```cpp
dscp_to_tc_map_id = gQosOrch->resolveTunnelQosMap(table_name, key, decap_dscp_to_tc_field_name, t);
...
tc_to_pg_map_id = gQosOrch->resolveTunnelQosMap(table_name, key, decap_tc_to_pg_field_name, t);
...
tc_to_dscp_map_id = gQosOrch->resolveTunnelQosMap(table_name, key, encap_tc_to_dscp_field_name, t);
...
tc_to_queue_map_id = gQosOrch->resolveTunnelQosMap(table_name, key, encap_tc_to_queue_field_name, t);
```

`qosorch.cpp` L113-116 (フィールド名 → テーブル名マッピング):
```cpp
{decap_dscp_to_tc_field_name, CFG_DSCP_TO_TC_MAP_TABLE_NAME},
{decap_tc_to_pg_field_name,   CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME},
{encap_tc_to_dscp_field_name, CFG_TC_TO_DSCP_MAP_TABLE_NAME},
{encap_tc_to_queue_field_name, CFG_TC_TO_QUEUE_MAP_TABLE_NAME}
```

`tunneldecaporch.cpp` L221, L236, L251, L266 (task_need_retry):
```cpp
task_status = task_process_status::task_need_retry;
```

### 依存内容

| TUNNEL フィールド | 参照先テーブル | 条件 | 解決失敗時の結果 |
|---|---|---|---|
| `decap_dscp_to_tc_map` | `DSCP_TO_TC_MAP` | 値が指定されているとき | `task_need_retry` — 当該 TUNNEL の処理が無限ループ待機 |
| `decap_tc_to_pg_map` | `TC_TO_PRIORITY_GROUP_MAP` | 値が指定されているとき | 同上 |
| `encap_tc_to_dscp_map` | `TC_TO_DSCP_MAP` | 値が指定されているとき | 同上 |
| `encap_tc_to_queue_map` | `TC_TO_QUEUE_MAP` | 値が指定されているとき | 同上 |

### 特記事項

- YANG に leafref 定義なし（文字列型のみ）。ただし orchagent は `gQosOrch->resolveTunnelQosMap()` で実際に対応する CONFIG_DB テーブルを参照する。
- 参照する QoS map が未作成の場合、当該 TUNNEL エントリの処理が `task_need_retry` でスタックし続ける。**QoS map を先に作成することが必須**。
- `encap_tc_to_dscp_map` / `encap_tc_to_queue_map` は `tunnelTable` に記録するのみで SAI には直接 push しない (`tunneldecaporch.cpp` L255-274)。これらは `muxorch` が `getQosMapId()` で取得し MUX トンネル encap に利用する。

---

## 4. MUX_CABLE テーブル (下流参照 — muxorch 経由の間接依存)

### 参照箇所

`muxorch.cpp` L2348-2377:
```cpp
IpAddresses dst_ips = decap_orch_->getDstIpAddresses(MUX_TUNNEL);
string dscp_mode_name = decap_orch_->getDscpMode(MUX_TUNNEL);
decap_orch_->getQosMapId(MUX_TUNNEL, encap_tc_to_dscp_field_name, tc_to_dscp_map_id);
decap_orch_->getQosMapId(MUX_TUNNEL, encap_tc_to_queue_field_name, tc_to_queue_map_id);
```

### 依存内容

| 依存方向 | テーブル | 役割 |
|---------|---------|------|
| TUNNEL → MUX_CABLE (逆参照) | `MUX_CABLE` | `MuxOrch::handleMuxCfg()` が TUNNEL のパラメータ (`dst_ip`, `dscp_mode`, QoS map) を `TunnelDecapOrch` 経由で読み取り、各 MUX_CABLE ポートのトンネル nexthop を設定する |

### 特記事項

- TUNNEL が MUX_CABLE を参照するのではなく、MUX_CABLE 側が TUNNEL を逆参照する。
- TUNNEL を DEL する前に `MUX_CABLE|*` を先に DEL しないと、muxorch がトンネル nexthop を解決できずエラーになる（DEL 安全順序参照）。

---

## 参照関係サマリ

```
TUNNEL
  ├─ [YANG leafref] PEER_SWITCH.address_ipv4         (src_ip — CONFIG_DB 書き込み時 YANG 検証)
  ├─ [実装依存]     LOOPBACK_INTERFACE|Loopback3      (ハードコード。tun0 ローカル IP ソース)
  ├─ [実装依存]     DSCP_TO_TC_MAP.<name>             (decap_dscp_to_tc_map — task_need_retry)
  ├─ [実装依存]     TC_TO_PRIORITY_GROUP_MAP.<name>   (decap_tc_to_pg_map — task_need_retry)
  ├─ [実装依存]     TC_TO_DSCP_MAP.<name>             (encap_tc_to_dscp_map — muxorch が取得)
  ├─ [実装依存]     TC_TO_QUEUE_MAP.<name>            (encap_tc_to_queue_map — muxorch が取得)
  └─ [逆参照]       MUX_CABLE                         (muxorch が TUNNEL パラメータを読み取る)
```

---

## evidence

- `sonic-tunnel.yang` L50-52 (`src_ip` leafref → `PEER_SWITCH.address_ipv4`)
- `tunnelmgr.cpp` L19 (`#define LOOPBACK_SRC "Loopback3"`), L112-127 (`m_cfgPeerTable` 購読, `m_peerIp` 取得), L252-258 (peer IP 未設定時の skip ロジック), L339 (`Loopback3` イベント処理), L405 (`m_intfCache.find(LOOPBACK_SRC)`)
- `tunneldecaporch.cpp` L215-272 (`resolveTunnelQosMap` 呼び出し群), L1450 (`getQosMapId()`)
- `qosorch.cpp` L113-116 (フィールド名 → CONFIG_DB テーブル名マップ), L2314 (`resolveTunnelQosMap` 実装)
- `muxorch.cpp` L2348-2377 (TUNNEL QoS map 逆参照), L2189 (`CFG_MUX_CABLE_TABLE_NAME` handler 登録)
