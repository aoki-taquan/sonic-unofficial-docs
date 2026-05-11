---
title: Active-Standby Dual ToR 設定と運用（CONFIG_DB / CLI / トラブルシューティング）
description: "Active-Standby Dual ToR の設定経路。CONFIG_DB / APP_DB / STATE_DB スキーマ、muxcable CLI、switchover 計測と運用時のトラブルシューティング手順を扱う。"
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
  cli:
    - config muxcable mode
    - show muxcable config
    - show muxcable status
  yang: []
---

# Active-Standby Dual ToR 設定と運用

このページは [Active-Standby Dual ToR（概要ハブ）](active-standby-dual-tor.md) の派生ページで、**CONFIG_DB / APP_DB / STATE_DB スキーマと CLI、トラブルシューティング** に絞って整理する。概念は [active-standby-dual-tor-concepts.md](active-standby-dual-tor-concepts.md)、内部実装は [active-standby-dual-tor-internals.md](active-standby-dual-tor-internals.md)、制限事項は [active-standby-dual-tor-limitations.md](active-standby-dual-tor-limitations.md) を参照。

## 1. CONFIG_DB

| Table | Key | フィールド | 説明 |
|-------|-----|-----------|------|
| `MUX_LINKMGR` | `LINK_PROBE` | `interval_v4` / `interval_v6` / `timeout` / `suspend_timer` / `positive_signal_count` / `negative_signal_count` | linkmgrd チューニング |
| `localhost MUX_DRIVER` | - | `i2c_retry_count` | ycabled の MUX 失敗判定回数 |
| `MUX_CABLE` | `<PORT>` | `state ∈ {active, standby, auto, manual}`, `server_ipv4`, `server_ipv6` | port 単位 mux 設定 |
| `PEER_SWITCH` | `<switchname>` | `address_ipv4` | peer ToR の loopback |
| `TUNNEL` | `MUX_TUNNEL` | `tunnel_type=IPINIP`, `dst_ip`, `dscp_mode`, `encap_ecn_mode`, `ecn_mode`, `ttl_mode` | IPinIP tunnel 定義 |
| `DEVICE_METADATA` | `localhost` | `type=ToRRouter`, `peer_switch`, `subtype=DualTor` | dual ToR 識別 |

## 2. APP_DB / STATE_DB

| Table | フィールド | 説明 |
|-------|-----------|------|
| `APP_DB.MUX_CABLE` | `state ∈ {active, standby, unknown}` | linkmgrd ↔ swss |
| `APP_DB.HW_MUX_CABLE` | `state ∈ {active, standby}` | orchagent ↔ ycabled |
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

## 関連ページ

- [Active-Standby Dual ToR（概要ハブ）](active-standby-dual-tor.md)
- [active-standby-dual-tor-concepts.md](active-standby-dual-tor-concepts.md) — 構成と要件
- [active-standby-dual-tor-internals.md](active-standby-dual-tor-internals.md) — 内部実装
- [active-standby-dual-tor-limitations.md](active-standby-dual-tor-limitations.md) — 制限事項

## 引用元

[^1]: `sonic-net/SONiC` `doc/dualtor/dualtor_active_standby_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
