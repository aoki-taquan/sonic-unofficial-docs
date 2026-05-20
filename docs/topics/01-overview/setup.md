---
title: 設定
description: 設定 — 全体像章での「設定」は個別機能の手順ではなく、SONiC で設定を入れるときに最低限押さえる入口の選び方と CONFIG_DB
  の触り方を整理する。
area: topics
verification: meta
last_verified: 2026-05-12
sources:
- docs/management/sonic-nos-configuration-methods.md
- docs/management/sonic-user-manual.md
- docs/architecture/sonic-generic-configuration-update-and-rollback.md
- docs/reference/cli/config-mgmt-trio.md
- docs/reference/cli/sonic-cfggen.md
- docs/reference/config-db/device-metadata.md
related:
  cli:
  - config reload
  - config save
  - config load
  - sonic-cfggen
  - config apply-patch
  config_db:
  - DEVICE_METADATA
  - FEATURE
  - VERSIONS
  yang:
  - sonic-device-metadata
  - sonic-feature
---

# 設定

全体像章での「設定」は個別機能の手順ではなく、[SONiC](../../reference/glossary.md#term-sonic) で設定を入れるときに最低限押さえる **入口の選び方と [CONFIG_DB](../../reference/glossary.md#term-config_db) の触り方** を整理する。個別機能の設定は各章 (`02-bgp` 以降) の `setup.md` を読む。

## 設定入口の地図

SONiC には設定を入れる入口が複数あり、最終的にはすべて CONFIG_DB に着地する。読み手はまず「自分の運用が何系か」で入口を選ぶ。

| 入口 | 典型用途 | 性質 |
| --- | --- | --- |
| `config` CLI (Click 系) | 手動運用、変更の都度 commit | CONFIG_DB を直接書く。validation は最低限 |
| `sonic-cli` / Management Framework | [gNMI](../../reference/glossary.md#term-gnmi)/REST/RESTCONF を併用する自動化 | [YANG](../../reference/glossary.md#term-yang) validation あり |
| `config_db.json` 直編集 + `config reload` | bootstrap、ラボ、[ZTP](../../reference/glossary.md#term-ztp) | DB を丸ごと差し替え |
| `config apply-patch` / `replace` ([GCU](../../reference/glossary.md#term-gcu)) | 差分適用と rollback | YANG-aware な partial update |
| `sonic-cfggen` | minigraph / template から CONFIG_DB を生成 | 主に build/ZTP/初期化フェーズ |

入口を混在させると `*mgrd` の再描画で意図しない上書きが起きやすい。**1 つの機能ドメインは原則 1 入口** に揃え、変更直前に `config save` で `config_db.json` を退避するのが最も事故が少ない。

## 最小の触り方 (read → mutate → verify)

CONFIG_DB を直接触る場合、最小の作法は次の 3 段に集約される。

```bash
# 1. 現在値を読む (DB 4 = CONFIG_DB)
redis-cli -n 4 hgetall 'DEVICE_METADATA|localhost'

# 2. 変更する (CLI 経由が原則。redis-cli 直書きは debug のみ)
sudo config hostname new-tor-01

# 3. 反映と永続化を確認する
sudo config save -y                 # /etc/sonic/config_db.json を更新
redis-cli -n 4 hgetall 'DEVICE_METADATA|localhost'
```

注意点は 3 つある。

- `config save` を忘れると、再起動で変更が消える。`config replace` 系は内部で save しないので明示する。
- `redis-cli -n 4` で直接書く運用は、`*mgrd` が変更通知を受け取らないテーブルがあるため非推奨。debug 以外では CLI / YANG 経由に揃える。
- `*mgrd` を経由する変更は CONFIG_DB → [APPL_DB](../../reference/glossary.md#term-appl_db) → [ASIC_DB](../../reference/glossary.md#term-asic_db) と伝搬する。CONFIG_DB に書いた直後に ASIC_DB が変わらない場合、`*mgrd` が落ちているか、validation で弾かれていることが多い。

## 設定の永続化レイヤ

SONiC の設定は **2 つのレイヤ** で永続化される。読み違えると「`config save` したのに reboot で消える」事故になる。

| レイヤ | 何が保存されるか | 触る操作 |
| --- | --- | --- |
| [Redis](../../reference/glossary.md#term-redis) CONFIG_DB (in-memory) | 現在の意図 | CLI / gNMI / `redis-cli` |
| `/etc/sonic/config_db.json` (disk) | 再起動時に CONFIG_DB に load する snapshot | `config save` / `config load` / `config reload` |

`config reload` は disk の `config_db.json` を CONFIG_DB に再 load し、`*mgrd` を再起動する。つまり「DB に直接書いたが save していない変更」は `config reload` で消える。ラボでは `config save` → `config reload -y` の往復で確実に永続化を試験する。

## bootstrap (ZTP / 初回起動) の入口

ZTP や初回起動では、`minigraph.xml` や YAML プロファイルから `sonic-cfggen` が `config_db.json` を生成する。流れは次の通り。

1. ONIE installer が image を展開し、`/etc/sonic/` に `minigraph.xml` (DC 系) または `config_db.json` (ベア start) を置く。
2. `swss.service` 起動前に `sonic-cfggen -H -m -y /etc/sonic/init_cfg.json --write-to-db` が走り、CONFIG_DB を埋める。
3. 各 `*mgrd` が CONFIG_DB を購読し APPL_DB に展開する。
4. ZTP は `ztp` daemon が DHCP option 経由で URL を取得し、上記 snapshot を上書きする。

bootstrap で読むべき設定は `DEVICE_METADATA|localhost`、`FEATURE|<docker>`、`PORT|<ifname>` の 3 種で、最初の 3 行に書かれている `hwsku`、`platform`、`type` が以降のすべての判断軸になる。

## 個別機能はどこを読むか

| 機能 | 設定入口の章 |
| --- | --- |
| [BGP](../../reference/glossary.md#term-bgp) / route policy | [BGP 章 - 設定](../02-bgp/setup.md) |
| L2 / [VLAN](../../reference/glossary.md#term-vlan) / [LAG](../../reference/glossary.md#term-lag) | [L2 章 - 設定](../06-l2-vlan-lag/setup.md) |
| [VxLAN](../../reference/glossary.md#term-vxlan) / [EVPN](../../reference/glossary.md#term-evpn) / [VNET](../../reference/glossary.md#term-vnet) | [VxLAN EVPN 章 - 設定](../03-vxlan-evpn/setup.md) |
| [ACL](../../reference/glossary.md#term-acl) / [CoPP](../../reference/glossary.md#term-copp) / mirror | [ACL 章 - 設定](../07-acl-copp-mirror/setup.md) |
| [QoS](../../reference/glossary.md#term-qos) / buffer | [QoS 章 - 設定](../08-qos-buffer/setup.md) |
| telemetry / gNMI | [Telemetry 章 - 設定](../09-telemetry-snmp/setup.md) |

## つまずきパターン

- **`config reload` 後に変更が消える**: `config save` 忘れ。または `config replace` / `apply-patch` を使ったあと save していない。
- **`redis-cli` で書いたら一部だけ効いた**: notify 経由で再描画される table と、ファイル監視 (`hostcfgd` 等) で描画される table が混ざる。CLI / GCU 経由に統一する。
- **GCU の patch が validation で落ちる**: `sonic-yang-models` の version と CONFIG_DB の schema が古い image でずれているとき。`show version` と YANG パッケージ版を確認する。
- **bootstrap で minigraph 反映が崩れる**: `minigraph.xml` の `hwsku` と platform 実体の不一致。`show platform summary` の `HwSKU` を正にして DB を作り直す。

## 観測の最小セット

CONFIG_DB を触ったあとに「効いているか」を最小コストで確認するための観測コマンドを並べる。機能別の詳しい確認は各章を読む。

```bash
# DB の状態を直接見る
redis-cli -n 4 keys '*' | head -20     # CONFIG_DB の table 一覧
redis-cli -n 0 keys '*_TABLE:*' | head # APPL_DB の orchagent 向け
redis-cli -n 6 keys 'STATE_*' | head   # STATE_DB の観測値

# 一段抽象化された CLI
show running-configuration | head -40
show ip interface
show interfaces status | head -10
show feature config

# 経路と最終投影
show ip route 0.0.0.0/0
redis-cli -n 1 keys 'ASIC_STATE:*' | wc -l
```

この 3 段 (CONFIG_DB → APPL_DB → ASIC_DB) を続けて観ると、`*mgrd` のどこで停まったかが明確になる。途中で値が消える場合は対応 daemon の log (`/var/log/syslog`、`docker logs <name>`) を読む。

## YANG / Management Framework 経由の設定

CLI と並行して gNMI / RESTCONF を使う運用では、入口は SONiC native YANG と OpenConfig の 2 系統がある。両者は最終的に同じ CONFIG_DB に着地するが、validation の厳しさと採用 leaf が異なる。

- **SONiC native YANG**: `sonic-bgp-global` などのモジュール群。CONFIG_DB の table 構造に近い。schema 更新は image と同期する。
- **OpenConfig**: `openconfig-network-instance` などの標準モジュール。SONiC 内部で transformer (`gnmi_translator`) が CONFIG_DB に変換する。マルチベンダ運用向け。

gNMI set / get の例は [gNMI / OpenConfig 章](../10-gnmi-openconfig/index.md) を読む。証明書や TLS 設定の起点は [Telemetry 章](../09-telemetry-snmp/setup.md)。

## 章の出口

- 設定変更の選択基準を細かく見たい → [設定変更の選び方](configuration.md)。
- 設定がどう daemon に流れるかを追いたい → [設定データフロー](architecture.md) と [内部実装](internals.md)。
- 運用観点 (rollback / 監視 / failure) → [運用入口](operations.md)。
- 個別機能の設定 → 各章 (`02-bgp/setup.md` ほか)。

<!-- glossary-links-injected: 8ba32e5aa69d -->
