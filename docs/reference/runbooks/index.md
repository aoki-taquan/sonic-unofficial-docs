---
title: Runbooks (症状逆引き)
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
  - repo: sonic-net/sonic-swss
    path: orchagent/orchdaemon.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db: []
  cli: []
  yang: []
---

# Runbooks (症状逆引き)

このセクションは「**現場で観測される症状から逆引きで切り分け手順に辿り着く**」ことを目的とした実務向けハンドブック集。各 runbook は次の構造に従う:

- **症状**: 何が起きているか（ユーザ視点）
- **想定原因**: 優先度順に 3〜5 件
- **切り分け手順**: 実行コマンドと期待 / 異常出力
- **対処方法**: 復旧手段
- **関連ページ**: 該当 topic / reference / discrepancy へのリンク

掲載コマンドおよび DB スキーマは `.cache/sonic-sources/` 内の master 実装を根拠としている。HLD 由来の推測は本文中に明示する。

## 一覧

| # | 症状 | Runbook |
|---|------|---------|
| 01 | BGP セッションが UP しない | [bgp-session-down.md](bgp-session-down.md) |
| 02 | VLAN メンバー追加してもタグが付かない | [vlan-tagging.md](vlan-tagging.md) |
| 03 | FEC エラーが多発する | [fec-errors.md](fec-errors.md) |
| 04 | Warm Reboot が失敗する / 通信断が長引く | [warm-reboot-failure.md](warm-reboot-failure.md) |
| 05 | PFC で帯域が出ない / Buffer overflow | [pfc-bandwidth.md](pfc-bandwidth.md) |
| 06 | DHCP Relay で IP が払い出されない | [dhcp-relay.md](dhcp-relay.md) |
| 07 | Multi-ASIC で namespace 間通信できない | [multi-asic-namespace.md](multi-asic-namespace.md) |
| 08 | Dual-ToR mux が切り替わらない | [dualtor-mux.md](dualtor-mux.md) |
| 09 | SAI failure / syncd リスタート多発 | [sai-failure.md](sai-failure.md) |
| 10 | コンテナが起動しない (FEATURE) | [container-not-starting.md](container-not-starting.md) |
| 11 | show techsupport が timeout する | [techsupport-timeout.md](techsupport-timeout.md) |
| 12 | counter が更新されない (FLEX_COUNTER) | [flex-counter-stuck.md](flex-counter-stuck.md) |
| 13 | RIF / ACL counter が 0 のまま | [rif-acl-counter-zero.md](rif-acl-counter-zero.md) |
| 14 | CONFIG_DB save / load が反映されない | [config-save-load.md](config-save-load.md) |
| 15 | SmartSwitch DPU が応答しない | [smartswitch-dpu-unresponsive.md](smartswitch-dpu-unresponsive.md) |

## 使い方の前提

- すべてのコマンドは admin ユーザ（sudo 可）で host 側 shell から実行することを想定する
- container 内コマンドの場合は明示的に `docker exec -it <container> bash` 経由で示す
- Redis key の確認は `redis-cli` ではなく **`sonic-db-cli <DB-NAME>`** を推奨（multi-ASIC 環境で namespace を意識せずに済むため）
- 出力例の数値・MAC・IP はマスクされたサンプル

## 引用元

[^1]: sonic-net/sonic-utilities @ 39732bceb（`show/`, `scripts/` 配下の各種ツール）
[^2]: sonic-net/sonic-swss @ 4305596（orchagent, syncd 連携）
