---
title: SUBNET_DECAP テーブル
description: "SUBNET_DECAP テーブル — IPinIP トンネルの サブネット単位の decapsulation ルール を定義する CONFIG_DB テーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-subnet-decap.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - SUBNET_DECAP
    - TUNNEL_DECAP_TABLE
  cli: []
  yang:
    - sonic-subnet-decap
---

# SUBNET_DECAP テーブル

## 概要

[IPinIP](../../reference/glossary.md#term-ipinip) トンネルの **サブネット単位の decapsulation ルール** を定義する [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル[^1]。`TUNNEL_DECAP_TABLE` が個別の outer IP を起点とした decap を扱うのに対し、`SUBNET_DECAP` は **outer source IP がプレフィックス内に該当する場合に decap を行う** という、より広範な一致条件を表す。[SmartSwitch](../../reference/glossary.md#term-smartswitch) / [DASH](../../reference/glossary.md#term-dash) や DualToR 系のシナリオで、ToR 配下のサーバ群から発した [IPinIP](../../reference/glossary.md#term-ipinip) encapsulated トラフィックを decap するために導入された。

[YANG](../../reference/glossary.md#term-yang) リビジョン 2024-12-19 で追加された比較的新しいテーブル。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>SUBNET_DECAP")]
  DM["tunnelmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_TUNNEL_DECAP_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_tunnel_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
SUBNET_DECAP|<name>
```

`<name>` はルール名 (任意文字列)。

## フィールド

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|----------|------|
| `name` (key) | string | yes | - | サブネット decap ルール名 |
| `status` | enum (`enable`/`disable`) | - | `disable` | ルールの有効/無効 |
| `src_ip` | inet:ipv4-prefix | **mandatory** | - | decap 対象とする outer source IPv4 プレフィックス |
| `src_ip_v6` | inet:ipv6-prefix | **mandatory** | - | decap 対象とする outer source IPv6 プレフィックス |

両プレフィックスとも `mandatory true` で、IPv4 と IPv6 の両方を必ず設定する必要がある（DualStack を前提とした設計）。

`status` は `sonic-types:mode-status` (`enable`/`disable`) で、最小権限の原則からデフォルトは `disable`。

## 制約

- `src_ip` / `src_ip_v6` は [YANG](../../reference/glossary.md#term-yang) で `mandatory true`。片方だけの設定は validation で拒否される。
- `status = enable` でない限りデータプレーンには反映されない。

## 購読者

- `swss` の tunnel-decap オーチェストレータが `SUBNET_DECAP` を読み、[SAI](../../reference/glossary.md#term-sai) の tunnel term entry を生成する（subnet ベースの match）。
- DualToR / [DASH](../../reference/glossary.md#term-dash) のサブシステムが補助的に参照する。

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `TUNNEL_DECAP_TABLE` (個別 IP の decap)、`MUX_CABLE` (DualToR)
- 関連 CLI: 現状 dedicated CLI コマンドは無く `sonic-cfggen` / `config load` 経由で投入することが多い
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-subnet-decap`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: `sonic-subnet-decap`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-subnet-decap.yang` (revision 2024-12-19). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-subnet-decap.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `SUBNET_DECAP|<vrf>`。
- `status`: `enable`、`src_ip`/`dst_ip`: T1 ToR ペアの管理サブネット。

### よくある誤設定

- VxLAN decap ルールと subnet decap の優先順位を誤解して期待した decap が起きない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'SUBNET_DECAP|*'
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `status` 値別挙動
| 値 | 挙動 |
|----|------|
| `enable` | `subnetDecapConfig.enable = true`。MP2MP tunnel term が有効化され [SAI](../../reference/glossary.md#term-sai) tunnel term entry が生成される。 |
| `disable` | `subnetDecapConfig.enable = false`（デフォルト）。MP2MP term から `"subnet decap is disabled, ignored."` ログでスキップ。データプレーンに反映されない。 |

### `src_ip` フィールド挙動
| 状態 | 挙動 |
|------|------|
| 有効な IPv4 prefix | `isV4()` チェック通過。subnetDecapConfig に格納され tunnel term の送信元 IP として使用。 |
| IPv6 アドレスを誤指定 | `isV4()` 失敗。`SWSS_LOG_ERROR("Invalid source IP prefix")` → 処理中断。 |
| 形式不正 | `swss::IpPrefix()` が `std::invalid_argument` → `SWSS_LOG_ERROR` → 処理中断。 |

### `src_ip_v6` フィールド挙動
| 状態 | 挙動 |
|------|------|
| 有効な IPv6 prefix | `!isV4()` チェック通過。subnetDecapConfig に格納。 |
| IPv4 アドレスを誤指定 | `isV4()` チェックが成功してしまう → `SWSS_LOG_ERROR("Invalid source IPv6 prefix")` → 処理中断。 |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **src_ip と src_ip_v6 の両方が未設定**: どちらも設定されていない場合 `SWSS_LOG_ERROR("Both src_ip and src_ip_v6 of subnet decap are not set.")` → エントリ破棄。[^2]
- **src_ip に IPv4 以外を指定**: `src_ip` フィールドに IPv6 アドレスを指定すると `isV4()` チェック失敗で `SWSS_LOG_ERROR("Invalid source IP prefix")` → 処理中断。[^2]
- **src_ip_v6 に IPv4 アドレスを指定**: `src_ip_v6` に IPv4 を指定すると `SWSS_LOG_ERROR("Invalid source IPv6 prefix")` → 処理中断。[^2]
- **IP プレフィクス形式不正**: `swss::IpPrefix()` が `std::invalid_argument` を投げた場合も `SWSS_LOG_ERROR("Invalid source IP prefix")` → 処理中断。[^2]
- **未知フィールド**: `src_ip` / `src_ip_v6` / `status` 以外のフィールドは `SWSS_LOG_ERROR("unknown subnet decap table attribute")` → エントリ破棄。[^2]
- **シングルトン制約**: `subnetDecapConfig` はシングルトン構造体として保持されるため、テーブルに複数エントリを書いても最後の SET_COMMAND で上書きされる。[^2]
- **MP2MP 以外のトンネル term は紐付け不可**: subnet decap トンネルに `MP2MP` 以外の term を紐付けようとすると `SWSS_LOG_ERROR("only MP2MP tunnel decap term is allowed for subnet decap tunnel.")` → 拒否。[^2]

[^2]: tunneldecaporch 実装: `sonic-swss/orchagent/tunneldecaporch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/tunneldecaporch.cpp>


<!-- defaults -->
## フィールド暗黙デフォルト (Phase A)

> コード精読由来。YANG `default` 値の外側にある実装上の暗黙挙動をまとめる。

| フィールド | YANG デフォルト | コード由来デフォルト | 乖離・注意点 |
|-----------|--------------|------------------|------------|
| `status` | `disable` | `false` (C++ bool、構造体初期化値) | YANG/実装一致。DEL_COMMAND 受信時も `false` にリセット[^3] |
| `src_ip` | なし (mandatory) | `""` 空文字列 | **YANG-実装 discrepancy**: 片方のみ未設定は silent 受理。両方未設定時のみエラー[^3] |
| `src_ip_v6` | なし (mandatory) | `""` 空文字列 | 同上。`src_ip` 未設定でも `src_ip_v6` だけで受理される[^3] |
| `tunnel` | (YANG に存在しない) | `"IPINIP_SUBNET"` **ハードコード** | CONFIG_DB から設定不可の隠し値。`tunneldecaporch.h` メンバ初期化[^3] |
| `tunnel_v6` | (YANG に存在しない) | `"IPINIP_SUBNET_V6"` **ハードコード** | 同上[^3] |
| `dscp_mode` (APP_DB へ) | (YANG に存在しない) | Broadcom T1: `"pipe"` / Broadcom 非T1: `"uniform"` / 他: `"pipe"` | **プラットフォーム依存**。`ipinip.json.j2` がビルド時に決定[^4] |
| `ecn_mode` (APP_DB へ) | (YANG に存在しない) | `"copy_from_outer"` | `ipinip.json.j2` にハードコード[^4] |
| `ttl_mode` (APP_DB へ) | (YANG に存在しない) | `"pipe"` | `ipinip.json.j2` にハードコード[^4] |

### 書込み順依存乖離

`status = disable` の状態で `src_ip` / `src_ip_v6` を変更すると:

- `subnetDecapConfig.src_ip` / `src_ip_v6` は更新される
- 既存の SAI tunnel term entry の送信元 IP は更新 **されない**（`setIpAttribute()` は `enable == true` 時のみ呼ばれる）

`enable` 後に `src_ip` を再設定すると SAI が更新される。先に `src_ip` を変えてから `enable` しても SAI 更新は走らない。

### YANG mandatory vs 実装の乖離

YANG は `src_ip` と `src_ip_v6` 両方を `mandatory true` とするが、実装の検査は「両方とも空の場合のみエラー」。
片方のみ設定した場合は YANG バリデーションを通過すれば orchagent もエラーにしない。
`sonic-cfggen` 経由の書き込みでは YANG validate が走るが、`sonic-db-cli` で直接書いた場合は実装側 validate のみ。

### シングルトン制約

`subnetDecapConfig` は orchagent 内でシングルトン保持。`SUBNET_DECAP|*` に複数エントリを書いた場合、最後に処理された SET_COMMAND で上書きされる（処理順序依存）。

[^3]: `tunneldecaporch.h` + `tunneldecaporch.cpp:566-699`. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/tunneldecaporch.cpp>
[^4]: `dockers/docker-orchagent/ipinip.json.j2`. <https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-orchagent/ipinip.json.j2>

<!-- /defaults -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

tunnelmgrd が `SUBNET_DECAP` エントリの存在に基づいて IP-in-IP デカプセルトンネルを自動作成する。Config-DB 内フィールド間の自動付与なし。YANG の `must` 制約による論理チェックのみ。

### Phase 7: 条件付き登録 (add_manager 条件)

tunnelmgrd は常時起動し `SUBNET_DECAP` テーブルを無条件購読する。`DEVICE_METADATA.subtype==DualToR` 構成で主に使用される。`ip_prefix_list` が空の場合はエラーログ + スキップ。

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `tunnelmgrd` | `SUBNET_DECAP` エントリ追加 | IP-in-IP デカプセルトンネル作成 | `tunnelmgrd` |
| `tunnelmgrd` | `SUBNET_DECAP` エントリ削除 | 対応トンネル削除 | `tunnelmgrd` |
| `tunnelmgrd` | `ip_prefix_list` が空 | ログエラー + スキップ | `tunnelmgrd` |

> **スキャン証跡**: `SUBNET_DECAP` は主に DualToR 構成で使われる。tunnelmgrd 経由でサブネット decap トンネルを管理。Config-DB 内の自動付与なし（該当なし）。

<!-- /handler-branching -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / SubnetDecapOrch**: `SUBNET_DECAP` テーブルを `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- SubnetDecapOrch がサブネット範囲とデカプセルアクションを解析。APP_DB への書き込みなし。

### 段階 3: APPL → SAI

- orchagent が `sai_tunnel_api` または `sai_acl_api` でサブネット単位のデカプセルルールを設定。

### 段階 4: タイミング + 副作用

- 設定反映は orchagent 処理後数 ms 以内。
- 副作用: サブネット範囲の重複があると ACL リソース競合が発生する可能性。

<!-- /runtime-trace -->

<!-- ordering -->
## 処理順序と順序依存 (Phase B)

### orchagent 初期化順序

`TunnelDecapOrch` は orchdaemon 起動時に他の Orch より先に `CONFIG_DB` の
`SUBNET_DECAP` テーブルを **`pops()` で即時先読み** し、`subnetDecapConfig`
構造体を初期化する（`tunneldecaporch.cpp` コンストラクタ行 39-46）。
その後 Consumer として `addExecutor` に登録され、以降の差分変更を受信する。

この先読み設計は以下の順序依存を解決するためのものである:

1. **SUBNET_DECAP → TUNNEL_DECAP_TERM の前提関係**  
   `doDecapTunnelTermTask()` は `subnetDecapConfig.src_ip` / `src_ip_v6` を参照して
   MP2MP tunnel term の source IP を補完する。SUBNET_DECAP の設定が tunnel term 処理
   より前に確定していなければ、subnet decap term を正しく生成できない。

2. **PortsOrch 依存**  
   `doTask()` は `gPortsOrch->allPortsReady()` が `true` を返すまで早期リターンする。
   したがって SUBNET_DECAP の実際の反映はポート初期化完了後になる。

3. **TUNNEL_DECAP_TABLE の先行投入**  
   `ipinip.json.j2` が `SUBNET_DECAP.status == enable` を確認してから
   `TUNNEL_DECAP_TABLE:IPINIP_SUBNET` / `IPINIP_SUBNET_V6` を APP_DB に投入する。
   このトンネルオブジェクトが存在しない間は tunnel term が `unhandledDecapTerms`
   に積まれ、tunnel 追加後に再処理される。

### VIP ルートとの連動順序

`RouteOrch::addRoute()` および `VNetRouteOrch` は VIP ルート追加時に
`gTunneldecapOrch->getSubnetDecapConfig().enable` を参照して動的に
MP2MP tunnel term (`subnet_type: vip`) を生成する。

```
SUBNET_DECAP (enable) ──┐
                         ├─→ subnetDecapConfig.enable = true
                         │
RouteOrch::addRoute()   ─┤─→ createVipRouteSubnetDecapTerm()
                         │       └─→ APP_DB TUNNEL_DECAP_TERM_TABLE SET
                         │
VNetRouteOrch::set()    ─┘─→ createSubnetDecapTerm()
                                 └─→ APP_DB TUNNEL_DECAP_TERM_TABLE SET
```

SUBNET_DECAP の enable が確定する前にルートが先行投入された場合、
tunnel term は生成されない（ルート削除・再投入が必要）。

### ビルド時プロビジョニング順序

`dockers/docker-orchagent/ipinip.json.j2` の処理順序:

| 順序 | 生成エントリ | 条件 |
|------|-------------|------|
| 1 | `TUNNEL_DECAP_TABLE:IPINIP_SUBNET` | `subnet_decap.enable = true` かつ IPv4 loopback あり |
| 2 | `TUNNEL_DECAP_TERM_TABLE:IPINIP_SUBNET:<vlan-prefix>` (MP2MP, vlan) | 上記と同条件 |
| 3 | `TUNNEL_DECAP_TABLE:IPINIP_TUNNEL` | IPv4 loopback あり |
| 4 | `TUNNEL_DECAP_TABLE:IPINIP_SUBNET_V6` | `subnet_decap.enable = true` かつ IPv6 loopback あり |
| 5 | `TUNNEL_DECAP_TERM_TABLE:IPINIP_SUBNET_V6:<vlan-prefix>` (MP2MP, vlan) | 上記と同条件 |

VIP 系の MP2MP term (`subnet_type: vip`) はビルド時 JSON には含まれず、
routeorch / vnetorch が **ランタイムで動的生成** する。

### warm-reboot 挙動

`TunnelDecapOrch` に warm-reboot 固有のコードパスはない。

- orchagent 再起動時にコンストラクタの `pops()` が CONFIG_DB から再読み込みを行うため、
  `subnetDecapConfig` は自動的に復元される（CONFIG_DB は永続ストアのため設定値は保持）
- APP_DB の `TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE` は
  通常の warm-reboot SAI reconciliation フローで再プログラムされる
- `unhandledDecapTerms` はメモリ上の状態なので再起動でリセットされるが、
  APP_DB からの再投入で自動的に再処理される

### 削除時の順序

`SUBNET_DECAP` エントリの DEL 受信時:

- `subnetDecapConfig.enable = false` に即座に設定
- 既存の tunnel term エントリは **自動的には削除されない**（GC なし）
- 以降の新規 tunnel term 生成が抑止されるのみ
- 既存 term を削除するには `APP_TUNNEL_DECAP_TERM_TABLE` への明示的な DEL 操作が必要

> **コード証跡**: `tunneldecaporch.cpp` L39-48 (先読み初期化), L55-57 (PortsOrch ガード),
> L392-394 (is_subnet_decap_term 判定), L468-509 (src_ip 補完ロジック), L691-694 (DEL処理);
> `routeorch.cpp` L2714-2718, L3220-3235; `vnetorch.cpp` L1563-1594;
> `orchdaemon.cpp` L343-348; `ipinip.json.j2` L37-42, L93-123, L160-190

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照 — Phase C (cross-table refs)

> **調査根拠**: `tunneldecaporch.cpp`, `tunneldecaporch.h`, `routeorch.cpp`, `vnetorch.cpp`, `ipinip.json.j2` 全行精読 (2026-05-18)
> 詳細証跡: `meta/_intermediate/cdb-flow/subnet-decap-ordering.md`

`SUBNET_DECAP` テーブルは直接の YANG leafref をほとんど持たないが、実行時に以下のテーブルを暗黙的に参照・連動する。

| 参照先 | DB | 参照方向 | YANG leafref | 実装上の必須度 | 証拠 |
|---|---|---|---|---|---|
| `TUNNEL_DECAP_TABLE:IPINIP_SUBNET` | APP_DB | 読み取り (tunnel オブジェクト存在確認) | なし | **実質必須** (ブート時 `ipinip.json.j2` が生成) | `tunneldecaporch.cpp:392` |
| `TUNNEL_DECAP_TABLE:IPINIP_SUBNET_V6` | APP_DB | 読み取り (IPv6 tunnel オブジェクト存在確認) | なし | **実質必須** | `tunneldecaporch.cpp:393` |
| `TUNNEL_DECAP_TERM_TABLE:IPINIP_SUBNET:*` | APP_DB | 読み取り (MP2MP vlan/vip term) | なし | 必須 | `tunneldecaporch.cpp:350-540` |
| `LOOPBACK_INTERFACE` | CONFIG_DB | 読み取り (`ipinip.json.j2` がビルド時参照) | なし | 実質必須 | `ipinip.json.j2:28-32` |
| `VLAN_INTERFACE` | CONFIG_DB | 読み取り (`ipinip.json.j2` が vlan term 生成に使用) | なし | VLAN subnet decap 必須 | `ipinip.json.j2:47-51` |
| `DEVICE_METADATA.localhost.switch_type` | CONFIG_DB | 読み取り (`ipinip.json.j2` が DPU で全設定をスキップ) | なし | platform 依存 | `ipinip.json.j2:1` |
| `DEVICE_METADATA.localhost.type` | CONFIG_DB | 読み取り (Broadcom T1 判定で dscp_mode 切り替え) | なし | platform 依存 | `ipinip.json.j2:13-14` |
| `STATE_TUNNEL_DECAP_TABLE` | STATE_DB | 書き込み (tunnel 状態を STATE_DB へ記録) | なし | 情報提供 | `tunneldecaporch.cpp:34, 287` |
| `STATE_TUNNEL_DECAP_TERM_TABLE` | STATE_DB | 書き込み (term 状態を STATE_DB へ記録) | なし | 情報提供 | `tunneldecaporch.cpp:35` |

### TUNNEL_DECAP_TABLE:IPINIP_SUBNET — 実質的な必須前提条件

`TunnelDecapOrch::doTunnelDecapTermTask()` は `tunnel_exists = (tunnelTable.find(tunnel_name) != tunnelTable.end())` でトンネルオブジェクトの存在を確認する。`IPINIP_SUBNET` が APP_DB に存在しない場合、subnet decap term は `unhandledDecapTerms` キューに積まれ SAI に反映されない。このトンネルは `ipinip.json.j2` がブート時に `SUBNET_DECAP[*].status == enable` を確認した場合のみ生成するため、**ブート前に `status=enable` が CONFIG_DB に存在すること**が実質的な必須条件となる（`tunneldecaporch.cpp:392-394, 516-521`）。

### RouteOrch / VNetRouteOrch — VIP ルート連動

`RouteOrch::addRoute()` および `VNetRouteOrch` は VIP ルート追加・削除時に `gTunneldecapOrch->getSubnetDecapConfig()` を参照する。`subnetDecapConfig.enable == true` の場合、VIP prefix に対する MP2MP tunnel term (`subnet_type: vip`) を動的に APP_DB へ書き込む。`SUBNET_DECAP` が disable / 未設定の場合は VIP ルートに対する decap term が生成されない（`routeorch.cpp:2714-2717, 3220-3251`; `vnetorch.cpp:1563-1594`）。

### VLAN_INTERFACE — ビルド時 vlan term 生成の前提

`ipinip.json.j2` は `VLAN_INTERFACE` から IPv4/IPv6 プレフィックスを取得し `TUNNEL_DECAP_TERM_TABLE:IPINIP_SUBNET:<prefix>` (MP2MP, vlan) を APP_DB へ注入する。VLAN_INTERFACE が存在しなければ vlan 型の decap term が生成されず、VLAN サブネット内からの IPinIP トラフィックが decap されない（`ipinip.json.j2:47-51`）。

### ASIC_VENDOR / DSCP_TO_TC_MAP — dscp_mode 自動決定

`ipinip.json.j2` が `ASIC_VENDOR` および `DEVICE_METADATA.localhost.type` を参照して `dscp_mode` (`pipe`/`uniform`) を決定する。また `DSCP_TO_TC_MAP.AZURE` が存在する場合は `decap_dscp_to_tc_map: AZURE` を付加する。CONFIG_DB の `SUBNET_DECAP` フィールドではなくビルド時テンプレートが決定するため、CONFIG_DB 側からの変更は不可（`ipinip.json.j2:8-25`）。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動 (Phase D)

<!-- evidence: meta/_intermediate/cdb-flow/subnet-decap-failure.md -->
<!-- source: sonic-swss/orchagent/tunneldecaporch.cpp -->

### `SUBNET_DECAP` テーブル処理 (`doSubnetDecapTask`) の失敗パス

`doSubnetDecapTask()` は `valid = true` で開始し、バリデーション失敗時に `valid = false` をセットして処理をスキップする。**いずれも `erase` されて再試行なし**。

| # | 失敗条件 | ログ | 再試行 | 影響 |
|---|---------|------|--------|------|
| 1 | `src_ip` が IPv4 プレフィックスとしてパース不能 | `SWSS_LOG_ERROR("Invalid source IP prefix %s.")` L593 | なし | `subnetDecapConfig` 更新されず |
| 2 | `src_ip` に IPv6 アドレスを指定 | `SWSS_LOG_ERROR("Invalid source IP prefix %s.")` L599 | なし | 同上 |
| 3 | `src_ip_v6` が IPv6 プレフィックスとしてパース不能 | `SWSS_LOG_ERROR("Invalid source IPv6 prefix %s.")` L613 | なし | 同上 |
| 4 | `src_ip_v6` に IPv4 アドレスを指定 | `SWSS_LOG_ERROR("Invalid source IPv6 prefix %s.")` L619 | なし | 同上 |
| 5 | 未知フィールド名 | `SWSS_LOG_ERROR("unknown subnet decap table attribute '%s'.")` L630 | なし | 同上 |
| 6 | `src_ip` と `src_ip_v6` の両方が空 | `SWSS_LOG_ERROR("Both src_ip and src_ip_v6 of subnet decap are not set.")` L638 | なし | 同上 |
| 7 | SET / DEL 以外の不明コマンド | `SWSS_LOG_ERROR("Unknown operation type %s.")` L697 | なし | 同上 |

DEL コマンドはバリデーションなしで `subnetDecapConfig.enable = false` をセットするため、失敗パスは存在しない。

### `TUNNEL_DECAP_TERM_TABLE` (subnet decap 関連) の失敗パス

`IPINIP_SUBNET` / `IPINIP_SUBNET_V6` トンネルに対する term 処理でも失敗が発生する。

| # | 失敗条件 | ログ | 再試行 | 影響 |
|---|---------|------|--------|------|
| 8 | subnet decap term が MP2MP 型以外 | `SWSS_LOG_ERROR("%s: only MP2MP tunnel decap term is allowed.")` L448 | なし (erase) | SAI 未作成 |
| 9 | 非 subnet decap term で MP2MP かつ `src_ip` なし | `SWSS_LOG_ERROR("%s: no source IP is provided.")` L458/L463 | なし (erase) | SAI 未作成 |
| 10 | `status=disable` 状態での term 受信 | `SWSS_LOG_ERROR("%s: subnet decap is disabled, ignored.")` L506 | なし (erase) | SAI 未作成 |
| 11 | トンネルオブジェクト未存在 (`IPINIP_SUBNET` 未作成) | `SWSS_LOG_NOTICE("%s: tunnel doesn't exist, added to unhandled list.")` L521 | **自動あり** (`unhandledDecapTerms` キュー) | tunnel 作成後に `processUnhandledDecapTunnelTerms()` が自動再処理 |
| 12 | `src_ip` 未設定で subnet decap term を処理 | `SWSS_LOG_ERROR("%s: source IP is not configured for subnet decap term, ignored.")` L484 | **自動あり** (`unhandledDecapTerms` キュー) | `SUBNET_DECAP` の `src_ip` 設定後に `updateUnhandledDecapTunnelTerms()` が埋め直す |
| 13 | SAI `create_tunnel_term_table_entry()` 失敗 | `SWSS_LOG_ERROR("%s: failed to add tunnel decap term to ASIC_DB.")` L515 | なし (erase) | SAI 未作成 |

### `unhandledDecapTerms` キューの自動回復経路

tunnel が存在しない場合 (#11) や `src_ip` が未設定の場合 (#12) の term は `unhandledDecapTerms[tunnel_name][key]` に積まれる。

- **tunnel 作成後**: `addDecapTunnel()` 成功時に `processUnhandledDecapTunnelTerms(key)` (L309) が呼ばれ、積み残し term を `addDecapTunnelTermEntry()` で再処理する。SAI 作成成功エントリは `unhandledDecapTerms` から削除。失敗エントリは残留。
- **`src_ip` 変更後**: `doSubnetDecapTask()` が新しい `src_ip` を受信した際に `updateUnhandledDecapTunnelTerms()` (L662) が src_ip を埋め直す。ただしこの時点では `addDecapTunnelTermEntry()` は呼ばれず、次の `processUnhandledDecapTunnelTerms()` 呼び出しまで SAI には反映されない。

### `src_ip` 変更時の SAI 不整合リスク

`subnetDecapConfig.src_ip` が変化した際 (L655: `subnetDecapConfig.src_ip != src_ip_str`) かつ `enable == true` の場合、`setIpAttribute()` (L660) が SAI `set_tunnel_term_table_entry_attribute()` で既存 term の `src_ip` を更新する。この SAI 呼び出しが失敗しても `subnetDecapConfig.src_ip` は新しい値で上書きされ (L664)、**SAI と CONFIG_DB の不整合が黙過される**点に注意が必要。

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

<!-- evidence: meta/_intermediate/cdb-flow/subnet-decap-constants.md -->
<!-- source: sonic-swss/orchagent/tunneldecaporch.cpp, sonic-swss/orchagent/tunneldecaporch.h, sonic-buildimage/dockers/docker-orchagent/ipinip.json.j2 -->

`TunnelDecapOrch` は `SUBNET_DECAP` テーブルの処理に関連するトンネル名・MTU・各種モード値をソースコードにハードコードしている。これらは CONFIG_DB の `SUBNET_DECAP` フィールドから変更できない。

### オーバーレイ RIF の MTU（`tunneldecaporch.cpp:14`）

```c
#define OVERLAY_RIF_DEFAULT_MTU 9100
```

decap トンネルのオーバーレイ RIF 作成時に固定値 `9100` バイトが設定される（`tunneldecaporch.cpp:749-750`）。`SUBNET_DECAP` テーブルに MTU フィールドは存在せず、CONFIG_DB からの変更手段がない。

### トンネル名（`tunneldecaporch.h:97-103`）

```cpp
SubnetDecapConfig subnetDecapConfig = {
    false, "", "",
    "IPINIP_SUBNET",      // tunnel
    "IPINIP_SUBNET_V6"    // tunnel_v6
};
```

| 定数 | 値 | 用途 |
|------|----|------|
| `subnetDecapConfig.tunnel` | `"IPINIP_SUBNET"` | IPv4 subnet decap トンネルオブジェクト名 |
| `subnetDecapConfig.tunnel_v6` | `"IPINIP_SUBNET_V6"` | IPv6 subnet decap トンネルオブジェクト名 |

`doDecapTunnelTermTask()` はこれらの名前で APP_DB の `TUNNEL_DECAP_TABLE` を検索する。名前が一致するトンネルが存在しない場合、term は `unhandledDecapTerms` キューに積まれたまま SAI に反映されない。`ipinip.json.j2` も同名でトンネルオブジェクトを生成するため、名前の変更は不可能（`tunneldecaporch.cpp:392-394`）。

### ビルド時テンプレートによるトンネルパラメータ（`ipinip.json.j2:95-210`）

`ipinip.json.j2` が生成する `TUNNEL_DECAP_TABLE:IPINIP_SUBNET` / `IPINIP_SUBNET_V6` エントリのパラメータは以下の通り固定される。`SUBNET_DECAP` テーブルフィールドには対応する設定項目が存在しない。

| パラメータ | 固定値 | 条件・備考 |
|-----------|--------|-----------|
| `ecn_mode` | `"copy_from_outer"` | 全プラットフォーム固定。SAI create-only のため作成後の変更はスキップ (`tunneldecaporch.cpp:179`) |
| `ttl_mode` | `"pipe"` | 全プラットフォーム固定 |
| `dscp_mode` | `"uniform"` | Broadcom T1 ToR (`DEVICE_METADATA.localhost.type == "ToRRouter"` かつ `ASIC_VENDOR == "broadcom"`) |
| `dscp_mode` | `"pipe"` | 上記以外の全プラットフォーム（デフォルト） |

!!! note "`ecn_mode` は SAI create-only"
    `ecn_mode` は SAI トンネルオブジェクト作成時にしか設定できない属性（`SAI_TUNNEL_ATTR_DECAP_ECN_MODE` は create-only）。`ipinip.json.j2` の値 `"copy_from_outer"` がビルド時に設定された後は変更不可。変更を試みると `SWSS_LOG_WARN("Skip setting ecn_mode since the SAI attribute is create only")` が出力されてスキップされる（`tunneldecaporch.cpp:179`）。

### Mux トンネル名定数（`tunneldecaporch.h:21`）

```c
#define MUX_TUNNEL "MuxTunnel0"
```

DualToR の Mux トンネル識別に使われる定数。`TunnelDecapOrch` が同クラスで管理するため、`SUBNET_DECAP` 処理とトンネルオブジェクトの区別に影響する。CONFIG_DB から変更不可。

> **Evidence**: `sonic-swss` `orchagent/tunneldecaporch.cpp:14,749-750`、`orchagent/tunneldecaporch.h:21,97-103`、`sonic-buildimage` `dockers/docker-orchagent/ipinip.json.j2:95-210`

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

<!-- evidence: meta/_intermediate/cdb-flow/subnet-decap-side-effects.md -->
<!-- source: sonic-swss/orchagent/tunneldecaporch.cpp, routeorch.cpp, vnetorch.cpp -->

CONFIG_DB `SUBNET_DECAP` テーブルの変更に伴って `TunnelDecapOrch` が副次的に書き込む DB エントリは以下のとおり。ASIC_DB への `sai_tunnel_api` 呼び出し（主作用）はこの表から除外する。

### STATE_DB への直接書込

`TunnelDecapOrch` はトンネルオブジェクト・トンネル term の追加/削除完了時に STATE_DB に結果を記録する。

| 副次キー | DB | 書込タイミング | evidence |
|---------|-----|---------------|----------|
| `STATE_TUNNEL_DECAP_TABLE:<tunnel_name>` | STATE_DB | `addDecapTunnel()` / `delDecapTunnel()` 完了時 | `tunneldecaporch.cpp:34, 287, 1531, 1536` |
| `STATE_TUNNEL_DECAP_TERM_TABLE:<tunnel_name>:<term_key>` | STATE_DB | `addDecapTunnelTermEntry()` / `delDecapTunnelTermEntry()` 完了時 | `tunneldecaporch.cpp:35, 1560, 1566` |

これらの STATE_DB エントリは `show` コマンド系や他サービスが tunnel/term の有効状態を確認するために読み取る。

### APP_DB への間接書込（RouteOrch / VNetRouteOrch 経由）

`SUBNET_DECAP.enable=true` の状態で VIP ルートが投入された場合、`RouteOrch::addRoute()` および `VNetRouteOrch::set()` が `getSubnetDecapConfig()` を参照して VIP prefix に対応する MP2MP tunnel term を **APP_DB** に書き込む。これは `SUBNET_DECAP` ハンドラの直接書込ではなく、他 orchagent が SUBNET_DECAP の設定値を読んで副次的に生成する。

| 副次キー | DB | 書込トリガー | evidence |
|---------|-----|------------|----------|
| `TUNNEL_DECAP_TERM_TABLE:IPINIP_SUBNET:<vip_prefix>` (MP2MP, vip) | APP_DB | IPv4 VIP ルート追加 | `routeorch.cpp:2714-2717, 3220-3238` |
| `TUNNEL_DECAP_TERM_TABLE:IPINIP_SUBNET_V6:<vip_prefix>` (MP2MP, vip) | APP_DB | IPv6 VIP ルート追加 | `vnetorch.cpp:1563-1594` |

`SUBNET_DECAP.enable=false` または `SUBNET_DECAP` が未設定の場合は上記の VIP 系 tunnel term が **生成されない**（既存 term は DEL されない — GC なし）。

### APPL_DB / COUNTERS_DB への書込

`TunnelDecapOrch` 自身は APPL_DB・COUNTERS_DB への直接書込を行わない。ASIC_DB への反映は SAI (`sai_tunnel_api`) 経由で orchagent フレームワークが管理する。FLEX_COUNTER_DB / APPL_STATE_DB / LOGLEVEL_DB / CONFIG_DB への書込みも検出されなかった。

詳細スキャン手順と grep 結果は `meta/_intermediate/cdb-flow/subnet-decap-side-effects.md` を参照。
<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

### Redis 購読方式

CONFIG_DB の `SUBNET_DECAP` への変更通知は、`TunnelDecapOrch` が **`swss::SubscriberStateTable`** (Redis keyspace 通知ベース) で購読する。コンストラクタ (`tunneldecaporch.cpp:39`) が直接 `new SubscriberStateTable(configDb, CFG_SUBNET_DECAP_TABLE_NAME, TableConsumable::DEFAULT_POP_BATCH_SIZE, 0)` を生成し、`Orch::addExecutor()` に渡す (`tunneldecaporch.cpp:48`)。

`Orch::addConsumer()` の CONFIG_DB / STATE_DB 分岐 (`orch.cpp:1186-1196`) と同様に、`SubscriberStateTable` は keyspace パターン `__keyspace@<dbId>__:SUBNET_DECAP|*` に `PSUBSCRIBE` する。書き込み側 (`sonic-cfggen` / `sonic-db-cli` / gNMI) は `HSET` のみ行い、明示的な `PUBLISH` は発行しない。

```cpp
// tunneldecaporch.cpp:39-48
auto cfgSubnetDecapSubTable = new SubscriberStateTable(
    configDb, CFG_SUBNET_DECAP_TABLE_NAME,
    TableConsumable::DEFAULT_POP_BATCH_SIZE, 0);
deque<KeyOpFieldsValuesTuple> entries;
cfgSubnetDecapSubTable->pops(entries);
// init subnet decap config (先読み初期化)
for (auto &entry : entries)
    doSubnetDecapTask(entry);
Orch::addExecutor(new Consumer(cfgSubnetDecapSubTable, this, CFG_SUBNET_DECAP_TABLE_NAME));
```

| 購読者 | 購読 API | 購読テーブル | バッチサイズ | 優先度 |
|--------|---------|--------------|------------|--------|
| `orchagent` (`TunnelDecapOrch`) | `swss::SubscriberStateTable` | `SUBNET_DECAP` | `DEFAULT_POP_BATCH_SIZE` = 128 | 0 (低) |

バッチサイズは `sonic-swss-common/common/table.h:164` の `DEFAULT_POP_BATCH_SIZE = 128` で固定される。優先度 `0` は他の orchagent ハンドラより低く、SUBNET_DECAP の処理は後回しになりやすい。CONFIG_DB のため TTL は使用されない。

### 先読み初期化（コンストラクタ pops）

`TunnelDecapOrch` のコンストラクタは `Orch::addExecutor()` に登録する **前** に `cfgSubnetDecapSubTable->pops(entries)` で既存エントリを全件先読みし、`doSubnetDecapTask()` で `subnetDecapConfig` を初期化する。これにより orchagent 起動時点で CONFIG_DB に存在する `SUBNET_DECAP` エントリが即座に処理され、keyspace 通知が来る前に `subnetDecapConfig.enable / src_ip / src_ip_v6` が確定する。

この設計の目的は「**SUBNET_DECAP の状態が RouteOrch / VNetRouteOrch の VIP ルート処理より先に確定する**」ことにある。`subnetDecapConfig.enable == true` でなければ VIP ルート投入時に tunnel term が生成されないため、先読みによる初期化保証が必要。

### keyspace 通知 → ハンドラ呼び出しの流れ

```
sonic-cfggen / sonic-db-cli / gNMI
  ↓ Table::set("SUBNET_DECAP|<name>", fvs)
CONFIG_DB: HSET "SUBNET_DECAP|<name>" <fields>
  ↓ Redis keyspace event "__keyspace@4__:SUBNET_DECAP|<name>" "hset"
OrchDaemon main loop: m_select->select(&s, SELECT_TIMEOUT=1000ms)
  ↓ Consumer::execute() → SubscriberStateTable::pops()
    └─ HGETALL "SUBNET_DECAP|<name>" で値再取得
TunnelDecapOrch::doTask(consumer)  (tunneldecaporch.cpp:69)
  ↓ table_name == CFG_SUBNET_DECAP_TABLE_NAME で分岐
TunnelDecapOrch::doSubnetDecapTask(consumer)
  ↓ SET: subnetDecapConfig 更新 + SAI tunnel term 更新
  ↓ DEL: subnetDecapConfig.enable = false
```

- `SELECT_TIMEOUT = 1000 ms` (`orchdaemon.cpp:23`)。keyspace 通知到着で即座に wake up し、通知がなければ最大 1 秒後にポーリング。
- `doTask` 内の `gPortsOrch->allPortsReady()` ガード (`tunneldecaporch.cpp:55-57`) により、ポート初期化完了前の通知は**早期リターン**される。通知は Consumer キューに残り、次のループで再試行される。
- `subnetDecapConfig` はシングルトン構造体のため、複数エントリを書き込んでも最後の SET で上書きされる（再試行キャッシュなし）。

### サービス再起動トリガー

なし。`TunnelDecapOrch` は orchagent プロセス内のハンドラであり、`SUBNET_DECAP` の追加・変更・削除は SAI `sai_tunnel_api` のライブ操作のみで反映され、プロセス再起動・サービス restart を伴わない。

> **Evidence**: `sonic-swss/orchagent/tunneldecaporch.cpp:39-48,55-57,69-72` (SubscriberStateTable 生成・先読み・doTask 分岐)、`sonic-swss/orchagent/orchdaemon.cpp:23,959` (SELECT_TIMEOUT / select ループ)、`sonic-swss-common/common/table.h:164` (`DEFAULT_POP_BATCH_SIZE = 128`)、`sonic-swss-common/common/subscriberstatetable.cpp:17,45-165` (PSUBSCRIBE + HGETALL 動作)
<!-- /pubsub -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

SUBNET_DECAP テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし

### minigraph / sonic-cfggen

minigraph.py に SUBNET_DECAP 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での SUBNET_DECAP マイグレーションなし

### ビルド時デフォルト (build-time default)

**`dockers/docker-orchagent/ipinip.json.j2`** が SUBNET_DECAP テーブルのデフォルト値をビルド時に生成 (sonic-buildimage/dockers/docker-orchagent/ipinip.json.j2)

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- glossary-links-injected: f9445b5b4106 -->
