---
title: 設定
description: 設定 — 仮想 lab / 開発環境の bring-up は、SONiC NOS そのものの設定ではなく「環境を組む → image を取る
  → topology を配線する → CONFIG_DB を流し込む」の前段に集中します。
area: topics
verification: meta
last_verified: 2026-05-11
sources: []
related:
  cli:
  - show interfaces
  - show ip
  - show platform
  - show version
  - show bgp
  - config bgp
  - show mclag
  config_db:
  - VRF
  - CONSOLE_PORT
  - ACL_RULE
  - ACL_TABLE
  - BGP_NEIGHBOR
  - BGP_GLOBALS
  - VXLAN_TUNNEL
  yang:
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-vxlan
  - sonic-mclag
  - sonic-vrf
  - sonic-bgp-bbr
  - sonic-bgp-peerrange
---

# 設定

仮想 lab / 開発環境の bring-up は、[SONiC](../../reference/glossary.md#term-sonic) NOS そのものの設定ではなく「環境を組む → image を取る → topology を配線する → [CONFIG_DB](../../reference/glossary.md#term-config_db) を流し込む」の前段に集中します。本ページでは代表的な 3 シナリオ (単一 SONiC-VS、containerlab マルチノード、[DASH](../../reference/glossary.md#term-dash)/[DPU](../../reference/glossary.md#term-dpu) 評価) で、ファイル例 + コマンド列 + 確認手順を示し、よくある詰まりどころと対処をまとめます。

実機運用時の CLI / CONFIG_DB / [YANG](../../reference/glossary.md#term-yang) の使い方は本章の他のページや機能章本文 ([BGP の運用](../02-bgp/operations.md) など) と同一なので、bring-up 後はそちらに合流してください。

## どこから始めるか

| 目的 | 最初に開くページ | 想定リソース |
| --- | --- | --- |
| 1 台の SONiC-VS を libvirt で立ち上げる | [SONiC-VS のビルドと libvirt 起動手順](../../architecture/steps-to-bring-up-sonic-vs.md) | 4 vCPU / 4 GB RAM / 20 GB disk |
| GNS3 で複数台をつなぐ | [GNS3 VM 上での SONiC 動作](../../architecture/sonic-on-gns3-vm.md) | 8 vCPU / 16 GB RAM / KVM 有効 |
| Kubernetes / KNE で並べる | [Alpine 仮想 SONiC](../../architecture/alpine-high-level-design.md) | k8s クラスタ + CNI |
| DPU / DASH を評価する | [DASH SONiC KVM](../../overlay/dash-sonic-kvm.md) | 8 vCPU / 16 GB RAM / SR-IOV 可能なら可 |

各ページに前提パッケージ、image 生成、libvirt 設定、ネットワーク bridge の作り方が書かれています。重複した記載をここで再掲はしません。

## シナリオ 1: SONiC-VS 単体を libvirt で起動

開発検証で 1 台の SONiC を最速で立ち上げるパターンです。

### 事前準備

```bash
# 必要パッケージ
sudo apt-get update
sudo apt-get install -y libvirt-daemon-system libvirt-clients qemu-kvm \
  virtinst bridge-utils cloud-image-utils

# KVM が使えるか
kvm-ok || egrep -c '(vmx|svm)' /proc/cpuinfo

# libvirt ユーザに追加
sudo usermod -aG libvirt,kvm $USER
newgrp libvirt
```

### image 取得

```bash
# 公開 build artifact (vs platform)
wget "https://sonic-build.azurewebsites.net/api/sonic/artifacts?branchName=master&platform=vs&target=target/sonic-vs.img.gz" \
  -O sonic-vs.img.gz
gunzip sonic-vs.img.gz

# 自前ビルド (時間がかかる)
git clone --recurse-submodules https://github.com/sonic-net/sonic-buildimage.git
cd sonic-buildimage
make init
make configure PLATFORM=vs
make target/sonic-vs.img.gz
```

### libvirt 起動

```bash
# domain XML を流し込む (テンプレートは buildimage の platform/vs/sonic-vs 参照)
virt-install --name sonic-vs --memory 4096 --vcpus 4 \
  --disk path=$(pwd)/sonic-vs.img,format=qcow2 \
  --os-variant debian11 --network network=default --import --noautoconsole

# console
virsh console sonic-vs
# 既定 credential: admin / YourPaSsWoRd
```

### 起動後の最低限の確認

```bash
# version
show version
show platform summary    # platform: x86_64-kvm_x86_64-r0

# docker
docker ps
sudo systemctl status swss bgp

# CONFIG_DB が読み込まれているか
sudo sonic-cfggen -d -y 'DEVICE_METADATA["localhost"]'

# interfaces (VS では仮想 port のみ)
show interfaces status
```

## シナリオ 2: containerlab で複数台 SONiC を配線

[BGP](../../reference/glossary.md#term-bgp) / [EVPN](../../reference/glossary.md#term-evpn)-[VXLAN](../../reference/glossary.md#term-vxlan) / [MCLAG](../../reference/glossary.md#term-mclag) など複数台が必要な lab 構成です。containerlab 例:

### topology.yml

```yaml
name: sonic-evpn-fabric

topology:
  nodes:
    leaf1:
      kind: sonic-vs
      image: docker-sonic-vs:latest
    leaf2:
      kind: sonic-vs
      image: docker-sonic-vs:latest
    spine1:
      kind: sonic-vs
      image: docker-sonic-vs:latest
    host1:
      kind: linux
      image: nicolaka/netshoot
    host2:
      kind: linux
      image: nicolaka/netshoot

  links:
    - endpoints: ["leaf1:eth1",  "spine1:eth1"]
    - endpoints: ["leaf2:eth1",  "spine1:eth2"]
    - endpoints: ["leaf1:eth9",  "host1:eth1"]
    - endpoints: ["leaf2:eth9",  "host2:eth1"]
```

```bash
# 起動
sudo containerlab deploy -t topology.yml

# 各ノードに入る
sudo docker exec -it clab-sonic-evpn-fabric-leaf1 bash

# 一括破棄
sudo containerlab destroy -t topology.yml --cleanup
```

### CONFIG_DB を流し込む

```bash
# minigraph 経由 (推奨)
sudo config load_minigraph -y
sudo config save -y

# config_db.json を直接 load
sudo config load /tmp/leaf1_config_db.json -y
sudo config reload -y
```

### 確認

```bash
# BGP セッション (leaf-spine)
show ip bgp summary
show ip bgp neighbors

# EVPN VNI
show evpn vni
show bgp l2vpn evpn summary

# host 側
docker exec -it clab-sonic-evpn-fabric-host1 ping 10.0.0.2
```

## シナリオ 3: DPU / DASH KVM 評価

DASH の overlay 機能を VS で評価するパターンです。詳細は [DASH SONiC KVM](../../overlay/dash-sonic-kvm.md) を参照してください。

```bash
# DASH image を pull
docker pull docker-sonic-vs-dash:latest

# VNET / ENI のテスト用 CONFIG_DB
cat > /tmp/dash_vnet.json <<'EOF'
{
  "DASH_VNET|Vnet1": {
    "vni": "1000",
    "guid": "559c6ce8-26ab-4193-b946-ccc6e8f930b2"
  },
  "DASH_ENI|F4939FEFC47E": {
    "mac_address": "F4:93:9F:EF:C4:7E",
    "qos": "qos-1",
    "underlay_ip": "10.0.0.18",
    "admin_state": "enabled",
    "vnet": "Vnet1"
  }
}
EOF
sonic-cfggen -j /tmp/dash_vnet.json --write-to-db
```

### 確認

```bash
# DASH 状態
redis-cli -n 4 KEYS 'DASH_*'
redis-cli -n 1 KEYS 'ASIC_STATE:SAI_OBJECT_TYPE_ENI*'

# DASH 統計 (実装あれば)
docker exec swss dashctl show eni
```

## 物理 lab の console / 配線

物理機材で lab を組む場合は、SONiC NOS の前に console / シリアル配線が必要になります。SONiC は console switch としても動くため、その設計を再利用できます。

| 設計ページ | 用途 |
| --- | --- |
| [SONiC console switch](../../management/sonic-console-switch.md) | SONiC スイッチを console concentrator にする方法。CONFIG_DB の `CONSOLE_PORT` / `CONSOLE_SWITCH` を含む |
| [Portable console device design](../../management/portable-console-device-design.md) | 持ち運び型 console 装置としての設計 |
| [udev rules design for terminal server](../../architecture/1-udev-rules-design-for-terminal-server.md) | USB シリアルを安定したデバイス名に貼り付ける udev 設計 |

### CONSOLE_PORT 設定例

```json
{
  "CONSOLE_PORT|1": {
    "baud_rate": "9600",
    "flow_control": "0",
    "remote_device": "leaf1"
  },
  "CONSOLE_SWITCH|console_mgmt": {
    "feature_enabled": "yes"
  }
}
```

```bash
sudo config console enable
sudo config console add 1 --baud 9600 --devicename leaf1
show console
```

## SONiC-VS 固有の差分

VS では [SAI](../../reference/glossary.md#term-sai) が仮想実装のため、以下は実機と振る舞いが違います:

| 項目 | 実機 | VS |
| --- | --- | --- |
| [ASIC](../../reference/glossary.md#term-asic) counter | 実 ASIC の値 | SAI shim の擬似値 / 一部 NULL |
| port speed / FEC | optic の capability から決定 | 強制 1G/10G、FEC は no-op |
| thermal / PSU / fan | platform daemon が SDK から取得 | dummy 値 (show platform で固定) |
| [QoS](../../reference/glossary.md#term-qos) / scheduling | ASIC scheduler 実動作 | 機能 enabled として通るが drop pattern は再現しない |
| [LAG](../../reference/glossary.md#term-lag) hash | ASIC ハッシュ実装 | Linux bonding driver |

機能の良し悪しではなく、VS のスコープ外という位置づけです。

## よくある設定エラーと対処

| 症状 | 原因 | 対処 |
| --- | --- | --- |
| `virt-install` で `KVM is unavailable` | nested virtualization が無効 / BIOS で VT-x 無効 | `cat /sys/module/kvm_intel/parameters/nested`、ホストの BIOS で VT-x 有効化 |
| SONiC-VS のシリアル console で何も出ない | grub の console 設定不一致 / domain XML の serial 未定義 | `virsh dumpxml sonic-vs` で `<serial type='pty'>` 確認、`virsh console --force` 試行 |
| containerlab で `eth1` が現れない | host kernel に macvlan / bridge 不足 | `lsmod \| grep -E 'macvlan\|veth\|bridge'`、`modprobe macvlan veth bridge` |
| BGP が UP しない | router-id 未設定 / loopback IP 未投入 / 別端で listen していない | `show ip bgp summary`、router-id は `redis-cli -n 4 HSET "BGP_GLOBALS|default" router_id <IP>` または `sonic-cfggen` / vtysh `bgp router-id` 経由で設定（`config bgp router-id` サブコマンドは存在しない）、`show interfaces ip address Loopback0` |
| `config load_minigraph` が失敗 | [minigraph.xml](../../reference/glossary.md#term-minigraph.xml) と [HwSku](../../reference/glossary.md#term-hwsku) 不整合 | `/usr/share/sonic/device/x86_64-kvm_x86_64-r0/Force10-S6000/` 配下の HwSku を確認、`sonic-cfggen -m -d` で minigraph パース確認 |
| docker ps に container が出ない | image build 失敗 / `INCLUDE_*` flag 不足 | `make -j$(nproc) target/sonic-vs.img.gz 2>&1 \| tee build.log`、`rules/config` の include flag を確認 |
| DASH の [ENI](../../reference/glossary.md#term-eni) を投入したが [ASIC_DB](../../reference/glossary.md#term-asic_db) に object が出ない | DASH SAI 未実装 image、ENI key の MAC 表記揺れ | DASH 対応 image (`docker-sonic-vs-dash`) を使う、MAC を大文字無区切り 12 桁に統一 |
| [Multi-ASIC](../../reference/glossary.md#term-multi-asic) VS で asic0 / asic1 が起動しない | namespace netns 未作成 / `database_global.json` 構文エラー | `ip netns list`、`jq . /etc/sonic/database_global.json`、`systemctl restart database` |
| port が UP しないが ping は通る | `show interfaces status` の表示遅延 | `redis-cli -n 6 HGETALL "PORT_TABLE|EthernetX"` で `oper_status` 直確認 |

## test plan に出てくる configuration

CI / test plan に出てくる configuration ([VRF](../../reference/glossary.md#term-vrf) VS test、[ACL](../../reference/glossary.md#term-acl) ingress/egress test など) は、本章の他ページや機能章本文の CONFIG_DB スキーマに従います。test plan は「どの設定をどう投入し、どう検証するか」の合意であり、初期投入の手順書ではありません。読む順序は **機能章 → test plan** です。

代表的な参照:

- `sonic-mgmt/tests/<feature>/test_*.py` の `setup_config` fixture
- `sonic-mgmt/ansible/roles/test/templates/*.j2`
- `sonic-buildimage/platform/vs/sonic-vs/` の minigraph テンプレート

## 関連ページ

- [SONiC-VS のビルドと libvirt 起動手順](../../architecture/steps-to-bring-up-sonic-vs.md)
- [GNS3 VM 上での SONiC 動作](../../architecture/sonic-on-gns3-vm.md)
- [Alpine 仮想 SONiC](../../architecture/alpine-high-level-design.md)
- [DASH SONiC KVM](../../overlay/dash-sonic-kvm.md)
- [SONiC console switch](../../management/sonic-console-switch.md)
- [Portable console device design](../../management/portable-console-device-design.md)
- [udev rules design for terminal server](../../architecture/1-udev-rules-design-for-terminal-server.md)
- [Lab vs Developer の概要](concept.md)
- [Lab vs Developer の運用](operations.md)

<!-- glossary-links-injected: 5c9b3765d470 -->
