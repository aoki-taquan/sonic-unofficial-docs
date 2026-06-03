---
title: DIP=SIP PTF 検証 内部実装（パケット仕様 / パラメータ）
description: DIP=SIP PTF 検証テストの dip_sip.py パラメータと送受信パケット仕様（DIP=SIP のまま L3 ルーティング、TTL/HL が 1 減って受信される）を整理する。
area: architecture
verification: discrepancy-found
last_verified: 2026-05-11
page_kind: split-child
monitor: evolved_beyond_hld
sources:
- repo: sonic-net/SONiC
  path: doc/dip-sip/DIP=SIP_HLD.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  _no_related_yang: true
  config_db: []
  cli: []
  yang: []
---

# DIP=SIP PTF 検証 内部実装

このページは [DIP=SIP PTF 検証（概要ハブ）](dip-sip-ptf-validation-high-level-design.md) の派生で、**PTF テスト本体のパラメータと送受信パケット仕様** に絞って整理する。概念は [dip-sip-ptf-validation-high-level-design-concepts.md](dip-sip-ptf-validation-high-level-design-concepts.md)、ファイル構成は [dip-sip-ptf-validation-high-level-design-operations.md](dip-sip-ptf-validation-high-level-design-operations.md)、制限と乖離は [dip-sip-ptf-validation-high-level-design-limitations.md](dip-sip-ptf-validation-high-level-design-limitations.md) を参照。

## 1. dip_sip.py のパラメータ

PTF テスト本体に渡す引数[^1]:

| Parameter | 説明 |
|-----------|------|
| `testbed_type` | Testbed 種別 |
| `dst_host_mac` / `src_host_mac` | host 側 MAC |
| `dst_router_mac` / `src_router_mac` | DUT 側 [RIF](../reference/glossary.md#term-rif) MAC |
| `dst_router_ipv4` / `src_router_ipv4` | DUT RIF IPv4 |
| `dst_router_ipv6` / `src_router_ipv6` | DUT RIF IPv6 |
| `dst_port_ids` / `src_port_ids` | PTF port index の配列（複数 member 用）|

## 2. テストパケット仕様

PTF は **送信パケット (data)** と **期待パケット (expected)** を生成し、source port から data を送って destination port のいずれかで expected が受かることを確認する[^1]。

既定値とアドレス計算[^1]:

```text
pkt_ttl_hlim   = 64
dst_host_ipv4/ipv6 = <dst_router_ipv4/ipv6> + 1
src_host_ipv4/ipv6 = <src_router_ipv4/ipv6> + 1
```

**Data packet** — DUT に届く時点でのフィールド[^1]:

| フィールド | 値 |
|-----------|----|
| DST_MAC | `<src_router_mac>` |
| SRC_MAC | `<src_host_mac>` |
| DST_IP | `<dst_host_ipv4_ipv6>` |
| **SRC_IP** | **`<dst_host_ipv4_ipv6>`** ← ここが本テストの主眼 |
| TTL/HL | `<pkt_ttl_hlim>`（既定 64）|

**Expected packet** — destination 側で観測される値[^1]:

| フィールド | 値 |
|-----------|----|
| DST_MAC | `<dst_host_mac>` |
| SRC_MAC | `<dst_router_mac>` |
| DST_IP | `<dst_host_ipv4_ipv6>` |
| SRC_IP | `<dst_host_ipv4_ipv6>` |
| TTL/HL | `<pkt_ttl_hlim>` − 1 |

DUT が **L3 ルーティング** していれば MAC は書き換わり、TTL/HL は 1 減って受信される。**SRC_IP = DST_IP** のままでもパケットがドロップされず到達することが「pass」の判定[^1]。

<!-- evidence-rendered:start -->
??? note "検証エビデンス: sonic-net/SONiC/doc/dip-sip/DIP=SIP_HLD.md#L120-L143"

    **出典**: `sonic-net/SONiC/doc/dip-sip/DIP=SIP_HLD.md#L120-L143 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    Default values:
    * pkt_ttl_hlim=64
    Values:
    * dst_host_ipv4_ipv6=<dst_router_ipv4_ipv6>+1
    * src_host_ipv4_ipv6=<src_router_ipv4_ipv6>+1
    Data packet:
    * DST_IPv4_IPv6=<dst_host_ipv4_ipv6>
    * SRC_IPv4_IPv6=<dst_host_ipv4_ipv6>
    Expected packet:
    * TTL_HL=<pkt_ttl_hlim>-1
    ```

    **判断根拠**: テストの判定ロジック（DIP=SIP のままルーティングされ TTL が 1 減る）の根拠。

<!-- evidence-rendered:end -->

## 3. 判定

期待パケットが destination port のいずれかで観測されれば pass、それ以外は fail。fail 時は **expected / received のパケットダンプを含むエラーメッセージ** が出力される[^1]。

## 4. 関連ページへの導線

- [dip-sip-ptf-validation-high-level-design.md](dip-sip-ptf-validation-high-level-design.md) — 概要ハブ
- [dip-sip-ptf-validation-high-level-design-concepts.md](dip-sip-ptf-validation-high-level-design-concepts.md) — 概念
- [dip-sip-ptf-validation-high-level-design-operations.md](dip-sip-ptf-validation-high-level-design-operations.md) — ファイル構成 / 実行
- [dip-sip-ptf-validation-high-level-design-limitations.md](dip-sip-ptf-validation-high-level-design-limitations.md) — 制限・[HLD](../reference/glossary.md#term-hld) 乖離

## 実装との乖離

`monitor: evolved_beyond_hld` — `monitor: evolved_beyond_hld` の HLD と実装の差分。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [DIP=SIP PTF 検証 内部実装 親ページ](dip-sip-ptf-validation-high-level-design.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

## 引用元

[^1]: `sonic-net/SONiC` `doc/dip-sip/DIP=SIP_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: 0ffb8e51f432 -->

## 制限事項

!!! diff "HLD と実装の乖離"
    - HLD と実装の差分は本ページの章本文で逐次注記している
    - 追加の境界事項は本セクションで列挙する

## 確認コマンド

dip-sip-ptf internals の動作確認に使う代表コマンド:

```bash
# 基本動作確認
show platform summary
show version
docker logs --tail 200 $(docker ps --format "{{.Names}}" | head -1)
```

