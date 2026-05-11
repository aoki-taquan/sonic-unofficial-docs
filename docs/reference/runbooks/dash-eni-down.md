---
title: DASH ENI が down する / トラフィック止まる
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-dash-api
    path: proto/dash_eni.proto
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/dash/dashorch.cpp
    ref: master
related:
  config_db: [DASH_ENI_TABLE, DASH_VNET, DASH_APPLIANCE]
  cli: [show dash eni, show dash vnet]
  yang: []
---

# Runbook: DASH ENI が admin_state=up に遷移しない / トラフィック断

!!! danger "実行前提"
    `dash` 系の orchagent 再起動や `config reload` は DPU 側 datapath のフロー table を消失させる。実行前に SDN controller 側で session migration を実施し、**変更前の `DASH_ENI_TABLE` / `DASH_ROUTE_TABLE` を `redis-dump` で退避**しておくこと。ロールバックは退避から `redis-cli` で再投入。

## 症状

- `show dash eni <eni>` で `oper_status=down` または `admin_state=down`
- `DASH_ENI_TABLE:STATE_DB` の counter が更新されない
- VM → DPU → outside の VNET 通信が無応答

## 想定原因（優先度順）

1. **MAC / underlay_ip 不整合**: ENI の `mac_address` / `underlay_ip` が SmartSwitch の物理構成と合っていない
2. **依存リソース未作成**: `DASH_VNET` / `DASH_APPLIANCE` が ENI より後に作られた / 削除された
3. **DPU 側 dataplane 異常**: DPU 内 ASIC programming が失敗
4. **License / capability mismatch**: model がサポートしない ENI count
5. **route / mapping table 衝突**

## 切り分け手順

### 1. CONFIG_DB / APPL_DB

```bash
sonic-db-cli CONFIG_DB hgetall "DASH_ENI_TABLE|<eni>"
sonic-db-cli APPL_DB keys "DASH_ENI_TABLE:*"
sonic-db-cli STATE_DB hgetall "DASH_ENI_TABLE|<eni>"
```

### 2. orchagent ログ

```bash
docker logs swss 2>&1 | grep -iE "dash|eni" | tail -200
```

### 3. DPU 側状態（SmartSwitch）

```bash
show chassis modules status
show platform inventory
docker exec swss redis-cli -n 0 keys "DASH_*" | head
```

### 4. 関連リソース

```bash
sonic-db-cli CONFIG_DB keys "DASH_VNET|*"
sonic-db-cli CONFIG_DB keys "DASH_APPLIANCE|*"
sonic-db-cli CONFIG_DB keys "DASH_ROUTE_TABLE|*"
```

### 5. counter

```bash
show dash counter eni <eni>
```

## 対処方法

- 依存欠如: 先に `DASH_APPLIANCE` → `DASH_VNET` → `DASH_ENI_TABLE` の順に投入
- MAC / IP 不整合: controller 側 inventory と突合、CONFIG_DB を `redis-cli hset` で修正（**ロールバック**: 退避値で hset 戻し）
- DPU dataplane 異常: SmartSwitch の DPU を graceful shutdown → 再起動（[smartswitch-dpu-graceful-shutdown-failure.md](smartswitch-dpu-graceful-shutdown-failure.md) を参照）
- 容量超過: ENI 数を削減、ベンダ提供の max_eni を確認

## 関連ページ

- [./smartswitch-dpu-unresponsive.md](./smartswitch-dpu-unresponsive.md)
- [./smartswitch-dpu-graceful-shutdown-failure.md](./smartswitch-dpu-graceful-shutdown-failure.md)
- [../../topics/13-dash-smartswitch/concept.md](../../topics/13-dash-smartswitch/concept.md)

## 引用元

[^1]: sonic-net/sonic-dash-api @ master — dash_eni.proto
[^2]: sonic-net/sonic-swss @ master — dashorch.cpp
