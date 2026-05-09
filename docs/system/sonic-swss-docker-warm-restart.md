---
title: SWSS docker warm restart（state restore / consistency / sync up）
area: system
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/warm-reboot/swss_warm_restart.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - WARM_RESTART
  cli:
    - config warm_restart
  yang: []
---

!!! warning "裏取りステータス: HLD-only / 古い HLD"
    本 HLD は SONiC 初期の swss container 単体 warm restart 設計。`m_toSync` 空判定や ProducerStateTable の consumer-only modify などは現行 master と差分の可能性。`priority=high`。

# SWSS docker warm restart（state restore / consistency / sync up）

## 概要

SWSS container（orchagent + 周辺 syncd 連携）を再起動・上げ替える際にデータプレーンを乱さないため、**control plane state を complete に復元 → 復元中に流れた変動を sync up する** 仕組み[^1]。

state は複数ソースから来る:

- `CONFIG_DB` + `port_config.ini` / `pg_lookup.ini`: ポート / VLAN / interface / buffer / QoS / CRM / PFC WD / ACL の基本情報
- Linux kernel: portsyncd / intfsyncd / neighsyncd が netlink から拾う
- teamd: LAG state（teamsyncd）
- bgp / fpmsyncd: ROUTE_TABLE
- json: COPP / Tunnel / Mirror
- syncd: FDB / port state（ASIC 由来）

## 動作仕様

### Restore: 各データの復元元

| Data | Restore source |
|------|---------------|
| Port / VLAN / INTF | port config + Linux `RTM_GETLINK` dump（APPDB から直接ではない）[^1] |
| ARP / LAG / route | APPDB から orchagent が直接復元 |
| QoS / Buffer / CRM / PFC WD / ACL | CONFIG_DB から起動時に再読込 |
| COPP / Tunnel / Mirror | JSON 経由で APPDB へ再ロード |
| FDB / port state | APPDB（事前に syncd が反映） |
| Switch default OID | SAI `get` で syncd から取得 |

### Pre / Post 検証

```mermaid
sequenceDiagram
    participant ORCH as orchagent
    participant CONS as Consumers
    participant DB as APPDB
    Note over ORCH: Pre-restart
    ORCH->>CONS: "restart prepare"
    CONS-->>ORCH: m_toSync 空? -> success/fail
    ORCH-->>ORCH: success なら APPDB 変更を凍結フラグ ON
    Note over ORCH: 再起動
    Note over ORCH: Post-restore
    CONS-->>ORCH: m_toSync 空であることを再確認
    ORCH->>DB: sync up（ARP/port/FDB/LAG/route）
```

`m_toSync` に未処理が残っている状態では warm restart に入れない（依存解消待ち）[^1]。`ProducerStateTable` / `ConsumerStateTable` は consumer 側だけが実テーブルを書くように改修される。

### Sync up

restart window 中に動的データ（ARP / port state / FDB / LAG / route）が変動するため、orchagent は復元後に最新ネットワーク状態と整合させる。各サブシステムごとに sync up ロジックを持つ[^1]。

### swss / syncd の docker 分離

旧設計では swss / syncd が同 systemd unit で起動していた。warm restart のため **syncd docker を分離**し、syncd は live のまま swss だけ再起動できる構成にする[^1]。

### 失敗時 fallback

warm start が失敗したら **automatic fallback to system cold restart**（手動切替コマンドも提供）[^1]。

## 設定

`config warm_restart enable swss` 系を CLI で叩いて `WARM_RESTART` テーブルを enable。

## 制限事項

- **CONFIG_DB は restart window 中に変えない**前提（HLD 明記）[^1]
- `STATE_DB` flush の是非は HLD 内で open issue
- swss に依存する他 docker（systemd 上）の扱いも open issue

## 干渉する機能

- **system-wide warmboot**: SWSS warm restart は単 container 版、system-wide はその上位
- **PFC / FDB / route / ARP**: 各 sync up ロジックが個別に実装される
- **ProducerStateTable / ConsumerStateTable**: 改修の影響が共通基盤に及ぶ

## トラブルシューティング

- 起動時に init view が完了しない → syncd の OID 取得が遅い、`m_toSync` 残留を疑う
- restart window 中の ROUTE 不整合 → fpmsyncd / bgp の sync up 経路を確認

## 引用元

[^1]: `sonic-net/SONiC` `doc/warm-reboot/swss_warm_restart.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- m_toSync 空判定 + restart prepare API の現行 orchagent 実装確認
- ProducerStateTable / ConsumerStateTable の consumer-only modify 改修の取り込み確認
- swss / syncd docker 分離の現行 systemd unit 構成確認
- WARM_RESTART テーブルの YANG 取り込み確認
- 失敗時 cold restart 自動 fallback の現行実装確認
- 古い HLD（priority=high）のため Warmboot Manager との置換確認
-->
