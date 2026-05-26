---
title: SmartSwitch HA DPU-Scope-DPU-Driven 運用（CLI / 設定 / failover 確認）
description: SmartSwitch HA DPU-Scope-DPU-Driven の設定経路（DASH SDN config）、failover
  確認、BFD / next hop / split-brain のトラブルシュート手順、制限事項と干渉機能を整理する。
area: architecture
verification: code-verified
last_verified: 2026-05-26
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/smart-switch/high-availability/smart-switch-ha-dpu-scope-dpu-driven-setup.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - DPU
  - DPUS
  - MID_PLANE_BRIDGE
  cli:
  - show bfd
  - show platform
  yang:
  - sonic-smart-switch
  - sonic-dash
---

# SmartSwitch HA DPU-Scope-DPU-Driven 運用

このページは [SmartSwitch HA - DPU-Scope-DPU-Driven 構成（概要ハブ）](smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md) の派生で、**設定経路・確認・トラブルシュート・制限事項** に絞る。概念は [concepts](smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup-concepts.md)、状態遷移と protocol は [internals](smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup-internals.md) を参照。

## 1. 設定経路の前提

`DPU-Scope-DPU-Driven` の HA 設定は **[CONFIG_DB](../reference/glossary.md#term-config_db) ではなく [DASH](../reference/glossary.md#term-dash) SDN config 経由**（`HA_SET` / `HA_SCOPE`）で行う[^1]。[NPU](../reference/glossary.md#term-npu) 上で完結する従来 NOS 機能の `config` CLI からは触れず、SDN controller の [gNMI](../reference/glossary.md#term-gnmi) / DASH API を起点に programming する設計である。

`hamgrd` は SDN controller から受けた DASH config を NPU 経由で [DPU](../reference/glossary.md#term-dpu) に中継するだけで、両 DPU 間の調停はしない[^1]。したがって運用者が手動で 1 ステップずつ叩く CLI シナリオは [HLD](../reference/glossary.md#term-hld) には記載されていない（SDN controller が自動化することを前提）。

## 2. 設定例（概念フロー）

実 CLI ではなく、SDN controller が踏む順序を擬似 config で示す:

```text
# 1. HA set / HA scope を作成（AdminState=Disabled）
HA_SET:scope-A
  Pair=(DPU0@Switch0, DPU0@Switch1)
  PreferredDPU=DPU0@Switch0
HA_SCOPE:scope-A
  Role=Active            # DPU0 側
  AdminState=Disabled
HA_SCOPE:scope-A
  Role=Standby           # DPU1 側
  AdminState=Disabled

# 2. ENI / policy をすべて push（両 DPU で identical を保証）

# 3. HA を起動
HA_SCOPE:scope-A
  AdminState=Enabled

# 4. role activation request が SDN に上がってきたら approve
```

順序を守らずに `AdminState=Enabled` を先行させると、policy 不整合のまま `Active` に上がる事故になりうる。role activation 承認は **両カードの policy 一致を SDN が裏取りした後** に出すこと[^1]。

## 3. 状態と forwarding の確認

DPU の HA 状態は telemetry（gNMI）でのみ正規に取得できる。CLI は HLD に明示されていないが、運用上は次の経路で間接確認する:

```bash
# DPU の HA 状態（telemetry / gNMI 経由）
gnmic -a <switch> get --path /smart-switch/dpu/0/ha-scope/state

# NPU 上の next hop が想定 DPU VIP を向いているか
ip route show | grep <DPU VIP range>

# BFD セッション一覧（両 DPU が応答していること）
show bfd sessions

# DPU カード状態（PMON 検知系）
show chassis modules status
show platform inventory
```

`Active` 確定後は [BFD](../reference/glossary.md#term-bfd) が両 DPU で Up になり、preferred DPU が next hop に選ばれる。`PendingActiveActivation` 段階では BFD は Down のままで、これは正常な dormant 状態[^1]。

## 4. failover の確認

### 4.1 Planned shutdown を打った後

1. SDN から `HA_SCOPE` の `desired state=dead` を送出
2. `show bfd sessions` で対象 DPU の BFD が Down に落ちる（応答停止）
3. `ip route` の next hop が standby 側に切り替わる
4. telemetry で対象 DPU が `Destroying` → `Dead` に推移
5. 相手 DPU が `SwitchingToStandalone` → `Standalone` に推移
6. SDN から `flow reconcile` 承認が出されたことを SDN controller のログで確認

`Destroying` 中の収束タイマー満了前に DPU が完全停止すると残留 traffic が drop するので、タイマー値は SDN policy の MTBF / 収束時間に合わせて調整する[^1]。

### 4.2 Unplanned failover

1. `show platform` で対象 DPU が PMON により dead 認識されているか確認
2. `show bfd sessions` で対象 DPU の BFD が Down
3. telemetry で相手 DPU が `Standalone` に上がっていること
4. SDN controller 側に `flow reconcile needed` notification が届いていること

## 5. トラブルシュート

| 症状 | 確認順 |
|------|--------|
| DPU が `PendingActiveActivation` で停まる | SDN controller 側で activation 承認が出ているか。policy 整合性チェックで弾かれていないか |
| BFD は Up なのに next hop が変わらない | `HA_SET` の `preferred DPU` 設定。preferred 側が Up であれば常にそちらが選ばれる仕様[^1] |
| 両 DPU が `Standalone`（split-brain） | DPU-DPU 通信路の断を疑う。midplane の link 状態、DPU-to-DPU probe ログを確認。**SDN controller が片方の HA scope を `disabled=true→false` で強制再起動** して解消[^1] |
| failover 後に新規 flow だけ通らない | `Standalone` 化した DPU が flow resimulation を凍結中の可能性。SDN からの `flow reconcile` 承認待ち |
| HA 再 pair で新 DPU が `Dead` のまま | 旧 HA set object の削除と新 HA set object の作成順。[ENI](../reference/glossary.md#term-eni) 全 program 後に `AdminState=Enabled` |

```bash
# 代表トラブルシュート
show bfd sessions
ip route show | grep <DPU VIP range>
show chassis modules status
gnmic -a <switch> get --path /smart-switch/dpu/0/ha-scope/state
```

## 6. 制限事項

- HLD は **DPU 内部の状態遷移を強制しない**。実装ごとに挙動差が出うる[^1]
- 現行 deployment は **1 DPU = 1 HA scope**。DPU 内で複数 scope を切る運用は scope 外
- forwarding は VIP route ベースで、ENI-Scope のような細粒度制御は不可
- `hamgrd` は状態機械を持たないため、状態追跡の責務は SDN controller に大きく寄る
- standby 側で既存 flow を forward する DPU 実装は許容されるが、新規 flow 決定は active 側に限定[^1]
- HA scope の `disabled` 切替は **強制 shutdown** であり graceful path を経ない。stuck 解消の非常手段としてのみ使う[^1]

## 7. 干渉する機能

- **主 HA HLD（ENI-Scope-NPU-Driven）**: 同一 [SmartSwitch](../reference/glossary.md#term-smartswitch) 上で本構成と混在運用する手順は HLD で未定義。`hamgrd` の両モード対応は要求されうる
- **SmartSwitch BFD detailed design (PR #1635)**: NPU-to-DPU の card level probe 実体
- **DASH overlay**: `HA_SET` / `HA_SCOPE` は DASH object として programming される。SmartSwitch Database design (`DPU_APPL_DB`) との整合が前提
- **flow sync / inline channel**: DPU-to-DPU の data plane channel は主 HLD のものを流用
- **PMON / Chassis modules**: DPU dead 検知の起点。`show chassis modules status` で状態を見る

## 引用元

[^1]: `sonic-net/SONiC` `doc/smart-switch/high-availability/smart-switch-ha-dpu-scope-dpu-driven-setup.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: dd580da5b801 -->
