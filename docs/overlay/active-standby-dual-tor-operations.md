---
title: Active-Standby Dual ToR 設定と運用（CONFIG_DB / CLI / トラブルシューティング）
description: Active-Standby Dual ToR の設定経路。CONFIG_DB / APP_DB / STATE_DB スキーマ、muxcable
  CLI、switchover 計測と運用時のトラブルシューティング手順を扱う。
area: overlay
verification: code-verified
last_verified: 2026-05-09
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/dualtor/dualtor_active_standby_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - MUX_LINKMGR
  - MUX_CABLE
  - PEER_SWITCH
  - TUNNEL
  - DEVICE_METADATA
  - XCVRD_LOG
  cli:
  - config muxcable mode
  - show muxcable config
  - show muxcable status
  - config muxcable
  - show muxcable
  yang:
  - sonic-mux-cable
---

# Active-Standby Dual ToR 設定と運用

このページは [Active-Standby Dual ToR（概要ハブ）](active-standby-dual-tor.md) の派生ページで、**[CONFIG_DB](../reference/glossary.md#term-config_db) / APP_DB / [STATE_DB](../reference/glossary.md#term-state_db) スキーマと CLI、トラブルシューティング** に絞って整理する。概念は [active-standby-dual-tor-concepts.md](active-standby-dual-tor-concepts.md)、内部実装は [active-standby-dual-tor-internals.md](active-standby-dual-tor-internals.md)、制限事項は [active-standby-dual-tor-limitations.md](active-standby-dual-tor-limitations.md) を参照。

## 1. CONFIG_DB

| Table | Key | フィールド | 説明 |
|-------|-----|-----------|------|
| `MUX_LINKMGR` | `LINK_PROBE` | `interval_v4` / `interval_v6` / `timeout` / `suspend_timer` / `positive_signal_count` / `negative_signal_count` | [linkmgrd](../reference/glossary.md#term-linkmgrd) チューニング |
| `localhost MUX_DRIVER` | - | `i2c_retry_count` | ycabled の [MUX](../reference/glossary.md#term-mux) 失敗判定回数 |
| `MUX_CABLE` | `<PORT>` | `state ∈ {active, standby, auto, manual}`, `server_ipv4`, `server_ipv6` | port 単位 mux 設定 |
| `PEER_SWITCH` | `<switchname>` | `address_ipv4` | peer ToR の loopback |
| `TUNNEL` | `MUX_TUNNEL` | `tunnel_type=IPINIP`, `dst_ip`, `dscp_mode`, `encap_ecn_mode`, `ecn_mode`, `ttl_mode` | [IPinIP](../reference/glossary.md#term-ipinip) tunnel 定義 |
| `DEVICE_METADATA` | `localhost` | `type=ToRRouter`, `peer_switch`, `subtype=DualTor` | dual ToR 識別 |

## 2. APP_DB / STATE_DB

| Table | フィールド | 説明 |
|-------|-----------|------|
| `APP_DB.MUX_CABLE` | `state ∈ {active, standby, unknown}` | linkmgrd ↔ swss |
| `APP_DB.HW_MUX_CABLE` | `state ∈ {active, standby}` | [orchagent](../reference/glossary.md#term-orchagent) ↔ ycabled |
| `APP_DB.MUX_CABLE_COMMAND` | `command ∈ {probe, link_status_peer}` | linkmgrd → ycabled |
| `APP_DB.MUX_CABLE_RESPONSE` | `response`, `link_status_peer` | ycabled → linkmgrd |
| `STATE_DB.MUX_CABLE_TABLE` | `state ∈ {active, standby, unknown, error}` | orchagent |
| `STATE_DB.HW_MUX_CABLE_TABLE` | `state ∈ {active, standby, unknown}` | ycabled |
| `STATE_DB.MUX_LINKMGR_TABLE` | `state ∈ {healthy, unhealthy, uninitialized}` | linkmgrd 合成 |
| `STATE_DB.MUX_METRICS_TABLE` | `<app>_switch_<state>_start/end` | 切替計測 |
| `STATE_DB.MUX_SWITCH_CAUSE` | `cause`, `time` | 最後の switchover 原因 |
| `STATE_DB.LINK_PROBE_STATS` | `pck_loss_count`, `pck_expected_count` 等 | プローブ統計 |

## 3. CLI

| Command | 用途 |
|---------|------|
| `config muxcable mode {active\|auto\|manual\|standby} {<port>\|all} [--json]` | mux モード切替 |
| `show muxcable config [<port>] [--json]` | 設定状態 |
| `show muxcable status [<port>] [--json]` | 動作状態（STATUS / HEALTH） |

```bash
config muxcable mode auto Ethernet4
config muxcable mode active Ethernet4
config muxcable mode auto all
```

`config muxcable mode active` の戻り値[^1]:

| RC | 出力 | 意味 |
|----|------|------|
| 100 | `{"Ethernet4":"OK"}` | 既に active |
| 100 | `{"Ethernet4":"INPROGRESS"}` | 切替中 |
| 0 / 1 | - | 成功 / 失敗 |

## 4. トラブルシューティング

| 症状 | 最初に見る場所 |
|------|---------------|
| `HEALTH=UNHEALTHY` | `MUX_LINKMGR_TABLE.state` と `LINK_PROBE_STATS.pck_loss_count` |
| standby 側 server 宛 traffic が永続 black-hole | `NEIGH` table の zero mac entry / tunnel route の有無 |
| `MUX_CABLE_TABLE.state=error`（I2C ループ） | `i2c_retry_count` 設定とハードウェア / cable 個体 |
| switchover に時間がかかる | `MUX_METRICS_TABLE` の `<app>_switch_active_*` |
| IPv6 のみ切替で断 | `accept_untracked_na` と `arp_update` の `FAILED → INCOMPLETE` 書き換え |

### コマンド例

下記コマンドで MUX/ToR の状態と切替動作を確認できる。

```bash
# Dual ToR mux 状態と切替メトリクス
show mux status
show mux config
redis-cli -n 0 keys 'MUX_CABLE_TABLE:*'
redis-cli -n 6 hgetall 'MUX_LINKMGR_TABLE|Ethernet0'
redis-cli -n 6 hgetall 'LINK_PROBE_STATS|Ethernet0'
```

## 関連ページ

- [Active-Standby Dual ToR（概要ハブ）](active-standby-dual-tor.md)
- [active-standby-dual-tor-concepts.md](active-standby-dual-tor-concepts.md) — 構成と要件
- [active-standby-dual-tor-internals.md](active-standby-dual-tor-internals.md) — 内部実装
- [active-standby-dual-tor-limitations.md](active-standby-dual-tor-limitations.md) — 制限事項

## 制限事項

- **詳細な制限の正典は別ページ**: 設計上の制約は [active-standby-dual-tor-limitations.md](active-standby-dual-tor-limitations.md) を参照。本ページでは運用面で意識すべき制限のみを抜粋する。
- **I2C アクセスは順次**: `MUX_CABLE` の `i2c_retry_count` を増やしても、I2C はバス共有でシリアル化されるため、同時 mux 切替の並列度は限られる。短時間に多数の切替を起こすとレイテンシが伸びる。
- **`config mux` の即時反映なし**: CLI による mux state 変更は [MuxOrch](../reference/glossary.md#term-muxorch) / linkmgrd 経由のため、`MUX_CABLE.state` が反映されるまで数秒のラグがある。
- **`show mux status` の値は STATE_DB スナップショット**: 切替中のレース観測のため瞬間値は揺れる。安定値を見るときは 1 〜 2 秒空けて再取得する運用が必要。
- **runbook 推奨**: 異常時のフロー切り分けは Dual-ToR 用 runbook (mux-state-flap, server-traffic-blackhole 等) を併用すること。CLI コマンド単独では切り分けきれないケースが多い。

## 引用元

[^1]: `sonic-net/SONiC` `doc/dualtor/dualtor_active_standby_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: 0a1df176ebd3 -->
