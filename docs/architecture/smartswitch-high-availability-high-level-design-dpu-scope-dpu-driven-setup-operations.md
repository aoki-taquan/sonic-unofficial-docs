---
title: SmartSwitch HA DPU-Scope-DPU-Driven 運用（CLI / 設定 / failover 確認）
description: SmartSwitch HA DPU-Scope-DPU-Driven の設定経路（DASH SDN config）、failover
  確認、BFD / next hop / split-brain のトラブルシュート手順、制限事項と干渉機能を整理する。
area: architecture
verification: hld-only
last_verified: 2026-06-04
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/smart-switch/high-availability/smart-switch-ha-dpu-scope-dpu-driven-setup.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/SONiC
  path: doc/smart-switch/high-availability/smart-switch-ha-detailed-design.md
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

DPU-Scope-DPU-Driven setup HLD は telemetry/gNMI の具体的な path を持たず、SmartSwitch HA detailed design に委譲している[^1]。後者は **NPU の `DASH_STATE_DB` 上の `DASH_HA_SCOPE_STATE` テーブルを gNMI 経由で SDN controller に公開** すると定義しており[^2]、運用者が参照する主な状態フィールドは以下のとおり:

| フィールド | 意味 |
|------------|------|
| `local_ha_state` | NPU `hamgrd` が見ている HA state machine の状態 |
| `local_target_asic_ha_state` / `local_acked_asic_ha_state` | hamgrd が DPU [ASIC](../reference/glossary.md#term-asic) に要求中の state / ASIC が ack した state |
| `local_target_term` / `local_acked_term` | 現在の target term / ASIC ack 済み term |
| `peer_ha_state` / `peer_term` | 相手 DPU の HA state / term |
| `local_vdpu_midplane_state` / `local_vdpu_control_plane_state` / `local_vdpu_data_plane_state` | midplane / control / data plane の health（`up` / `down` / `unknown`） |
| `local_vdpu_up_bfd_sessions_v4` / `_v6` | up になっている BFD セッションの peer NPU IP |
| `pending_operation_types` / `switchover_state` / `flow_sync_session_state` | 進行中の switchover / flow_reconcile / brainsplit_recover の状態 |

これらは detailed design の §2.2 "External facing state tables" に定義されている[^2]。DPU 側にも別途 `DASH_HA_SET_STATE` / `DASH_HA_SCOPE_STATE`（ASIC ack 済みの `ha_role` = `dead` / `active` / `standby` / `standalone` / `switching_to_active` を保持）がある[^2]が、SDN controller への公開は NPU 側のみ。

以下のコマンド例は上記スキーマに対する参照例で、`gnmic` の path 文字列は platform 実装ごとに decorate 形式が異なる（OC-style か proprietary か）ため、実環境では platform/SDN controller 側のドキュメントを優先すること。CLI 名（`show bfd` / `show chassis modules` / `show platform`）は [SONiC](../reference/glossary.md#term-sonic) 既存 NOS 機能であり、本 HLD に裏取りされた HA 専用 CLI ではない（本ページが `verification: hld-only` である理由）。

```bash
# DPU の HA 状態（NPU DASH_STATE_DB / DASH_HA_SCOPE_STATE を gNMI で取得）
# path は SDN controller の YANG/OC モデル依存。テーブル名と field 名は detailed design §2.2 を参照
gnmic -a <switch> get --path '/.../DASH_HA_SCOPE_STATE/<vdpu_id>/<ha_scope_id>'

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

以降の確認手順は HLD §3 状態遷移と §4 telemetry の記述[^1]を運用フローに落とした **推定手順** であり、個別 CLI 出力例の文言までは HLD に裏取りされていない。状態名 (`Destroying` / `Dead` / `SwitchingToStandalone` / `Standalone`) と SDN controller の `flow reconcile` 承認フローのみが HLD 由来である。

### 4.1 Planned shutdown を打った後

1. SDN から `HA_SCOPE` の `desired state=dead` を送出
2. `show bfd sessions` で対象 DPU の BFD が Down に落ちる（応答停止）
3. `ip route` の next hop が standby 側に切り替わる
4. telemetry（`DASH_HA_SCOPE_STATE.local_ha_state`）で対象 DPU が `Destroying` → `Dead` に推移[^2]
5. 相手 DPU の `local_ha_state` が `SwitchingToStandalone` → `Standalone` に推移[^2]
6. `DASH_HA_SCOPE_STATE.pending_operation_types` から `flow_reconcile` が落ち、`flow_sync_session_state` が `completed` になることを SDN controller 側で確認[^2]

`Destroying` 中の収束タイマー満了前に DPU が完全停止すると残留 traffic が drop するので、タイマー値は SDN policy の MTBF / 収束時間に合わせて調整する[^1]。

### 4.2 Unplanned failover

1. `show platform` で対象 DPU が PMON により dead 認識されているか確認（NPU `CHASSIS_STATE_DB` の `DPU_STATE` 経由[^2]）
2. `show bfd sessions` で対象 DPU の BFD が Down
3. telemetry の `DASH_HA_SCOPE_STATE.local_ha_state` で相手 DPU が `Standalone` に上がっていること[^2]
4. `DASH_HA_SCOPE_STATE.pending_operation_types` に `flow_reconcile` が積まれ、SDN controller 側に承認要求が届いていること[^2]

## 5. トラブルシュート

| 症状 | 確認順 |
|------|--------|
| DPU が `PendingActiveActivation` で停まる | SDN controller 側で activation 承認が出ているか。policy 整合性チェックで弾かれていないか |
| BFD は Up なのに next hop が変わらない | `HA_SET` の `preferred DPU` 設定。preferred 側が Up であれば常にそちらが選ばれる仕様[^1] |
| 両 DPU が `Standalone`（split-brain） | DPU-DPU 通信路の断を疑う。midplane の link 状態、DPU-to-DPU probe ログを確認。**SDN controller が片方の HA scope を `disabled=true→false` で強制再起動** して解消[^1] |
| failover 後に新規 flow だけ通らない | `Standalone` 化した DPU が flow resimulation を凍結中の可能性。SDN からの `flow reconcile` 承認待ち |
| HA 再 pair で新 DPU が `Dead` のまま | 旧 HA set object の削除と新 HA set object の作成順。[ENI](../reference/glossary.md#term-eni) 全 program 後に `AdminState=Enabled` |

```bash
# 代表トラブルシュート（CLI 名は SONiC 既存 NOS 機能、gNMI path は §3 参照）
show bfd sessions
ip route show | grep <DPU VIP range>
show chassis modules status
# DASH_HA_SCOPE_STATE の local_ha_state / pending_operation_types を見る
gnmic -a <switch> get --path '/.../DASH_HA_SCOPE_STATE/<vdpu_id>/<ha_scope_id>'
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
[^2]: `sonic-net/SONiC` `doc/smart-switch/high-availability/smart-switch-ha-detailed-design.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06` (§2.2 External facing state tables / §3 Telemetry)

<!-- glossary-links-injected: ec18b66e3507 -->
