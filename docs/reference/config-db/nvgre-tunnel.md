---
title: NVGRE_TUNNEL / NVGRE_TUNNEL_MAP テーブル
description: "NVGRE_TUNNEL / NVGRE_TUNNEL_MAP テーブル — NVGRE (Network Virtualization using GRE, RFC 7637) のトンネル端点と VLAN ↔ VSID マップを CONFIG_DB に保持する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-nvgre-tunnel.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - NVGRE_TUNNEL
    - NVGRE_TUNNEL_MAP
    - VLAN
  cli:
    - config nvgre
  yang:
    - sonic-nvgre-tunnel
---

# NVGRE_TUNNEL / NVGRE_TUNNEL_MAP テーブル

## 概要

NVGRE (Network Virtualization using GRE, RFC 7637) のトンネル端点と [VLAN](../../reference/glossary.md#term-vlan) ↔ VSID マップを [CONFIG_DB](../../reference/glossary.md#term-config_db) に保持する[^1]。`vxlanorch` 系（NVGRE は [VXLAN](../../reference/glossary.md#term-vxlan) orch と一部実装を共有）が [SAI](../../reference/glossary.md#term-sai) 経由でカプセル化/デカプセル化を構成する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>NVGRE_TUNNEL")]
  DM["NvgreTunnelOrch"]
  CDB --> DM
  SAI["SAI<br/>sai_tunnel_api"]
  DM --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
NVGRE_TUNNEL|<tunnel_name>
NVGRE_TUNNEL_MAP|<tunnel_name>|<tunnel_map_name>
```

## NVGRE_TUNNEL フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `tunnel_name` (key) | string (1..255) | — | NVGRE トンネル名 |
| `src_ip` | inet:ip-address | yes | ソース [VTEP](../../reference/glossary.md#term-vtep) IP |

## NVGRE_TUNNEL_MAP フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `tunnel_name` (key) | leafref → `NVGRE_TUNNEL.tunnel_name` | — | 親トンネル |
| `tunnel_map_name` (key) | string (1..255) | — | マップエントリ名 |
| `vlan_id` | uint16 (1..4094) | yes | [VLAN](../../reference/glossary.md#term-vlan) ID |
| `vsid` | uint32 (0..16777214) | yes | NVGRE Virtual Subnet ID (24bit) |

## 制約

- `vsid` は 24bit (0..16777214)、`vlan_id` は 1..4094

## 購読者

- `orchagent` (vxlanorch / NVGRE 拡張) — [SAI](../../reference/glossary.md#term-sai) tunnel オブジェクト生成

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `VLAN`、`VXLAN_TUNNEL`（並存可能）
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-nvgre-tunnel`
- 関連 CLI: `config nvgre`

<!-- value-behavior -->
## 値依存挙動マトリクス

### NVGRE_TUNNEL フィールド

| フィールド | 値 / 範囲 | [orchagent](../../reference/glossary.md#term-orchagent) 挙動 |
|-----------|----------|---------------|
| `src_ip` | 任意の有効 IP アドレス | [SAI](../../reference/glossary.md#term-sai) `sai_tunnel_api` でトンネル端点として設定 |
| `src_ip` | フォーマット不正 / 未設定 | YANG validate 段階で reject |

### NVGRE_TUNNEL_MAP フィールド

| フィールド | 値 / 範囲 | [orchagent](../../reference/glossary.md#term-orchagent) 挙動 |
|-----------|----------|---------------|
| `vlan_id` | 1..4094 | [VLAN](../../reference/glossary.md#term-vlan) ID として SAI トンネルマップに登録 |
| `vlan_id` | 範囲外 | WARN ログ後スキップ: `VLAN ID doesn't exist: %d` |
| `vsid` | 0..16777214 | NVGRE VSID として SAI に反映 |
| `vsid` | 範囲外 | WARN ログ後スキップ: `VSID is invalid: %d` |
| `tunnel_name` | 存在する NVGRE_TUNNEL を参照 | MAP エントリ作成 |
| `tunnel_name` | 存在しない親トンネルを参照 | WARN ログ: `NVGRE tunnel '%s' doesn't exist` |

*enum なし — src_ip は inet:ip-address 型、vlan_id / vsid は数値範囲のみ。*

<!-- /value-behavior -->

<!-- defaults -->
## コード由来デフォルト (Task F Phase A)

<!-- evidence: meta/_intermediate/cdb-flow/nvgre-tunnel-defaults.md -->

`sonic-swss/orchagent/nvgreorch.{h,cpp}` を全行調査した結果、**NVGRE_TUNNEL / NVGRE_TUNNEL_MAP 双方のフィールドにコード由来のデフォルト値は存在しない**。`request_description_t` の mandatory リストに全フィールドが登録されており、未指定時は `request_parser` 段階で reject される。

### フィールド別 デフォルト有無

| フィールド | テーブル | コード由来デフォルト | 未指定時の挙動 | ソース |
|-----------|---------|-------------------|---------------|--------|
| `tunnel_name` (key) | `NVGRE_TUNNEL` | なし | key 必須、自動採番なし | `nvgreorch.h:32` |
| `src_ip` | `NVGRE_TUNNEL` | なし | mandatory、`request_parser` reject | `nvgreorch.h:36`, `nvgreorch.cpp:354` |
| `tunnel_map_name` (key) | `NVGRE_TUNNEL_MAP` | なし | key 必須 | `nvgreorch.h:141` |
| `vlan_id` | `NVGRE_TUNNEL_MAP` | なし | mandatory、reject | `nvgreorch.h:144,146` |
| `vsid` | `NVGRE_TUNNEL_MAP` | なし | mandatory、reject | `nvgreorch.h:143,146` |

```cpp
// nvgreorch.h:31-37 (NVGRE_TUNNEL の request 定義 — 第3要素が mandatory リスト)
const request_description_t nvgre_tunnel_request_description = {
            { REQ_T_STRING },
            {
                { "src_ip", REQ_T_IP },
            },
            { "src_ip" }
};
```

### 付随する SAI ハードコード値 (デフォルトではないが固定)

`NvgreTunnel` 構築時、フィールド値とは独立に以下が常時 SAI へ渡される (`nvgreorch.cpp:136-257`):

| SAI 属性 | 値 | 備考 |
|---|---|---|
| `SAI_TUNNEL_ATTR_TYPE` | `SAI_TUNNEL_TYPE_NVGRE` | テーブル名から確定 |
| `SAI_TUNNEL_ATTR_UNDERLAY_INTERFACE` | `gUnderlayIfId` | 起動時のグローバル [RIF](../../reference/glossary.md#term-rif) |
| `SAI_TUNNEL_TERM_..._TYPE` | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP` | NVGRE は P2MP 固定 |
| `SAI_TUNNEL_TERM_..._VR_ID` | `gVirtualRouterId` | デフォルト [VRF](../../reference/glossary.md#term-vrf) |
| Encap/Decap mapper | `MAP_T_VLAN` / `MAP_T_BRIDGE` を常時両方作成 | `nvgreMapTypes` static |
| VSID 上限 | `NVGRE_VSID_MAX_VALUE = 16777214` | `nvgreorch.cpp:7` |

> **結論**: 利用者視点では「CLI / RESTCONF で全フィールドを明示指定するしかなく、未指定の救済デフォルトは無い」と覚えればよい。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

### allPortsReady ガードなし

`NvgreTunnelOrch::addOperation()` および `NvgreTunnelMapOrch::addOperation()` はいずれも `gPortsOrch->allPortsReady()` をチェックしない (`nvgreorch.cpp:350-508`)。orchdaemon 起動直後から SET を処理できる。

### NVGRE_TUNNEL → NVGRE_TUNNEL_MAP の順序が必須

`NvgreTunnelMapOrch::addOperation()` (L464-508) は冒頭で `tunnel_orch->isTunnelExists(tunnel_name)` を確認する。親トンネルが未登録の場合は `SWSS_LOG_WARN("NVGRE tunnel '%s' doesn't exist", ...)` + `return true` で**エントリを破棄する**（retry キューに戻らない）。

```
SET NVGRE_TUNNEL|<tunnel_name>    src_ip=<vtep_ip>      # 先に作成
SET NVGRE_TUNNEL_MAP|<tunnel_name>|<map_name>  vlan_id=<vid> vsid=<vsid>  # その後
```

### VLAN が先行必須（MAP 登録時）

`addOperation()` L489: `gPortsOrch->getVlanByVlanId(vlan_id, port)` が false を返すと WARN + `return true` でエントリ破棄。`VLAN|<vlan_id>` が PortsOrch に登録されてから MAP を書き込むこと。

### 安全な DEL 順序

```
DEL NVGRE_TUNNEL_MAP|<tunnel_name>|<map_name>  # 先に MAP を削除
DEL NVGRE_TUNNEL|<tunnel_name>                  # その後トンネルを削除
```

`NvgreTunnelMapOrch::delOperation()` (L554) はトンネル存在チェック後に MAP 削除処理を行う。NVGRE_TUNNEL を先に DEL すると MAP の DEL で `does not exist` WARN となり SAI 上のマップエントリが残留する可能性がある。

| 依存関係 | 方向 | 緩和策 |
|---|---|---|
| `NVGRE_TUNNEL` SET → `NVGRE_TUNNEL_MAP` SET | 必須 | 逆順だと MAP エントリが**永続的に破棄**（retry なし） |
| `VLAN` 登録完了 → `NVGRE_TUNNEL_MAP` SET | 必須 | 逆順だと MAP エントリが**永続的に破棄**（retry なし） |
| `NVGRE_TUNNEL_MAP` DEL → `NVGRE_TUNNEL` DEL | 推奨 | 逆順でも [orchagent](../../reference/glossary.md#term-orchagent) は継続するが SAI エントリ孤立リスク |
| allPortsReady | 不要 | NVGRE orch には allPortsReady ガードなし |

> **スキャン証跡**: `nvgreorch.cpp:464-508` 全行精読、`orchdaemon.cpp:361-364` 登録順確認。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照 — Phase C (cross-table refs)

YANG leafref を超えた実装上の依存関係。ソース: `sonic-swss/orchagent/nvgreorch.cpp` および `sonic-swss/orchagent/orchdaemon.cpp`。

| 参照先 | DB / 場所 | 方向 | 契機 | 根拠コード |
|--------|-----------|------|------|-----------|
| `NVGRE_TUNNEL\|<tunnel_name>` | [CONFIG_DB](../../reference/glossary.md#term-config_db) (orchagent 内部 map) | READ | `NvgreTunnelMapOrch::addOperation()` 冒頭で `isTunnelExists(tunnel_name)` を呼ぶ。親トンネルが未登録なら WARN + エントリ破棄（retry なし） | `nvgreorch.cpp:464-472` |
| `VLAN\|Vlan<vlan_id>` | CONFIG_DB / PortsOrch 内部 map | READ | MAP 登録時に `gPortsOrch->getVlanByVlanId(vlan_id, port)` で VLAN の存在確認。VLAN 未登録なら `VLAN ID doesn't exist` WARN + エントリ破棄 | `nvgreorch.cpp:489-492` |
| `gUnderlayIfId` | SAI グローバル（ルータ IF OID） | READ | `NvgreTunnel` 構築時に `sai_create_tunnel(..., gUnderlayIfId)` でアンダーレイ [RIF](../../reference/glossary.md#term-rif) として渡す。orchagent 起動時にグローバル初期化されたオブジェクト | `nvgreorch.cpp:312` |
| `gVirtualRouterId` | SAI グローバル（デフォルト VR OID） | READ | `sai_create_tunnel_termination(..., gVirtualRouterId)` でトンネル終端のデフォルト [VRF](../../reference/glossary.md#term-vrf) を指定 | `nvgreorch.cpp:313` |

### 依存解決タイミング

- **`NVGRE_TUNNEL` → `NVGRE_TUNNEL_MAP`**: `NvgreTunnelMapOrch` は親トンネルを `isTunnelExists()` でチェックするが、未登録時に retry キューへ戻さず即廃棄する。よって `NVGRE_TUNNEL` の SET が orchagent で処理完了してから `NVGRE_TUNNEL_MAP` を書き込む必要がある（ordering 参照）。
- **`VLAN` 参照**: `gPortsOrch->getVlanByVlanId()` は PortsOrch 内部の VLAN マップを参照する。`VLAN` テーブルの SET が PortsOrch により処理完了していない場合、MAP エントリは永続的に失われる。
- **`gUnderlayIfId` / `gVirtualRouterId`**: orchagent 起動時に `main.cpp` が SAI を初期化して設定するグローバル値。これらは orchagent が稼動していれば常に有効であり、ユーザーが CONFIG_DB に書き込む前提条件にはならない。

<!-- /cross-refs -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: meta/_intermediate/cdb-flow/nvgre-tunnel.md -->

### YANG スキーマ検証
- `src_ip` は mandatory (`inet:ip-address`)。未設定またはフォーマット不正は YANG validate で reject。
- `vlan_id` は uint16 (1..4094)、`vsid` は uint32 (0..16777214)。範囲外は YANG 段階で拒否。
- `NVGRE_TUNNEL_MAP.tunnel_name` は `NVGRE_TUNNEL` への leafref。親トンネルが存在しない場合は reject。

### consumer (nvgreorch) 例外動作
- 重複 SET: `NVGRE tunnel '%s' already exists` → WARN ログ、処理スキップ。
- 存在しない親トンネルへの MAP 追加: `NVGRE tunnel '%s' doesn't exist` → WARN。
- `vlan_id` 未登録: `VLAN ID doesn't exist: %d` → WARN。
- `vsid` 範囲外: `VSID is invalid: %d` → WARN。
- SAI オブジェクト生成失敗: `std::runtime_error` throw → orchagent クラッシュ扱い。
- DEL で存在しない tunnel/map: WARN ログ、処理スキップ。

<!-- /cdb-exceptions -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-nvgre-tunnel`](../yang/sonic-nvgre-tunnel.md)
- CLI: `config nvgre`

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-nvgre-tunnel.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-nvgre-tunnel.yang>

## 関連ページ
- [CONFIG_DB: VXLAN_TUNNEL](vxlan-tunnel.md)
- [CONFIG_DB: VLAN](vlan.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `NVGRE_TUNNEL|<name>` / `NVGRE_TUNNEL_MAP|<tunnel>|<map_entry>`。
- `src_ip`: ローカル [VTEP](../../reference/glossary.md#term-vtep) の loopback アドレス。
- `vsid`: 24bit (0..16777214)、`vlan_id`: 1..4094。

### よくある誤設定

- `src_ip` がローカル IP として実在しない (Loopback 未設定) ためトンネルが up しない。
- `VXLAN_TUNNEL` と `NVGRE_TUNNEL` を同一スイッチで併用し、orch が想定外動作。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'NVGRE_TUNNEL*'
sonic-db-cli ASIC_DB keys 'ASIC_STATE:SAI_OBJECT_TYPE_TUNNEL:*'
```
<!-- /ops-hint -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / NvgreTunnelOrch + NvgreTunnelMapOrch**: `NVGRE_TUNNEL` / `NVGRE_TUNNEL_MAP` テーブルを `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- NvgreTunnelOrch がエントリを解析し APP_DB `TUNNEL_DECAP_TABLE` に書き込む (一部実装)。
- 実装は VS/仮想 [ASIC](../../reference/glossary.md#term-asic) 向けが主体で、物理 [ASIC](../../reference/glossary.md#term-asic) サポートはベンダー依存。

### 段階 3: APPL → SAI

- orchagent から SAI `sai_tunnel_api->create_tunnel()` を呼び出して NVGRE デカプセルトンネルを作成。
- SAI_TUNNEL_TYPE_NVGRE を使用。

### 段階 4: タイミング + 副作用

- トンネル作成は orchagent が処理を受け取った数 ms 以内。
- 副作用: 対応する SAI サポートが必要。非サポート [ASIC](../../reference/glossary.md#term-asic) では task_failed となる。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

NVGRE_TUNNEL / NVGRE_TUNNEL_MAP テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config nvgre_tunnel add/del ...` — `config/plugins/nvgre_tunnel.py` が `set_entry()` を呼ぶ ([sonic-utilities](../../reference/glossary.md#term-sonic-utilities)/config/plugins/nvgre_tunnel.py)

### minigraph / sonic-cfggen

minigraph.py に NVGRE_TUNNEL 生成なし

### REST / gNMI

REST/[gNMI](../../reference/glossary.md#term-gnmi) 書き込み経路なし

### db_migrator

db_migrator.py での NVGRE マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- glossary-links-injected: 91a36a875109 -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

minigraph.py および init_cfg.json.j2 からの `NVGRE_TUNNEL` 自動派生はなし。CLI (`config nvgre-tunnel`) または RESTCONF 経由での手動設定のみ。

### Phase 7: 条件付き登録

| 条件 | 影響 | ソース |
|---|---|---|
| `NvgreTunnelOrch` は常時登録 (platform 非依存) | `CFG_NVGRE_TUNNEL_TABLE_NAME` を無条件で購読 | `orchdaemon.cpp:361` |
| `NvgreTunnelMapOrch` は常時登録 (platform 非依存) | `CFG_NVGRE_TUNNEL_MAP_TABLE_NAME` を無条件で購読 | `orchdaemon.cpp:363` |
| `NvgreTunnelOrch` は `Orch2` ベース (request_parser 使用) | `addOperation()`/`delOperation()` で処理 (allPortsReady guard なし) | `sonic-swss/orchagent/nvgreorch.cpp:350-385` |

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| NvgreTunnelOrch 登録 | 1 | `orchdaemon.cpp:361` |
| addOperation entry point | 1 | `nvgreorch.cpp:350` |

<!-- /derivation -->

<!-- failure -->
## 失敗挙動 (Phase D)

<!-- evidence: sonic-swss/orchagent/nvgreorch.cpp:106,124,190,207,253,270,325-327,357-360,376-377,438,473-474,482-483,491-492,498-499,527,539-543,565-566,571-573 -->

`NVGRE_TUNNEL` / `NVGRE_TUNNEL_MAP` のエントリ書き込みに関わる失敗シナリオを一覧化する。`NvgreTunnelOrch` および `NvgreTunnelMapOrch` は `Orch2` フレームワークを使用し、`addOperation()` / `delOperation()` が `true` を返せばエントリ消費完了（リトライなし）、`false` を返せばキュー再投入（リトライあり）となる。

### 失敗シナリオ一覧

| # | 操作 | 失敗トリガー | 挙動 | ログ | リトライ |
|---|------|------------|------|------|---------|
| 1 | SET `NVGRE_TUNNEL` | 同名トンネルがすでに存在 | WARN ログ + `return true` (消費完了) | `SWSS_LOG_WARN("NVGRE tunnel '%s' already exists")` `nvgreorch.cpp:359` | なし |
| 2 | SET `NVGRE_TUNNEL` | SAI `create_tunnel_map()` 失敗 (非 `SAI_STATUS_SUCCESS`) | `std::runtime_error` throw → `NvgreTunnel` コンストラクタがクラッシュ → orchagent プロセス abort | `nvgreorch.cpp:106` | orchagent 再起動後に再処理 |
| 3 | SET `NVGRE_TUNNEL` | SAI `create_tunnel()` 失敗 | `std::runtime_error` throw → orchagent abort | `nvgreorch.cpp:190` | orchagent 再起動後に再処理 |
| 4 | SET `NVGRE_TUNNEL` | SAI `create_tunnel_termination()` 失敗 | `std::runtime_error` throw → orchagent abort | `nvgreorch.cpp:253` | orchagent 再起動後に再処理 |
| 5 | DEL `NVGRE_TUNNEL` | 存在しないトンネルを削除 | ERROR ログ + `return true` (消費完了) | `SWSS_LOG_ERROR("NVGRE tunnel '%s' doesn't exist")` `nvgreorch.cpp:376` | なし |
| 6 | DEL `NVGRE_TUNNEL` | SAI `remove_tunnel_termination()` / `remove_tunnel()` 失敗 | `std::runtime_error` が `removeNvgreTunnel()` 内でキャッチされ `SWSS_LOG_ERROR` のみ。エラーを飲み込んで処理を継続する | `SWSS_LOG_ERROR("Error while removing tunnel entry …")` `nvgreorch.cpp:325-327` | なし (エラー消費) |
| 7 | SET `NVGRE_TUNNEL_MAP` | 親トンネルが未登録 | WARN ログ + `return true` (消費完了、**永続破棄**) | `SWSS_LOG_WARN("NVGRE tunnel '%s' doesn't exist")` `nvgreorch.cpp:473` | なし — 再投入されない |
| 8 | SET `NVGRE_TUNNEL_MAP` | 同名マップエントリがすでに存在 | WARN ログ + `return true` (消費完了) | `SWSS_LOG_WARN("NVGRE tunnel map '%s' already exist")` `nvgreorch.cpp:482` | なし |
| 9 | SET `NVGRE_TUNNEL_MAP` | 指定 `vlan_id` が PortsOrch に未登録 | WARN ログ + `return true` (消費完了、**永続破棄**) | `SWSS_LOG_WARN("VLAN ID doesn't exist: %d")` `nvgreorch.cpp:491` | なし — VLAN 登録後に再投入が必要 |
| 10 | SET `NVGRE_TUNNEL_MAP` | `vsid` が範囲外 (> 16777214) | WARN ログ + `return true` (消費完了) | `SWSS_LOG_WARN("VSID is invalid: %d")` `nvgreorch.cpp:498` | なし |
| 11 | SET `NVGRE_TUNNEL_MAP` | SAI `create_tunnel_map_entry()` 失敗 | `std::runtime_error` throw → orchagent abort | `nvgreorch.cpp:438` | orchagent 再起動後に再処理 |
| 12 | DEL `NVGRE_TUNNEL_MAP` | 親トンネルが存在しない | WARN ログ + `return true` (消費完了) | `SWSS_LOG_WARN("NVGRE tunnel '%s' does not exist")` `nvgreorch.cpp:565` | なし |
| 13 | DEL `NVGRE_TUNNEL_MAP` | 指定マップエントリが存在しない | WARN ログ + `return true` (消費完了) | `SWSS_LOG_WARN("NVGRE tunnel map '%s' does not exist")` `nvgreorch.cpp:571` | なし |
| 14 | DEL `NVGRE_TUNNEL_MAP` | SAI `remove_tunnel_map_entry()` 失敗 | `std::runtime_error` が `delMapperEntry()` 内でキャッチされ `SWSS_LOG_ERROR` 後 `false` を返す。`delOperation()` は `return true` で消費完了扱い | `SWSS_LOG_ERROR("Error while removing decap tunnel map …")` `nvgreorch.cpp:539-543` | なし (エラー消費) |

### 重要な設計特性

**`return true` による永続廃棄 (シナリオ 7、9)**:
`NvgreTunnelMapOrch` は親トンネル未登録 (シナリオ 7) および VLAN 未登録 (シナリオ 9) のいずれの場合も `return true` を返してエントリを**永続廃棄**する。`Orch2` フレームワークでは `true` = 消費完了のためキューへ再投入されない。これらの条件が解消された後も MAP エントリは自動復旧しない。`NVGRE_TUNNEL` SET が orchagent 処理完了した後に `NVGRE_TUNNEL_MAP` を書き込む手順を守ることで回避できる（Phase B 参照）。

**SAI 操作失敗は orchagent abort (シナリオ 2–4、11)**:
SAI 呼び出し (`sai_tunnel_api->create_tunnel_map / create_tunnel / create_tunnel_termination / create_tunnel_map_entry`) が `SAI_STATUS_SUCCESS` 以外を返すと `std::runtime_error` がスローされる。`NvgreTunnelOrch::addOperation()` には catch ブロックが存在しないため、例外はスタックを伝播して orchagent プロセスを abort させる。systemd の自動再起動後に orchagent が CONFIG_DB を再読み込みして再処理する。

**DEL の SAI 失敗はエラーを飲み込む (シナリオ 6、14)**:
削除操作 (`removeNvgreTunnel()` / `delMapperEntry()`) は `std::runtime_error` を catch してログ出力後に処理を継続 / `false` を返す。`delOperation()` は `return true` で消費完了扱いにするため、SAI 上でオブジェクトが残留する可能性がある。

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

<!-- evidence: meta/_intermediate/cdb-flow/nvgre-tunnel-constants.md -->

`sonic-swss/orchagent/nvgreorch.cpp` および `nvgreorch.h` を全行調査して検出した、CONFIG_DB / YANG では管理されないハードコード定数の一覧。

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `NVGRE_VSID_MAX_VALUE` | `16777214` (2^24 − 2) | `NvgreTunnelMapOrch::addOperation()` で `vsid > NVGRE_VSID_MAX_VALUE` チェックに使用。RFC 7637 で定義される 24bit VSID の最大値 | `nvgreorch.cpp:7, 496` |
| MAP タイプセット | `{ MAP_T_VLAN, MAP_T_BRIDGE }` (固定 2 種) | `NvgreTunnel` 構築時に Encap + Decap 計 4 個のマッパーオブジェクトを常時作成。ユーザー設定で変更不可 | `nvgreorch.cpp:16-19` |
| SAI トンネルタイプ | `SAI_TUNNEL_TYPE_NVGRE` | `sai_create_tunnel()` の type 引数として固定 | `nvgreorch.cpp:177` |
| SAI termination タイプ | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP` | `sai_create_tunnel_termination()` の type 引数として固定 (NVGRE は常に P2MP) | `nvgreorch.cpp:241` |
| `gUnderlayIfId` | orchagent 起動時に `main.cpp` が SAI 初期化で確定するグローバル [RIF](../../reference/glossary.md#term-rif) OID | `sai_create_tunnel()` の underlay RIF 引数として渡す | `nvgreorch.cpp:312` |
| `gVirtualRouterId` | orchagent 起動時に `main.cpp` が SAI 初期化で確定するデフォルト VR OID | `sai_create_tunnel_termination()` の VR OID 引数として渡す | `nvgreorch.cpp:313` |

### 補足

- `NVGRE_VSID_MAX_VALUE = 16777214` は YANG の `vsid` range (`0..16777214`) と一致しており、orchagent 側は YANG validate を通過した値をさらにコード上で再チェックする二段構えになっている。
- MAP タイプは `MAP_T_VLAN` と `MAP_T_BRIDGE` の 2 種が常に作成される。これは `nvgreMapTypes` static 定数で宣言されており、実行時に変更する手段はない。
- `gUnderlayIfId` / `gVirtualRouterId` はユーザーが CONFIG_DB に書き込む前提条件にはならない（orchagent が稼動していれば常に有効）が、orchagent 未起動時は NVGRE トンネル設定を処理できない。

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

> 調査対象: `sonic-swss/orchagent/nvgreorch.cpp`, `sonic-swss/orchagent/orchdaemon.cpp`
> 調査日: 2026-05-19

`NVGRE_TUNNEL` / `NVGRE_TUNNEL_MAP` の SET/DEL が orchagent を経由して引き起こす CONFIG_DB 以外への書込みを示す。

### ASIC_DB — SAI オブジェクト生成 (orchagent)

`NvgreTunnelOrch` は CONFIG_DB の変化を直接 SAI API 呼び出しに変換し、[ASIC_DB](../../reference/glossary.md#term-asic_db) に SAI オブジェクトを作成する。[syncd](../../reference/glossary.md#term-syncd) が [ASIC_DB](../../reference/glossary.md#term-asic_db) の変化を検知して実ハードウェアに反映する。

| 操作 | 書込先 DB | SAI API / テーブル | 生成オブジェクト | ソース |
|---|---|---|---|---|
| SET `NVGRE_TUNNEL` | [ASIC_DB](../../reference/glossary.md#term-asic_db) | `sai_tunnel_map_api->create_tunnel_map()` ×4 | `SAI_OBJECT_TYPE_TUNNEL_MAP` (VLAN/BRIDGE 各 2 個: encap + decap) | `nvgreorch.cpp:106-155` |
| SET `NVGRE_TUNNEL` | ASIC_DB | `sai_tunnel_api->create_tunnel()` | `SAI_OBJECT_TYPE_TUNNEL` (type=NVGRE) | `nvgreorch.cpp:177-205` |
| SET `NVGRE_TUNNEL` | ASIC_DB | `sai_tunnel_api->create_tunnel_term_table_entry()` | `SAI_OBJECT_TYPE_TUNNEL_TERM_TABLE_ENTRY` (P2MP) | `nvgreorch.cpp:235-261` |
| SET `NVGRE_TUNNEL_MAP` | ASIC_DB | `sai_tunnel_map_api->create_tunnel_map_entry()` | `SAI_OBJECT_TYPE_TUNNEL_MAP_ENTRY` (VLAN ↔ VSID) | `nvgreorch.cpp:415-441` |
| DEL `NVGRE_TUNNEL` | ASIC_DB | `sai_tunnel_api->remove_tunnel_term_table_entry()` / `remove_tunnel()` / `sai_tunnel_map_api->remove_tunnel_map()` | 上記 SAI オブジェクトの削除 | `nvgreorch.cpp:282-330` |
| DEL `NVGRE_TUNNEL_MAP` | ASIC_DB | `sai_tunnel_map_api->remove_tunnel_map_entry()` | `SAI_OBJECT_TYPE_TUNNEL_MAP_ENTRY` の削除 | `nvgreorch.cpp:530-544` |

### APPL_DB / STATE_DB への書込み

`NvgreTunnelOrch` / `NvgreTunnelMapOrch` は [APPL_DB](../../reference/glossary.md#term-appl_db) や [STATE_DB](../../reference/glossary.md#term-state_db) への書込みを行わない。

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| [APPL_DB](../../reference/glossary.md#term-appl_db) | なし | `nvgreorch.cpp` 全行に [ProducerStateTable](../../reference/glossary.md#term-producerstatetable) / AppTable 書込なし |
| [STATE_DB](../../reference/glossary.md#term-state_db) | なし | `nvgreorch.cpp` 全行に StateTable 書込なし |
| [COUNTERS_DB](../../reference/glossary.md#term-counters_db) | なし | NVGRE トンネル統計は別経路（[FlexCounter](../../reference/glossary.md#term-flexcounter)）で管理されるが nvgreorch.cpp は [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) に直接書込みなし |

### FLEX_COUNTER_DB への書込み

`NvgreTunnelOrch` は [FlexCounter](../../reference/glossary.md#term-flexcounter) への登録を行わない（`nvgreorch.cpp` に `addFlexCounter` / `FLEX_COUNTER_DB` 参照なし）。NVGRE トンネルのトラフィック統計はハードウェアサポート依存であり、[SONiC](../../reference/glossary.md#term-sonic) の [FlexCounter](../../reference/glossary.md#term-flexcounter) フレームワーク経由では管理されない。

詳細スキャン証跡: `meta/_intermediate/cdb-flow/nvgre-tunnel-side-effects.md`
<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

> 調査証跡: `meta/_intermediate/cdb-flow/nvgre-tunnel-pubsub.md`
> ソース: `sonic-swss/orchagent/orchdaemon.cpp` L361-364; `sonic-swss/orchagent/nvgreorch.h` L115,155; `sonic-swss/orchagent/orch.h` L389-410

### 購読チャンネル一覧

`NVGRE_TUNNEL` / `NVGRE_TUNNEL_MAP` は **CONFIG_DB 経路のみ**を持ち、[APPL_DB](../../reference/glossary.md#term-appl_db) 経由の購読チャンネルは存在しない。

| 区間 | DB | テーブル名 | 購読クラス | 発行元 |
|---|---|---|---|---|
| CLI/CONFIG_DB → NvgreTunnelOrch | CONFIG_DB (dbId=4) | `NVGRE_TUNNEL` (`CFG_NVGRE_TUNNEL_TABLE_NAME`) | `SubscriberStateTable` | `config nvgre-tunnel add/del ...` (`sonic-utilities/config/plugins/nvgre_tunnel.py`) |
| CLI/CONFIG_DB → NvgreTunnelMapOrch | CONFIG_DB (dbId=4) | `NVGRE_TUNNEL_MAP` (`CFG_NVGRE_TUNNEL_MAP_TABLE_NAME`) | `SubscriberStateTable` | 同上 |
| NvgreTunnelOrch/MapOrch → [syncd](../../reference/glossary.md#term-syncd) | ASIC_DB ([syncd](../../reference/glossary.md#term-syncd) 経由) | — | SAI API 直接呼び出し | `sai_tunnel_api->create_tunnel()` / `create_tunnel_map_entry()` 等 |

### 登録経路

`orchdaemon.cpp:361` で `NvgreTunnelOrch(m_configDb, CFG_NVGRE_TUNNEL_TABLE_NAME)`、`orchdaemon.cpp:363` で `NvgreTunnelMapOrch(m_configDb, CFG_NVGRE_TUNNEL_MAP_TABLE_NAME)` を構築する。両クラスは `Orch2` ベース (`nvgreorch.h:115,155`)。`Orch2` コンストラクタが `Orch(db, tableName)` を呼び (`orch.h:392-395`)、`Orch::addConsumer()` (`orch.cpp:1186-1196`) が `m_configDb` の DB ID = CONFIG_DB を検出して `SubscriberStateTable` を選択する。

### SubscriberStateTable の動作

[Redis](../../reference/glossary.md#term-redis) keyspace 通知 `PSUBSCRIBE __keyspace@4__:NVGRE_TUNNEL|*` / `__keyspace@4__:NVGRE_TUNNEL_MAP|*` を購読。CONFIG_DB への `HSET "NVGRE_TUNNEL|<name>" ...` が PUBLISH されると `Orch2::doTask(Consumer&)` が `addOperation()` / `delOperation()` を呼ぶ。

keyspace 通知のペイロードは [Redis](../../reference/glossary.md#term-redis) 操作名のみ。フィールド値は通知後に `HGETALL` で別途取得する (`subscriberstatetable.cpp:95-`)。

**起動時スナップショット**: `SubscriberStateTable` ctor は PSUBSCRIBE 直後に既存エントリを `SET_COMMAND` として buffer に充填する (`subscriberstatetable.cpp:26-44`)。orchagent 再起動時に CONFIG_DB に残存する `NVGRE_TUNNEL|*` / `NVGRE_TUNNEL_MAP|*` エントリは遅延なく再配信され、`NvgreTunnelOrch` / `NvgreTunnelMapOrch` が再設定を実行する。

### ProducerStateTable は不使用

CONFIG_DB 経路では `ProducerStateTable` を使用しない。CLI (`sonic-utilities/config/plugins/nvgre_tunnel.py`) は `ConfigDBConnector.set_entry()` → 直接 [Redis](../../reference/glossary.md#term-redis) `HSET` で書き込む。APPL_DB への中継テーブルは存在せず、`NVGRE_TUNNEL` / `NVGRE_TUNNEL_MAP` の変更は常に CONFIG_DB → `SubscriberStateTable` → NvgreTunnelOrch → SAI の経路を通る。

### orchList 内の位置

`orchdaemon.cpp:598-599` で `m_orchList.push_back(nvgre_tunnel_orch)` / `m_orchList.push_back(nvgre_tunnel_map_orch)` が末尾に追加される。`gPortsOrch`（`m_orchList` の上位）への依存は `allPortsReady` ガードではなく `gPortsOrch->getVlanByVlanId()` の直接呼び出しで表現される (Phase B 参照)。

<!-- /pubsub -->

<!-- platform -->
## プラットフォーム差 (Phase H)

<!-- evidence: meta/_intermediate/cdb-flow/nvgre-tunnel-platform.md -->

`NvgreTunnelOrch` / `NvgreTunnelMapOrch` は**全プラットフォームで同一の動作**をする。`orchdaemon.cpp:361-364` で両 Orch が無条件にインスタンス化されており、`platform` 変数や SAI capability 照会による条件分岐はゼロ。

### プラットフォーム依存ゼロの証跡

`nvgreorch.cpp` 全 582 行・`nvgreorch.h` 全行を `platform|broadcom|mellanox|barefoot|cisco|namespace|multi_asic` でスキャンしたがヒット 0 件。`orchdaemon.cpp:190` で `platform = getenv("platform")` を読み込むが、直後の NVGRE orch 生成 (L361-364) は `if (platform == ...)` の外側にある無条件ブロックである。L503 以降の platform 分岐（DTEL / FlexCounter / [QoS](../../reference/glossary.md#term-qos) 制御）は NVGRE に関与しない。

### multi-asic / VOQ chassis

multi-asic 構成では orchagent が `asic0`/`asic1`/... ごとに独立起動するが、各インスタンスが同じ無条件経路を通るため namespace 間で挙動差はない。NVGRE_TUNNEL テーブルは per-asic CONFIG_DB に書かれた分だけ各 orchagent が処理する。[VOQ](../../reference/glossary.md#term-voq) chassis でも特別なガードは存在しない。

### SAI 実装依存性（プラットフォーム間の実質的な差）

`NvgreTunnelOrch` は SAI capability を事前照会しない。`create_tunnel(SAI_TUNNEL_TYPE_NVGRE)` が成功するかどうかはハードウェア SAI 実装依存である。非サポート ASIC では SAI が非 `SAI_STATUS_SUCCESS` を返して `std::runtime_error` がスローされ orchagent が abort する（Phase D シナリオ 2–4 参照）。コードレベルでの ASIC 種別チェックはないため、サポート可否はハードウェアベンダーの SAI 実装に委ねられる。

| 項目 | 状況 |
|------|------|
| orchagent コードの platform 分岐 | なし |
| SAI capability 事前照会 | なし |
| multi-asic での挙動差 | なし（各 orchagent が同一処理） |
| 非サポート ASIC での帰結 | orchagent abort（SAI 失敗 → runtime_error） |
| VS (仮想 ASIC) | テスト (`test_nvgre_tunnel.py`) が VS 上で動作確認済み |

<!-- /platform -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

`NvgreTunnelOrch::addOperation()` の分岐:

| Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `NvgreTunnelOrch` | `addOperation()` | `isTunnelExists(tunnel_name)` = true | WARN ログ + `return true` (冪等、エラーなし) | `sonic-swss/orchagent/nvgreorch.cpp:357-361` |
| `NvgreTunnelOrch` | `addOperation()` | `isTunnelExists(tunnel_name)` = false | 新規 `NvgreTunnel` オブジェクトを作成して SAI トンネルを設定 | `nvgreorch.cpp:363` |
| `NvgreTunnelOrch` | `delOperation()` | `!isTunnelExists(tunnel_name)` | ERROR ログ + `return true` (冪等) | `nvgreorch.cpp:374-378` |

> **スキャン証跡**: `nvgreorch.cpp:350-385` を全行読了、3 件分岐抽出。minigraph.py からの自動派生なしを確認 — 誤読なし。

<!-- /handler-branching -->

<!-- glossary-links-injected: ff34a209121d -->
