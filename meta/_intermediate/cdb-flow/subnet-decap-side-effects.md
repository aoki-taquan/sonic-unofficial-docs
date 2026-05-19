# SUBNET_DECAP — Phase F 副次 DB 書込 (調査メモ)

対象ページ: `docs/reference/config-db/subnet-decap.md`
調査日: 2026-05-19
調査者: batch-q67-f

## 調査ソース

- `sonic-swss/orchagent/tunneldecaporch.cpp`（`TunnelDecapOrch` クラス全体）
- `sonic-swss/orchagent/tunneldecaporch.h` L34-35（STATE_DB テーブルフィールド宣言）
- `sonic-swss/orchagent/routeorch.cpp` L2714-2718, L3220-3251（VIP ルート連動）
- `sonic-swss/orchagent/vnetorch.cpp` L1563-1594（VNet ルート連動）

## 副次 DB 書込の調査結果

### STATE_DB 書込（直接）

`TunnelDecapOrch` は STATE_DB に以下のテーブルを書き込む。

| キー | DB | 書込タイミング | evidence |
|------|----|---------------|----------|
| `STATE_TUNNEL_DECAP_TABLE:<tunnel_name>` | STATE_DB | トンネルオブジェクト追加 / 削除完了時 | tunneldecaporch.cpp:34, 287 |
| `STATE_TUNNEL_DECAP_TERM_TABLE:<tunnel_name>:<term_key>` | STATE_DB | tunnel term 追加 / 削除完了時 | tunneldecaporch.cpp:35 |

### APP_DB 書込（間接：RouteOrch / VNetRouteOrch 経由）

`SUBNET_DECAP.enable=true` の状態で VIP ルートが追加されると、`RouteOrch::addRoute()` および `VNetRouteOrch::set()` が以下を APP_DB に書き込む。これは `SUBNET_DECAP` テーブルが直接書き込むのではなく、他の orchagent ハンドラが `getSubnetDecapConfig()` を参照して副次的に生成する。

| キー | DB | 書込トリガー | evidence |
|------|----|------------|----------|
| `TUNNEL_DECAP_TERM_TABLE:IPINIP_SUBNET:<vip_prefix>` | APP_DB | VIP ルート追加（`subnet_type: vip`、MP2MP） | routeorch.cpp:3220-3251 |
| `TUNNEL_DECAP_TERM_TABLE:IPINIP_SUBNET_V6:<vip_prefix>` | APP_DB | IPv6 VIP ルート追加 | vnetorch.cpp:1563-1594 |

### APPL_DB / COUNTERS_DB / ASIC_DB への直接書込

`TunnelDecapOrch` 自身は APPL_DB・COUNTERS_DB への直接書込を行わない。ASIC_DB への反映は SAI (`sai_tunnel_api`) 経由で行われ、orchagent フレームワークが管理する。
