# DPU テーブル — ハードコード定数調査ノート (Phase E)

調査日: 2026-05-17  
対象ブランチ: sonic-net/sonic-swss (43055967), sonic-net/sonic-host-services (c5bbbe84), sonic-net/sonic-gnmi (eb635b7e), sonic-net/sonic-buildimage (9ea932ec)

---

## dashenifwdorch.h — テーブル名・フィールド名定数 (DashEniFwd 名前空間)

| 定数名 | 値 | 行 |
|--------|-----|-----|
| `DPU_TABLE` | `"DPU"` | `dashenifwdorch.h:63` |
| `REMOTE_DPU_TABLE` | `"REMOTE_DPU"` | `dashenifwdorch.h:64` |
| `VDPU_TABLE` | `"VDPU"` | `dashenifwdorch.h:65` |
| `VIP_TABLE` | `"VIP_TABLE"` | `dashenifwdorch.h:66` |
| `STATE` | `"state"` | `dashenifwdorch.h:75` |
| `PA_V4` | `"pa_ipv4"` | `dashenifwdorch.h:76` |
| `PA_V6` | `"pa_ipv6"` | `dashenifwdorch.h:77` |
| `NPU_V4` | `"npu_ipv4"` | `dashenifwdorch.h:78` |
| `NPU_V6` | `"npu_ipv6"` | `dashenifwdorch.h:79` |
| `DPU_IDS` | `"main_dpu_ids"` | `dashenifwdorch.h:80` |
| `VDPU_IDS` | `"vdpu_ids"` | `dashenifwdorch.h:71` |
| `PRIMARY` | `"primary_vdpu"` | `dashenifwdorch.h:72` |

## dpu_table_desc — required_attributes

`dpu_table_desc.required_attributes = { STATE, PA_V4 }` — 欠如時は Orch2 フレームワークが request reject。

## caclmgrd — テーブル名定数

| 定数名 | 値 | 行 |
|--------|-----|-----|
| `DPU_TABLE` | `"DPU"` | `caclmgrd:90` |
| swbus_port フィールド文字列 | `"swbus_port"` | `caclmgrd:1096` |

## sonic-gnmi dpuproxy/resolver.go — 接続定数

| 定数名 | 値 | 説明 | 行 |
|--------|-----|------|-----|
| `StateDB` | `6` | Redis DB インデックス (STATE_DB) | `resolver.go:10` |
| `ConfigDB` | `4` | Redis DB インデックス (CONFIG_DB) | `resolver.go:13` |
| `ChassisMidplaneTablePrefix` | `"CHASSIS_MIDPLANE_TABLE\|DPU"` | STATE_DB での DPU 状態キープレフィックス | `resolver.go:22` |
| `DPUConfigTablePrefix` | `"DPU\|dpu"` | CONFIG_DB での DPU 設定キープレフィックス | `resolver.go:25` |
| `DefaultGNMIPort` | `"50052"` | CONFIG_DB に `gnmi_port` がない場合の fallback | `resolver.go:19` |
| `commonGNMIPorts` | `["8080", "50052"]` | 接続試行ポートのフォールバックリスト（設定ポートの次に試行） | `resolver.go:104` |

## YANG 型制約

| フィールド | YANG 型 | パターン / 制約 |
|-----------|---------|----------------|
| `dpu_name` | `string` | pattern `[a-zA-Z0-9_-]+[0-9]`, length 1..255 |
| `state` | `stypes:admin_status` | enum: `up` / `down`（sonic-types.yang） |
| `local_port` | `stypes:interface_name` | interface_name 型 |
| `vip_ipv4` / `pa_ipv4` / `midplane_ipv4` | `inet:ipv4-address` | RFC 準拠 IPv4 |
| `vip_ipv6` / `pa_ipv6` | `inet:ipv6-address` | RFC 準拠 IPv6 |
| `dpu_id` | `string` | pattern `[0-7]`（1 文字, 0〜7） |
| `vdpu_id` | `string` | length 1..255 |
| `gnmi_port` / `orchagent_zmq_port` / `swbus_port` | `inet:port-number` | 1–65535 |

## 慣例値（YANG 強制なし）

| フィールド | 慣例値 | 根拠 |
|-----------|--------|------|
| `swbus_port` | `23606 + dpu_id` | YANG コメント + HLD記載; YANG 強制なし |
| `orchagent_zmq_port` | `5555` | HLD 典型値; コード側 fallback なし |
| `gnmi_port` | `50052` | resolver.go DefaultGNMIPort; HLD 記載典型値は `50051` (不一致あり) |
