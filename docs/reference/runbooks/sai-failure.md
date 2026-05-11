---
title: SAI failure / syncd リスタート多発
description: "Runbook: SAI failure / syncd リスタート多発 — : sonic-net/sonic-sairedis @ 88bc51a — syncd 本体 : sonic-net/sonic-swss @ 4305596 — orchagent"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-sairedis
    path: syncd/Syncd.cpp
    ref: 88bc51ae95df66977601957515e5527119ffd4c5
  - repo: sonic-net/sonic-swss
    path: orchagent/orchdaemon.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db: []
  cli: [show platform summary, show system-health detail]
  yang: []
---

# Runbook: SAI failure / syncd リスタート多発

!!! danger "実行前提"
    `systemctl restart swss` は syncd 連動再起動を伴い、**ASIC を一度再初期化** するため data plane が 30 秒～数分中断する（cold restart 相当）。warm_restart が enable でも syncd crash 直後は再生成必須。実行前に `sudo cp -r /var/log/syncd* /tmp/syncd.bak.$(date +%s)/` で crash log を退避し、`show techsupport` を取得して原因解析用 evidence を残す。問題が ASIC ハード障害の場合は再起動しても改善せず、platform vendor の RMA フロー（chassis 全交換）が必要。

## 症状

- `syncd` コンテナが `Exited (134)` / `Aborted (core dumped)` で再起動を繰り返す
- `ASIC_DB` への書き込みが詰まる、orchagent ログに `SAI API failed` が連続
- ASIC レベルのテーブル限界エラー (`CRM` の overflow) が観測される

## 想定原因

1. **CRM (Critical Resource Monitor) で table 枯渇**: FDB / ROUTE / NEXTHOP / ACL のいずれかが ASIC 容量を超過
2. **SAI 属性の未対応**: SDK バージョンが古く、orchagent が新属性を打って失敗
3. **同名 object の重複作成 / 削除順序ミス**: 古い参照を残したまま親 object を削除
4. **メモリ / shared memory 不足**: redis / syncd が OOM kill
5. **HW 側の障害**: ASIC reset、PCIe link down、Fabric link error

## 切り分け手順

### 1. syncd の異常終了情報

```bash
docker ps -a | grep syncd
sudo journalctl -u syncd -n 200
docker logs syncd 2>&1 | tail -200
ls /var/core/ /var/dump/ 2>/dev/null
```

- 期待: 直近 Exit code 0、core file なし
- 異常: `SIGABRT` / `coredump` → core を解析（gdb 必要）

### 2. CRM の閾値超過

```bash
crm show summary
crm show resources all
crm show thresholds all
```

- 期待: usage がいずれの table も threshold 未満
- 異常: `fdb_entry`, `ipv4_route`, `ipv6_nexthop`, `acl_table_entry` 等が 95% 超 → 容量超過

### 3. orchagent ログから具体的失敗 API

```bash
docker logs swss 2>&1 | grep -iE "SAI_STATUS|sai_api|sai_create|sai_remove" | tail -100
```

- `SAI_STATUS_TABLE_FULL` → CRM 枯渇
- `SAI_STATUS_NOT_SUPPORTED` → SDK 非対応属性
- `SAI_STATUS_INVALID_OBJECT_ID` → object 削除順序の問題

### 4. プラットフォーム / SDK バージョン

```bash
show platform summary
show version
sudo cat /etc/sonic/sonic_version.yml
docker exec syncd ls /usr/lib/aarch64-linux-gnu/ | grep -i sai 2>/dev/null
```

### 5. メモリ

```bash
free -h
docker stats --no-stream
dmesg | grep -i -E "oom|kill" | tail
```

## 対処方法

- CRM 枯渇: 容量設計を見直す（FDB aging を短く、ACL の `match_in_ports` を集約、route summarization）
- syncd / swss の単発復旧: `sudo systemctl restart swss` → syncd も連動再起動
- 重大障害（PCIe 等）の疑い時: techsupport を取得して保守問い合わせ
- SDK のバグの場合: 該当 image にバックポートされた fix を持つ build に更新

## 関連ページ

- [../../topics/20-swss-sai-redis/architecture.md](../../topics/20-swss-sai-redis/architecture.md)
- [../../topics/20-swss-sai-redis/internals.md](../../topics/20-swss-sai-redis/internals.md)
- [../config-db/crm.md](../config-db/crm.md)

## 引用元

[^1]: sonic-net/sonic-sairedis @ 88bc51a — syncd 本体
[^2]: sonic-net/sonic-swss @ 4305596 — orchagent
