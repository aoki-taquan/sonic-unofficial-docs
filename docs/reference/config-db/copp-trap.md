---
title: COPP_TRAP テーブル
description: "COPP_TRAP テーブル — CoPP の trap エントリを定義し、SAI hostif trap ID 群を COPP_GROUP に束ねる。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-copp.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - COPP_TRAP
    - COPP_GROUP
  cli:
    - config copp
  yang:
    - sonic-copp
---

# COPP_TRAP テーブル

## 概要

[CoPP](../../reference/glossary.md#term-copp) の trap エントリを定義し、[SAI](../../reference/glossary.md#term-sai) hostif trap ID 群を `COPP_GROUP` に束ねる。各 trap は `trap_ids` フィールドにカンマ区切り識別子 (`bgp`、`lldp`、`arp_req` など) を列挙し、`trap_group` で `COPP_GROUP` に紐付ける[^1]。`coppmgr` が両テーブルを結合し [APPL_DB](../../reference/glossary.md#term-appl_db) の `COPP_TABLE` に書く。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>COPP_TRAP")]
  DM["coppmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_COPP_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_hostif_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
COPP_TRAP|<name>
```

## 主要フィールド

| フィールド | 型 | 必須 | 既定 | 説明 |
|-----------|----|------|------|------|
| `trap_ids` | string | yes | - | カンマ区切り trap 識別子。例: `bgp,bgpv6` |
| `trap_group` | leafref `COPP_GROUP.name` | no | - | 適用する [CoPP](../../reference/glossary.md#term-copp) group |
| `always_enabled` | boolean | no | - | true なら feature の有効/無効に関わらず常時インストール |

## 動作上の注意

- `always_enabled = true` のエントリ (例: [BGP](../../reference/glossary.md#term-bgp) / [LLDP](../../reference/glossary.md#term-lldp) のシステム必須 trap) はユーザの `config feature state` 操作と独立にインストールされる
- 既定の `COPP_TRAP` 群は `dockers/docker-orchagent/copp_cfg.j2` および `files/image_config/copp/copp_cfg.j2` 由来でビルド時に生成される

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **NAT trap_id → NAT 非対応時 ignore**: スイッチが NAT 非対応 (`gIsNatSupported == false`) の場合、`SNAT_MISS` / `DNAT_MISS` の trap_id は `SWSS_LOG_NOTICE("Ignoring the trap_id: %s, as NAT is not supported")` を出力してスキップされる。<!-- evidence: copporch.cpp L400-406 -->
- **SAI 非対応 trap_id → ignore**: `isTrapIdSupported()` が false の場合 `SWSS_LOG_NOTICE("Ignoring the trap_id: %s, since not supported by vendor SAI")` を出力してスキップ。ベンダー SAI が実装していない trap は適用されない。<!-- evidence: copporch.cpp L408-413 -->
- **COPP_GROUP 未到着時の trap_group 参照 → 書き込み保留**: `trap_group` に指定したグループが pending の場合、`coppmgr` は APPL_DB への書き込みを保留し COPP_GROUP 到着後に再処理する。<!-- evidence: coppmgr.cpp L62-81 checkTrapGroupPending -->
- **feature 無効な trap_id → COPP_TABLE から除外**: feature が off の trap_id は `isTrapIdDisabled()` で除外される。trap_group の trap_ids が空になった場合は APPL_DB エントリを削除。<!-- evidence: coppmgr.cpp L173-191 isTrapIdDisabled -->
- **task_failed → プロセス終了**: `CoppOrch` は `task_failed` が返った場合プロセスを終了する。<!-- evidence: copporch.cpp L922 -->

<!-- value-behavior -->
## 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `always_enabled` | `true` | `coppmgr` が feature の有効/無効に関わらず trap を APPL_DB に書き込む（`coppmgr.cpp:90`）。`config feature state <feature> disabled` を実行しても trap はアクティブのまま。BGP / LLDP など必須プロトコルに使用。 |
| `always_enabled` | `false` / 未設定 | feature が enabled のときのみ trap をインストール。feature が disabled になると trap が削除される。 |
| `trap_ids` | 有効な trap_id（例: `bgp`） | `CoppOrch` が `trap_id_map` で SAI hostif trap type に変換してインストール。 |
| `trap_ids` | 未知の trap_id | `CoppOrch` の `trap_id_map.at()` が例外を投げ、当該エントリ全体が適用されない（サイレント失敗）。 |
| `trap_ids` | プラットフォーム SAI 非対応の trap_id | `isTrapIdSupported()=false` で個別 trap がスキップ（NOTICE ログのみ）（`copporch.cpp:408-413`）。他の trap_id は継続適用。 |
| `trap_ids` | `snat_miss` / `dnat_miss` | NAT 非対応スイッチ（`gIsNatSupported=false`）ではスキップ（NOTICE ログ）（`copporch.cpp:400-406`）。 |
<!-- /value-behavior -->

## 購読者

- `coppmgr`: [CONFIG_DB](../../reference/glossary.md#term-config_db) → [APPL_DB](../../reference/glossary.md#term-appl_db) `COPP_TABLE`
- `orchagent` `CoppOrch`: [SAI](../../reference/glossary.md#term-sai) HOSTIF_TRAP オブジェクト生成

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `COPP_GROUP`、`FEATURE`
- 関連 CLI: `config copp`、`show copp`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-copp`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-copp`](../yang/sonic-copp.md)
- CLI: `config copp`

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-copp.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-copp.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: ACL / CoPP / Mirror / Packet Action](../../topics/07-acl-copp-mirror/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `COPP_TRAP|<trap-name>` (`bgp`, `lldp`, `arp` 等)。
- `trap_ids`: `bgp,bgpv6` 等のカンマ区切り。
- `trap_group`: 紐付ける `COPP_GROUP` 名。

### よくある誤設定

- 存在しない `trap_group` を参照すると copporch が trap を install しない。
- `trap_ids` のスペル違いは silently 無視され該当トラフィックが CPU に上がらない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'COPP_TRAP|*'
show copp config
```
<!-- /ops-hint -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `COPP_TRAP`

### CLI
- `config copp trap add/del <trap-name> ...`
  - ソース: `sonic-utilities/config/main.py (copp グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `copp_cfg.j2` が `sonic-cfggen` 経由でデフォルトトラップセットを生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
<!-- /entry-points -->

<!-- glossary-links-injected: 7a3847939b09 -->
