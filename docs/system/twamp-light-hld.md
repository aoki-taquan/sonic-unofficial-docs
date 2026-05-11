---
title: TWAMP Light（Session-Sender / Session-Reflector）
description: "TWAMP Light（Session-Sender / Session-Reflector） — RFC 5357 に基づく軽量な双方向性能測定（latency / jitter / packet loss）を SONiC ASIC offload で実装する HLD（2023-06）。"
area: system
verification: discrepancy-found
monitor: partially_implemented
last_verified: 2026-05-11
sources:
  - repo: sonic-net/SONiC
    path: doc/TWAMP/SONiC-TWAMP-Ligth-HLD.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - CFG_TWAMP_SESSION_TABLE
  cli:
    - config twamp-light
    - show twamp-light
  yang:
    - sonic-twamp-light
---

!!! warning "裏取りステータス: discrepancy-found（partially_implemented）"
    `sonic-swss/orchagent/twamporch.{cpp,h}` で `TwampOrch` 実装（`twamporch.cpp:55/92/109`、`NotificationTwampSessionEvent` ハンドリング）、テストは `tests/test_twamp.py` / `tests/mock_tests/twamporch_ut.cpp` / `tests/dvslib/dvs_twamp.py` に存在。一方 `sonic-buildimage` 配下に `sonic-twamp-light.yang` が **無く**、`sonic-utilities/config/` / `show/` に **`twamp-light` CLI が無い**。orch / SAI 層は完備、YANG / CLI 層が完全欠落（verified at: 2026-05-11）。

# TWAMP Light（Session-Sender / Session-Reflector）

## どんな機能か

RFC 5357 に基づく軽量な双方向性能測定（latency / jitter / packet loss）を SONiC ASIC offload で実装する HLD（2023-06）[^1]。control connection を持たず、Session-Sender 側が Test-Request を送り、Session-Reflector が timestamp 付きで返す純粋な data-plane プロトコル。

```text
Latency = (t3 - t0) - (t2 - t1)
Jitter  = | Latency_n - Latency_{n-1} |
PLR     = (txPkt - rxPkt) / txPkt
```

t0=sender tx, t1=reflector rx, t2=reflector tx, t3=sender rx[^1]。

Phase 1 で扱う 2 役:

- **Session-Sender**: packet-count モード（指定数）/ continuous モード（無限）
- **Session-Reflector**: 受け取って timestamp を付加して返すだけ

## コンポーネント / DB

```mermaid
flowchart LR
    USER[(CONFIG_DB\nCFG_TWAMP_SESSION_TABLE)] --> ORCH[twamp orch]
    ORCH -->|capability query| STATE[(STATE_DB\nSTATE_SWITCH_CAPABILITY_TABLE)]
    ORCH --> SAI[(SAI TWAMP)]
    SAI -->|stats| CDB[(COUNTERS_DB)]
    SAI -->|session-sender event| ORCH
    ORCH --> STATE2[(STATE_DB\nSTATE_TWAMP_SESSION_TABLE)]
    CDB --> CLI[show twamp-light ...]
```

### CONFIG_DB

```text
CFG_TWAMP_SESSION_TABLE|<name>:
  mode             = SENDER | REFLECTOR
  src_ip / dst_ip
  src_udp_port / dst_udp_port
  packet_count     # SENDER packet-count モード
  tx_interval      # SENDER 用 (us)
  timeout          # SENDER 用 reply 待ち
  vrf_name
  dscp / ttl
  hw_lookup
```

### STATE_DB / COUNTERS_DB

- `STATE_TWAMP_SESSION_TABLE|<name>`: 状態（active / completed / error）、`tx_packets` / `rx_packets` / latency / jitter
- `STATE_SWITCH_CAPABILITY_TABLE`: ASIC TWAMP support flag、CLI が事前 check[^1]
- COUNTERS_DB: session 単位で `tx_pkts` / `rx_pkts` / `latency_*` / `jitter_*` polling[^1]

ASIC は packet-count 終了時 / error 発生時に session-sender event を発行、orch が STATE を更新[^1]。`config twamp-light start/stop` で restart 可能（counter リセット → session 再 create）[^1]。

## CLI / 設定例

| Command（HLD 例示）| 用途 |
|---------|------|
| `config twamp-light session add sender <name> --mode packet-count --count N` | sender 作成 |
| `config twamp-light session add reflector <name> ...` | reflector 作成 |
| `config twamp-light session start/stop <name>` | 開始/停止 |
| `show twamp-light session status` | 状態 |
| `show twamp-light latency-jitter` / `packet-loss` | 計測結果 |

**注意**: 現状 CLI / YANG は未取り込み（実装との乖離を参照）。CONFIG_DB 直書きで起動するしかない:

```bash
# Sender 側
sonic-db-cli CONFIG_DB hmset 'TWAMP_SESSION|sender1' \
  mode "LIGHT" role "SENDER" \
  src_ip "10.0.0.1" dst_ip "10.0.0.2" \
  src_udp_port "862" dst_udp_port "862" \
  packet_count "100" tx_interval "1000" timeout "5" vrf_name "default"

# Reflector 側
sonic-db-cli CONFIG_DB hmset 'TWAMP_SESSION|reflector1' \
  mode "LIGHT" role "REFLECTOR" \
  src_ip "10.0.0.2" dst_ip "10.0.0.1" \
  src_udp_port "862" dst_udp_port "862" vrf_name "default"

sonic-db-cli STATE_DB hgetall 'TWAMP_SESSION_TABLE|sender1'
sonic-db-cli STATE_DB hgetall 'SWITCH_CAPABILITY|switch' | grep -i twamp
```

session は **warm/fast boot 越しに保持しない**（再起動で再 create）[^1]。

## 制限事項

- Phase 1: Sender / Reflector のみ。Control-Client を含む完全 TWAMP は対象外
- ASIC offload 必須。未対応 platform は capability で reject
- warm/fast boot 越しの状態保持なし
- CLI / YANG 未取り込み → `config save` で永続化できない（直書きで運用）

## 干渉する機能

- **VRF**: `vrf_name` で VRF 内 session
- **CRM / TCAM**: session ごとに ASIC リソースを消費
- **SNMP / gNMI / OAM**: 結果吸い上げ経路は HLD 外

## トラブルシューティング

```bash
sonic-db-cli STATE_DB hgetall 'TWAMP_SESSION_TABLE|sender1'         # error code
sonic-db-cli STATE_DB hgetall 'SWITCH_CAPABILITY|switch' | grep -i twamp
sonic-db-cli COUNTERS_DB keys 'COUNTERS_TWAMP_SESSION_NAME_MAP'
```

- `error` 終了 → STATE_DB の error code を確認
- capability not supported → ASIC TWAMP offload 未対応

## 実装との乖離

| 層 | 状況 |
|----|------|
| Orch / SAI | **取り込み済**（`twamporch.cpp` 実装、SAI_TWAMP_* 属性使用、test 完備）|
| YANG `sonic-twamp-light` | **欠落**（sonic-buildimage に存在せず）|
| `config/show twamp-light` CLI | **欠落**（sonic-utilities 配下に grep ヒット 0）|

**読者への影響**:

- HLD の `config/show twamp-light` を叩くと `No such command`
- YANG 無しで `config save/load` 経由は schema validation で reject されうる → 生 CONFIG_DB 直書きで運用
- HA / `config_reload` 越しの再現には独自 playbook が必要

> 分類: `monitor: partially_implemented` — HLD スタックのうち低層が取り込まれ、上層（YANG / CLI）が未完成。

### 関連 GitHub Issue / PR

- [sonic-swss #2927: \[orchagent\] TWAMP Light orchagent implementation (merged)](https://github.com/sonic-net/sonic-swss/pull/2927) — TwampOrch 取り込み確定 PR
- [sonic-buildimage #24135: Enhancement: \[YANG\] YANG model needed for TWAMP_SESSION (open)](https://github.com/sonic-net/sonic-buildimage/issues/24135) — YANG 欠落 issue
- [SONiC #1192: Two-Way Active Measurement Protocol (TWAMP) Light (open)](https://github.com/sonic-net/SONiC/issues/1192) — community 全体トラッキング

## 関連 Topics

- [09-telemetry-snmp](../topics/09-telemetry-snmp/index.md): 計測 / telemetry 全般
- [04-vrf-ecmp](../topics/04-vrf-ecmp/index.md): VRF 内 session

## 引用元

[^1]: `sonic-net/SONiC` `doc/TWAMP/SONiC-TWAMP-Ligth-HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: NAT / DHCP Relay / Time-DNS Services](../topics/16-nat-dhcp-dns/index.md)

<!-- /topics-back-ref -->
