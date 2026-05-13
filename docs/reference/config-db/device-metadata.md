---
title: DEVICE_METADATA テーブル
description: "DEVICE_METADATA テーブル — 装置全体のメタ情報を保持する CONFIG_DB テーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-device_metadata.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - DEVICE_METADATA
  cli:
    - config hostname
    - config bgp
  yang:
    - sonic-device_metadata
---

# DEVICE_METADATA テーブル

## 概要

装置全体のメタ情報を保持する [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル。hostname、ベース MAC、[BGP](../../reference/glossary.md#term-bgp) ASN、ハードウェア SKU、プラットフォーム、デバイス役割 (`type`)、サブタイプ (`DualToR` / `SmartSwitch` 等)、deployment ID、buffer model（dynamic / traditional）、synchronous mode、[YANG](../../reference/glossary.md#term-yang) 検証の有効化、syslog / [FRR](../../reference/glossary.md#term-frr) 関連スイッチなど、SONiC の起動時挙動を決める根本設定を 1 行 (`localhost`) にまとめる。`bmc` キーは BMC 接続情報を別ロウで持つ[^1]。

各 Orch / daemon は起動時に `DEVICE_METADATA|localhost` を読み出す。`bgpcfgd` は `bgp_asn` と `frr_mgmt_framework_config` を、`orchagent` は `synchronous_mode` と `async_swss_rec`、`buffer_model` を、`hostcfgd` は `hostname` と `timezone` を、それぞれ依存リソースの初期化に用いる。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>DEVICE_METADATA")]
  DM["SwitchOrch"]
  CDB --> DM
  SAI["SAI<br/>sai_switch_api"]
  DM --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
DEVICE_METADATA|localhost
DEVICE_METADATA|bmc
```

key は固定文字列 `localhost`（必須）と任意の `bmc`。

## フィールド一覧 (localhost)

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `hwsku` | string (`stypes:hwsku`) | - | ハードウェア SKU 識別子。ポートレイアウトと能力を決める |
| `asic_id` | string (1..16) | - | [SAI](../../reference/glossary.md#term-sai) 初期化に使う ASIC 識別子 |
| `default_bgp_status` | enum `up` / `down` | `up` | 起動時の [BGP](../../reference/glossary.md#term-bgp) daemon 既定状態 |
| `docker_routing_config_mode` | string `separated`/`unified`/`split`/`split-unified` | `unified` | [FRR](../../reference/glossary.md#term-frr) 設定生成モード |
| `hostname` | string (`stypes:hostname`) | - | システムホスト名 |
| `platform` | string (1..255) | - | プラットフォーム識別子（vendor + model） |
| `mac` | mac-address | - | システムベース MAC |
| `default_pfcwd_status` | enum `disable`/`enable` | `disable` | 起動時の [PFC](../../reference/glossary.md#term-pfc) watchdog 既定状態 |
| `bgp_asn` | as-number | - | [BGP](../../reference/glossary.md#term-bgp) 自律システム番号 |
| `deployment_id` | uint32 | - | 同一ネットワークセグメントを括る deployment ID |
| `type` | enum (ToRRouter / LeafRouter / SpineRouter / SmartSwitchDPU / 等) | - | デバイス役割 |
| `buffer_model` | string `dynamic`/`traditional` | - | バッファ計算モード。Mellanox 等は dynamic |
| `frr_mgmt_framework_config` | boolean | `false` | true で `sonic-frr-mgmt-framework` が [FRR](../../reference/glossary.md#term-frr) 設定を担当、false で `bgpcfgd` がテンプレ展開 |
| `synchronous_mode` | enum `enable`/`disable` | `enable` | [orchagent](../../reference/glossary.md#term-orchagent) ASIC 同期モード |
| `yang_config_validation` | enum `enable`/`disable` | `disable` | `config_db.json` 直接ロード時の [YANG](../../reference/glossary.md#term-yang) 検証 |
| `cloudtype` | string | - | デプロイ先のクラウドタイプ |
| `region` | string | - | 地理的リージョン |
| `sub_role` | string | - | ASIC が FrontEnd か BackEnd かを示す |
| `downstream_subrole` | string | - | 下流接続デバイスのサブ役割 |
| `resource_type` | string | - | リソースタイプ分類 |
| `mgmt_type` | string | - | 管理タイプ |
| `cluster` | string | - | 所属クラスタ名 |
| `subtype` | string `DualToR`/`SmartSwitch`/`Supervisor`/`UpstreamLC`/`DownstreamLC` | - | 特殊トポロジ種別 |
| `peer_switch` | hostname | - | dual ToR 構成のピアホスト名 |
| `storage_device` | boolean | - | ストレージバックエンドに繋がるか |
| `asic_name` | string | - | VoQ スイッチでグローバル DB key の修飾子に使う ASIC 名 |
| `switch_id` | uint16 | - | ベンダ固有スイッチ ID |
| `switch_type` | string `chassis-packet`/`fabric`/`npu`/`voq`/`dpu`/`dummy-sup` | - | スイッチタイプ。既定は npu |
| `max_cores` | uint8 | - | VoQ シャーシの最大 core 数 |
| `dhcp_server` | admin_mode | - | 組み込み DHCP サーバを有効化するか |
| `bgp_adv_lo_prefix_as_128` | boolean | - | true で Loopback0 IPv6 /128 をそのまま広告（既定は /64 化） |
| `suppress-fib-pending` | enum `enabled`/`disabled` | `disabled` | BGP suppress-fib-pending。`enabled` には `synchronous_mode = enable` が必須 |
| `async_swss_rec` | enum `enabled`/`disabled` | `disabled` | [orchagent](../../reference/glossary.md#term-orchagent) の swss.rec 非同期記録 |
| `rack_mgmt_map` | string (0..128) | - | rack 管理マップ情報 |
| `timezone` | timezone-name (1..255) | `UTC` | TZ database name (`Europe/Stockholm` 等) |
| `create_only_config_db_buffers` | boolean | - | true で [CONFIG_DB](../../reference/glossary.md#term-config_db) のバッファ設定通り、false で [SAI](../../reference/glossary.md#term-sai) から読んだ最大バッファを生成 |
| `supporting_bulk_counter_groups` | leaf-list string | - | バルク操作対応のカウンタグループ名 |
| `bgp_router_id` | ipv4-address | - | BGP router-id |
| `chassis_hostname` | hostname | - | このリニアカード／スーパバイザが属するシャーシ名 |
| `slice_type` | string | - | デバイスのメタデータタグ |
| `location_type` | string | - | 場所タイプ |
| `nexthop_group` | enum `enabled`/`disabled` | `disabled` | Nexthop Group 機能。boot 時のみ反映 |
| `ring_thread_enabled` | boolean | `false` | OrchDaemon の gRingMode |
| `t2_group_asns` | leaf-list as-number | - | 同一グループ内の ASN |
| `anchor_route_source` | leaf-list string | - | anchor route のソース |
| `orch_northbond_dash_zmq_enabled` | boolean | `true` | [APPL_DB](../../reference/glossary.md#term-appl_db) [DASH](../../reference/glossary.md#term-dash) テーブル ZMQ |
| `orch_northbond_route_zmq_enabled` | boolean | `false` | [APPL_DB](../../reference/glossary.md#term-appl_db) ROUTE テーブル ZMQ |
| `syslog_with_osversion` | boolean | `false` | syslog に OS version を付加 |
| `syslog_counter` | boolean | `false` | syslog counter |
| `has_sonic_dhcpv4_relay` | boolean_type | `false` | DHCPv4 relay プロセスを有効化 |
| `zebra_nexthop` | enum `enabled`/`disabled` | `enabled` | next-hop group サポート。boot 時のみ反映 |

`type` の取りうる値は [YANG](../../reference/glossary.md#term-yang) の正規表現で 30 種以上が列挙されている (`ToRRouter|LeafRouter|SpineChassisFrontendRouter|...|UpperRegionalHub`)。詳細は `sonic-device_metadata.yang` を直接参照[^1]。

## フィールド一覧 (bmc)

| フィールド | 型 | 説明 |
|-----------|----|------|
| `bmc_if_name` | string (1..64) | BMC インタフェース名 |
| `bmc_if_addr` | ipv4-address | BMC インタフェース IP |
| `bmc_addr` | ipv4-address | BMC IP |
| `bmc_net_mask` | ipv4-address | BMC ネットマスク |

<!-- value-behavior -->
## 値依存挙動マトリクス

### `default_bgp_status`

| 値 | 挙動 |
|----|------|
| `up` (デフォルト) | [bgpcfgd](../../reference/glossary.md#term-bgpcfgd) 起動時に BGP daemon を auto-start 状態にする |
| `down` | BGP daemon を shutdown 状態で起動（メンテナンス用） |

### `docker_routing_config_mode`

| 値 | 挙動 |
|----|------|
| `separated` | minigraph デフォルト。[bgpcfgd](../../reference/glossary.md#term-bgpcfgd) が J2 テンプレを展開して frr.conf を生成 |
| `unified` | frrcfgd が起動時に全 BGP テーブルをリプレイしてから変更を監視 |
| `split` / `split-unified` | frrcfgd が `separated` モードとして動作（frrcfgd.py:2170） |
| 未設定 | frrcfgd が `separated` とみなす |

### `frr_mgmt_framework_config`

| 値 | 挙動 |
|----|------|
| `false` (デフォルト) | [bgpcfgd](../../reference/glossary.md#term-bgpcfgd) が FRR 設定を担当 |
| `true` | sonic-frr-mgmt-framework (frrcfgd) が BGP 設定を担当。BGP_NEIGHBOR 等を frrcfgd が受け付ける |

### `default_pfcwd_status`

| 値 | 挙動 |
|----|------|
| `disable` (デフォルト) | pfcwd は `config reload` 後に自動起動しない |
| `enable` | `config reload` 後に `pfcwd start_default` が自動実行（config/main.py:2434） |
| type が MgmtToRRouter 等 | pfcwd 呼び出し自体をスキップ（device_type チェック） |

### `synchronous_mode`

| 値 | 挙動 |
|----|------|
| `enable` (デフォルト) | orchagent を `-s` フラグで synchronous mode 起動（[SAI](../../reference/glossary.md#term-sai) 操作がブロッキング） |
| `disable` | orchagent を非同期 SAI モードで起動 |
| switch_type=`dpu` のとき | `enable` でも zmq_sync モードが優先（orchagent.sh:39-41） |

### `suppress-fib-pending`

| 値 | 挙動 |
|----|------|
| `disabled` (デフォルト) | suppress-fib-pending 無効 |
| `enabled` | bgpcfgd が FRR に `bgp suppress-fib-pending` を適用（managers_bgp.py:502） |
| `enabled` かつ `synchronous_mode ≠ enable` | YANG `must` 違反 → reject |

### `buffer_model`

| 値 | 挙動 |
|----|------|
| `dynamic` | buffermgr が BUFFER_POOL/PROFILE の CONFIG_DB 変更を無視。dynamic buffer mgr (Mellanox 等) が SAI 直接更新（buffermgr.cpp:476-478） |
| `traditional` (またはその他) | buffermgr が CONFIG_DB の BUFFER_POOL/PROFILE を [APPL_DB](../../reference/glossary.md#term-appl_db) に転写 |

### `switch_type`

| 値 | 挙動 |
|----|------|
| `npu` / 未設定 | 通常スイッチとして起動 |
| `voq` | orchagent が [VOQ](../../reference/glossary.md#term-voq) モードで起動、switch_id を SAI に渡す |
| `fabric` | SAI_SWITCH_TYPE_FABRIC として作成、switch_id 必須（未設定で exit） |
| `dpu` | orchagent.sh が zmq_sync + bulk limit 65536 で起動 |
| 不正値 | orchagent がエラーログを出して `switch` に fallback（main.cpp:262） |

### `async_swss_rec`

| 値 | 挙動 |
|----|------|
| `disabled` (デフォルト) | swss.rec 同期書き込み |
| `enabled` | swss.rec を非同期で書き込み（高トラフィック時の遅延軽減） |

<!-- /value-behavior -->

## 購読者

- `bgpcfgd` / `sonic-frr-mgmt-framework`: `bgp_asn`、`bgp_router_id`、`frr_mgmt_framework_config`、`docker_routing_config_mode`、`default_bgp_status`、`suppress-fib-pending`、`bgp_adv_lo_prefix_as_128`
- `orchagent`: `synchronous_mode`、`async_swss_rec`、`buffer_model`、`create_only_config_db_buffers`、`switch_type`、`asic_name`、`switch_id`、`ring_thread_enabled`、`nexthop_group`、`zebra_nexthop`
- `hostcfgd`: `hostname`、`timezone`、`syslog_*`
- `pfcwd` / `pfcwd_init`: `default_pfcwd_status`
- `dhcp_server` 系: `dhcp_server`、`has_sonic_dhcpv4_relay`

## 制約

- `suppress-fib-pending = enabled` のとき `synchronous_mode = enable` が必須（YANG `must`）
- `subtype = DualToR` のときは `peer_switch` の指定が運用上必要（[HLD](../../reference/glossary.md#term-hld) 由来、YANG では強制されない）
- `type` は enum パターンに合致する文字列のみ受理

## 関連 CONFIG_DB テーブル / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `BGP_DEVICE_GLOBAL`（`bgp_asn` と独立した装置全体 BGP スイッチ）、`MGMT_PORT`（管理ポート設定）、`FEATURE`（docker on/off）
- 関連 CLI: [`config bgp`](../cli/config-bgp.md)、`config hostname`
- 関連 YANG: `sonic-device_metadata`（`hostname`、`hwsku`、`mode-status` などの typedef を当該モジュール内で定義）

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-device_metadata`](../yang/sonic-device_metadata.md)
- CLI: `config hostname` / [`config bgp`](../cli/config-bgp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_metadata.yang` (sha `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`)。<https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-device_metadata.yang>

<!-- evidence:
source: sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_metadata.yang#L37-L411 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
excerpt: |
  container DEVICE_METADATA {
      container localhost { ... 50+ leafs ... }
      container bmc { bmc_if_name, bmc_if_addr, bmc_addr, bmc_net_mask }
  }
reasoning: フィールド一覧と型・デフォルト・enum 値はこのモジュールの leaf 宣言から抽出
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_metadata.yang#L37-L411 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)"

    **出典**:

    `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_metadata.yang#L37-L411 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)`

    **抜粋**:

    ```text
    container DEVICE_METADATA {
        container localhost { ... 50+ leafs ... }
        container bmc { bmc_if_name, bmc_if_addr, bmc_addr, bmc_net_mask }
    }
    ```

    **判断根拠**: フィールド一覧と型・デフォルト・enum 値はこのモジュールの leaf 宣言から抽出

<!-- evidence-rendered:end -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `DEVICE_METADATA|localhost`。
- `hostname`、`hwsku`、`platform`、`mac`、`type` (`ToRRouter`/`LeafRouter`/`SpineRouter`)。
- `bgp_asn`、`default_bgp_status: up`、`default_pfcwd_status: enable`。

### よくある誤設定

- `hwsku` を実機と異なる値にすると [sonic-buildimage](../../reference/glossary.md#term-sonic-buildimage) 起動時に platform plugin が読み込まれず [orchagent](../../reference/glossary.md#term-orchagent) が起動しない。
- `type` を誤ると generic_config_updater のチェックや MC-[LAG](../../reference/glossary.md#term-lag) の role 判定で誤動作。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'DEVICE_METADATA|localhost'
show platform summary
```
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| consumer | 条件 | 挙動 |
|---|---|---|
| bgpcfgd | `bgp_asn` が `localhost` に存在しない | BGP ピア追加を `return False` で延期・再試行待ち（managers_bgp.py:192） |
| bgpcfgd | `bgp_router_id` も未設定かつ Loopback IPv4 未取得 | ピア追加待機、`log_warn` を出力（managers_bgp.py:186-188） |
| bgpcfgd | `type` (switch_role) が未設定 | `switch_role=None` のまま継続、デフォルト補完なし（managers_device_global.py:53-54） |
| [syncd](../../reference/glossary.md#term-syncd) | `switch_type` が `hget` で取得できない | 空文字のまま続行、例外なし（Syncd.cpp:167-169） |
| dhcprelayd | `has_sonic_dhcpv4_relay = "True"` | 旧来 `dhcrelay` プロセスを起動しない（新 dhcpv4-relay サービスに委譲）（dhcprelayd.py:112-113） |
| [linkmgrd](../../reference/glossary.md#term-linkmgrd) | `mac` フィールドのフォーマット不正 | `MUX_ERROR(ConfigNotFound)` 例外を throw し [linkmgrd](../../reference/glossary.md#term-linkmgrd) が起動失敗（DbInterface.cpp:576） |
| db_migrator | `synchronous_mode` キーが存在しない | 移行元から取得して補完、既存値は上書きしない（db_migrator.py:676-677） |

> **Evidence**: [sonic-buildimage](../../reference/glossary.md#term-sonic-buildimage) `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`, `managers_device_global.py`; [sonic-sairedis](../../reference/glossary.md#term-sonic-sairedis) `syncd/Syncd.cpp:167`; [sonic-buildimage](../../reference/glossary.md#term-sonic-buildimage) `src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py:112`; sonic-[linkmgrd](../../reference/glossary.md#term-linkmgrd) `src/DbInterface.cpp:576`; [sonic-utilities](../../reference/glossary.md#term-sonic-utilities) `scripts/db_migrator.py:676`
<!-- /cdb-exceptions -->

<!-- glossary-links-injected: e22e287b939b -->
