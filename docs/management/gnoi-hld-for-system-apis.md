---
title: gNOI System Reboot / RebootStatus / CancelReboot（reboot method と sanity check）
description: gNOI System Reboot / RebootStatus / CancelReboot（reboot method と sanity check） — gnoi.system.System のうち SONiC が初期サポートする RPC は Reboot / RebootStatus / CancelReb…
area: management
verification: discrepancy-found
monitor: partially_implemented
last_verified: 2026-06-06
sources:
- repo: sonic-net/SONiC
  path: doc/mgmt/gnmi/gnoi_system_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - DPU
  - CHASSIS_MODULE
  - MID_PLANE_BRIDGE
  - DPUS
  cli:
  - gnoi_client
  yang:
  - sonic-gnmi
  - sonic-telemetry
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 10 章: gNMI / OpenConfig / 管理プレーン](../topics/10-gnmi-openconfig/index.md) を参照。
<!-- /topics-tip -->

!!! warning "裏取りステータス: discrepancy-found"
    `sonic-gnmi/gnmi_server/gnoi_system.go` L34 `ValidateRebootRequest`、L116 `sendRebootReqOnNotifCh`（DB notification 経由で reboot 要求を書き込む）、L193 `Server.Reboot`、L241 `Server.RebootStatus`、L270 `Server.CancelReboot` のハンドラ実装を確認。`sonic-gnmi/pkg/gnoi/system/system.go` L22 `HandleReboot`、L180 `HandleDPUReboot` で DPU 対応も確認。`sonic-gnmi/gnoi_client/system/reboot.go` L13/25/42 で client 側 Reboot / CancelReboot / RebootStatus の 3 RPC を確認。一方で **HLD と現行実装の乖離** を確認: 実装 `ValidateRebootRequest` (L37-L46) は `delay > 0` および method=`POWERUP` を一律 reject するため、HLD が示唆する「遅延付き reboot」「POWERUP を sanity check 対象 method として並列扱い」とは挙動が異なる。詳細は下記「実装との差異」節を参照（verified at: 2026-06-06）。

# gNOI System Reboot / RebootStatus / CancelReboot（reboot method と sanity check）

## 概要

`gnoi.system.System` のうち [SONiC](../reference/glossary.md#term-sonic) が初期サポートする RPC は **Reboot / RebootStatus / CancelReboot** の 3 つ[^1]。OpenConfig の [system.proto](https://github.com/openconfig/gnoi/blob/main/system/system.proto) 定義をそのまま利用する。

reboot method は仕様上以下の 6 種類[^1]（COLD のみ全 target で必須）:

| method | 意味 |
|--------|------|
| `COLD` | OS とハードウェア全体を再起動。**全 target 必須サポート** |
| `POWERDOWN` | 可能なら停止 + 電源 off |
| `HALT` | 停止のみ |
| `WARM` | 構成のみ再ロード（ハードウェア維持）。NSF と同等扱いかは vendor 依存 |
| `NSF` | Non-Stop-Forwarding reboot |
| `POWERUP` | 電源を入れる（既に on なら no-op） |

`RESET` は **deprecated**（FactoryReset RPC 側へ移行）[^1]。

## 動作仕様

### 全体フロー

```mermaid
sequenceDiagram
    participant CL as Client
    participant SV as gNOI System (UMF)
    participant DB as DB / state
    participant HS as host (reboot exec)
    CL->>SV: Reboot{method, delay, message, subcomponents, force}
    SV->>SV: sanity check (method 対応 / delay 範囲)
    alt 失敗 & force=false
        SV-->>CL: error
    else 受理
        SV->>SV: 既存の active/pending reboot と衝突確認
        SV->>DB: write request to DB
        SV-->>CL: RebootResponse{}
        Note over DB,HS: BE は独立に reboot を実行
        DB->>HS: trigger reboot
    end
    CL->>SV: RebootStatus{}
    SV-->>CL: { active, wait, when, count, method, status }
    CL->>SV: CancelReboot{}
    SV-->>CL: CancelRebootResponse{}
```

### Reboot RPC の仕様

`RebootRequest` の主要フィールド[^1]:

```proto
message RebootRequest {
  RebootMethod method = 1;
  uint64       delay = 2;          // ns 単位の遅延
  string       message = 3;        // 監査ログ向け理由
  repeated types.Path subcomponents = 4; // optional: 部分 reboot
  bool         force = 5;          // sanity check fail でも実行
}
```

サニティチェック（`force=false` で fail すると拒否）[^1]:

- platform で **未対応の method** が指定された
- パラメータが範囲外（例: 1 年後の delay 等）

受理条件[^1]:

1. リクエスト validation 成功
2. **active / pending な reboot が無い**
3. DB への書き込み成功

active control processor への reboot が pending な状態で **更なる reboot 要求** が来たら、必ず reject する[^1]。

### RebootStatus RPC

`RebootStatusResponse` で返るフィールド[^1]:

| フィールド | 内容 |
|----------|------|
| `active` | reboot が進行/予約中か |
| `wait` | 残り時間（ns） |
| `when` | epoch 基準の reboot 時刻（ns） |
| `reason` | 理由（`message` 由来） |
| `count` | active になってからの reboot 回数 |
| `method` | `RebootMethod` |
| `status` | `active=false` の時のみ意味あり: SUCCESS / RETRIABLE_FAILURE / FAILURE / UNKNOWN |

### CancelReboot RPC

`CancelRebootRequest{message, subcomponents}` で **pending な reboot を取消** する。subcomponents 指定時は該当部分のみキャンセル[^1]。応答は空。

### subcomponent 指定の reboot

`subcomponents: []types.Path` で **特定の component のみ reboot** することを許可（例: `/components/component[name=ASIC0]`）。platform が対応していなければ sanity check で拒否される[^1]。

### warm / NSF reboot との関係

`WARM` / `NSF` の挙動は **vendor 定義**。[HLD](../reference/glossary.md#term-hld) 本文では「`WARM` と `NSF` が同じかは実装次第」と明記[^1]。SONiC での具体実装は別 HLD（Warmboot Manager HLD、リンク先は upstream / fork のドラフト段階）に委ねており、本 HLD 自体には warm reboot 経路の詳細記載は無い[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/mgmt/gnmi/gnoi_system_hld.md#L176-L188 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  The gNOI server performs sanity checks after receiving the requests, and rejects if it fails (and `force` is not set).
  ...
  The Reboot Request Succeeds when:
  - The gNOI server validates the request,
  - checks that no requests are pending/ active, and
  - writes the data successfully to the DB.
  - Once notified, the back end will act on the operation independently.
reasoning: 受理条件が「validation OK + 既存 reboot 無し + DB 書込成功」、BE は独立実行という記述の根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/mgmt/gnmi/gnoi_system_hld.md#L176-L188 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/mgmt/gnmi/gnoi_system_hld.md#L176-L188 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    The gNOI server performs sanity checks after receiving the requests, and rejects if it fails (and `force` is not set).
    ...
    The Reboot Request Succeeds when:
    - The gNOI server validates the request,
    - checks that no requests are pending/ active, and
    - writes the data successfully to the DB.
    - Once notified, the back end will act on the operation independently.
    ```

    **判断根拠**: 受理条件が「validation OK + 既存 reboot 無し + DB 書込成功」、BE は独立実行という記述の根拠。

<!-- evidence-rendered:end -->

## 設定

### 関連する CONFIG_DB

専用スキーマは HLD 上明記無し。「DB に書き込む」だけ抽象化されているため、現行 master では `STATE_DB` / `CONFIG_DB` のどこに書くか実装に委ねられる。

### 関連する CLI

| Command | 用途 |
|---------|------|
| `gnoi_client system reboot ...` | Reboot RPC（JSON / proto 双方サポート予定）[^1] |
| `gnoi_client system reboot_status` | RebootStatus RPC |
| `gnoi_client system cancel_reboot` | CancelReboot RPC |

### 関連する YANG

該当 [YANG](../reference/glossary.md#term-yang) モジュールは HLD で言及無し。

### 設定例

```bash
# 即時 cold reboot
gnoi_client system reboot --method COLD --message "scheduled maintenance"

# 注: 現行 sonic-gnmi 実装では delay>0 は ValidateRebootRequest で reject される
# （`gnoi_system.go` L43-L46）。遅延 reboot は upstream HLD 文面上は許容だが、
# 実機では `INVALID_ARGUMENT` を返すため、遅延スケジューリングは呼出側で行う。

# 状態確認
gnoi_client system reboot_status

# 取消
gnoi_client system cancel_reboot --message "delayed by SRE"
```

## 実装との差異

現行 `sonic-net/sonic-gnmi` master の `ValidateRebootRequest` (`gnmi_server/gnoi_system.go` L34-L49) は HLD よりも厳格で、以下を一律拒否する:

| 拒否対象 | 実装根拠 | HLD 上の位置付け |
|---------|---------|-----------------|
| `method == POWERUP` | L37 で `UNKNOWN` と並んで unsupported 扱い | HLD では POWERUP を有効な reboot method として列挙[^1] |
| `method == UNKNOWN` | L37 | HLD でも 0 値は無効扱い（差異なし） |
| `delay > 0`（任意の遅延） | L43 で `Invalid request: reboot is not immediate.` | HLD では `delay` を `uint64` で受け取り、サニティチェックの例として「1 年後 delay」のような極端値のみ NG と例示[^1] |

つまり、現行 master では実質的に「`method ∈ {COLD, POWERDOWN, HALT, WARM, NSF}` かつ `delay == 0`」のみが validation を通る。HLD で示される 6 method（POWERUP を含む）の並列扱いや、ns 単位 delay スケジューリングは実機で動作しない。

<!-- evidence:
source: sonic-net/sonic-gnmi/gnmi_server/gnoi_system.go#L34-L49 (master)
excerpt: |
  func ValidateRebootRequest(req *syspb.RebootRequest) error {
      if req.GetMethod() == syspb.RebootMethod_UNKNOWN || req.GetMethod() == syspb.RebootMethod_POWERUP {
          return fmt.Errorf("Invalid request: reboot method is not supported.")
      }
      if req.GetDelay() > 0 {
          return fmt.Errorf("Invalid request: reboot is not immediate.")
      }
      return nil
  }
reasoning: 実装が POWERUP と delay>0 を一律 reject している事実の根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-gnmi/gnmi_server/gnoi_system.go#L34-L49 (master)"

    **出典**:

    `sonic-net/sonic-gnmi/gnmi_server/gnoi_system.go#L34-L49 (master)`

    **抜粋**:

    ```text
    func ValidateRebootRequest(req *syspb.RebootRequest) error {
        if req.GetMethod() == syspb.RebootMethod_UNKNOWN || req.GetMethod() == syspb.RebootMethod_POWERUP {
            return fmt.Errorf("Invalid request: reboot method is not supported.")
        }
        if req.GetDelay() > 0 {
            return fmt.Errorf("Invalid request: reboot is not immediate.")
        }
        return nil
    }
    ```

    **判断根拠**: 実装が POWERUP と delay>0 を一律 reject している事実の根拠。

<!-- evidence-rendered:end -->

## 制限事項

- **`COLD` のみ全 target 必須**[^1]。それ以外（POWERDOWN / HALT / WARM / NSF / POWERUP）は platform 依存
- 現行 sonic-gnmi 実装では **`POWERUP` および `delay > 0` は一律 reject**（上記「実装との差異」節）
- `RESET` は **deprecated**。代わりに `gnoi.factory_reset.FactoryReset.Start` を使う[^1]
- active control processor への reboot pending 中は別の reboot 要求は **reject**[^1]
- `Time` RPC は initial scope **対象外**（v0.2 で削除）[^1]
- subcomponent 指定 reboot の対応は platform 依存
- warm / NSF reboot の意味（同一視するか別物にするか）は **vendor 定義**[^1]

## 干渉する機能

- **[gNOI](../reference/glossary.md#term-gnoi) OS Activate**: `Activate(no_reboot=true)` 後の本 RPC で実 reboot を発火する想定[^1]
- **gNOI FactoryReset.Start**: `RESET` の代替。reboot とは別のセマンティクス
- **Warm / Fast reboot 機構**: SONiC 標準の `warm-reboot` / `fast-reboot` スクリプトとの連携経路は別 HLD 側で詳細化
- **`config save` / `config reload`**: reboot で揮発する設定が無いか事前確認

## トラブルシューティング

- `INVALID_ARGUMENT` で reject: `RebootMethod` が platform 非対応か `delay` が範囲外。`force=true` で再試行可だが推奨されない
- `Reboot` 受理後に `RebootStatus.active=false`: 既に reboot 完了したか、BE が DB 書き込みを処理しなかった
- `CancelReboot` が効かない: subcomponents 指定が unmatched、または既に reboot が走り始めている

確認コマンド例:

```bash
# gNOI/gNSI/gNMI クライアント疎通と server 状態
gnmi_cli -a 127.0.0.1:9339 -capabilities -insecure
docker exec gnmi ps aux | grep -E 'telemetry|gnmi'
docker logs gnmi 2>&1 | tail
redis-cli -n 4 hgetall 'GNMI|certs'
```

## 参考リンク

- [Topics: gNMI / OpenConfig](../topics/10-gnmi-openconfig/index.md)
- [Topics: Reboot](../topics/11-reboot/index.md)
- [CLI: reboot / fast / warm](../reference/cli/reboot-fast-warm.md)
- [HLD: gnsi-hld](gnsi-hld.md)

## 引用元

[^1]: `sonic-net/SONiC` `doc/mgmt/gnmi/gnoi_system_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- UMF / sonic-gnmi の System Reboot/RebootStatus/CancelReboot handler 実装存在確認
- reboot 要求を書き込む DB スキーマ (STATE_DB / CONFIG_DB) の現行実装確認
- COLD 以外 (WARM / NSF / POWERDOWN / HALT / POWERUP) の platform サポート状況
- subcomponent 指定 reboot の実装存否
- Warmboot Manager HLD（別 HLD）と本 HLD の連携経路実装確認
- gnoi_client の system サブコマンド実装状況
-->

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: DASH と SmartSwitch](../topics/13-dash-smartswitch/index.md)

<!-- /topics-back-ref -->

## 関連リファレンス

本ページに関連する参照ドキュメント:

- [management カテゴリ目次](index.md)
- [用語集 (Glossary)](../reference/glossary.md)

<!-- augmented-links: v1 -->

<!-- ops-entry -->
## 運用入口

この HLD に対応する運用面の入口（CLI / [CONFIG_DB](../reference/glossary.md#term-config_db) / YANG / Runbook）を以下にまとめる。

### 関連 CLI

- `gnoi_client`

<!-- /ops-entry -->

<!-- glossary-links-injected: 809619d7ad9f -->

## 実装との乖離

本 HLD は gnoi.system.System の RPC 群を網羅的に提案するが、現行 master ではサブセットのみが実装されている (`partially_implemented`)。具体的には Reboot / RebootStatus / CancelReboot が実装済で、KillProcess / Ping / SetPackage / SwitchControlProcessor / Time / Traceroute 等は未実装または部分実装。詳細は本文の HLD 提案部分と実装現状を比較すること。


機能項目別の実装状況は以下のとおり。

| 機能項目 | HLD 提案 | 実装状況 |
|---|---|---|
| Reboot RPC | 必須 | 実装済 |
| RebootStatus RPC | 必須 | 実装済 |
| CancelReboot RPC | 必須 | 実装済 |
| KillProcess RPC | 提案 | 未実装 |
| Ping RPC | 提案 | 未実装 |
| SetPackage RPC | 提案 | 未実装 |
| Time RPC | 提案 | 未実装 |
| SwitchControlProcessor RPC | 提案 | 未対応 |
| Traceroute RPC | 提案 | 未実装 |
