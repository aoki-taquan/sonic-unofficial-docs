---
title: 運用
description: 運用 — ここでは lab を「日常的にどう回すか」を、persona 別と test plan 別に整理します。実機運用の章本文ではなく、lab
  環境の運用に閉じた話だけを書きます。
area: topics
verification: meta
last_verified: 2026-05-11
sources: []
related:
  cli:
  - show techsupport
  - show version
  - show interfaces
  - config interface
  - show ip
  - show vlan
  - config vlan
  config_db: []
  yang: []
  _no_related_config_db: true
  _no_related_yang: true
---

# 運用

ここでは lab を「日常的にどう回すか」を、persona 別と test plan 別に整理します。実機運用の章本文ではなく、lab 環境の運用に閉じた話だけを書きます。

## persona ごとの典型ループ

### 評価者

- 仮想 lab を 1 つ立て、[評価者向けガイド](../../guides/evaluator.md) を起点に章をめくる。
- 必要なら GNS3 で 2〜3 台つなぎ、[BGP](../../reference/glossary.md#term-bgp) / [VLAN](../../reference/glossary.md#term-vlan) / L3 / [VRF](../../reference/glossary.md#term-vrf) の章を試す。
- [ASIC](../../reference/glossary.md#term-asic) 依存の挙動（buffer、[PFC](../../reference/glossary.md#term-pfc)、watermark、optics）は [VS](../../reference/glossary.md#term-vs) では再現しないため、評価対象から外すか、対応 HW での検証に切り替える。
- 毎回 image を作り直すのが手間なら、`docker save` で [SONiC](../../reference/glossary.md#term-sonic)-VS image を tar で保存して再 import すると 1 分以内で復旧できる。

```bash
host$ docker save docker-sonic-vs:latest | gzip > sonic-vs.tar.gz
host$ docker load -i sonic-vs.tar.gz
```

### 初学者

- SONiC-VS 1 台で `docker ps`、[Redis](../../reference/glossary.md#term-redis)、[orchagent](../../reference/glossary.md#term-orchagent)、[syncd](../../reference/glossary.md#term-syncd) を見る。
- [初学者向けガイド](../../guides/beginner.md) から章本文の概念ページに進む。
- [CONFIG_DB](../../reference/glossary.md#term-config_db) と CLI を写経しながら、章本文の設定ページを開く。

最初に触ると概観が掴める典型コマンド:

```bash
admin@sonic:~$ docker ps
admin@sonic:~$ show version
admin@sonic:~$ show interfaces status
admin@sonic:~$ redis-cli -n 4 KEYS "PORT|*" | head
admin@sonic:~$ docker exec swss supervisorctl status
admin@sonic:~$ docker exec syncd supervisorctl status
```

`config interface ip add Ethernet0 10.0.0.1/24` のような操作のあと、CONFIG_DB → [APPL_DB](../../reference/glossary.md#term-appl_db) → [ASIC_DB](../../reference/glossary.md#term-asic_db) へどう伝わったかを `redis-cli -n {4,0,1}` で覗くと SONiC の流れ全体が体感できる。

### 運用者

- 実機を触る前に SONiC-VS で CLI / CONFIG_DB の手応えを確認する。
- [運用者向けガイド](../../guides/operator.md) と [Reboot / Upgrade / Lifecycle 章](../11-reboot/index.md) で reboot 系の流れを掴む。
- console / terminal server の構成は本章 [設定](setup.md) の物理 lab セクションを使う。
- 本番投入予定の image は事前に lab で `show techsupport` を 1 回取り、ベースラインの dump を残しておくと、現地で「ふだんと違うログ」が一目で分かる。

```bash
admin@sonic:~$ sudo show techsupport
admin@sonic:~$ ls /var/dump/
sonic_dump_<host>_<ts>.tar.gz
```

### 開発者

- [開発者向けガイド](../../guides/developer.md) で build / test / [HLD](../../reference/glossary.md#term-hld) 起票の流れを押さえる。
- VS で再現可能な範囲は VS で完結させ、CI（test plan ページ）に乗せる。
- ASIC 依存の改修は HW lab を別途確保し、[SAI](../../reference/glossary.md#term-sai) / syncd / platform 章と組で読む。
- VS 内の orchagent / syncd は gdb / strace でアタッチ可能。

```bash
admin@sonic:~$ docker exec -it swss bash
root@sonic:/# gdb -p $(pidof orchagent)
root@sonic:/# strace -fp $(pidof portsyncd) 2>&1 | head
```

## test plan の読み方

test plan ページは「何を検証するか」「どの topology / PTF を使うか」「想定 result」が書かれています。実機 troubleshooting や運用手順書ではないので、章本文と混ぜないようにします。

| 章 | 関連 test plan |
| --- | --- |
| [VRF / ECMP / RIB-FIB](../04-vrf-ecmp/index.md) | [VRF VS test plan](../../routing/vrf-vs-test-plan.md)、[VRF Ansible test plan](../../routing/vrf-feature-ansible-test-plan-omit-in-toc.md) |
| [ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md) | [ACL Ingress/Egress test plan](../../acl-qos/acl-ingress-egress-test-plan.md)、[Everflow test plan](../../acl-qos/everflow-test-plan.md) |
| Telemetry 系 | [Dataplane Telemetry test plan](../../system/dataplane-telemetry-test-plan.md) |
| Platform 系 | [Thermal Control test plan](../../platform/thermal-control-test-plan.md) |

実機が要らない test plan（VS test、Ansible test）はローカルで再現できます。実機 or PTF + ASIC が要る test plan は、CI 側で何が回っているかの参照として読むのが現実的です。

### VS test の最小回し方

VS image のビルドは [sonic-buildimage](../../reference/glossary.md#term-sonic-buildimage) の README に従い、`make init` → `make configure PLATFORM=vs` → KVM 用 `.img.gz` ターゲット (`platform/vs/kvm-image.mk` で `SONIC_KVM_IMAGE = sonic-vs.img.gz` と定義) を作る、という 3 段構成です。`platform/vs` 配下に独立した `make sonic-vs-image` ターゲットは無く、トップレベル Makefile から target/ パスを直接指定します。

```bash
host$ git clone --recurse-submodules https://github.com/sonic-net/sonic-buildimage
host$ cd sonic-buildimage
host$ make init
host$ make configure PLATFORM=vs
host$ make SONIC_BUILD_JOBS=4 target/sonic-vs.img.gz
```

テスト側 (sonic-mgmt) は、testbed を立ち上げてから sonic-mgmt コンテナの中で `tests/run_tests.sh` か `pytest` を直接叩きます。`run_tests.sh` の `-t` は test path ではなく **topology** (`t0` / `t1` / `any`)、テストケース指定は `-c` です。canonical な引数は sonic-mgmt の トップレベル `Makefile` (`make test T=...`) が出力する形と一致しています。

```bash
# sonic-mgmt コンテナ内、/data/sonic-mgmt/tests で実行
container$ ./run_tests.sh -u \
    -n vms-kvm-t0 \
    -d vlab-01 \
    -f vtestbed.yaml \
    -i ../ansible/veos_vtb \
    -c bgp/test_bgp_fact.py \
    -e "--skip_sanity --disable_loganalyzer"
```

`pytest` を直接呼ぶ場合は、testbed / inventory / host-pattern を明示します。

```bash
container$ cd /data/sonic-mgmt/tests
container$ pytest \
    --inventory ../ansible/veos_vtb \
    --host-pattern vlab-01 \
    --module-path ../ansible/library \
    --testbed vms-kvm-t0 \
    --testbed_file ../ansible/vtestbed.yaml \
    bgp/test_bgp_fact.py
```

詳細な topology / inventory / testbed の組み立ては [sonic-mgmt](../../reference/glossary.md#term-sonic-mgmt) リポジトリの `docs/testbed/` 配下 (`README.testbed.VsSetup.md` 等) を参照します。

## lab で起きがちな異常と対処

| 症状 | 一次切り分け | 対処 |
| --- | --- | --- |
| VS 起動後 `system not ready` が消えない | `show system-health detail` で停止 service 特定 | 当該 docker のログ確認、不要 feature は disable |
| `docker ps` に SWSS / syncd が出ない | `journalctl -u swss.service`、image の build 失敗 | image 再 import、`config feature state` 確認 |
| GNS3 でリンクが上がらない | host 側の veth、MTU、bridge | `ip link`、`brctl show`、MTU を 9100 に揃える |
| PTF 経由のパケットが届かない | PTF と DUT の inject ポート対応 | `testbed.yaml` の `vlan_configs` を再確認 |
| VS で reboot が `kdump` で落ちる | VM の cpu/mem が足りない | KVM のリソース増強、`platform` 系設定を minimal に |

## lab のスナップショットとやり直し

仮想 lab は壊して作り直すのが安いので、運用上の壊れ・状態の不整合は再起動より image 再生成のほうが早い場合が多いです。実機運用の手順を「lab で何度も繰り返す」のが lab の役目で、状態を温存する設計は基本的に不要です。

ただし「再現に時間がかかる障害を掴んだ瞬間」は別で、そのときは下記を取ってから何もせず保全します。Redis snapshot は、`sonic-utilities` の `fast-reboot` / `generate_dump` と同じパターンで、**database コンテナの中で `SAVE` (または `BGSAVE`) を発行 → サーバ側 `/var/lib/redis*/dump.rdb` を `docker cp` でホストにコピー** します。`redis-cli --rdb` をホストの sonic admin から打つ形は、SONiC の database コンテナが UNIX socket 構成かつ namespace 分離されている関係で取り違いが起きやすく、CI / techsupport では使われていません。

```bash
admin@sonic:~$ sudo show techsupport
admin@sonic:~$ sudo docker exec syncd syncd_dump.sh

# 各 DB instance の RDB を保存 → ホスト側にコピー
# (single-ASIC VS なら database コンテナ 1 つ、multi-ASIC では database0/1/... を回す)
admin@sonic:~$ sudo docker exec database sonic-db-cli APPL_DB SAVE
admin@sonic:~$ sudo docker cp database:/var/lib/redis/dump.rdb /tmp/dump-appl.rdb
admin@sonic:~$ sudo docker exec database sonic-db-cli CONFIG_DB SAVE
admin@sonic:~$ sudo docker cp database:/var/lib/redis/dump.rdb /tmp/dump-config.rdb

admin@sonic:~$ sudo tar czf /tmp/lab-snapshot.tgz /var/dump /var/log /tmp/dump-*.rdb
```

これは [SWSS / SAI / Redis 章](../20-swss-sai-redis/operations.md) の techsupport / dump 取得と同じ手順です (`sonic-utilities/scripts/fast-reboot` や `scripts/generate_dump` の `Dump by using Redis SAVE.` 経路と同じパターン)。

## 仮想 lab の日常操作

頻出する VS / KVM 操作をまとめておくと、毎回検索する手間が省けます。

```text
host$ virsh list --all
host$ virsh start sonic-vs-01
host$ virsh console sonic-vs-01
host$ virsh shutdown sonic-vs-01
host$ virsh destroy sonic-vs-01   # 強制停止（state は壊れる前提）
host$ virsh snapshot-create-as sonic-vs-01 baseline
host$ virsh snapshot-revert sonic-vs-01 baseline
```

snapshot を 1 つ作っておくと「設定を試す → 戻す」を秒で回せます。docker ベースの VS（`docker run docker-sonic-vs`）なら commit / restore でも同じことが可能。

```bash
host$ docker commit sonic-vs-01 sonic-vs-baseline:latest
host$ docker rm -f sonic-vs-01
host$ docker run -d --name sonic-vs-01 sonic-vs-baseline:latest
```

## CONFIG_DB を素早く差し替える

lab では `config_db.json` をテンプレ化しておき、用途別に差し替えると章ごとの検証が速い。

```bash
admin@sonic:~$ sudo cp /etc/sonic/config_db.json /etc/sonic/config_db.bgp-t0.json
admin@sonic:~$ sudo cp /tmp/config_db.vlan-only.json /etc/sonic/config_db.json
admin@sonic:~$ sudo config reload -y
admin@sonic:~$ show ip bgp summary
admin@sonic:~$ show vlan brief
```

minigraph 経由派なら `minigraph.xml` を差し替えて `config load_minigraph -y` でも同じ。

## CI ローカル再実行のヒント

CI で落ちた test を手元 VS で再現する場合、PTF と DUT の port mapping が一致しないと PTF テストが空振りする。

```bash
host$ cat sonic-mgmt/ansible/inventory
host$ cat sonic-mgmt/ansible/testbed.yaml | grep -A5 vms-kvm-t0
host$ docker exec ptf_vms-kvm-t0 ip link show | grep eth
```

`ptf_*` コンテナ内の eth と DUT 側の Ethernet の対応は testbed yaml で決まる。失敗の 9 割はここの番号ずれ。

## 関連ページ

- [評価者向けガイド](../../guides/evaluator.md)
- [初学者向けガイド](../../guides/beginner.md)
- [運用者向けガイド](../../guides/operator.md)
- [開発者向けガイド](../../guides/developer.md)
- [Reboot / Upgrade / Lifecycle 章](../11-reboot/index.md)
- [SWSS / SAI / Redis 章](../20-swss-sai-redis/operations.md)（共通 dump / SAI 失敗観察）
- [BGP 章](../02-bgp/index.md) / [VLAN・LAG 章](../06-l2-vlan-lag/index.md)（VS で最初に試すと感覚が掴める）
- 本章 [設定](setup.md)（lab の物理 / 仮想セットアップ）

<!-- glossary-links-injected: 75921d013977 -->
