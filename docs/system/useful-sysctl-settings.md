---
title: FRR 用 sysctl チューニングのデフォルト
area: system
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-frr
    path: doc/user/Useful_Sysctl_Settings.md
    ref: 799f47f215e4266063c4ebde0041a0c7dd2d11d0
related:
  config_db: []
  cli: []
  yang: []
---

!!! warning "裏取りステータス: HLD-only"
    このページは sonic-frr の上流 FRR ドキュメントを再構成している。SONiC 側のイメージで実際に投入されている sysctl（`sonic-buildimage` の `etc/sysctl.d/` または起動スクリプトでの set）は未裏取り。SONiC が同等の値を採用しているとは限らないため、本ページは「FRR が推奨する出発点」として読むこと。

# FRR 用 sysctl チューニングのデフォルト

## 概要

SONiC の制御プレーンでは FRR を使ってルーティングプロトコル（BGP / OSPF / 等）を回す。Linux カーネルの sysctl は **forwarding 有効化、ARP 挙動、neighbor GC、ルート / IGMP / MLD のスケール上限など** を細かく制御でき、FRR の挙動を大きく左右する[^1]。

このページは sonic-frr 同梱の `doc/user/Useful_Sysctl_Settings.md` が示す **「論理的なデフォルト set」** を整理したもの。BGP unnumbered や OSPF を素直に動かすのに有用な値が並ぶ[^1]。

> 注意: これは **FRR 上流の推奨値**。SONiC のリリースイメージが同じ値を採用しているかは別途確認が必要。本ページの値を直接 `/etc/sysctl.d/99frr_defaults.conf` に流し込むなら、SONiC 既定値との差分を意識する必要がある。

## 動作仕様

### IPv4 / IPv6 forwarding を有効化

```text
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
net.ipv4.conf.all.forwarding = 1
net.ipv4.conf.default.forwarding = 1
```

ルータとして使う以上、forwarding は ON 必須[^1]。`all` と `default` の両方を立てるのは、新規生成 interface にも自動でデフォルト適用させる典型構成。

### ルート関連

```text
net.ipv6.route.max_size = 131072
net.ipv4.conf.all.ignore_routes_with_linkdown = 1
net.ipv6.conf.all.ignore_routes_with_linkdown = 1
```

- IPv6 ルート最大数を 128K に拡張[^1]。SONiC 規模のフルテーブルを抱えるには既定値だと不足。
- リンクダウンしたインターフェース経由のルートを **無視** する。FRR が link state に追従して経路を切替えるための前提[^1]。

### BGP unnumbered / OSPF 向け

```text
net.ipv4.conf.all.rp_filter = 0
net.ipv4.conf.default.rp_filter = 0
net.ipv4.conf.lo.rp_filter = 0
net.ipv4.conf.default.arp_announce = 2
net.ipv4.conf.default.arp_notify = 1
net.ipv4.conf.default.arp_ignore = 1
net.ipv4.conf.all.arp_announce = 2
net.ipv4.conf.all.arp_notify = 1
net.ipv4.conf.all.arp_ignore = 1
net.ipv4.icmp_errors_use_inbound_ifaddr = 1
```

- **`rp_filter = 0`**: uRPF を無効化。BGP unnumbered のように非対称経路や IPv6 link-local 経由 nexthop を扱う構成では、strict mode の uRPF が誤って drop することがある[^1]。
- **ARP 系**:
  - `arp_announce = 2`: best local address only を announce。loopback アドレスを意図せず ARP しないため。
  - `arp_notify = 1`: link up やアドレス追加時に GARP を送出。
  - `arp_ignore = 1`: 入力 interface 上のアドレス向けの ARP のみ応答[^1]。
  これらは **アドレスをループバックに集約** する SONiC のような設計と相性が良い。
- `icmp_errors_use_inbound_ifaddr = 1`: ICMP エラーの送信元アドレスに **入力インターフェースのアドレス** を使う。traceroute の見え方が直感的になる[^1]。

### IPv6 アドレスを admin down で残す

```text
net.ipv6.conf.all.keep_addr_on_down = 1
```

interface を admin down にしても、permanent な IPv6 アドレスを **残す**[^1]。FRR の動作中に link を上げ下げしても link-local の neighborship を壊さないようにする。

### IGMP / MLD のスケール

```text
net.ipv4.igmp_max_memberships = 1000
net.ipv4.neigh.default.mcast_solicit = 10
net.ipv6.mld_max_msf = 512
```

multicast 関連の上限を引き上げる[^1]。デフォルトのままでは多数の (S,G) を扱う運用で詰まりやすい。

### ARP / Neighbor GC

```text
net.ipv4.neigh.default.gc_thresh2 = 7168
net.ipv4.neigh.default.gc_thresh3 = 8192
net.ipv4.neigh.default.base_reachable_time_ms = 14400000
net.ipv6.neigh.default.gc_thresh2 = 3584
net.ipv6.neigh.default.gc_thresh3 = 4096
net.ipv6.neigh.default.base_reachable_time_ms = 14400000
```

- `gc_thresh2/3`: neighbor table の **soft / hard 上限**。SONiC 規模のスイッチでは neighbor が数千になりがちなので緩める[^1]。
- `base_reachable_time_ms = 14400000`（4 時間）: neighbor が reachable として扱われる時間。長めに取って probe 頻度を下げる[^1]。

### ECMP の neighbor 利用

```text
net.ipv4.fib_multipath_use_neigh = 1
```

multipath ECMP の nexthop 選択に **neighbor 情報を使う**[^1]。

### VRF と TCP

```text
net.ipv4.tcp_l3mdev_accept = 1
```

VRF（L3 master device）に bind されていない app からも、VRF 上の TCP 接続を受けられるようにする[^1]。SONiC で management VRF を使う場合などに有用。

### 適用方法

ファイルとして `/etc/sysctl.d/99frr_defaults.conf` に配置し、再起動するか以下で即時反映する[^1]:

```bash
sysctl -p /etc/sysctl.d/99frr_defaults.conf
```

ファイル名の `99` プレフィックスは sysctl ファイルの読み込み順を **遅らせて、他の設定を上書きする** ための慣習。

```mermaid
flowchart LR
    F[/etc/sysctl.d/99frr_defaults.conf/] -->|boot or sysctl -p| K[Linux kernel\nsysctl values]
    K --> FRR[FRR\nbgpd / ospfd / zebra]
    K --> KERNEL[Forwarding plane\n(Linux netdev / RIB)]
```

<!-- evidence:
source: sonic-net/sonic-frr/doc/user/Useful_Sysctl_Settings.md#L1-L60 (sha: 799f47f215e4266063c4ebde0041a0c7dd2d11d0)
excerpt: |
  # /etc/sysctl.d/99frr_defaults.conf
  net.ipv6.route.max_size=131072
  net.ipv4.conf.all.rp_filter = 0
  net.ipv6.conf.all.keep_addr_on_down=1
  net.ipv4.fib_multipath_use_neigh=1
  net.ipv4.tcp_l3mdev_accept=1
reasoning: 推奨デフォルト群の出典・キー名の根拠。
-->

## 設定

### 関連する CONFIG_DB

該当なし。sysctl は Linux カーネルの設定で、SONiC の CONFIG_DB は通らない。

### 関連する CLI

該当なし。SONiC の `config` 系から sysctl を直接編集する CLI は無い。Linux 標準の `sysctl` / `/etc/sysctl.d/` を使う。

### 確認方法

```bash
# 全 sysctl を確認
sysctl -a | grep -E 'forward|rp_filter|gc_thresh|keep_addr_on_down'

# 個別確認
sysctl net.ipv6.route.max_size
sysctl net.ipv4.tcp_l3mdev_accept
```

## 制限事項

- これは **FRR 上流の推奨**。SONiC 側で同じ値が既に投入されているか、別の値が好まれているかは別途確認が必要[^1]。
- `rp_filter = 0` はセキュリティ機能（spoof 防止）を弱める方向の変更。**意図的に外して unnumbered / 非対称ルーティングを許容する** 性格の設定。要件次第で `loose mode (1)` を選ぶ判断もありうる。
- `gc_thresh2/3` の数値はスイッチ規模に応じて調整する。データセンタ向けにはここよりさらに大きくしたい場合がある。
- `base_reachable_time_ms = 14400000` は `4h` で長め。stale neighbor の検知が遅くなる副作用があるが、neighbor フラッピングを抑える狙いで意図された値[^1]。
- `keep_addr_on_down` は IPv6 link-local の挙動を変える。link-local を再生成して欲しい運用と衝突する可能性がある。

## 干渉する機能

- **BGP unnumbered**: `rp_filter=0`、`keep_addr_on_down=1`、`arp_*` 群と整合的な構成[^1]。これらが揃わないと unnumbered の neighborship が安定しないことがある。
- **management VRF**: `tcp_l3mdev_accept=1` がないと、VRF 上のサービス（mgmt VRF 経由 SSH 等）に bind しないアプリから接続できないケースが出る[^1]。
- **ECMP**: `fib_multipath_use_neigh=1` が無いと multipath で実 reachable な nexthop に偏らせる挙動が弱まる[^1]。
- **IGMP / MLD scale**: マルチキャストを使う運用で `igmp_max_memberships` / `mld_max_msf` が既定だとカウンタ詰まりが起きる。`mcast_solicit=10` は応答性のチューニング。
- **大規模 IPv6 RIB**: `net.ipv6.route.max_size=131072` を超える RIB を扱うとカーネル側でルートが落ち始める。フルテーブルの IPv6 を扱うなら更に拡張が必要。

## トラブルシューティング

- BGP unnumbered の neighborship が成立しない: `rp_filter`, `arp_*`, `keep_addr_on_down` を確認。`sysctl -a | grep -E 'rp_filter|arp_'` で値を点検[^1]。
- IPv6 ルートが受け取れない / 一部 drop される: `net.ipv6.route.max_size` の上限に達している可能性。`dmesg` に該当メッセージがないか確認[^1]。
- neighbor が大量に消える: `gc_thresh2/3` を超過。値を上げる[^1]。
- traceroute の "から" の IP が想定と違う: `icmp_errors_use_inbound_ifaddr=1` の有無を確認[^1]。
- mgmt VRF 上のアプリで bind 失敗: `tcp_l3mdev_accept=1` の有無を確認[^1]。

## 引用元

[^1]: `sonic-net/sonic-frr` `doc/user/Useful_Sysctl_Settings.md` @ `799f47f215e4266063c4ebde0041a0c7dd2d11d0`
