# chassis-orch ordering (Phase B)

対象ファイル: `docs/reference/config-db/chassis-orch.md`
調査ソース: `orchagent/chassisorch.cpp`, `orchagent/chassisorch.h`, `orchagent/orchdaemon.cpp`

## 依存関係サマリ

ChassisOrch (`chassis_frontend_orch`) は `m_orchList` の `gPbhOrch` の直後（line 571）に登録される。
これは初期一覧（line 503: `{gSwitchOrch, gCrmOrch, gPortsOrch, ...}` の後）の push_back 群のうち比較的前半。

生成時（orchdaemon.cpp:279-294）の依存解決順:
1. `VNetOrch` 生成（APP_DB 側 VNet テーブル管理）
2. `VNetCfgRouteOrch` 生成
3. **`VNetRouteOrch` 生成** ← ChassisOrch が constructor 引数として受け取る唯一の依存
4. `ChassisOrch` 生成（VNetRouteOrch ポインタを保持）

m_orchList での処理順（抜粋）:
- ... gAclOrch → gPbhOrch → **chassis_frontend_orch** → vrf_orch → vxlan_tunnel_orch ...
- ... cfg_vnet_rt_orch → vnet_orch → **vnet_rt_orch** (VNetRouteOrch) ...

ChassisOrch は m_orchList では VNetRouteOrch より前に登録されるが、
VNetRouteOrch は constructor 時点で既にインスタンス化済みのため問題なし。

## warm-reboot 挙動

ChassisOrch は `bake()` (Orch 基底) + `doTask()` が warm restore ループ（3 イテレーション）で呼び出される。
ChassisOrch::doTask は Consumer のキューを単純に flush するだけで、SAI 呼び出しも ASIC 状態保持も行わない。
したがって warm-reboot 時の reconciliation は VNetRouteOrch 側に委ねられ、ChassisOrch 自身は
CONFIG_DB の再通知を受けて observer を再 attach する。

## 結論

- **生成順**: VNetRouteOrch ≺ ChassisOrch（必須、constructor 引数）
- **m_orchList 処理順**: ChassisOrch は gPbhOrch の直後。VNetRouteOrch より前に処理されるが、
  ChassisOrch は VNetRouteOrch への attach/detach のみ行い SAI を直接叩かないため機能上の問題なし
- **allPortsReady ガード**: なし（ChassisOrch::doTask に early-return ガードなし）
- **warm-reboot**: 専用の restore ロジックなし。CONFIG_DB 再通知で自然に再 attach
