---
title: DPU の IP 割当・gNMI 連携・KVM 検証
description: DPU の IP 割当・gNMI 連携・KVM 検証 — SmartSwitch / DASH の設定は「DPU の管理面をどう立ち上げるか」「コントローラに状態をどう返すか」「実機を持っていない開発者がどう検証するか」の
  3 つに分けて考えると見通しが良くなります。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - show feature
  - show platform
  - show chassis modules status
  config_db:
  - DEVICE_METADATA
  - FEATURE
  - CHASSIS_MODULE
  yang:
  - sonic-device_metadata
---

# DPU の IP 割当・gNMI 連携・KVM 検証

[SmartSwitch](../../reference/glossary.md#term-smartswitch) / [DASH](../../reference/glossary.md#term-dash) の設定は「[DPU](../../reference/glossary.md#term-dpu) の管理面をどう立ち上げるか」「コントローラに状態をどう返すか」「実機を持っていない開発者がどう検証するか」の 3 つに分けて考えると見通しが良くなります。

## このページの読み方: DASH は controller-driven 系

DASH / SmartSwitch は「運用者が CLI を叩いて 1 件ずつ [ENI](../../reference/glossary.md#term-eni) / [VNET](../../reference/glossary.md#term-vnet) / Route を投入する」プロダクトではありません。**人手で `config dash ...` のような CLI を打つことはほぼ無く**、外部の DASH appliance controller（典型的には Microsoft Azure SDN のような大規模 SDN コントローラ）が [gNMI](../../reference/glossary.md#term-gnmi) / gRPC で `DASH_*` テーブルを送り込みます。本ページの CLI 例は「コントローラ無しで開発・検証する際のショートカット」「障害時の確認手段」として読んでください。

代表的な設定経路は次の通りです。

| 経路 | 用途 | 投入先 |
|---|---|---|
| DASH appliance controller (gNMI / gRPC) | 本番。ENI / VNET / Route / [ACL](../../reference/glossary.md#term-acl) を大量 push | `APPL_DB` の `DASH_*_TABLE`（[NPU](../../reference/glossary.md#term-npu) 側 gNMI server 経由） |
| `swssconfig` で JSON 流し込み | lab / CI、controller 不在時のスモークテスト | `APPL_DB` の `DASH_*_TABLE`（直接） |
| `redis-cli` / `sonic-db-cli` 手打ち | 障害切り分け、1 件だけ試す | 同上 |
| `config dash ...` CLI | **基本存在しない**。show 系は一部あり | — |

典型的な投入フローは次の形になります。

```text
DASH Controller
  └─ gNMI Set (version_id 付き)
       └─ NPU 側 gNMI server
            └─ APPL_DB:DASH_*_TABLE
                 └─ dashorch (NPU)
                      └─ DPU redisdpuN / dashha (DPU 側)
                           └─ SAI (DASH SAI)
                                └─ DPU データプレーン (実 ASIC または BMv2)
                                     ↑ 反映完了
                                APPL_STATE_DB に version_id を書く
                                     └─ gNMI server が subscribe で controller へ返す
```

確認も「controller 側で gNMI subscribe してフィードバックを受ける」が一次手段で、`show` CLI は副次的です。エラーも基本は **gRPC status code / APPL_STATE_DB の version mismatch** という形で controller に通知されます。後半の「設定エラーと対処」節で CLI 側の症状と合わせて整理しています。

## controller-driven 系のエラー対処

CLI を打たない運用では、エラーは大きく分けて次の 3 層で出ます。

| 層 | 代表的な症状 | 一次切り分け |
|---|---|---|
| gRPC / gNMI トランスポート | `UNAVAILABLE`、`UNAUTHENTICATED`、`DEADLINE_EXCEEDED` | NPU 側 gNMI server の起動 (`show feature status gnmi`)、TLS 証明書、ファイアウォール |
| スキーマ / バリデーション | gNMI `SetResponse` で `INVALID_ARGUMENT`、`NOT_FOUND` | path が `/sonic-db:APPL_DB/DASH_*` の規約通りか、[YANG](../../reference/glossary.md#term-yang) 定義との突き合わせ |
| 反映遅延 / 不一致 | `version_id` が `APPL_STATE_DB` に降りない、controller subscribe が古い version で stuck | `dashorch` ログ、`sairedis.rec` の [SAI](../../reference/glossary.md#term-sai) status、DPU 側 `database-dpu.service` 生死 |

```bash
# controller 視点で「どの version まで適用済みか」を見る (NPU 上で代替確認)
sonic-db-cli APPL_STATE_DB HGETALL 'DASH_ENI_TABLE:F4939FEFC47E'

# gNMI server の現状
show feature status gnmi
docker logs gnmi 2>&1 | tail -50

# SAI レベルの戻り値 (反映失敗時に NOT_SUPPORTED / FAILURE が見える)
grep -E 'SAI_STATUS_(NOT_SUPPORTED|FAILURE)' /var/log/swss/sairedis.rec | tail
```

CLI で確認だけしたいときは、後述の `show chassis modules status` / `show platform dpu-status` / `sonic-db-cli` 系を使います。これらは「controller の代わりに状態を書く」用途ではなく、あくまで read-only な health check に留めてください。

## 全体像

SmartSwitch を立ち上げて DASH を回すまでに必要な操作は次の 5 ステップに整理できます。

1. **platform 認識**: `platform.json` / `platform_components.json` で DPU が module として宣言されており、`pmon` が pick up していることを確認。
2. **midplane**: NPU 上で midplane bridge と DHCP server が起動し、DPU の管理 IP が決定論的に払い出される。
3. **DPU Online**: NPU から `redisdpuN` に到達でき、`CHASSIS_STATE_DB` で DPU が Online。
4. **DASH 制御**: コントローラから gNMI ないし `swssconfig` で `DASH_*` テーブルを [APPL_DB](../../reference/glossary.md#term-appl_db) に投入し、`dashorch` 経由で SAI / DPU データプレーンへ。
5. **検証**: 物理機がなければ `dash-sonic-kvm` で同じ流れを KVM + BMv2 で再現。

以降のシナリオはこの順番に沿って書きます。

## DPU 管理 IP の払い出し

NPU と DPU は midplane bridge（通常 `169.254.200.0/24` 系の内部 L2）で繋がります。DPU の管理 IP は、NPU 上で動く DHCP server から払い出されます。手順としては次の流れになります。

1. NPU 起動時に midplane bridge を作成する。
2. NPU 側 DHCP server に DPU 数分のリースエントリを用意する。
3. 各 DPU は boot 時に midplane の DHCP discovery を打ち、IP を取る。
4. DPU は取得した IP で NPU 上の `redisdpuN` へ remote 接続する。

これにより、外部の管理ネットワーク設定なしで NPU が「DPU の親ルータ兼 DHCP サーバ」として完結します。midplane の運用や DPU 数の規模に応じて、bridge のサブネット設計とリース台数を合わせる必要があります。

詳細は [Smart Switch DPU IP アドレス割当](../../system/smart-switch-ip-address-assignment.md) を参照してください。

## コントローラへの gNMI フィードバック

DASH のコントローラは設定をプッシュした後、「DPU が実際に受理して反映できたか」を知る必要があります。SmartSwitch では DPU の `APPL_STATE_DB` に書かれた version_id を NPU 側 gNMI server が読み、コントローラへフィードバックします。

ポイントは次の通りです。

- コントローラは `version_id` を付けて設定を送る。
- DPU 側 [orchagent](../../reference/glossary.md#term-orchagent) は SAI 反映後、その `version_id` を `APPL_STATE_DB` に書く。
- NPU 側 gNMI server がそれを集約し、subscribe しているコントローラへ返す。
- これによりコントローラは「どの version までが DPU で active か」を確認できる。

この経路は [HLD](../../reference/glossary.md#term-hld) 範囲では `hld-only` の項目もあるため、最新の実装差分は [SmartSwitch gNMI フィードバック設計](../../management/smart-switch-gnmi-feedback-design-omit-in-toc.md) で確認してください。

## DASH SONiC KVM での検証

物理 SmartSwitch がなくても、DASH の動作確認は **BMv2 ベースの仮想 DPU** で行えます。`dash-sonic-kvm` は KVM 上で [SONiC](../../reference/glossary.md#term-sonic) を動かし、DPU を BMv2（P4 ソフトウェアスイッチ）として接続することで、`DashOrch` 系 → SAI → BMv2 のループを再現します。

検証で確認できる主な観点は次の通りです。

- `DASH_VNET` / `DASH_ENI` / `DASH_ROUTE` を入れた時の APPL_DB / SAI / BMv2 までの伝搬
- ACL ルール（タグ含む）の挙動
- フロー単位の packet path（VxLAN encap / decap、Service Tunnel など）

実環境投入前のスモークテストと CI に使えますが、性能や HA の細部は実機特性に依存します。詳細は [DASH SONiC KVM](../../overlay/dash-sonic-kvm.md) を参照してください。

## 設定シナリオ 1: 単一 SmartSwitch + 2 DPU の初期立ち上げ

最も小さい構成として、NPU 1 台に DPU 2 台が PCIe / midplane で接続されたシャーシを考えます。出荷直後の状態から「DPU の管理 IP が払い出されて NPU から ping できる」までを順に追います。

1. `config_db.json` の `DEVICE_METADATA|localhost` に `subtype: SmartSwitch`、`switch_type: dpu` のような属性が入っているか確認します。これは `sonic_yang_models` の DPU 関連 leaf がアンロックされる条件です。
2. midplane bridge を確認します。`/etc/sonic/midplane_network.json` ないし platform 提供の hook で `169.254.200.0/24` 等の internal subnet が登録され、`brctl show midplane` で DPU 側 vNIC が見えます。
3. NPU 側で `dhcp_server` / `dhcrelay` ではなく **midplane 専用の dnsmasq** か等価な DHCP が起動し、DPU MAC とリースを払い出します。
4. DPU 側の boot 後、`ip -4 addr show eth0-midplane` 相当で `169.254.200.10` のようなアドレスを取得していることを確認します。

```bash
# NPU 上から DPU の生存確認
show chassis modules status
sudo redis-cli -h redisdpu0 -n 0 PING
```

期待される出力イメージ:

```text
Name      Description     Physical-Slot   Oper-Status    Admin-Status
--------  --------------  --------------  -------------  --------------
DPU0      Pensando DPU    N/A             Online         up
DPU1      Pensando DPU    N/A             Online         up
```

`redis-cli` 側は `PONG` が返れば NPU から DPU の [Redis](../../reference/glossary.md#term-redis) インスタンスへ到達できています。Online にならない場合は、まず midplane bridge の link、次に DHCP リース、最後に DPU 側の `database-dpu.service` の起動順で切り分けます。

## 設定シナリオ 2: DASH ENI と VNET の最小投入

DPU が Online になったら、コントローラなしでも [CONFIG_DB](../../reference/glossary.md#term-config_db) に直接書いて DASH のスモークテストができます。`APPL_DB` の `DASH_*` テーブルへ `swssconfig` で投入する形式を取ります。

```json
{
    "DASH_VNET_TABLE:Vnet1": {
        "vni": "45654",
        "guid": "559c6ce8-26ab-4193-b946-ccc6e8f930b2"
    },
    "DASH_ENI_TABLE:F4939FEFC47E": {
        "mac_address": "F4:93:9F:EF:C4:7E",
        "qos": "qos-1",
        "underlay_ip": "25.1.1.1",
        "admin_state": "enabled",
        "vnet": "Vnet1"
    }
}
```

このファイルを `swssconfig dash_eni.json` で適用すると、`dashorch` が SAI の `create_eni()` / `create_vnet()` を呼び、DPU 側 BMv2 ないし実 [ASIC](../../reference/glossary.md#term-asic) にプログラムされます。確認は次の通りです。

```bash
sonic-db-cli APPL_DB KEYS 'DASH_ENI_TABLE:*'
sonic-db-cli APPL_STATE_DB HGETALL 'DASH_ENI_TABLE:F4939FEFC47E'
```

`APPL_STATE_DB` 側に `version_id` と `status: applied` 相当のエントリが現れれば、コントローラへのフィードバックも閉じています。

## 設定シナリオ 3: gNMI を介したコントローラ連携

外部 SDN コントローラから設定を投げる場合は、NPU 側 gNMI server を有効化し、`gnmi-set` で `version_id` 付きの transaction を送ります。

```bash
# NPU 側で gNMI server を有効化（既定で 8080）
sudo config feature state gnmi enabled
show feature status gnmi

# クライアントから set
gnmic -a <npu>:8080 --insecure set \
  --update-path /sonic-db:APPL_DB/DASH_ROUTE_TABLE/F4939FEFC47E:10.1.0.0/24 \
  --update-value '{"action_type":"vnet","vnet":"Vnet1","version":"v3"}'

# コントローラへのフィードバック確認
gnmic -a <npu>:8080 --insecure subscribe \
  --path /sonic-db:APPL_STATE_DB/DASH_ROUTE_TABLE/F4939FEFC47E:10.1.0.0/24/version
```

`subscribe` が `version: v3` を返した時点で「DPU が SAI まで適用完了」と解釈できます。タイムアウトする場合は、DPU 側 `dashorch` のログ (`/var/log/swss/sairedis.rec`) で SAI 呼び出しが成功しているかを確認します。

## 設定エラーと対処

| 症状 | ありがちな原因 | 対処 |
|---|---|---|
| `show chassis modules status` で DPU が Offline | midplane bridge 未作成、または DPU 側 NIC が DOWN | `brctl show midplane`、`ip link` で物理リンクを確認。`platform.json` の `chassis.modules` 定義漏れも疑う |
| DPU の IP が `169.254.x.x` のリンクローカルのまま | DHCP server が NPU 上で未起動 | `systemctl status dhcp-relay@<midplane>` ないし platform 固有の DHCP service を確認 |
| `redis-cli -h redisdpu0 PING` がタイムアウト | DPU 側 `database-dpu.service` が未起動か、`database_config.json` の bind アドレス不一致 | DPU 側 `docker logs database` と `/var/run/redis/sonic-db/database_config.json` を確認 |
| `APPL_STATE_DB` に `version_id` が降りてこない | `dashorch` が SAI 呼び出しで失敗 | `sairedis.rec` で `SAI_STATUS_NOT_SUPPORTED` を grep、capability ファイルと behavior の組合せを見直す |
| `gnmic subscribe` が空のまま | NPU 側 gNMI server が APPL_STATE_DB を購読していない | `show feature status gnmi`、`docker logs gnmi` で `--with-state-db` 系オプションを確認 |

## lab と production の違い

| 観点 | lab (KVM / 単機) | production (SmartSwitch 実機) |
|---|---|---|
| DPU | BMv2 仮想 DPU | SoC 実機 + SAI 実装 |
| midplane | 仮想 bridge | 物理 PCIe / midplane [SerDes](../../reference/glossary.md#term-serdes) |
| HA | 単 DPU で擬似的に確認 | DPU ペア / 跨ぎ ENI |
| 性能 | データプレーンは BMv2 速度 | line-rate（DPU SAI 依存） |
| 上限 | ENI 数・rule 数は小さく | 規模パラメータは DPU 仕様 |

lab 検証はスキーマや状態遷移の確認に使い、性能・HA フェイルオーバー時間・障害シナリオは実機で確認するのが基本方針になります。

## 設定シナリオ 4: dash-sonic-kvm で BMv2 をスモークテスト

物理が無い開発者向け。`dash-sonic-kvm` リポジトリの `Makefile` 経由で KVM 上に SONiC + BMv2 DPU を立てます。

```bash
git clone https://github.com/sonic-net/dash-sonic-kvm
cd dash-sonic-kvm
make all-debian-bullseye
make start                       # KVM 上の sonic-vs を起動
make dash-bmv2-attach            # BMv2 DPU を midplane 相当に接続
```

立ち上がったら、ホスト側から SSH で sonic-vs に入り、シナリオ 2 と同じ JSON を `swssconfig` で投入します。BMv2 側は `simple_switch_CLI` で flow table を確認できます。

```bash
docker exec -it bmv2 simple_switch_CLI --thrift-port 9090
RuntimeCmd: table_dump dash_eni
```

`dash_eni` テーブルに ENI が一覧されれば、APPL_DB → SAI → BMv2 のループが閉じています。

## 設定シナリオ 5: HA ペアを意識した DPU 1-1 構成

DPU 1 台が単独で稼働する形では HA の検証ができないため、本番投入前に最低限のペア（同一シャーシ内の DPU0 / DPU1、ないし対向シャーシの DPU）を組んで、ENI 跨ぎのフェイルオーバーを試します。CONFIG_DB の `DASH_HA_*` 系を直接入れる場合の輪郭:

```json
{
    "DASH_HA_SET_TABLE:ha-set-1": {
        "version": "1",
        "vip_v4": "203.0.113.100",
        "owner": "switch",
        "scope": "dpu",
        "local_npu_ip": "25.1.1.1",
        "peer_ip": "25.1.1.2"
    },
    "DASH_HA_SCOPE_TABLE:ha-scope-1": {
        "ha_set_id": "ha-set-1",
        "ha_role": "active"
    }
}
```

これを片側 DPU で `active`、対向 DPU で `standby` として入れ、`vip_v4` への traffic が active 側に集中し、active 側を `admin_state=disabled` にした際に standby が引き取ることを確認します。動作の細部は [advanced](advanced.md) の HA 章を参照。

## 関連リファレンス

- CONFIG_DB: `CHASSIS_MODULE`、`DPU`、`DEVICE_METADATA`（SmartSwitch サブタイプ）
- APPL_DB: `DASH_VNET_TABLE`、`DASH_ENI_TABLE`、`DASH_ROUTE_TABLE`、`DASH_VNET_MAPPING_TABLE`
- APPL_STATE_DB: 各 DASH_*_TABLE に対応する状態反映
- CLI: `show chassis modules status`、`config chassis modules`、`show platform dpu-status`
- gNMI path: `/sonic-db:APPL_DB/DASH_*` および `/sonic-db:APPL_STATE_DB/DASH_*`

## 関連ページ

- [Smart Switch DPU IP アドレス割当](../../system/smart-switch-ip-address-assignment.md)
- [SmartSwitch gNMI フィードバック設計](../../management/smart-switch-gnmi-feedback-design-omit-in-toc.md)
- [DASH SONiC KVM](../../overlay/dash-sonic-kvm.md)
- [Smart Switch のデータベース構成](../../architecture/smart-switch-database-design.md)

<!-- glossary-links-injected: ec18b66e3507 -->
