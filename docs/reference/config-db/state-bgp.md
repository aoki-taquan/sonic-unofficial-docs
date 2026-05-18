---
title: STATE_DB BGP 関連テーブル
description: "STATE_DB / BMP_STATE_DB の BGP 関連テーブル（BGP_STATE_TABLE・BGP_PEER_CONFIGURED_TABLE・BGP_NEIGHBOR_TABLE・BGP_RIB_IN_TABLE・BGP_RIB_OUT_TABLE）のスキーマ・フィールドデフォルト・書き込みタイミングを解説する。"
area: reference
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: fpmsyncd/bgp_eoiu_marker.py
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: fpmsyncd/fpmsyncd.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: doc/swss-schema.md
    ref: HEAD
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py
    ref: HEAD
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: HEAD
  - repo: sonic-net/SONiC
    path: doc/bmp/bmp.md
    ref: HEAD
  - repo: sonic-net/SONiC
    path: doc/BGP/Bgpcfgd-dyn-peer-modification-support.md
    ref: HEAD
related:
  config_db:
    - BGP_NEIGHBOR
    - BGP_PEER_RANGE
    - BMP
---

# STATE_DB BGP 関連テーブル

<!-- defaults -->

## 概要

SONiC の BGP ランタイム状態は 2 つの Redis DB にまたがって格納される。

- **STATE_DB** — `BGP_STATE_TABLE`（EOIU マーカー）・`BGP_PEER_CONFIGURED_TABLE`（bgpcfgd によるピア確認状態）
- **BMP_STATE_DB** — `BGP_NEIGHBOR_TABLE`・`BGP_RIB_IN_TABLE`・`BGP_RIB_OUT_TABLE`（BMP コンテナが FRR/bgpd から収集する BGP モニタリングデータ）

いずれも **読み取り専用** の観測テーブルであり、CONFIG_DB への書き戻しは行われない[^1]。

[^1]: `sonic-swss-common/common/schema.h` L437, L502, L511, L557-559 にテーブル名定数が定義されている。

---

## BGP_STATE_TABLE (STATE_DB)

### 目的

Warm Restart 時に `bgp` docker の `bgp_eoiu_marker` プロセスが書き込む **EOIU（End-Of-Initial-Update）マーカー**[^2]。`fpmsyncd` がこのフラグを監視し、全 BGP ピアのルート収束完了を確認してから RIB 再構成（reconciliation）を開始する。Warm Restart が無効の場合は書き込まれない。

[^2]: `sonic-swss/fpmsyncd/bgp_eoiu_marker.py` L4-17 (ファイルヘッダコメント)

### key 構造

```text
BGP_STATE_TABLE|<family>|eoiu
```

- `<family>`: `"IPv4"` または `"IPv6"`
- サブキー: 常に `eoiu` 固定

### フィールド

<!-- defaults -->
| フィールド | 型 | 初期値 | 設定値 | 説明 |
|-----------|----|-------|-------|------|
| `state` | enum string | `"unknown"` | `"unknown"` / `"reached"` / `"consumed"` | EOIU 到達状態。Warm Restart 開始時に `"unknown"` で初期化 |
| `timestamp` | string | (書き込み時刻) | `"YYYY-MM-DD HH:MM:SS"` | 最終更新時刻。`strftime("%Y-%m-%d %H:%M:%S", gmtime())` で生成 |

`state` の遷移[^3]:

| 値 | セット元 | タイミング |
|----|---------|----------|
| `"unknown"` | `bgp_eoiu_marker.py` | Warm Restart 開始時（クリア後に再セット） |
| `"reached"` | `bgp_eoiu_marker.py` | 全 BGP ピアの EOR 受信完了後 |
| `"consumed"` | `fpmsyncd` | reconciliation 開始後に更新（スキーマ定義上の値; fpmsyncd は read のみ確認） |

[^3]: `sonic-swss/fpmsyncd/bgp_eoiu_marker.py` L78-88, L200-208; `sonic-swss/fpmsyncd/fpmsyncd.cpp` L54-72; `sonic-swss/doc/swss-schema.md` L1155-1164

### 関連定数

| 定数 | 値 | 意味 |
|-----|-----|------|
| `DEFAULT_EOIU_HOLD_INTERVAL` | `3` 秒 | EOIU 検出後の reconciliation 開始待機時間 |
| `DEFAULT_ROUTING_RESTART_INTERVAL` | `120` 秒 | Warm Restart タイムアウト |

ソース: `fpmsyncd/fpmsyncd.cpp` L46, L51

---

## BGP_PEER_CONFIGURED_TABLE (STATE_DB)

### 目的

`bgpcfgd`（`managers_bgp.py`）が CONFIG_DB の `BGP_NEIGHBOR` / `BGP_PEER_RANGE` を処理した後、ピアが **bgpcfgd によって認識・設定済み** であることを示す確認テーブル[^4]。SDN コントローラが BGP ピアの設定反映を確認するために参照する。

[^4]: `SONiC/doc/BGP/Bgpcfgd-dyn-peer-modification-support.md` L53-90

### key 構造

```text
BGP_PEER_CONFIGURED_TABLE|<vrf>|<peer_name>
BGP_PEER_CONFIGURED_TABLE|<peer_name>          # default VRF の場合
```

- `<vrf>`: VRF / VNET 名。`"default"` VRF では省略
- `<peer_name>`: ピア IP アドレス（静的）またはピアグループ名（動的）

ソース: `bgpcfgd/managers_bgp.py` L280-283

### フィールド（動的ピア）

<!-- defaults -->
| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `ip_range` | list/string | 必須 | 動的ピアの listen range IP リスト |
| `name` | string | 必須 | ピアグループ名 |
| `peer_asn` | string | 任意 | ピアの AS 番号 |
| `src_address` | string | 任意 | セッション送信元 IP |

静的ピアの場合も同じテーブル名で `BGP_NEIGHBOR` のフィールドをそのまま転記する。

**デフォルト値なし**: CONFIG_DB の値を `list(sorted(data.items()))` でそのまま書き込む[^5]。

[^5]: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` L289

### 書き込みタイミング

| 操作 | コード |
|------|-------|
| SET（ピア追加・更新時） | `state_peer_table.set(key, list(sorted(data.items())))` (L289) |
| DEL（ピア削除時） | `state_peer_table.delete(key)` (L294) |
| 全削除（`config bgp remove neighbor` 等） | `sonic-utilities/config/main.py` L1613: `delete_all_by_pattern(STATE_DB, "BGP_PEER_CONFIGURED_TABLE|*")` |

---

## BGP_NEIGHBOR_TABLE (BMP_STATE_DB)

### 目的

BGP Monitoring Protocol (BMP)[^6] が FRR/bgpd から収集した **BGP ネイバー属性**（capability、ポート番号、AS 情報など）を格納するテーブル。`bmp` docker 内の `openbmpd` が BGP OPEN メッセージを解析して書き込む。

[^6]: RFC 7854; `SONiC/doc/bmp/bmp.md`

### key 構造

```text
BGP_NEIGHBOR_TABLE|<peer_ip>
```

### フィールド

<!-- defaults -->
| フィールド | 型 | サンプル値 | 説明 |
|-----------|----|----------|------|
| `peer_addr` | IP string | `"10.0.0.23"` | ピア IP アドレス |
| `peer_asn` | string | `"65200"` | ピア AS 番号 |
| `peer_rd` | string | `"0:0"` | Route Distinguisher |
| `remote_port` | string | `"179"` | ピアのポート番号（BGP は 179） |
| `local_ip` | IP string | `"10.0.0.22"` | ローカル IP アドレス |
| `local_asn` | string | `"65100"` | ローカル AS 番号 |
| `local_port` | string | `"40760"` | ローカルポート番号（エフェメラル） |
| `sent_cap` | string | `"MPBGP (1) : afi=1 ..."` | 送信 BGP capabilities（OPEN メッセージから） |
| `recv_cap` | string | `"MPBGP (1) : afi=1 ..."` | 受信 BGP capabilities（OPEN メッセージから） |

デフォルト値なし。FRR が BGP OPEN メッセージを送受信したタイミングで `openbmpd` が書き込む。

ソース: `SONiC/doc/bmp/bmp.md` L141-166（`redis-cli HGETALL` 実例）; `sonic-utilities/show/main.py` L2550-2573

---

## BGP_RIB_IN_TABLE / BGP_RIB_OUT_TABLE (BMP_STATE_DB)

### 目的

FRR が受信・送信した BGP ルートのスナップショット。**RIB-In** はピアから受信した経路（post-policy）、**RIB-Out** はピアへ送信する経路を格納する。`openbmpd` が BGP UPDATE メッセージを解析して書き込む[^7]。

[^7]: `SONiC/doc/bmp/bmp.md` L286-306

### key 構造

```text
BGP_RIB_IN_TABLE|<nlri>|<peer_ip>
BGP_RIB_OUT_TABLE|<nlri>|<peer_ip>
```

- `<nlri>`: ネットワークプレフィックス（例: `"192.172.80.128/25"`、`"20c0:ef50::/64"`）
- `<peer_ip>`: BGP ピア IP アドレス

### フィールド（RIB_IN / RIB_OUT 共通）

<!-- defaults -->
| フィールド | 型 | サンプル値 | デフォルト | 説明 |
|-----------|----|----------|----------|------|
| `origin` | string | `"igp"` | — | 経路起源。`"igp"` / `"egp"` / `"incomplete"` |
| `as_path` | string | `"65100 64600 65534"` | — | AS パス（スペース区切り） |
| `as_path_count` | string | `"3"` | — | AS パスのホップ数 |
| `origin_as` | string | `"65534"` | — | 起源 AS 番号 |
| `next_hop` | IP string | `""` | `""` | ネクストホップ IP。未設定時は空文字 |
| `local_pref` | string | `"0"` | `"0"` | Local Preference 値 |
| `community_list` | string | `""` | `""` | コミュニティ属性。未設定時は空文字 |
| `ext_community_list` | string | `""` | `""` | 拡張コミュニティ属性。未設定時は空文字 |
| `large_community_list` | string | `""` | `""` | Large Community 属性。未設定時は空文字 |
| `originator_id` | string | `""` | `""` | ORIGINATOR_ID 属性。未設定時は空文字 |

ソース: `SONiC/doc/bmp/bmp.md` L167-209; `sonic-utilities/tests/show_bmp_test.py` L70-130

---

## BMP テーブルのライフサイクル

BMP コンテナが再起動または FRR との接続が切断・再確立された場合、テーブルはクリアされてから再書き込みされる[^8]。

[^8]: `sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py` L64-65: `delete_all_by_pattern(BMP_STATE_DB, 'BGP_RIB_IN_TABLE*')` 等

`bmpcfgd` は CONFIG_DB の `BMP.table` エントリ（`bgp_neighbor_table` / `bgp_rib_in_table` / `bgp_rib_out_table`）を参照し、テーブルごとに収集の有効/無効を制御する。

```text
CONFIG_DB BMP|table:
  bgp_neighbor_table = "true" | "false"
  bgp_rib_in_table   = "true" | "false"
  bgp_rib_out_table  = "true" | "false"
```

<!-- ordering -->
## 書込み順依存 (Phase B)

各テーブルの書き込み元デーモンと前提条件を示す。

### BGP_STATE_TABLE — Warm Restart の完了マーカー

`BGP_STATE_TABLE` は **Warm Restart が有効なときのみ** 書き込まれる。書込み順は以下の通り。

1. **クリア**: Warm Restart 開始時に `bgp_eoiu_marker.py` が `BGP_STATE_TABLE|IPv4|eoiu` および `BGP_STATE_TABLE|IPv6|eoiu` を削除 (`clean_bgp_eoiu_marker` — bgp_eoiu_marker.py L91–96)
2. **`"unknown"` セット**: 各ファミリーの状態を `"unknown"` で初期化。前提: STATE_DB 接続が成立していること。
3. **`"reached"` セット**: 全 BGP ピアから EOR（End-of-RIB）を受信したときに `set_bgp_eoiu_marker(family, "reached")` を呼ぶ。前提: FRR bgpd が全ネイバーと Established セッションを確立していること (bgp_eoiu_marker.py L141–166)
4. **`fpmsyncd` による読み取り**: `fpmsyncd` は `eoiuCheckTimer`（デフォルト周期）で `BGP_STATE_TABLE|IPv4|eoiu` / `IPv6|eoiu` の `state` フィールドをポーリングし、両方が `"reached"` になった時点で `DEFAULT_EOIU_HOLD_INTERVAL`（3 秒）待機後に RIB reconciliation を開始する (fpmsyncd.cpp L54–70, L127–131)

`BGP_STATE_TABLE` と APPL_DB `ROUTE_TABLE` への書き込みは独立した経路であり、EOIU マーカーが存在しても reconciliation 開始前は ROUTE_TABLE の再投入は保留される。

### BGP_PEER_CONFIGURED_TABLE — bgpcfgd による FRR 設定投入完了確認

`bgpcfgd` の `BGPPeerMgrBase.update_state_db()` が FRR コンフィグ push 直後に書き込む。前提依存の詳細は [bgp-state.md の Phase B](bgp-state.md) を参照。主な順序制約:

- **SET**: FRR `cfg_mgr.push()` 成功後にのみ HSET。テンプレートレンダリング失敗時は書き込まれない。
- **DEL**: FRR `no neighbor` 発行後に DELETE。`config reload` 時は全エントリを先に削除してから bgpcfgd が再投入する。

### BGP_NEIGHBOR_TABLE / BGP_RIB_IN_TABLE / BGP_RIB_OUT_TABLE — BMP による収集

BMP（BGP Monitoring Protocol）テーブルは `openbmpd` が FRR bgpd から BMP メッセージ（RFC 7854）を受信するたびに書き込む。書込み前提:

1. CONFIG_DB `BMP.table` に対応するフィールド（`bgp_neighbor_table` / `bgp_rib_in_table` / `bgp_rib_out_table`）が `"true"` に設定されていること
2. `bmp` コンテナが起動し `openbmpd` が bgpd の BMP ポートに接続していること
3. bgpd と BMP セッションが確立していること（BGP OPEN メッセージを受信して初めて `BGP_NEIGHBOR_TABLE` にエントリが生成される）

**クリアタイミング**: `bmpcfgd` は BMP コンテナ再起動・FRR 接続切断時に `delete_all_by_pattern` で各テーブルを全削除してから再収集する (bmpcfgd.py L64–65)。

### 書込み順依存サマリ

| テーブル | 書込み元 | 前提条件 | 書込みタイミング |
|---------|---------|---------|----------------|
| `BGP_STATE_TABLE` | `bgp_eoiu_marker.py` | Warm Restart 有効、FRR EOR 受信完了 | 全ネイバーの EOR 受信後 |
| `BGP_PEER_CONFIGURED_TABLE` | `bgpcfgd` | CONFIG_DB ネイバー設定、FRR push 成功 | FRR コンフィグ push 直後 |
| `BGP_NEIGHBOR_TABLE` | `openbmpd` (BMP) | BMP 有効、bgpd-BMP セッション確立 | BGP OPEN メッセージ受信時 |
| `BGP_RIB_IN_TABLE` | `openbmpd` (BMP) | BMP 有効、BGP OPEN 完了後 | BGP UPDATE 受信時（RIB-In） |
| `BGP_RIB_OUT_TABLE` | `openbmpd` (BMP) | BMP 有効、BGP OPEN 完了後 | BGP UPDATE 送信時（RIB-Out） |

> 中間調査詳細: `meta/_intermediate/cdb-flow/bgp-state-ordering.md`
<!-- /ordering -->

<!-- cross-refs -->
## 暗黙テーブル参照 (Phase C)

各テーブルの書き込みデーモンが暗黙的に参照する CONFIG_DB テーブルおよび外部コンポーネントを示す。

### BGP_STATE_TABLE の前提参照

| 参照先テーブル / コンポーネント | 参照方向 | 条件 | evidence |
|--------------------------------|---------|------|---------|
| `WARM_RESTART` (CONFIG_DB, `CFG_WARM_RESTART_TABLE_NAME`) | `WarmStart::checkWarmStart("bgp", "bgp", false)` 経由で読み出し | `isWarmStart()` が false の場合、`bgp_eoiu_marker` サービス全体がスキップされ `BGP_STATE_TABLE` への書き込みは **発生しない** | bgp_eoiu_marker.py L191–197 |
| FRR bgpd (ネイバー EOR 確認) | `bgp_eoiu_marker.py` が bgpd の EOR 状態をポーリング | 全ネイバーの EOR 到達確認が完了するまで `wait_for_bgp_eoiu()` が待機。bgpd が応答しない間は STATE_DB に `"reached"` が書かれない | bgp_eoiu_marker.py L141–166 |
| `DEVICE_METADATA` (CONFIG_DB, `CFG_DEVICE_METADATA_TABLE_NAME`) | `fpmsyncd` が `SubscriberStateTable` として購読。`routing_mode` 等を参照 | `BGP_STATE_TABLE` を読む fpmsyncd 側の依存として存在 | fpmsyncd.cpp L81–83 |

### BGP_PEER_CONFIGURED_TABLE の前提参照

`bgpcfgd` (`BGPPeerMgrBase`) は以下の CONFIG_DB テーブルへの SET/DEL イベントを購読し、内容を `BGP_PEER_CONFIGURED_TABLE` へ転写する（`main.py` L87–92）。

| 購読テーブル (転写元) | peer_type | evidence |
|---|---|---|
| `BGP_NEIGHBOR` (`CFG_BGP_NEIGHBOR_TABLE_NAME`) | `"general"` (外部 eBGP ピア) | main.py:87 |
| `BGP_INTERNAL_NEIGHBOR` (`CFG_BGP_INTERNAL_NEIGHBOR_TABLE_NAME`) | `"internal"` (iBGP ピア) | main.py:88 |
| `BGP_MONITORS` | `"monitors"` | main.py:89 |
| `BGP_PEER_RANGE` | `"dynamic"` (listen range 動的ピア) | main.py:90 |
| `BGP_VOQ_CHASSIS_NEIGHBOR` | `"voq_chassis"` (VOQ シャーシ間 iBGP) | main.py:91 |
| `BGP_SENTINELS` | `"sentinels"` | main.py:92 |

上記テーブルのエントリが処理されるためには、以下の前提依存テーブル (`deps` リスト) がすべて到着している必要がある（未到着時はピア追加処理がブロックされる）。

| 前提依存テーブル | キー / フィールド | 用途 | evidence |
|---|---|---|---|
| `DEVICE_METADATA` | `localhost/bgp_asn` | `router bgp <ASN>` コマンド生成に使用 | managers_bgp.py:119, 192 |
| `DEVICE_METADATA` | `localhost/type` | デバイスロール判定（spine / leaf 等） | managers_bgp.py:120 |
| `LOOPBACK_INTERFACE` | `Loopback0` | ルータ ID の IPv4 アドレス取得 | managers_bgp.py:121, 186 |
| `BGP_DEVICE_GLOBAL` | `tsa_enabled` | TSA ルートマップ適用判定 | managers_bgp.py:122 |
| `BGP_DEVICE_GLOBAL` | `idf_isolation_state` | IDF isolation ルートマップ判定 | managers_bgp.py:123 |
| `DEVICE_NEIGHBOR_METADATA` | — | `use_neighbors_meta = true` のとき条件付きで追加 | managers_bgp.py:140 |

!!! note "FRR push 成功が必須条件"
    `BGP_PEER_CONFIGURED_TABLE` への書き込みは `cfg_mgr.push()` (FRR への `vtysh -f` 設定投入) が成功した後にのみ実行される（managers_bgp.py:239, 353, 444）。FRR bgpd が応答不能の場合、STATE_DB への反映も遅延・欠落する。

### BGP_NEIGHBOR_TABLE / BGP_RIB_IN_TABLE / BGP_RIB_OUT_TABLE の前提参照

| 参照先テーブル / コンポーネント | 参照方向 | 条件 | evidence |
|--------------------------------|---------|------|---------|
| `BMP` (CONFIG_DB, `BMP_TABLE`) | `bmpcfgd` が `config_db.subscribe(BMP_TABLE, ...)` で購読。各フィールド (`bgp_neighbor_table` / `bgp_rib_in_table` / `bgp_rib_out_table`) が `"false"` の場合は `delete_all_by_pattern` でテーブルを全削除する | 常時 | bmpcfgd.py:82–86 |
| FRR bgpd BMP ソケット | `openbmpd` が bgpd の BMP ポートに TCP 接続。BGP OPEN メッセージ受信後にのみ `BGP_NEIGHBOR_TABLE` エントリが生成される | bgpd との接続が確立しない間はエントリが生成されない | SONiC/doc/bmp/bmp.md L141–166 |
| FRR bgpd UPDATE メッセージ | `openbmpd` が BGP UPDATE を解析して `BGP_RIB_IN_TABLE` / `BGP_RIB_OUT_TABLE` を書く | BGP OPEN 完了後に受信・送信する UPDATE のみ対象 | SONiC/doc/bmp/bmp.md L286–306 |

> 中間調査詳細: `meta/_intermediate/cdb-flow/state-bgp-cross-refs.md`
<!-- /cross-refs -->
