---
title: SONiC on Multi-ASIC platforms（namespace / per-asic Redis / sonic-net）
area: platform
verification: hld-only
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/multi_asic/SONiC_multi_asic_hld.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - DEVICE_METADATA
    - PORT
    - BGP_INTERNAL_NEIGHBOR
  cli:
    - show platform summary
    - show ip route -n
    - show ip bgp summary -n
  yang:
    - sonic-device_metadata
---

!!! warning "裏取りステータス: HLD-only / 大規模 HLD"
    HLD は 71KB。本ページは architecturally distinctive な要素（namespace 分離・per-ASIC Redis・internal BGP・sonic-net link）に絞り、設定詳細や BGP テンプレートは HLD 本文を参照する形にする。

# SONiC on Multi-ASIC platforms（namespace / per-asic Redis / sonic-net）

## 概要

1 台の chassis 内に複数 ASIC を持つ platform 上で SONiC を動かすための設計[^1]。中核アイデア:

- **ASIC ごとに linux network namespace を分ける**（`asic0` / `asic1` / ...）
- **各 namespace に独自の Redis インスタンス**（`database0`、`database1`...）と独自の SWSS / syncd / FRR インスタンスを置く
- ASIC 間は **internal links（sonic-net / fabric / cross-port）と internal BGP** で結ぶ
- 外部から見える操作（CLI / SNMP / gNMI）は **host namespace 上の集約レイヤ** が ASIC 横断で扱う

## 動作仕様

```mermaid
flowchart LR
    subgraph host[host namespace]
      CLI[sonic-utilities\n(host)]
      DB_HOST[(database (host)\nCONFIG_DB shared)]
    end
    subgraph asic0[asic0 namespace]
      SW0[swss0]
      SY0[syncd0]
      FR0[FRR / bgp0]
      DB0[(database0)]
    end
    subgraph asic1[asic1 namespace]
      SW1[swss1]
      SY1[syncd1]
      FR1[FRR / bgp1]
      DB1[(database1)]
    end
    CLI -.aggregate.-> DB0
    CLI -.aggregate.-> DB1
    SY0 --- ASIC0[(ASIC 0)]
    SY1 --- ASIC1[(ASIC 1)]
    ASIC0 -. internal links .- ASIC1
    FR0 -- iBGP --- FR1
```

主要な仕組み[^1]:

- **`asic.conf` / `platform.json`**: ASIC 数と type、internal port マッピング、role（front-panel / fabric）を宣言
- **per-namespace docker**: `swss@asic0`、`syncd@asic0` のような instanced systemd unit
- **共有 CONFIG_DB（host）+ per-asic DB**: device-wide 設定は host CONFIG_DB に、port / asic 固有は per-asic に分離
- **internal BGP**: front-panel ASIC 同士で iBGP を張り、route 情報を共有（`BGP_INTERNAL_NEIGHBOR`）
- **CLI 集約**: `show ... -n asic0` 等で per-asic クエリ、引数なしで全 ASIC 集約

### sub_role による役割分担

`DEVICE_METADATA|<asic>.sub_role` が `FrontEnd` / `BackEnd` を区別:

- **FrontEnd**: 外向き port を持つ。BGP / ARP / 通常の SONiC 機能が動く
- **BackEnd**: fabric 役。trafic は通すが control plane は限定的

## 設定

### 関連する CONFIG_DB

| Table | 説明 |
|-------|------|
| `DEVICE_METADATA` | `localhost.platform`、`asic_name`、`sub_role`、`asic_id` |
| `PORT` | per-asic（namespace ごとの DB に存在） |
| `BGP_INTERNAL_NEIGHBOR` | ASIC 間 iBGP 用 neighbor |

### 関連する CLI

| Command | 用途 |
|---------|------|
| `show platform summary` | platform 名、ASIC 数 |
| `show interfaces -n asic0` | per-asic interface |
| `show ip bgp summary -n asic0` | per-asic FRR 状態 |
| `sudo ip netns exec asic0 bash` | namespace に入る |

## 制限事項

- **multi-asic 対応の sonic-utilities** が必要。`-n` オプション未対応コマンドは ASIC 横断で正しく動かない
- **memory 消費**: ASIC 数 × Redis / swss / syncd / FRR の常駐、CPU / メモリ要件が高い
- **warm reboot 同期**: 全 ASIC を協調的に shutdown / boot する仕組みが必要（multi-asic warm reboot HLD）
- **single-json multi-asic**: `multi-asic-single-json` HLD で扱う統合 config 形式と要使い分け

## 干渉する機能

- **multi-asic warm reboot**: per-asic syncd / swss を協調 shutdown する HLD
- **single-json multi-asic config**: 一枚の JSON で per-asic 設定を一元管理する HLD
- **CRM（critical resource monitoring）**: per-asic で監視
- **Internal BGP / chassis BGP**: 内部 iBGP の設計と外部 eBGP の境界

## トラブルシューティング

- `show interfaces` が空 → namespace を `-n` で指定し直す
- iBGP が上がらない → `BGP_INTERNAL_NEIGHBOR` と internal link 物理状態、`sub_role` を確認
- per-asic Redis に接続できない → `redis-cli -s /var/run/redis<asic>/redis.sock` の socket を確認

## 引用元

[^1]: `sonic-net/SONiC` `doc/multi_asic/SONiC_multi_asic_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- asic.conf / platform.json の現行 multi-asic platform での記述差分確認
- DEVICE_METADATA.sub_role / asic_name / asic_id の現行 sonic-yang-models 値確認
- swss@asicN / syncd@asicN systemd 経路と instanced unit の現行 sonic-buildimage 確認
- BGP_INTERNAL_NEIGHBOR スキーマと FRR テンプレートの現行値確認
- sonic-utilities の -n / --namespace 対応カバレッジの現行確認
- multi-asic warm reboot / single-json HLD との統合状況確認
-->
