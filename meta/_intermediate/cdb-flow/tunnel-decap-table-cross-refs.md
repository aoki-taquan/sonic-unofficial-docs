# tunnel-decap-table — Phase C: 暗黙参照テーブル

## 調査対象

- `sonic-swss/orchagent/tunneldecaporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/muxorch.cpp`
- `sonic-swss/orchagent/qosorch.cpp`

## 暗黙参照一覧

TUNNEL_DECAP_TABLE (APPL_DB) は CONFIG_DB テーブルを直接参照しないが、
tunneldecaporch が QoS map フィールドを OID に解決する際に QoS_TABLE を間接参照する。
また MuxOrch が TunnelDecapOrch のゲッタを通じて逆参照する。

### QoS マップ (OID 解決 — `gQosOrch->resolveTunnelQosMap`)

| 参照先テーブル | 参照フィールド | 条件 | 未作成時の挙動 | evidence |
|---|---|---|---|---|
| `DSCP_TO_TC_MAP\|<name>` | `decap_dscp_to_tc_map` | フィールドが空でないとき | `SAI_NULL_OBJECT_ID` → `task_need_retry` で無限待機 | `tunneldecaporch.cpp:L217-221` |
| `TC_TO_PRIORITY_GROUP_MAP\|<name>` | `decap_tc_to_pg_map` | フィールドが空でないとき | `SAI_NULL_OBJECT_ID` → `task_need_retry` で無限待機 | `tunneldecaporch.cpp:L232-236` |
| `TC_TO_DSCP_MAP\|<name>` | `encap_tc_to_dscp_map` | フィールドが空でないとき | `SAI_NULL_OBJECT_ID` → `task_need_retry`。OID は SAI へ push されず tunnelTable に記録。muxorch が `getQosMapId()` 経由で取得 | `tunneldecaporch.cpp:L247-257` |
| `TC_TO_QUEUE_MAP\|<name>` | `encap_tc_to_queue_map` | フィールドが空でないとき | `SAI_NULL_OBJECT_ID` → `task_need_retry`。`encap_tc_to_dscp_map` と同様に muxorch 経由でのみ消費 | `tunneldecaporch.cpp:L260-272` |

### STATE_DB ミラー (書き込み先)

| 書き込み先 | タイミング | evidence |
|---|---|---|
| `STATE_TUNNEL_DECAP_TABLE\|<tunnel_name>` | トンネル作成成功時にフィールドを STATE_DB へ同期 | `tunneldecaporch.cpp:L287` |
| `STATE_TUNNEL_DECAP_TERM_TABLE\|<tunnel_name>\|<dst_ip>` | decap term 作成成功時 | `tunneldecaporch.cpp:setDecapTunnelTermStatus()` |

### 逆参照 (MuxOrch → TunnelDecapOrch)

| 参照元 | API | 取得内容 | 条件 | evidence |
|---|---|---|---|---|
| `MuxOrch::setPeerSwitch()` | `getDstIpAddresses(MUX_TUNNEL)` | `dst_ip` リスト | PEER_SWITCH SET 時。TUNNEL_DECAP_TABLE が未作成なら `false` を返して PEER_SWITCH SET を延期 | `muxorch.cpp:L2348-2356` |
| `MuxOrch::setPeerSwitch()` | `getDscpMode(MUX_TUNNEL)` | `dscp_mode` 文字列 | 同上 | `muxorch.cpp:L2359` |
| `MuxOrch::setPeerSwitch()` | `getQosMapId(MUX_TUNNEL, encap_tc_to_dscp)` | TC→DSCP map OID | 同上 | `muxorch.cpp:L2368` |
| `MuxOrch::setPeerSwitch()` | `getQosMapId(MUX_TUNNEL, encap_tc_to_queue)` | TC→Queue map OID | 同上 | `muxorch.cpp:L2374` |

## 注意点

- `decap_dscp_to_tc_map` / `decap_tc_to_pg_map` は SAI に直接 push され QoS が機能する。未作成の場合はエントリ全体が `task_need_retry` で処理待ちになる。
- `encap_tc_to_dscp_map` / `encap_tc_to_queue_map` は SAI に push されず tunnelTable 内部に記録されるだけ。MuxOrch の Dual-ToR Peer 設定時にのみ利用される。
- TUNNEL_DECAP_TABLE が存在しないと MuxOrch が PEER_SWITCH を処理できないため、Dual-ToR 構成では TUNNEL_DECAP_TABLE の SET が PEER_SWITCH より先である必要がある。
