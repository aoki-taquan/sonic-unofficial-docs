---
title: TUNNEL_DECAP_TABLE (APPL_DB)
description: TUNNEL_DECAP_TABLE — tunneldecaporch が消費する アプリケーション層テーブル。CONFIG_DB の TUNNEL を tunnelmgrd が APPL_DB に投影する形で生成され、SAI tunnel/tunnel-term オブジェクトに反映される。
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/sonic-swss-common
  path: common/schema.h
  ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
- repo: sonic-net/sonic-swss
  path: orchagent/tunneldecaporch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
  - TUNNEL
  - TUNNEL_DECAP_TABLE
  cli: []
  yang:
  - sonic-tunnel
  - sonic-vxlan
---

# TUNNEL_DECAP_TABLE

!!! warning "YANG 未定義"
    `TUNNEL_DECAP_TABLE` は CONFIG_DB ではなく **APPL_DB / STATE_DB** のテーブルであり、`sonic-yang-models` には対応モジュールが存在しない。本ページは `schema.h` のテーブル名定数と `tunneldecaporch.cpp` の実装からフィールドを起こしたもの。CONFIG_DB に同名テーブルを直接書くことは想定されていない。

## 概要

`tunneldecaporch` が消費する **アプリケーション層テーブル**。[CONFIG_DB](../../reference/glossary.md#term-config_db) の [`TUNNEL`](./tunnel.md) を `tunnelmgrd` が [APPL_DB](../../reference/glossary.md#term-appl_db) に投影する形で生成され、[SAI](../../reference/glossary.md#term-sai) tunnel/tunnel-term オブジェクトに反映される[^1]。[STATE_DB](../../reference/glossary.md#term-state_db) にも同名のミラーがある。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>TUNNEL")]
  TMGR["tunnelmgrd"]
  CDB --> TMGR
  APPDB[("APPL_DB<br/>TUNNEL_DECAP_TABLE")]
  TMGR --> APPDB
  ORCH["orchagent<br/>TunnelDecapOrch"]
  APPDB --> ORCH
  SAI["SAI<br/>sai_tunnel_api"]
  ORCH --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## DB / key

```yaml
APPL_DB:   TUNNEL_DECAP_TABLE:<tunnel_name>
STATE_DB:  TUNNEL_DECAP_TABLE|<tunnel_name>
APPL_DB:   TUNNEL_DECAP_TERM_TABLE:<tunnel_name>:<dst_ip>   # 終端 IP の管理用 sub テーブル
```

テーブル名定数は `schema.h` の `APP_TUNNEL_DECAP_TABLE_NAME` / `APP_TUNNEL_DECAP_TERM_TABLE_NAME` / `STATE_TUNNEL_DECAP_TABLE_NAME` / `STATE_TUNNEL_DECAP_TERM_TABLE_NAME`[^2]。

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `tunnel_type` | string `IPINIP` | カプセル化種別。それ以外はエラー |
| `src_ip` | IPv4 アドレス | トンネル送信元 IP |
| `dst_ip` | IPv4 アドレスのカンマ区切りリスト | 終端 IP 群（`TUNNEL_DECAP_TERM_TABLE` で個別管理） |
| `dscp_mode` | string `uniform`/`pipe` | [DSCP](../../reference/glossary.md#term-dscp) 継承 |
| `ecn_mode` | string `copy_from_outer`/`standard` | ECN モード（create-only） |
| `encap_ecn_mode` | string `standard` | カプセル時 ECN |
| `ttl_mode` | string `uniform`/`pipe` | TTL モード |
| `decap_dscp_to_tc_map` | string | [DSCP](../../reference/glossary.md#term-dscp)→TC マップ名（OID 解決） |
| `decap_tc_to_pg_map` | string | TC→PG マップ名 |
| `encap_tc_to_dscp_map` | string | TC→[DSCP](../../reference/glossary.md#term-dscp) マップ名 |
| `encap_tc_to_queue_map` | string | TC→Queue マップ名 |

## 制約

- `tunnel_type` は `IPINIP` のみ受け入れる（`tunneldecaporch.cpp` でハードコード）
- `ecn_mode` は [SAI](../../reference/glossary.md#term-sai) `SAI_TUNNEL_ATTR_DECAP_ECN_MODE` が create-only のため、生成後の更新はスキップされる旨が WARN ログで残る

## 購読者

- `tunneldecaporch` ([orchagent](../../reference/glossary.md#term-orchagent)): [SAI](../../reference/glossary.md#term-sai) tunnel / tunnel-term オブジェクト作成
- `STATE_DB` 側はモニタリング用ミラー

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): [`TUNNEL`](./tunnel.md)（[CONFIG_DB](../../reference/glossary.md#term-config_db) 側のソース）
- 関連 [YANG](../../reference/glossary.md#term-yang): なし
- 関連 CLI: なし（テーブルは内部）

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連リンクなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: tunneldecaporch 実装: `tunneldecaporch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/tunneldecaporch.cpp>
[^2]: テーブル名定数: `schema.h`. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h#L49-L50>

<!-- value-behavior -->
## 値依存挙動マトリクス

`tunnel_type` / `dscp_mode` / `ecn_mode` / `ttl_mode` は [YANG](../../reference/glossary.md#term-yang) 未定義 ([APPL_DB](../../reference/glossary.md#term-appl_db) テーブル) のため string 型。制約は `tunneldecaporch.cpp` のコード判定。

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `tunnel_type` | `IPINIP` | SAI tunnel + tunnel-term オブジェクトを作成 |
| `tunnel_type` | `IPINIP` 以外 | LOG_ERROR してエントリをスキップ |
| `dscp_mode` | `uniform` | 外側 DSCP を内側にコピー |
| `dscp_mode` | `pipe` | 内側 DSCP を保持 |
| `dscp_mode` | 上記以外 | LOG_ERROR してエントリをスキップ |
| `ecn_mode` | `copy_from_outer` | 外側 ECN を内側にコピー |
| `ecn_mode` | `standard` | RFC 6040 ECN 処理 |
| `encap_ecn_mode` | `standard` 以外 | LOG_ERROR して拒否 |
| `ecn_mode` | 作成後に変更 | SAI create-only 属性のため変更スキップ (WARN ログ) |
| `ttl_mode` | `uniform` | 外側 TTL を内側にコピー |
| `ttl_mode` | `pipe` | 内側 TTL を保持 |
| `src_ip` | 作成後に変更 | LOG_ERROR して拒否。削除→再作成が必要 |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-swss/orchagent/tunneldecaporch.cpp@4305596156d70e9797e8a881b3d19b46de0bce0d L51-697 -->

- **`src_ip` の変更不可**: 既存トンネルの `src_ip` を変更しようとすると `"cannot modify src ip for existing tunnel"` を LOG_ERROR して拒否する。変更するにはトンネルを削除して再作成する必要がある。
- **無効な tunnel_type / dscp_mode / ecn_mode / ttl_mode**: 有効値以外の文字列が来ると `"Invalid tunnel type/dscp mode/ecn mode/ttl mode <value>"` を LOG_ERROR してエントリをスキップする。
- **encap_ecn_mode は `standard` のみ対応**: `ecn_mode` が `standard` 以外の場合 `"Only standard encap ecn mode is supported currently"` を LOG_ERROR して拒否。
- **存在しないトンネルの DEL**: 未作成のトンネルへの DEL は `"Tunnel <key> cannot be removed since it doesn't exist."` を LOG_ERROR する。
- **subnet decap 制約**: subnet decap の decap term は `MP2MP` タイプのトンネルにのみ許可される。`src_ip` / `src_ip_v6` なしで subnet decap term を追加しようとするとそれぞれ `"no source IP is provided."` を LOG_ERROR。
- **subnet decap 無効時の decap term**: `subnet_decap` が無効な状態で decap term を追加しようとすると `"subnet decap is disabled, ignored."` を LOG_ERROR してスキップ。
- **[ASIC_DB](../../reference/glossary.md#term-asic_db) 操作失敗**: トンネルや decap term の [ASIC_DB](../../reference/glossary.md#term-asic_db) 追加/削除が失敗するとそれぞれエラーを LOG_ERROR する。

<!-- /cdb-exceptions -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `TUNNEL_DECAP_TABLE|<tunnel-name>`。
- `tunnel_type`: `IPINIP` / `VXLAN`、`dst_ip`: 自 Loopback、`ttl_mode`/`dscp_mode`: `uniform`。

### よくある誤設定

- dst_ip を物理 IF アドレスに向けてしまい、IF down で decap も停止する。Loopback を使う。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'TUNNEL_DECAP_TABLE|*'
```
<!-- /ops-hint -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

tunneldecaporch が `src_ip` フィールドの有無から SAI term entry type を自動決定する。`src_ip` あり → `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2P`、なし → `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP`。`dscp_mode` / `ttl_mode` の値が SAI enum に自動変換される。

### Phase 7: 条件付き登録 (add_manager 条件)

tunneldecaporch は常時登録し `TUNNEL_DECAP_TABLE` テーブルを無条件購読する。SAI tunnel capability 未サポートの場合は SAI 属性設定がエラーになるがログのみで継続。

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `tunneldecaporch` | `tunnel_type==IPINIP` | SAI_TUNNEL_TYPE_IPINIP を使用 | `tunnelorch.cpp` |
| `tunneldecaporch` | `tunnel_type==VXLAN` | SAI_TUNNEL_TYPE_VXLAN を使用 | `tunnelorch.cpp` |
| `tunneldecaporch` | `dscp_mode==pipe` | pipe model で DSCP を設定 | `tunnelorch.cpp` |
| `tunneldecaporch` | `dscp_mode==uniform` | uniform model で DSCP を伝播 | `tunnelorch.cpp` |
| `tunneldecaporch` | `src_ip` あり | P2P term entry 作成 | `tunnelorch.cpp` |
| `tunneldecaporch` | `src_ip` なし | P2MP term entry 作成 (any source) | `tunnelorch.cpp` |
| `tunneldecaporch` | del_handler | SAI tunnel + term entry を削除 | `tunnelorch.cpp` |

> **スキャン証跡**: `TUNNEL_DECAP_TABLE` は IP-in-IP/[VXLAN](../../reference/glossary.md#term-vxlan) デカプセルトンネルの termination 設定。`src_ip` の有無が P2P/P2MP を自動決定する点が主要 Phase 6 派生。

<!-- /handler-branching -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **[orchagent](../../reference/glossary.md#term-orchagent) / TunnelDecapOrch** (`sonic-swss/orchagent/tunneldecaporch.cpp`): `TUNNEL_DECAP_TABLE` を `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- TunnelDecapOrch がトンネルタイプ (IPINIP) と内側/外側 IP 情報を解析。
- APP_DB への書き込みなし ([orchagent](../../reference/glossary.md#term-orchagent) → SAI 直接)。

### 段階 3: APPL → SAI

- TunnelDecapOrch が `sai_tunnel_api->create_tunnel()` / `create_tunnel_term_table_entry()` を呼び出し IP-in-IP デカプセルトンネルをハードウェアに設定。

### 段階 4: タイミング + 副作用

- トンネル作成は orchagent 処理後数 ms 以内。
- 副作用: 内側 IP アドレスの重複がある場合 SAI が resource エラーを返す。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

TUNNEL_DECAP_TABLE テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし — `config load` または minigraph 経由

### minigraph / sonic-cfggen

minigraph.py に TUNNEL_DECAP_TABLE 直接生成なし

### REST / gNMI

REST/[gNMI](../../reference/glossary.md#term-gnmi) 書き込み経路なし

### db_migrator

**db_migrator.py** が TUNNEL_DECAP_TABLE のマイグレーション処理を実装 ([sonic-utilities](../../reference/glossary.md#term-sonic-utilities)/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

<!-- evidence: sonic-swss/orchagent/tunneldecaporch.cpp@4305596156d70e9797e8a881b3d19b46de0bce0d + tunneldecaporch.h -->

### ハードコード定数（フィールドで上書き不可）

| 定数 | 値 | 説明 |
|------|----|------|
| `OVERLAY_RIF_DEFAULT_MTU` | **9100** | デカプセル用オーバーレイ loopback [RIF](../../reference/glossary.md#term-rif) の MTU。フィールドとして公開されておらず変更不可 |
| subnet decap tunnel 名 | `"IPINIP_SUBNET"` / `"IPINIP_SUBNET_V6"` | `SubnetDecapConfig` にハードコード。ユーザーが別名を指定しても subnet decap 機能は動作しない |

### フィールド省略時の暗黙デフォルト

| フィールド | 省略時の挙動 |
|-----------|-------------|
| `src_ip` | `nullptr` として扱い `SAI_TUNNEL_ATTR_ENCAP_SRC_IP` をスキップ。P2MP タームが自動選択される |
| `decap_dscp_to_tc_map` | `SAI_NULL_OBJECT_ID` → SAI 属性をプッシュしない（[QoS](../../reference/glossary.md#term-qos) マップなし） |
| `decap_tc_to_pg_map` | 同上 |
| `encap_ecn_mode` | 空文字列 → `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` をスキップ（SAI デフォルト依存） |
| `term_type` (DECAP_TERM) | デフォルト `P2MP`（`TUNNEL_TERM_TYPE_P2MP`、`doDecapTunnelTermTask` 内変数初期値） |

### Dead-SAI フィールド（SAI に流れない）

`encap_tc_to_dscp_map` と `encap_tc_to_queue_map` は `addDecapTunnel()` に渡されず SAI には設定されない。内部 `tunnelTable` に記録され、**`muxorch` が `getQosMapId()` 経由で読み出すためだけに使用**される。tunnel decap の [QoS](../../reference/glossary.md#term-qos) には影響しない。

### Create-Only 属性（更新時スキップ）

| フィールド | 更新時の挙動 |
|-----------|------------|
| `ecn_mode` | 既存トンネルへの変更は `SAI_TUNNEL_ATTR_DECAP_ECN_MODE` が create-only のため WARN ログを出してスキップ、エントリ全体が再処理対象外になる |
| `encap_ecn_mode` | 同様に `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` が create-only。NOTICE ログでスキップ |

### 書込み順依存

- `allPortsReady()` が false の間は `doTask()` が即 return。ports 初期化前のエントリはキューに留まる。
- DECAP_TERM_TABLE エントリがトンネル本体より先に届いた場合、`unhandledDecapTerms` に蓄積され、トンネル作成成功後にまとめて処理される。

### Unknown フィールドによる Silent Drop

認識されないフィールド名が含まれると `LOG_ERROR` して **エントリ全体をスキップ**する。フィールド名の typo が設定欠落を引き起こす。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

TUNNEL_DECAP_TABLE エントリを書き込む際に守るべき順序制約を実装から導出した。

### 先行必須テーブル (SET 時)

| 依存テーブル | 理由 | 緩和策 | evidence |
|---|---|---|---|
| PortsOrch 初期化完了 (`allPortsReady()`) | `doTask()` が false の間即 return — TUNNEL_DECAP_TABLE / DECAP_TERM_TABLE ともにキュー待機 | なし（自動待機） | `tunneldecaporch.cpp:L55-57` |
| `CONFIG_DB TUNNEL` SET 済み | `tunnelmgrd` が TUNNEL を受け取って初めて [APPL_DB](../../reference/glossary.md#term-appl_db) へ投影。APPL_DB エントリは自動生成 | なし | `tunnelmgr.cpp:L263-293` |
| `LOOPBACK_INTERFACE\|Loopback3` IP 設定 | [tunnelmgrd](../../reference/glossary.md#term-tunnelmgrd) がトンネル IF への IP 付与に Loopback3 の IP を参照。未設定時は IP 付与スキップ | Loopback3 後付けで遅延付与される | `tunnelmgr.cpp:L337-348` |

### TUNNEL_DECAP_TABLE と TUNNEL_DECAP_TERM_TABLE の依存

| 操作 | 制約 | 理由 | evidence |
|---|---|---|---|
| TUNNEL_DECAP_TERM_TABLE SET | **TUNNEL_DECAP_TABLE より先に届いた term は `unhandledDecapTerms` に蓄積** | `tunnel_exists` が false のとき `addUnhandledDecapTunnelTerm()` に保留。トンネル本体作成成功後に `processUnhandledDecapTunnelTerms()` で一括処理される | `tunneldecaporch.cpp:L309,L513,L1497-1520` |
| SET の推奨順序 | `TUNNEL_DECAP_TABLE` SET → `TUNNEL_DECAP_TERM_TABLE` SET | 前後逆でも自動調停されるが、トンネル本体が先のほうがエラーログが出ない | — |

### SET / DEL 操作順序

| 操作 | 制約 | 理由 | evidence |
|---|---|---|---|
| `src_ip` の変更 | **DEL → SET の順が必須** | 既存トンネルの `src_ip` 更新は LOG_ERROR して拒否。変更には削除→再作成が必要 | `tunneldecaporch.cpp:L136` |
| `TUNNEL_DECAP_TABLE` の DEL | **TUNNEL_DECAP_TERM_TABLE を先に DEL** | tunneldecaporch はトンネル本体 DEL 時に term を自動削除しない。term 残存のままトンネル本体を削除すると SAI リソースリークの恐れがある | `tunneldecaporch.cpp` `removeDecapTunnel()` |

### warm-restart / cold-restart 影響

- `tunnelmgrd` は warm-restart 対応 (`replayDone` / `m_tunnelReplay`)。warm boot 時は APPL_DB への重複書き込みをスキップし orchagent クラッシュを防ぐ。
- `tunneldecaporch` は warm-restart 非対応。cold restart 後に CONFIG_DB 再 replay → [tunnelmgrd](../../reference/glossary.md#term-tunnelmgrd) が APPL_DB 再投影 → orchagent が SAI 再設定、という自動再構築フローで収束する。

!!! warning "src_ip の変更"
    既存トンネルの `src_ip` を変更する場合は `TUNNEL_DECAP_TABLE` エントリを必ず DEL してから SET し直すこと。SET のみでは `"cannot modify src ip for existing tunnel"` を LOG_ERROR してスキップされる (`tunneldecaporch.cpp`)。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`TUNNEL_DECAP_TABLE` エントリが APPL_DB に書かれると `tunneldecaporch` が以下のテーブル / リソースを暗黙的に参照する。
YANG leafref は存在せず、すべて実装コードのみに現れる暗黙依存。

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| `gVirtualRouterId`（デフォルト [VRF](../../reference/glossary.md#term-vrf) OID） | 読み取り（ハードコード） | TUNNEL_DECAP_TABLE SET 処理時、常時。overlay loopback [RIF](../../reference/glossary.md#term-rif) と tunnel term entry が常にデフォルト [VRF](../../reference/glossary.md#term-vrf) に紐付く | `tunneldecaporch.cpp` L23, L742 (`SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID`), L922 (`SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_VR_ID`) |
| `DSCP_TO_TC_MAP\|<name>` | OID 解決（`gQosOrch->resolveTunnelQosMap`） | `decap_dscp_to_tc_map` フィールドに値を指定したとき。未作成 map は `task_need_retry` 無限待機 | `tunneldecaporch.cpp` L215-221; `qosorch.cpp` L113 |
| `MUX_CABLE`（逆参照） | 下流が TUNNEL_DECAP_TABLE を読み取り | `MuxOrch` が MUX_CABLE SET 処理時に `TunnelDecapOrch::getQosMapId()` を呼び出し `encap_tc_to_dscp_map` / `encap_tc_to_queue_map` の OID を取得して MUX トンネル encap [QoS](../../reference/glossary.md#term-qos) を設定する | `tunneldecaporch.cpp` L103, L1450-1465; `muxorch.cpp` L2348-2377 |

!!! note "デフォルト VRF への固定依存"
    `tunneldecaporch` は overlay RIF / tunnel term entry を常に `gVirtualRouterId`（デフォルト VRF）に紐付ける。
    VRF フィールドは存在せず、VRF 分離したデカプセルトンネルは現行実装では作成できない。

!!! note "DSCP_TO_TC_MAP の事前作成必須"
    `decap_dscp_to_tc_map` に指定する QoS map が未作成の場合、当該 TUNNEL_DECAP_TABLE エントリの処理が
    `task_need_retry` でスタックし続ける。TUNNEL_DECAP_TABLE SET 前に `DSCP_TO_TC_MAP` を作成すること。

!!! note "MUX_CABLE 削除順序"
    TUNNEL_DECAP_TABLE エントリを DEL する前に `MUX_CABLE|*` の設定を先に削除すること。
    `encap_tc_to_dscp_map` / `encap_tc_to_queue_map` は muxorch の QoS 設定専用の暗黙インターフェースであり、
    TUNNEL_DECAP_TABLE DEL 後に muxorch が OID を参照するとエラーになる。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動 (Phase D)

<!-- evidence: sonic-net/sonic-swss orchagent/tunneldecaporch.cpp@4305596156d70e9797e8a881b3d19b46de0bce0d -->

### 不正 IP / フィールド値による拒否

| 条件 | ログ / 動作 | evidence |
|------|-----------|----------|
| `tunnel_type` が `IPINIP` 以外 | `SWSS_LOG_ERROR("Invalid tunnel type %s")` → `valid=false`、エントリ全体スキップ | `tunneldecaporch.cpp:L129` |
| `src_ip` が不正 IP 文字列 | `std::invalid_argument` 例外を捕捉 → `SWSS_LOG_ERROR(e.what())` → `valid=false`、エントリスキップ | `tunneldecaporch.cpp:L141-144` |
| `dscp_mode` が `uniform`/`pipe` 以外 | `SWSS_LOG_ERROR("Invalid dscp mode %s")` → `valid=false`、エントリスキップ | `tunneldecaporch.cpp:L157` |
| `ecn_mode` が `copy_from_outer`/`standard` 以外 | `SWSS_LOG_ERROR("Invalid ecn mode %s")` → `valid=false`、エントリスキップ | `tunneldecaporch.cpp:L173` |
| `encap_ecn_mode` が `standard` 以外 | `SWSS_LOG_ERROR("Only standard encap ecn mode is supported currently")` → `valid=false`、エントリスキップ | `tunneldecaporch.cpp:L189` |
| `ttl_mode` が `uniform`/`pipe` 以外 | `SWSS_LOG_ERROR("Invalid ttl mode %s")` → `valid=false`、エントリスキップ | `tunneldecaporch.cpp:L205` |
| 未知フィールド名 | `SWSS_LOG_ERROR("unknown decap tunnel table attribute '%s'")` → `valid=false`、エントリスキップ | `tunneldecaporch.cpp:L277` |

### VRF 未解決 / QoS マップ未解決

| 条件 | ログ / 動作 | evidence |
|------|-----------|----------|
| `decap_dscp_to_tc_map` が未解決（OID = `SAI_NULL_OBJECT_ID`） | `SWSS_LOG_NOTICE("QoS map %s is not ready yet")` → `task_need_retry`、エントリをキューに戻す | `tunneldecaporch.cpp:L218-221` |
| `decap_tc_to_pg_map` が未解決 | 同上 → `task_need_retry` | `tunneldecaporch.cpp:L233-236` |
| `encap_tc_to_dscp_map` が未解決 | 同上 → `task_need_retry` | `tunneldecaporch.cpp:L248-251` |
| `encap_tc_to_queue_map` が未解決 | 同上 → `task_need_retry` | `tunneldecaporch.cpp:L263-266` |
| tunnel decap term で `tunnel_name` が未登録 | `SWSS_LOG_ERROR("Tunnel %s does not exist.")` → term エントリスキップ | `tunneldecaporch.cpp:L904` |

### SAI tunnel 作成失敗

| 条件 | ログ / 動作 | evidence |
|------|-----------|----------|
| `sai_tunnel_api->create_tunnel()` 失敗 | `SWSS_LOG_ERROR("Failed to create tunnel")` → `handleSaiCreateStatus()` → 失敗時 `parseHandleSaiStatusFailure()` でエントリ再処理またはドロップ | `tunneldecaporch.cpp:L852-858` |
| overlay RIF (`sai_router_intfs_api->create_router_interface()`) 失敗 | `SWSS_LOG_ERROR("Failed to create overlay router interface %d")` → `false` 返却、[ASIC_DB](../../reference/glossary.md#term-asic_db) 未書込み | `tunneldecaporch.cpp:L756` |
| `sai_tunnel_api->create_tunnel_term_table_entry()` 失敗 | `SWSS_LOG_ERROR("Failed to create tunnel decap term entry %s.")` → `handleSaiCreateStatus()` 経由で再処理またはドロップ | `tunneldecaporch.cpp:L982-985` |
| DEL 時 `sai_tunnel_api->remove_tunnel()` 失敗 | `SWSS_LOG_ERROR("Failed to remove tunnel: %" PRIu64)` → `handleSaiRemoveStatus()` 経由 | `tunneldecaporch.cpp:L1194-1198` |
| DEL 時 overlay RIF `remove_router_interface()` 失敗 | `SWSS_LOG_ERROR("Failed to remove tunnel overlay interface: %" PRIu64)` → `handleSaiRemoveStatus()` 経由 | `tunneldecaporch.cpp:L1203` |
| `TUNNEL_DECAP_TABLE` DEL 時に decap term が残存 | `SWSS_LOG_ERROR("Failed to remove tunnel %s that has decap terms.")` → DEL 拒否 (`false` 返却) | `tunneldecaporch.cpp:L1184` |

### create-only 属性の変更試行

| 条件 | ログ / 動作 | evidence |
|------|-----------|----------|
| 既存トンネルに `ecn_mode` を SET | `SWSS_LOG_WARN("Skip setting ecn_mode since the SAI attribute SAI_TUNNEL_ATTR_DECAP_ECN_MODE is create only")` → `valid=false`、処理中断 | `tunneldecaporch.cpp:L179` |
| 既存トンネルに `encap_ecn_mode` を SET | `SWSS_LOG_NOTICE("Skip setting encap_ecn_mode since the SAI attribute SAI_TUNNEL_ATTR_ENCAP_ECN_MODE is create only")` → `valid=false`、処理中断 | `tunneldecaporch.cpp:L194` |
| 既存トンネルの `src_ip` を変更 | `SWSS_LOG_ERROR("cannot modify src ip for existing tunnel")` → 変更拒否（DEL → SET が必要） | `tunneldecaporch.cpp:L149` |

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

`TUNNEL_DECAP_TABLE` の処理で CONFIG_DB フィールドから読み込まれず、コードに直書きされている定数。`config_db.json` での設定変更は効果なく、変更にはコードのリコンパイルが必要。

| 定数名 | 値 | 定義場所 | 用途 |
|--------|----|---------|------|
| `OVERLAY_RIF_DEFAULT_MTU` | `9100` | `tunneldecaporch.cpp` L14 | Overlay loopback ルータインターフェースの MTU。`SAI_ROUTER_INTERFACE_ATTR_MTU` として SAI に渡す。フィールドで上書き不可 |
| `SAI_TUNNEL_TYPE_IPINIP` | SAI enum | `tunneldecaporch.cpp` L768 | `tunnel_type == "IPINIP"` のとき `SAI_TUNNEL_ATTR_TYPE` に設定される固定値 |
| `SAI_ROUTER_INTERFACE_TYPE_LOOPBACK` | SAI enum | `tunneldecaporch.cpp` L746 | Overlay [RIF](../../reference/glossary.md#term-rif) は常に LOOPBACK タイプ。変更不可 |
| `SAI_TUNNEL_TTL_MODE_UNIFORM_MODEL` | SAI enum | `tunneldecaporch.cpp` L811 | `ttl_mode == "uniform"` のとき `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` に設定 |
| `SAI_TUNNEL_TTL_MODE_PIPE_MODEL` | SAI enum | `tunneldecaporch.cpp` L815 | `ttl_mode == "pipe"` のとき同属性に設定 |
| `SAI_TUNNEL_DSCP_MODE_UNIFORM_MODEL` | SAI enum | `tunneldecaporch.cpp` L823 | `dscp_mode == "uniform"` のとき `SAI_TUNNEL_ATTR_DECAP_DSCP_MODE` に設定 |
| `SAI_TUNNEL_DSCP_MODE_PIPE_MODEL` | SAI enum | `tunneldecaporch.cpp` L827 | `dscp_mode == "pipe"` のとき同属性に設定 |
| `SAI_TUNNEL_DECAP_ECN_MODE_COPY_FROM_OUTER` | SAI enum | `tunneldecaporch.cpp` L789 | `ecn_mode == "copy_from_outer"` のとき `SAI_TUNNEL_ATTR_DECAP_ECN_MODE` に設定 |
| `SAI_TUNNEL_DECAP_ECN_MODE_STANDARD` | SAI enum | `tunneldecaporch.cpp` L793 | `ecn_mode == "standard"` のとき同属性に設定 |
| `SAI_TUNNEL_ENCAP_ECN_MODE_STANDARD` | SAI enum | `tunneldecaporch.cpp` L802 | `encap_ecn_mode == "standard"` のとき `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` に設定 |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2P` | SAI enum | `tunneldecaporch.cpp` L928 | `term_type == P2P` のとき `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_TYPE` に設定 |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP` | SAI enum | `tunneldecaporch.cpp` L932 | `term_type == P2MP` のとき同属性に設定（省略時のデフォルト） |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_MP2MP` | SAI enum | `tunneldecaporch.cpp` L936 | `term_type == MP2MP` のとき同属性に設定（subnet decap 必須） |
| `MUX_TUNNEL` | `"MuxTunnel0"` | `tunneldecaporch.h` L21 | [MuxOrch](../../reference/glossary.md#term-muxorch) が固定参照する Dual-ToR トンネル名。キーが異なると MuxOrch はトンネルを見つけられずエラー |
| `SubnetDecapConfig.tunnel` | `"IPINIP_SUBNET"` | `tunneldecaporch.h` L101 | サブネット decap 用 IPv4 トンネル内部識別子 |
| `SubnetDecapConfig.tunnel_v6` | `"IPINIP_SUBNET_V6"` | `tunneldecaporch.h` L102 | サブネット decap 用 IPv6 トンネル内部識別子 |

### Overlay RIF の固定 SAI 属性

Overlay ループバック RIF は以下の SAI 属性を常時ハードコードで設定する。

| SAI 属性 | 固定値 | 備考 |
|----------|--------|------|
| `SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID` | `gVirtualRouterId`（デフォルト [VRF](../../reference/glossary.md#term-vrf)） | VRF 分離不可。VRF フィールドは存在しない |
| `SAI_ROUTER_INTERFACE_ATTR_TYPE` | `SAI_ROUTER_INTERFACE_TYPE_LOOPBACK` | 固定 LOOPBACK タイプ |
| `SAI_ROUTER_INTERFACE_ATTR_MTU` | `9100`（`OVERLAY_RIF_DEFAULT_MTU`） | Jumbo frame 対応デフォルト |

!!! warning "MuxTunnel0 固定名の制約"
    [YANG](../../reference/glossary.md#term-yang) パターン `"MuxTunnel[0-9]+"` で複数エントリを許容しているが、
    `MuxOrch` は `MuxTunnel0` をハードコードで参照する。
    トンネル名を `MuxTunnel1` 等にすると MuxOrch が対象を見つけられず Dual-ToR が機能しない。

> 詳細スキャンノート: `meta/_intermediate/cdb-flow/tunnel-decap-table-constants.md`

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

`tunneldecaporch` が APPL_DB の `TUNNEL_DECAP_TABLE` を処理する際に発生する副次的な DB 書き込みを整理する。

### ASIC_DB — SAI オブジェクト群

| SAI API | 生成オブジェクト | トリガ条件 |
|---------|--------------|----------|
| `sai_router_intfs_api->create_router_interface()` | `SAI_OBJECT_TYPE_ROUTER_INTERFACE` (overlay loopback, MTU=9100) | `addDecapTunnel()` 実行時・常時 |
| `sai_tunnel_api->create_tunnel()` | `SAI_OBJECT_TYPE_TUNNEL` (IPINIP) | `addDecapTunnel()` 成功時 |
| `sai_tunnel_api->create_tunnel_term_table_entry()` | `SAI_OBJECT_TYPE_TUNNEL_TERM_TABLE_ENTRY` | `addDecapTunnelTermEntry()` 成功時 |

SAI tunnel に付与される主要属性: `SAI_TUNNEL_ATTR_TYPE=IPINIP`, `SAI_TUNNEL_ATTR_DECAP_ECN_MODE`, `SAI_TUNNEL_ATTR_DECAP_TTL_MODE`, `SAI_TUNNEL_ATTR_DECAP_DSCP_MODE`。
`decap_dscp_to_tc_map` が設定済みなら `SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` も付与。
`decap_tc_to_pg_map` が設定済みなら `SAI_TUNNEL_ATTR_DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP` も付与。

### STATE_DB — STATE_TUNNEL_DECAP_TABLE / STATE_TUNNEL_DECAP_TERM_TABLE

| テーブル | 操作 | トリガ | 書込フィールド |
|---------|------|-------|--------------|
| `STATE_TUNNEL_DECAP_TABLE` | SET | SAI `create_tunnel` 成功後 (`setDecapTunnelStatus()`) | `tunnel_type`, `dscp_mode`, `ecn_mode`, `encap_ecn_mode`, `ttl_mode` |
| `STATE_TUNNEL_DECAP_TABLE` | DEL | トンネル削除時 (`removeDecapTunnelStatus()`) | — |
| `STATE_TUNNEL_DECAP_TERM_TABLE` | SET | SAI `create_tunnel_term_table_entry` 成功後 (`setDecapTunnelTermStatus()`) | `term_type`, `src_ip` (P2P/MP2MP のみ), `subnet_type` (サブネット decap 時のみ) |
| `STATE_TUNNEL_DECAP_TERM_TABLE` | DEL | decap term 削除時 (`removeDecapTunnelTermStatus()`) | — |

evidence: `tunneldecaporch.cpp` L1521-1566

### MuxOrch への間接 QoS 副次反映

`encap_tc_to_dscp_map` / `encap_tc_to_queue_map` は SAI に直接 push **されない**。`tunneldecaporch` は OID を内部キャッシュ (`tunnelTable`) に保持し、`MuxOrch` が `MUX_CABLE` 処理時に `TunnelDecapOrch::getQosMapId()` 経由で取得して自身の SAI 書き込みに利用する (`muxorch.cpp:L2368-2380`)。

!!! note "詳細スキャンノート"
    `meta/_intermediate/cdb-flow/tunnel-decap-table-cross-refs.md`

<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

### Consumer 登録経路

`TunnelDecapOrch` は `orchdaemon` から APPL_DB テーブルリストを受け取り `Orch` 基底クラス経由で `ConsumerStateTable` を登録する。加えてコンストラクタ内で CONFIG_DB の `SUBNET_DECAP_TABLE` を `SubscriberStateTable` として個別登録する。

```cpp
// orchdaemon.cpp (TunnelDecapOrch 生成箇所)
vector<string> tunnel_tables = {
    APP_TUNNEL_DECAP_TABLE_NAME,        // "TUNNEL_DECAP_TABLE"
    APP_TUNNEL_DECAP_TERM_TABLE_NAME    // "TUNNEL_DECAP_TERM_TABLE"
};
gTunneldecapOrch = new TunnelDecapOrch(m_applDb, m_stateDb, m_configDb, tunnel_tables);

// tunneldecaporch.cpp L39-48
auto cfgSubnetDecapSubTable = new SubscriberStateTable(
    configDb, CFG_SUBNET_DECAP_TABLE_NAME,
    TableConsumable::DEFAULT_POP_BATCH_SIZE, 0);
Orch::addExecutor(new Consumer(cfgSubnetDecapSubTable, this, CFG_SUBNET_DECAP_TABLE_NAME));
```

起動時に `cfgSubnetDecapSubTable->pops(entries)` で `SUBNET_DECAP_TABLE` の現在値を一括取得して初期化し、その後は keyspace notification で更新を受け取る。

### 購読テーブルと API 種別

| テーブル | DB | 購読 API | Handler |
|---------|----|---------|----|
| `TUNNEL_DECAP_TABLE` | APPL_DB | `ConsumerStateTable` (Orch 基底) | `doDecapTunnelTask()` |
| `TUNNEL_DECAP_TERM_TABLE` | APPL_DB | `ConsumerStateTable` (Orch 基底) | `doDecapTunnelTermTask()` |
| `SUBNET_DECAP_TABLE` | CONFIG_DB | `SubscriberStateTable` + `addExecutor` | `doSubnetDecapTask()` |

CONFIG_DB の `TUNNEL` テーブルは **orchagent が直接購読しない**。`tunnelmgrd` が CONFIG_DB → APPL_DB へ変換し、orchagent は APPL_DB 側を `ConsumerStateTable` で受け取る二段構成。

### PortsOrch ゲート（受動的待機）

```cpp
// tunneldecaporch.cpp L55-58
void TunnelDecapOrch::doTask(Consumer &consumer)
{
    if (!gPortsOrch->allPortsReady()) return;
    ...
}
```

`gPortsOrch->allPortsReady()` が `false` の間は全トンネルタスクをスキップ。PortsOrch が ready 状態になると orchagent のメインループが次の select サイクルで `doTask()` を再呼び出しし、スタックしていたエントリを処理する（受動的待機パターン）。

### SAI tunnel_api 呼び出し（出力方向）

```cpp
// tunneldecaporch.cpp L853 付近
status = sai_tunnel_api->create_tunnel(
    &tunnel_id, gSwitchId, tunnel_attrs.size(), tunnel_attrs.data());
task_process_status handle_status = handleSaiCreateStatus(SAI_API_TUNNEL, status);
```

`handleSaiCreateStatus()` が SAI エラーを `task_need_retry` / `task_success` / `task_failed` に変換。`task_need_retry` はキューに残留して次サイクルでリトライ（QoS map 未作成時に発生）。

### STATE_DB 書き戻し（Observer 逆方向）

SAI `create_tunnel()` / `create_tunnel_term_table_entry()` 成功後、`stateTunnelDecapTable` と `stateTunnelDecapTermTable` へ書き戻す。これらは `Table`（非 [ProducerStateTable](../../reference/glossary.md#term-producerstatetable)）のため [Redis](../../reference/glossary.md#term-redis) `hset`/`del` を直接発行する。NotificationProducer / Consumer 型のチャンネル通知は使用しない。

> 詳細スキャンノート: `meta/_intermediate/cdb-flow/tunnel-decap-table-pubsub.md`

<!-- /pubsub -->

<!-- platform -->
## プラットフォーム差・SAI capability 分岐 (Phase H)

### SAI create-only 属性の更新スキップ — 全プラットフォーム共通

`SAI_TUNNEL_ATTR_DECAP_ECN_MODE` / `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` は SAI 仕様上 create-only 属性であり、既存トンネルへの更新試行は自動スキップされる[^1]。

| 属性 | create-only の影響 | ログ |
|-----|------------------|------|
| `SAI_TUNNEL_ATTR_DECAP_ECN_MODE` (`ecn_mode`) | 更新 SET をスキップ。作成時の値が永続する | `SWSS_LOG_WARN("Skip setting ecn_mode since the SAI attribute SAI_TUNNEL_ATTR_DECAP_ECN_MODE is create only")` |
| `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` (`encap_ecn_mode`) | 更新 SET をスキップ | `SWSS_LOG_NOTICE("Skip setting encap_ecn_mode since the SAI attribute SAI_TUNNEL_ATTR_ENCAP_ECN_MODE is create only")` |

この挙動は SAI 仕様準拠の共通動作であり、特定ベンダーに依存しない。`ecn_mode` を変更する場合は TUNNEL_DECAP_TABLE エントリを一度削除して再作成する必要がある。

### OVERLAY_RIF_DEFAULT_MTU = 9100 — プラットフォーム非依存ハードコード

オーバーレイ loopback RIF の MTU が `OVERLAY_RIF_DEFAULT_MTU = 9100` でハードコードされている (tunneldecaporch.cpp:14)。SAI プラットフォームのデフォルト MTU（通常 1500）に依存せず、[VXLAN](../../reference/glossary.md#term-vxlan) / IP-in-IP カプセルパケットの断片化を防ぐための固定値。プラットフォームを問わず適用される。

### subnet decap — ハードコードトンネル名制約

`TUNNEL_DECAP_TABLE` で subnet decap を有効にするには `"IPINIP_SUBNET"` (IPv4) / `"IPINIP_SUBNET_V6"` (IPv6) という名前でトンネルを作成する必要がある。これらの名前は `SubnetDecapConfig` にハードコードされており、プラットフォームや構成に関わらず変更不可。別名のトンネルへ subnet decap term を設定しようとすると `"subnet decap is disabled, ignored."` を LOG_ERROR してスキップされる。

### SAI capability query なし

`tunneldecaporch` は orchagent 起動時に `sai_query_attribute_enum_values_capability()` を呼ばない。プラットフォーム capability による動作分岐は存在せず、すべてのプラットフォームで同一の SAI 属性セットを使用する。特定の SAI 属性が非サポートの場合はエラーログのみで継続する。

> 詳細スキャンノート: `meta/_intermediate/cdb-flow/tunnel-decap-table-platform.md`

<!-- /platform -->

<!-- glossary-links-injected: da83a21dfcb6 -->
