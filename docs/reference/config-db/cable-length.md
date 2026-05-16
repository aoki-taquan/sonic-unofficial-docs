---
title: CABLE_LENGTH テーブル
description: "CABLE_LENGTH テーブル — ポートごとのケーブル長を保持し、lossless バッファ (PG headroom) の動的計算に使用する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-cable-length.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss
    path: cfgmgr/buffermgr.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: cfgmgr/buffermgrdyn.cpp
    ref: HEAD
  - repo: sonic-net/sonic-buildimage
    path: files/build_templates/buffers_config.j2
    ref: HEAD
related:
  config_db:
    - CABLE_LENGTH
    - BUFFER_PG
    - BUFFER_PROFILE
    - BUFFER_POOL
    - DEVICE_METADATA
    - PORT
  yang:
    - sonic-cable-length
---

# CABLE_LENGTH テーブル

## 概要

ポートごとのケーブル長を保持し、バッファマネージャ (`buffermgr` / `buffermgrdyn`) が lossless Priority Group (PG) の headroom サイズを計算するために参照する[^1]。dynamic buffer モードでは `buffermgrdyn` が speed・mtu と組み合わせてリアルタイムに `BUFFER_PG` プロファイルを生成する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>CABLE_LENGTH")]
  BM["buffermgr / buffermgrdyn"]
  CDB --> BM
  APPL[("APPL_DB<br/>BUFFER_PG / BUFFER_PROFILE")]
  BM --> APPL
  SAI["SAI<br/>buffer API"]
  APPL --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を示すミニ図。詳細・例外は本ページ本文を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
CABLE_LENGTH|<name>
```

`<name>` はケーブル長設定グループ名。デフォルトでは `AZURE` が使われる（後述）。

## 主要フィールド

| フィールド | 型 | YANG default | 説明 |
|-----------|----|--------------|------|
| `<ifname>` (フィールド名) | `string` (`[0-9]+m`) | — | ポート名をキーとし、ケーブル長 (`40m` 等) を値とする。`PORT_LIST.name` への leafref |

!!! note "テーブル構造の特殊性"
    このテーブルは「フィールド名 = ポート名、値 = ケーブル長」という構造。  
    例: `CABLE_LENGTH|AZURE` → `{"Ethernet0": "40m", "Ethernet4": "5m"}`

## 購読者

- **`buffermgr`** (`sonic-swss/cfgmgr/buffermgr.cpp`): static buffer モード。`pg_profile_lookup.ini` を参照して PG プロファイルを設定。
- **`buffermgrdyn`** (`sonic-swss/cfgmgr/buffermgrdyn.cpp`): dynamic buffer モード (`buffer_model=dynamic`)。speed・mtu と組み合わせてリアルタイムに headroom 計算し `BUFFER_PG`/`BUFFER_PROFILE` を生成。

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `BUFFER_PG`、`BUFFER_PROFILE`、`BUFFER_POOL`、`DEVICE_METADATA` (buffer_model)
- 関連 CLI: `config interface cable-length <ifname> <length>` (dynamic buffer モードのみ)
- 関連 YANG: `sonic-cable-length`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): `sonic-cable-length`
- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`BUFFER_PG`](buffer-pg.md)、[`BUFFER_PROFILE`](buffer-profile.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-cable-length.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-cable-length.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `CABLE_LENGTH|AZURE`
- フィールド: `{"Ethernet0": "40m", "Ethernet4": "5m", "Ethernet8": "300m"}`
- dynamic buffer モードのみ CLI で変更可能: `config interface cable-length Ethernet0 40m`

### よくある誤設定

- `"0m"` を設定すると lossless PG が削除される（DPC ポート向け特殊値）。誤って通常ポートに設定しないこと。
- static buffer モードで CLI を使うと「dynamic buffer が必要」エラーになる。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'CABLE_LENGTH|AZURE'
show buffer configuration
show buffer information
```
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-swss/cfgmgr/buffermgr.cpp, buffermgrdyn.cpp, buffers_config.j2 -->

- **`length = "0m"` → lossless PG 削除**: `buffermgr.cpp:159` および `buffermgrdyn.cpp:1492` で `"0m"` は「lossless PG を削除する」特殊値として扱われる。DPC ポート向け意図的設定。
- **`length = "None"` → silent skip**: `buffermgr.cpp:104` で `"None"` は更新をスキップ。エラーなし。
- **エントリが存在しない場合**: `buffermgrdyn` は speed や admin_up が来ても cable_length が空なら headroom 計算を延期する (`buffermgrdyn.cpp:2157-2159`)。WARN ログが出るが retry はしない。
- **admin down ポート**: cable_length が更新されても `PORT_ADMIN_DOWN` 状態のポートは `refreshPgsForPort` をスキップ (`buffermgrdyn.cpp:2191-2194`)。
- **mtu 未設定時の仮計算**: cable_length と speed が揃っているが mtu がない場合、`DEFAULT_MTU_STR = "9100"` で headroom を仮計算する (`buffermgrdyn.cpp:2174`)。mtu が後で設定されると再計算。

<!-- /cdb-exceptions -->

<!-- value-behavior -->
## 値依存挙動マトリクス

<!-- evidence: sonic-swss/cfgmgr/buffermgr.cpp:159, buffermgrdyn.cpp:1492, buffermgrdyn.cpp:1782 -->

| `length` 値 | 挙動 |
|------------|------|
| `"0m"` | lossless PG を削除。lossy PG は維持。DPC ポートや headroom 不要ポート向け |
| `"None"` | buffermgr が更新をスキップ (silent no-op) |
| `"5m"` 〜 `"500m"` | speed・mtu と組み合わせて headroom 計算。dynamic モードは `pg_lossless_<speed>_<length>_profile` を自動生成 |
| 未設定 (空) | headroom 計算を延期。speed・mtu が揃っても計算されない |

<!-- /value-behavior -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **buffermgr** / **buffermgrdyn** が `CABLE_LENGTH` テーブルを購読 (`CFG_PORT_CABLE_LEN_TABLE_NAME`)。

### 段階 2: CFG → キャッシュ

- `buffermgr`: `doCableTask()` でポート→ケーブル長の `m_cableLenLookup` マップを更新。その後 `doSpeedUpdateTask()` を呼び PG プロファイルを選択。
- `buffermgrdyn`: `handleCableLenTable()` で `portInfo.cable_length` を更新。speed・mtu が揃っていれば `refreshPgsForPort()` を即時呼び出す。

### 段階 3: headroom 計算 → APPL_DB

- **static モード** (`buffermgr`): `pg_profile_lookup.ini` から speed + cable_length に対応するエントリを引いて `BUFFER_PROFILE` を設定。
- **dynamic モード** (`buffermgrdyn`): `allocateProfile()` が speed/cable/mtu/threshold を引数に headroom ツール (`generate_headroom_info.py` or 内部計算) を呼び出し、`BUFFER_PROFILE` と `BUFFER_PG` を APPL_DB に書き込む。

### 段階 4: APPL → SAI

- `bufferorch` が APPL_DB の `BUFFER_PG`・`BUFFER_PROFILE` を購読し、SAI buffer API (`sai_buffer_api`) を通じてチップの PG headroom を設定。

<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

CABLE_LENGTH テーブルへの書き込みが発生するコード経路。

### sonic-cfggen / Jinja テンプレート (初期化)

- `buffers_config.j2:231-239` が `CABLE_LENGTH|AZURE` エントリを生成。ポートの neighbor role と `ports2cable` テーブルでケーブル長を決定。
- ロールが不明な場合は HWSKU の `buffers_defaults_*.j2` で定義された `default_cable` を使用。

### CLI (dynamic buffer モードのみ)

- `config interface cable-length <ifname> <length>` → `config/main.py:6326` → `config_db.mod_entry("CABLE_LENGTH", keys[0], ...)` でポート単位に上書き。

### config load_minigraph (マージ)

- `config/main.py:3886-3915` でテンプレート値と DB 既存値をポート単位にマージ。DB 側の既存ポートは保持され、テンプレート側のポートが追加/上書き。

<!-- /entry-points -->

<!-- ordering -->
## 書込み順依存 (Phase B)

> 調査証跡: `meta/_intermediate/cdb-flow/cable-length-ordering.md`

### SET 時の先行必須テーブル

| 先行テーブル | 理由 | ソース |
|---|---|---|
| `PORT` (`speed` フィールド) | `buffermgrdyn.handleCableLenTable()` が `effectiveSpeed.empty()` を確認し、空の場合は WARN ログを出しリトライなしで中断する。`buffermgr.doCableTask()` も `doSpeedUpdateTask()` 内で `m_speedLookup[port]` を参照するため speed 未着では不正キーになる | `buffermgrdyn.cpp:2155-2159`, `buffermgr.cpp:101-109` |
| `PORT_QOS_MAP` (`pfc_enable`) | `buffermgr.doSpeedUpdateTask()` が `m_portStatusLookup.count(port) == 0` で `task_need_retry` を返す。PORT_QOS_MAP が未着だと CABLE_LENGTH 通知がクリアされ、PORT_QOS_MAP 着信時に自動再処理される（static モードのみ） | `buffermgr.cpp:165-178` |
| `BUFFER_POOL` (`ingress_lossless_pool`) | `buffermgrdyn.allocateProfile()` が `m_bufferPoolReady == false` の場合に `task_need_retry` を返す。BUFFER_POOL 確立後にリトライキューから自動再処理（dynamic モードのみ） | `buffermgrdyn.cpp:978` |
| `PortInitDone` (STATE_DB / APPL_DB) | `m_portInitDone = false` の間はポートが PORT_INITIALIZING 状態に留まり、`refreshPgsForPort()` で PORT_READY チェックが通らず headroom 計算がスキップされる（dynamic モードのみ） | `buffermgrdyn.cpp:826-856`, `buffermgrdyn.cpp:1485-1487` |

!!! warning "speed 未設定はリトライなし（dynamic モード）"
    `buffermgrdyn` では speed が未設定の状態で `CABLE_LENGTH` を書いても headroom 計算はスキップされ、
    **リトライキューに残らない**。speed が後着した際に `handlePortTable()` から再処理されるが、
    speed 未着のまま `CABLE_LENGTH` だけ先に書いても lossless PG は設定されない。

### テーブル出力方向

`CABLE_LENGTH` は **上流テーブル** であり、`BUFFER_PG` / `BUFFER_PROFILE` は下流（自動生成）テーブルである。
`buffermgrdyn` は speed・cable_length・mtu が揃った時点で `refreshPgsForPort()` → `allocateProfile()` を呼び、
`APPL_DB.BUFFER_PG` と `APPL_DB.BUFFER_PROFILE` を自動生成・上書きする。
dynamic モードでは `BUFFER_PG` を手動書き込みすることは非推奨。

### PORT admin down 時の挙動

PORT が admin down 状態では `refreshPgsForPort()` を呼ばない (`buffermgrdyn.cpp:1454-1456`)。
admin down ポートへの `CABLE_LENGTH` 更新は headroom に反映されない（admin up になった時点で再処理）。

### 起動時シーケンス (dynamic モード)

```
BUFFER_POOL (ingress_lossless_pool) 設定
  ↓
PORT テーブル (speed, mtu) 設定 → portsyncd が PortInitDone を APPL_DB に書き込む
  ↓
m_portInitDone = true → buffermgrdyn がバッファプールサイズ更新開始
  ↓
CABLE_LENGTH エントリを書き込む
  ↓
handleCableLenTable() → refreshPgsForPort() → allocateProfile()
  ↓
APPL_DB.BUFFER_PROFILE / BUFFER_PG 生成 → bufferorch → SAI buffer API
```

実運用では `config qos reload` と `config load_minigraph` が Jinja テンプレート
(`buffers_config.j2`) から PORT / CABLE_LENGTH / BUFFER_POOL を一括生成するため、
順序は sonic-cfggen が暗黙に担保する。

<!-- /ordering -->

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

YANG default と別に、コード側で「フィールド不在時の fallback」が実装されている field を全列挙する。

| field | YANG default | コード default | 適用箇所 | 種別 | evidence |
|---|---|---|---|---|---|
| `name` (エントリキー) | — | `"AZURE"` ハードコード | `buffers_config.j2:232` | ハードコード固定値 | buffers_config.j2:232 |
| `name` (複数エントリ) | — | CLI は `keys[0]` のみ更新 (2番目以降 silent drop) | `config/main.py:6349` | silent drop | config/main.py:6344 |
| `length` | — | `"None"` → buffermgr が更新スキップ (silent no-op) | `buffermgr.cpp:104` | silent drop | buffermgr.cpp:104 |
| `length` | — | `"0m"` → lossless PG 削除 (特殊値) | `buffermgr.cpp:159`, `buffermgrdyn.cpp:1492` | 値依存挙動乖離 | buffermgr.cpp:159 |
| `length` | — | DPC ポート → 強制 `"0m"` (neighbor role 無視) | `buffers_config.j2:109` | ハードコード固定値 | buffers_config.j2:109 |
| `length` | — | `Ethernet-BP` (VoQ backplane) → `"5m"` | `buffers_config.j2:115` | ハードコード固定値 | buffers_config.j2:115 |
| `length` | — | ロール別デフォルト: `torrouter_server`=`5m`, `leafrouter_torrouter`=`40m`, `spinerouter_leafrouter`=`300m`, `lowerspinerouter_leafrouter`=`500m` 等 | `buffers_config.j2:54-72` | ハードコード固定値 | buffers_config.j2:54 |
| `length` | — | HWSKU `default_cable`: `td2`→`0m`, `th(t0)`→`5m`, `th(t1)`→`40m`, `th5`→`5m`, `th2/7260(t1)`→`300m` 等 (プラットフォーム依存) | `buffers_defaults_*.j2` | プラットフォーム依存 | device/common/profiles/ |
| `length` (間接) | — | mtu 未設定時に `DEFAULT_MTU_STR="9100"` で仮 headroom 計算 (後で mtu 設定時に再計算) | `buffermgrdyn.cpp:2174` | fallback / 経路依存乖離 | buffermgrdyn.h:15 |
| (エントリ全体) | — | `config load_minigraph`: DB + template をポート単位 partial merge (DB 側の既存ポートは維持) | `config/main.py:3911-3915` | 書き込み時 vs 実行時乖離 | config/main.py:3911 |

### 該当なし field (探したが fallback 無し)

- `length` の YANG パターン (`[0-9]+m`) 違反値 → YANG バリデーションで拒否される (コード側 fallback なし)

<!-- /defaults -->
