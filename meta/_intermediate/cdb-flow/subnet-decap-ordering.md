# SUBNET_DECAP — Phase B: ordering / 順序依存調査メモ

調査日: 2026-05-16
調査対象: sonic-swss orchagent/tunneldecaporch.cpp、orchagent/routeorch.cpp、
          orchagent/vnetorch.cpp、orchagent/orchdaemon.cpp、
          sonic-buildimage dockers/docker-orchagent/ipinip.json.j2

---

## 1. 初期化順序

orchdaemon.cpp 行 347 で `TunnelDecapOrch` がインスタンス化される。
この時点でコンストラクタ内部で CONFIG_DB の `SUBNET_DECAP` テーブルを即時
`pops()` し、`doSubnetDecapTask()` を呼び出す（行 39-46）。
これにより **orchagent 起動時に SUBNET_DECAP の状態が subnetDecapConfig 構造体
へ先読み** される。その後 Consumer として `addExecutor` に登録することで
以降の差分更新を受信する（行 48）。

初期化順序の依存:
1. `PortsOrch` が `allPortsReady()` を返す前は `doTask()` が早期リターン（行 55-57）
2. `SUBNET_DECAP` は `CONFIG_DB` を直接購読するため `tunnelmgrd` を経由しない
3. `TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE` は `APP_DB` 経由なので
   `ipinip.json.j2` が生成した JSON が swss コンテナ起動時に APP_DB に投入されるまで
   tunnel エントリが存在しない

## 2. SUBNET_DECAP → TUNNEL_DECAP_TERM 生成の順序依存

- `SUBNET_DECAP` が enable のとき、`doDecapTunnelTermTask()` は
  `subnetDecapConfig.src_ip` / `src_ip_v6` を参照して tunnel term の `src_ip` を補完する
- よって **SUBNET_DECAP の処理が tunnel term 処理より前に完了している必要がある**
- コンストラクタで `pops()` による先読みを行うのは、この順序依存を回避するため
- tunnel 自体が未存在の場合は `unhandledDecapTerms` に積まれ、
  tunnel が追加されたタイミングで `processUnhandledDecapTunnelTerms()` が処理する

## 3. VIP ルートとの連動（routeorch.cpp）

- `RouteOrch::addRoute()` 内で VIP ルートが追加される際に
  `createVipRouteSubnetDecapTerm()` を呼び出す（行 2714-2718）
- この時点で `gTunneldecapOrch->getSubnetDecapConfig().enable` が `false` ならば
  tunnel term は作成されない
- **SUBNET_DECAP → RouteOrch のルート投入** という順序が正しい動作を保証する
- 同様に VNet ルート（VNetRouteOrch）も `createSubnetDecapTerm()` / `removeSubnetDecapTerm()`
  で同一の `subnetDecapConfig` を参照する（vnetorch.cpp 行 1563-1593）

## 4. ipinip.json.j2 によるビルド時プロビジョニング順序

`ipinip.json.j2` は `SUBNET_DECAP.status == 'enable'` を確認してから
`TUNNEL_DECAP_TABLE:IPINIP_SUBNET` および `TUNNEL_DECAP_TABLE:IPINIP_SUBNET_V6` の
エントリを生成する（行 93-123, 160-189）。
- `IPINIP_SUBNET` / `IPINIP_SUBNET_V6` トンネルは `subnet_decap.enable = true` の場合のみ作成
- VLAN サブネットの MP2MP term (`subnet_type: vlan`) もこの JSON で静的投入
- VIP 系の MP2MP term (`subnet_type: vip`) は routeorch / vnetorch が動的生成

## 5. warm-reboot 挙動

`tunneldecaporch.cpp` に warm reboot 固有のコードパスは存在しない。
- `subnetDecapConfig` は構造体でメモリ上に保持されるため、warm-reboot で orchagent が
  再起動すると **コンストラクタの `pops()` による再読み込み** が発生する
- CONFIG_DB は永続ストアなので SUBNET_DECAP の設定値は保持される
- APP_DB の `TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE` は SAI reconciliation
  フェーズで再プログラムされる（通常の warm-reboot reconcile と同一フロー）
- `unhandledDecapTerms` は再起動でリセットされるが、APP_DB からの再投入で再処理される

## 6. 削除操作の順序

DEL_COMMAND 受信時（行 691-694）:
- `subnetDecapConfig.enable = false` に設定
- 既存の tunnel term エントリは即座には削除されない（ガベージコレクション的な挙動なし）
- 次回の `doDecapTunnelTermTask` で新規の subnet decap term が作成されなくなるだけ
- 既存 term の明示的削除には `TUNNEL_DECAP_TERM_TABLE` の DEL 操作が必要

---

refs:
- sonic-swss orchagent/tunneldecaporch.cpp (L39-48, L69-72, L392-522, L636-694)
- sonic-swss orchagent/tunneldecaporch.h (L48-55, L97-103)
- sonic-swss orchagent/routeorch.cpp (L2714-2718, L3220-3251)
- sonic-swss orchagent/vnetorch.cpp (L1563-1594)
- sonic-swss orchagent/orchdaemon.cpp (L343-348)
- sonic-buildimage dockers/docker-orchagent/ipinip.json.j2 (L37-42, L93-123, L160-190)
