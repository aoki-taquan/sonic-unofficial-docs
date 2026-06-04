---
title: 発展トピック
description: 発展トピック — SONiC を全体像として見たときに、初学者の足場が固まったあとで触れたい横断テーマを並べる。GCU による差分適用、warm/fast/cold
  reboot の選び分け、multi-ASIC、SmartSwitch、Application Extension といった現代的な拡張軸が中心。
area: topics
verification: meta
last_verified: 2026-05-12
sources: []
related:
  cli:
  - config apply-patch
  - config replace
  - warm-reboot
  - fast-reboot
  - show version
  config_db: []
  yang: []
  _no_related_config_db: true
  _no_related_yang: true
---

# 発展トピック

[SONiC](../../reference/glossary.md#term-sonic) を全体像として見たときに、初学者の足場が固まったあとで触れたい横断テーマを並べる。個別機能の発展トピックは各章 (`02-bgp/advanced.md` 以降) を読む。本章では「全体像を一段深く読むときに引っ掛かりやすい点」だけを扱う。

## GCU と JSON Patch の現実

[GCU](../../reference/glossary.md#term-gcu) (Generic Config Updater) は `config apply-patch` / `config replace` の中身で、[CONFIG_DB](../../reference/glossary.md#term-config_db) を JSON 木として扱い RFC 6902 の JSON Patch を当てる仕組みである。

- patch は `sonic-yang-models` の [YANG](../../reference/glossary.md#term-yang) で validate される。validation を通らない patch はそもそも適用されない。
- 適用順序は YANG の依存 (`leafref` 等) を尊重して order を組み替える。順序依存で失敗するときは patch の中で参照が前方になっていないかを確認する。
- rollback 用の inverse patch が自動生成され、失敗時はそれで巻き戻す。inverse patch は CONFIG_DB の現在値に依存するため、別ホストで使い回せない。

実運用では、GCU を使うのは「複数機能をまたぐ大きな変更」と「自動化からの partial update」が中心。1〜2 行の変更は `config` CLI で十分。

## reboot の選び分け

SONiC の reboot は 4 種類あり、データプレーン断と再収束時間が違う。読み手はまず違いを表で頭に入れる。

| 種別 | データプレーン断 | 復帰条件 | 主な用途 |
| --- | --- | --- | --- |
| cold reboot | あり (秒〜分) | 全 daemon 再起動 | 通常の reboot、image 入替後の最終確認 |
| fast reboot | 短い (~30s) | kernel と一部 daemon が引き継ぎ、forwarding は維持 | image 入替の影響緩和 |
| warm reboot | ほぼゼロ | [SAI](../../reference/glossary.md#term-sai)/[syncd](../../reference/glossary.md#term-syncd) の state 引き継ぎ、[ASIC](../../reference/glossary.md#term-asic) 内 forwarding 継続 | 主要 daemon の hot upgrade |
| warm-restart (per-daemon) | ほぼゼロ | bgpd など個別 daemon の hot restart | [BGP](../../reference/glossary.md#term-bgp) graceful restart 連動 |

warm reboot は SAI vendor 実装と platform driver の対応に強く依存する。同じ platform でも image 版で対応状況が変わるので、`show reboot-cause history` と `show platform warm-reboot capability` を使って事前確認する。詳細は [Reboot 章](../11-reboot/index.md)。

## Multi-ASIC と SmartSwitch

SONiC を「箱の中に 1 つの ASIC」前提で読むと、最近の以下二系は混乱の元になる。

- **[Multi-ASIC](../../reference/glossary.md#term-multi-asic) / VoQ**: 1 シャーシ内に複数 ASIC があり、`/etc/sonic/sonic_environment` の `NAMESPACE_*` で namespace を切る構成。`show` 系コマンドは `-n asic0` のような namespace 修飾を要求する。詳細は [Multi-ASIC 章](../12-multi-asic-voq/index.md)。
- **[SmartSwitch](../../reference/glossary.md#term-smartswitch) / [DPU](../../reference/glossary.md#term-dpu)**: [NPU](../../reference/glossary.md#term-npu) + DPU の混載で、DPU 側は独立 SONiC instance になることがある。CONFIG_DB は NPU 側、[DASH](../../reference/glossary.md#term-dash) 用の DPU_APPL_DB / DPU_STATE_DB は DPU 側、と DB が物理的に分かれる。詳細は [DASH/SmartSwitch 章](../13-dash-smartswitch/index.md)。

両者とも「DB 1 つを redis-cli で見れば全体が分かる」前提を崩すため、`show ip route` のような単純コマンドの結果が namespace 別で違うことに最初に気付けるかが分水嶺になる。

## Application Extension Infrastructure (AEI)

SONiC core を再ビルドせずに後付けで機能 docker を入れる仕組みが AEI と SPM (SONiC Package Manager) で、`sonic-package-manager install <repo>:<tag>` で extension を入れる。

- extension は manifest (`manifest.json`) と docker image で構成され、CONFIG_DB schema 拡張、CLI 拡張、`*mgrd` 追加を宣言する。
- core 側との依存は manifest の `depends` で表現され、SONiC 版や他 extension に対する版指定ができる。
- 動かなくなったときは `show feature config` で extension の `state` を確認し、`FEATURE` テーブルを正に CONFIG_DB を直す。

詳細は [Build / Packaging 章](../19-build-packaging/index.md) と [SONiC Application Extension Infrastructure](../../architecture/sonic-application-extension-infrastructure.md)。

## Streaming Telemetry の前提知識

[SNMP](../../reference/glossary.md#term-snmp) polling から streaming telemetry ([gNMI](../../reference/glossary.md#term-gnmi) / OpenConfig) へ移る運用では、SONiC は次の点で他 NOS と異なる。

- telemetry 用 daemon `telemetry` (旧) と `gnmi` (新) があり、image 版で切替中。`show feature config` で確認する。
- subscribe path は SONiC 内部の [Redis](../../reference/glossary.md#term-redis) path を XPath で叩く `SONIC-DB` モードと、OpenConfig YANG をマップする `OC` モードがあり、collector 側でどちらを使うか決める。
- secure 化は `config telemetry secure-mode enable` で TLS を有効にし、`/etc/sonic/telemetry/` の証明書ファイルを正にする。

詳細は [Telemetry / gNMI 章](../09-telemetry-snmp/index.md) と [gNMI / OpenConfig 章](../10-gnmi-openconfig/index.md)。

## 観測の標準動線

「変更後に何を確認すれば良いか」を一巡しておくと運用での迷いが減る。

1. `show running-configuration <area>` または `sonic-cfggen -d -y /dev/null --print-data | jq '.<TABLE>'` で CONFIG_DB の現状を読む。
2. `redis-cli -n 0 keys '<TABLE>:*'` で [APPL_DB](../../reference/glossary.md#term-appl_db) を読み、`*mgrd` が反応しているか確認する。
3. `redis-cli -n 1 keys 'ASIC_STATE:*'` で [ASIC_DB](../../reference/glossary.md#term-asic_db) を読み、SAI に投影されているか確認する。
4. `show logging` と `show platform summary` で異常 / version を確認する。
5. 必要なら `gnmi_cli` または `gnmic` で OC path を読み、telemetry 経路でも観測できるかを確認する。

この 5 段は機能を問わず使え、新しい機能をデバッグするときの最短経路になる。

## 関連 RFC / 仕様書

- [RFC 6902](https://datatracker.ietf.org/doc/html/rfc6902) — JSON Patch (GCU の理論的基盤)
- [RFC 7950](https://datatracker.ietf.org/doc/html/rfc7950) — YANG 1.1
- [RFC 8040](https://datatracker.ietf.org/doc/html/rfc8040) — RESTCONF Protocol
- [gNMI specification](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md) — telemetry / streaming
- [SAI specification](https://github.com/opencomputeproject/SAI) — Switch Abstraction Interface

## 複数 image slot と rollback 戦略

SONiC は `sonic-installer` が管理する 2 image slot を持ち、`current` と `next` を切り替えながら運用する。発展運用として押さえる点は次の通り。

- **bisect 用に旧 image を残す**: `sonic-installer remove` を急がず、安定確認まで旧 image を残しておくと数分での fallback ができる。
- **GRUB の default 上書き**: `sonic-installer set-default <image>` で固定すると、reboot 時に意図しない slot に戻る事故を防げる。
- **warm reboot との組合せ**: image 入替後の最初の reboot を warm にできれば forwarding 断を抑えられる。`show platform warm-reboot capability` で対応可否を確認する。

image 切替を CI / 自動化で扱うときは、SSH 切れに耐える wrapper (`nohup` + log redirect) で `sonic-installer install` を起動し、reboot 後の `show version` で `Build commit` を確認するまでを 1 ループにする。

## Discrepancy が見つかった時の動線

`docs/_meta/discrepancies.md` には [HLD](../../reference/glossary.md#term-hld) と実コードが乖離している箇所が一覧化されている。発展トピックとしての扱いは次の通り。

- `monitor: not_implemented` のページは HLD だけが先行している。Issue / PR を upstream に投げるか、本リポで discrepancy として残す判断をする。
- `monitor: evolved_beyond_hld` のページは実コードが先行している。HLD 改稿 PR を upstream に出すか、本リポの該当章で「実コード優先」と明記する。
- 自動化で監視したい場合は、`docs/_meta/discrepancies.md` を CI で paste し PR 本文に差分要約を出す scrutiny step を回す。

discrepancy を読み手に隠さず、しかし sea of YAML にしないバランスが索引層の責務である。

## 章の出口

- 設定の中身を読み直す → [設定データフロー](architecture.md) と [設定変更の選び方](configuration.md)。
- 個別機能の発展 → 各章の `advanced.md`。
- 障害時の動線 → [運用入口](operations.md) と [Reboot 章](../11-reboot/index.md)。

<!-- glossary-links-injected: 5c9b3765d470 -->
