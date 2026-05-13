# FLEX_COUNTER_TABLE 値依存挙動分析

## enum フィールド

### FLEX_COUNTER_STATUS (flexcounterorch.cpp L225-356)
- `enable`: ポーリング開始。グループ別に追加処理:
  - PORT: m_port_counter_enabled = true → ポート統計 counter_id_list 投入
  - PORT_BUFFER_DROP: m_port_buffer_drop_counter_enabled = true
  - QUEUE: m_queue_enabled = true → キュー counter_id_list
  - QUEUE_WATERMARK: m_queue_watermark_enabled = true
  - PG_DROP: m_pg_enabled = true
  - PG_WATERMARK: m_pg_watermark_enabled = true
  - WRED_ECN_PORT: m_wred_port_counter_enabled = true
  - WRED_ECN_QUEUE: m_wred_queue_counter_enabled = true
  - RIF: gIntfsOrch に counter_id_list
  - BUFFER_POOL_WATERMARK: gBufferOrch に通知
  - TUNNEL: vxlan_tunnel_orch に通知
  - FLOW_CNT_ROUTE: m_route_flow_counter_enabled = true
- `disable`: 対応グループのカウンタ無効化。FLOW_CNT_ROUTE は m_route_flow_counter_enabled=false
- 未設定: デフォルト disable（コメント: "counters are disabled for polling by default"）

## 結論
enum 有り: FLEX_COUNTER_STATUS (enable/disable)。グループごとに enable 時の追加処理が異なる。
