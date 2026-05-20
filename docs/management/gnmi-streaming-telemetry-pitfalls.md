---
title: gNMI ストリーミングテレメトリの落とし穴
area: management
tags: [gnmi, telemetry, streaming, oom, memory]
description: dial-in ストリーミングテレメトリで発生する OOM・メモリリーク・RESOURCE_EXHAUSTED エラーの原因と対策。
source_issues:
  - https://github.com/sonic-net/sonic-gnmi/issues/26
verification: issue-confirmed
last_verified: 2026-05-20
---

# gNMI ストリーミングテレメトリの落とし穴

## 概要

[gNMI](../reference/glossary.md#term-gnmi) dial-in モードでストリーミングテレメトリを利用する場合、コレクターの処理が遅いとスイッチ側のメモリが際限なく増加し、最終的に OOM（Out of Memory）が発生することがある。

## 問題の詳細

### 症状

- `sonic-gnmi` プロセスのメモリ使用量が継続的に増加する
- スイッチの物理メモリを使い切り、プロセスが OOM Killer によって終了する
- コレクター側に遅延や輻輳がある場合に顕著

### 原因

dial-in ストリーミングでは、gNMI サーバー（スイッチ側）がサブスクリプションに対するデータを内部キューにバッファリングし、コレクターに送信する。コレクターの受信速度がデータ生成速度を下回ると、キューが際限なく積み上がり、メモリを圧迫する。

```
[SONiC gNMI server]
  データ生成 → キュー → コレクター
              ↑ ここが詰まる
```

## 対処方法

### RESOURCE_EXHAUSTED エラーへの対応

キューが一定以上膨らむと、gNMI サーバーは接続に対して `RESOURCE_EXHAUSTED` エラーを返して接続を切断する。これはメモリ保護のための意図的な動作である。

- 接続を切断した時点で、キューは破棄されメモリは解放される
- **再接続はコレクター側の責任**である。コレクターは `RESOURCE_EXHAUSTED` エラーを受信したら、適切なバックオフを挟んで再接続を試みる必要がある

### コレクター側の対策

1. **サブスクリプション間隔を広げる**: `SAMPLE` モードでのサンプリング間隔を長くし、データ量を減らす
2. **サブスクリプション対象を絞る**: 必要なパスのみサブスクライブする
3. **コレクターの処理能力を向上させる**: コレクターのリソースを増強するか、水平スケールアウトを検討する
4. **`ON_CHANGE` モードを慎重に使う**: 変化が多いパスに対して `ON_CHANGE` を使うと、大量のイベントが発生する可能性がある

### スイッチ側の確認

```bash
# gnmi プロセスのメモリ使用量を確認
ps aux | grep gnmi

# Docker コンテナのメモリ使用量を確認（gnmi は telemetry コンテナ内）
docker stats telemetry --no-stream
```

## gNMIc を使ったテスト

[gNMIc](https://gnmic.openconfig.net/) を使うと、コレクターの動作をシミュレートしてテストできる。

```bash
# サブスクリプションのテスト
gnmic -a <sonic-ip>:8080 \
  --username admin \
  --password <password> \
  --skip-verify \
  subscribe \
  --path /openconfig-interfaces:interfaces/interface/state/counters \
  --mode stream \
  --stream-mode sample \
  --sample-interval 10s
```

## 関連

- [gNMI Translib 書き込み有効化](gnmi-translib-write-enable.md)
- [gNMI 利用ガイド](gnmi-usage.md)
- GitHub Issue: [sonic-net/sonic-gnmi#26](https://github.com/sonic-net/sonic-gnmi/issues/26)
- GitHub Issue: [sonic-net/sonic-gnmi#562](https://github.com/sonic-net/sonic-gnmi/issues/562)

<!-- glossary-links-injected: 658dfbdca882 -->
