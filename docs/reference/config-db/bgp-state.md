---
title: STATE_DB BGP 状態テーブル (NEIGH_STATE_TABLE / BGP_PEER_CONFIGURED_TABLE)
description: "STATE_DB の BGP 隣接状態テーブル群。bgpmon デーモンが 15 秒周期で FRR vtysh から取得した BGP ネイバー状態を NEIGH_STATE_TABLE に書き込み、bgpcfgd は CONFIG_DB のネイバー設定をプログラム完了後に BGP_PEER_CONFIGURED_TABLE へ反映する。"
area: reference
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-bgpcfgd/bgpmon/bgpmon.py
    ref: HEAD
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py
    ref: HEAD
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: HEAD
  - repo: sonic-net/sonic-snmpagent
    path: src/sonic_ax_impl/mibs/vendor/cisco/bgp4.py
    ref: HEAD
related:
  config_db:
    - BGP_NEIGHBOR
    - BGP_PEER_RANGE
  cli:
    - show bgp summary
    - show ip bgp neighbors
  _no_related_yang: true
---

# STATE_DB BGP 状態テーブル

## 概要

STATE_DB には BGP 隣接状態を保持する 2 つのテーブルが存在する。

| テーブル名 | 書き込みデーモン | 主な利用者 |
|-----------|----------------|-----------|
| `NEIGH_STATE_TABLE` | `bgpmon` (bgp コンテナ内) | SNMP (CiscoBgp4MIB), テレメトリ |
| `BGP_PEER_CONFIGURED_TABLE` | `bgpcfgd` の `BGPPeerMgrBase` | SDN コントローラ |

`NEIGH_STATE_TABLE` は BGP セッションのライブ状態 (FRR `show bgp summary json` の出力) を表し、`BGP_PEER_CONFIGURED_TABLE` は bgpcfgd が CONFIG_DB のネイバー設定を FRR に投入済みであることを示す確認テーブルである。

## テーブル 1: NEIGH_STATE_TABLE

### key 構造

```text
NEIGH_STATE_TABLE|<neighbor_ip>
```

- `<neighbor_ip>`: BGP ネイバーの IP アドレス (IPv4 / IPv6)

bgpmon 起動時に `NEIGH_STATE_TABLE|*` のエントリがすべて削除され (bgpmon.py L51)、その後スキャン結果で再構築される。

### フィールド

| フィールド | 型 | 値域 / 説明 |
|-----------|----|------------|
| `state` | enum string | FRR のセッション状態文字列 |
| `peerType` | enum string | `"i-BGP"` または `"e-BGP"` |

`state` の値域 (snmp_ciscobgp4mib.md / bgp4.py の STATE_CODE 定義より):

| `state` 値 | SNMP 整数値 | 意味 |
|-----------|-----------|------|
| `"Idle"` または `"Idle (Admin)"` | 1 | セッション停止中 |
| `"Connect"` | 2 | TCP 接続試行中 |
| `"Active"` | 3 | TCP 接続待機中 |
| `"OpenSent"` | 4 | OPEN メッセージ送信済み |
| `"OpenConfirm"` | 5 | OPEN 確認待ち |
| `"Established"` | 6 | セッション確立済み |
| `"Clearing"` | — | セッション解除中 (FRR 独自状態) |

`peerType` は `remoteAs == localAs` のとき `"i-BGP"`、それ以外のとき `"e-BGP"` と判定される (bgpmon.py L163, L171)。

### 書き込みタイミング

`bgpmon` は 15 秒ごとに `/var/log/frr/frr.log` のタイムスタンプを確認し、変化があった場合のみ `vtysh -c 'show bgp summary json'` を実行する (bgpmon.py L59-68, L203-206)。

1. **新ネイバー検出時**: `state` + `peerType` を HSET
2. **状態変化時**: `state` + `peerType` を HSET (変化がない場合はスキップ)
3. **ネイバー消失時**: エントリを DEL
4. **bgpmon 起動時**: 全エントリを一括削除して再スキャン

Redis Pipeline (`PIPE_BATCH_MAX_COUNT = 50`) でバッチ更新される (bgpmon.py L35)。

### 購読者

- **SNMP サブエージェント** (`sonic-snmpagent/src/sonic_ax_impl/mibs/vendor/cisco/bgp4.py`): `NEIGH_STATE_TABLE|*` を読み取り CiscoBgp4MIB (cbgpPeer2State, OID `.1.3.6.1.4.1.9.9.187.1.2.5.1.3`) に変換。マルチ ASIC 構成では各 namespace の STATE_DB から収集。
- テレメトリ / 将来拡張 (snmp_ciscobgp4mib.md L33)

---

## テーブル 2: BGP_PEER_CONFIGURED_TABLE

### key 構造

```text
BGP_PEER_CONFIGURED_TABLE|<key>
```

- 静的ピア: `<key>` = VRF が `"default"` の場合はネイバー IP、それ以外は `<vrf>|<neighbor_ip>`
- 動的ピア (BGP listen range): `<key>` = `<vrf/vnet-name>|<peer-name>`

### フィールド

フィールドは CONFIG_DB のネイバー設定 (`BGP_NEIGHBOR` または `BGP_PEER_RANGE`) のキー・バリューペアをそのまま転写する。固定フィールド定義はなく、CONFIG_DB の内容に依存する。

動的ピアの代表的フィールド (Bgpcfgd-dyn-peer-modification-support.md §2.2):

| フィールド | 型 | 説明 |
|-----------|----|------|
| `ip_range` | list | listen range (IP プレフィックスのカンマ区切り) |
| `name` | string | ピア名 |
| `peer_asn` | uint string | ピアの ASN (オプション) |
| `src_address` | IP string | セッション発端 IP (オプション) |

### 書き込みタイミング

`bgpcfgd` (`BGPPeerMgrBase.update_state_db`) が FRR に設定を投入した後に書き込む (managers_bgp.py L284-303):

1. **SET (ネイバー追加/管理状態変更)**: `state_peer_table.set(key, list(sorted(data.items())))`
2. **DEL (ネイバー削除)**: `state_peer_table.delete(key)`
3. **`config reload` 時**: `sonic-utilities/config/main.py` が `BGP_PEER_CONFIGURED_TABLE|*` を全削除 (config/main.py L1613)

### 利用者

SDN コントローラが CONFIG_DB への設定投入後、このテーブルのエントリ存在を確認することで bgpcfgd による FRR 設定完了を検知する (Bgpcfgd-dyn-peer-modification-support.md §1.1)。

---

## `show bgp` コマンドとの対応

`NEIGH_STATE_TABLE` の `state` は `show bgp summary` が表示する `State/PfxRcd` 列の状態と対応する。ただし bgpmon のポーリング間隔は 15 秒であるため、リアルタイムの FRR 状態とは最大 15 秒の遅延が生じる。

<!-- constants -->
## ハードコード定数 (Phase E)

### テーブル名定数 (schema.h)

| C マクロ名 | 文字列値 | ソース |
|-----------|---------|--------|
| `STATE_BGP_PEER_CONFIGURED_TABLE_NAME` | `"BGP_PEER_CONFIGURED_TABLE"` | `sonic-swss-common/common/schema.h:511` |
| `STATE_BGP_TABLE_NAME` | `"BGP_STATE_TABLE"` | `sonic-swss-common/common/schema.h:437` |

`BGP_PEER_CONFIGURED_TABLE_NAME` は `managers_bgp.py:287` で `swsscommon.STATE_BGP_PEER_CONFIGURED_TABLE_NAME` として参照される。`NEIGH_STATE_TABLE` はソースコード中に文字列リテラルとしてハードコードされており、対応する schema.h マクロは存在しない（`bgpmon.py:51,157,179` の文字列リテラル `"NEIGH_STATE_TABLE|*"` が実体）。

### state フィールド文字列定数 (bgpmon.py)

`NEIGH_STATE_TABLE` の `state` フィールド値は FRR `show bgp summary json` の `state` キーをそのまま転写する。bgpmon.py に直接定義はなく、FRR が出力する文字列に依存する。SNMP サブエージェント (`bgp4.py`) は以下の文字列を定数的に扱う:

| `state` 文字列値 | 意味 | 備考 |
|----------------|------|------|
| `"Idle"` または `"Idle (Admin)"` | セッション停止中 | SNMP 整数値 1 |
| `"Connect"` | TCP 接続試行中 | SNMP 整数値 2 |
| `"Active"` | TCP 接続待機中 | SNMP 整数値 3 |
| `"OpenSent"` | OPEN メッセージ送信済み | SNMP 整数値 4 |
| `"OpenConfirm"` | OPEN 確認待ち | SNMP 整数値 5 |
| `"Established"` | セッション確立済み | SNMP 整数値 6 |
| `"Clearing"` | セッション解除中 (FRR 独自) | SNMP 対応なし |

### peerType フィールド文字列定数 (bgpmon.py)

| フィールド値 | 判定条件 | ソース |
|------------|---------|--------|
| `"i-BGP"` | `remoteAs == localAs` | `bgpmon.py:163,171` |
| `"e-BGP"` | `remoteAs != localAs` | `bgpmon.py:163,171` |

### 操作種別文字列定数 (managers_bgp.py)

`BGPPeerMgrBase.update_state_db` の `op` 引数として使用されるリテラル:

| 文字列値 | 用途 | ソース |
|---------|------|--------|
| `"SET"` | ネイバー追加 / 管理状態変更時に STATE_DB へ書き込む | `managers_bgp.py:239,288,353,443` |
| `"DEL"` | ネイバー削除時に STATE_DB からエントリを消す | `managers_bgp.py:487,291` |

VRF が `"default"` の場合は key = `nbr`、それ以外は `vrf + "|" + nbr` とするロジックも文字列リテラル `"default"` としてハードコードされている (`managers_bgp.py:280`)。

### ポーリング・バッチ定数 (bgpmon.py)

| 定数名 / 用途 | 値 | ソース |
|-------------|----|----|
| `PIPE_BATCH_MAX_COUNT` — Redis パイプラインのバッチ上限 | **50** | `bgpmon.py:35` |
| ポーリング sleep — bgpmon メインループの待機間隔 | **15** 秒 (`time.sleep(15)`) | `bgpmon.py:203` |
| FRR ログ確認待機 — FRR 変化なし時の sleep | **1** 秒 (`time.sleep(1)`) | `bgpmon.py:109,115` |

### ハードコードされたパス・コマンド文字列 (bgpmon.py)

| 文字列値 | 用途 | ソース |
|---------|------|--------|
| `"/var/log/frr/frr.log"` | FRR ログファイルのタイムスタンプ監視 | `bgpmon.py:61` |
| `"show bgp summary json"` | vtysh 経由で BGP ネイバー状態を取得するコマンド | `bgpmon.py:80` |
<!-- /constants -->

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

STATE_DB `NEIGH_STATE_TABLE` および `BGP_PEER_CONFIGURED_TABLE` には対応する YANG schema が存在しない。値はすべてコードレベルで決定される。

### NEIGH_STATE_TABLE

| フィールド | STATE_DB 初期値 | コード由来 | 備考 |
|-----------|---------------|----------|------|
| `state` | FRR 由来の文字列 (初期書き込み時点の FRR 状態) | `peer_dict["peers"][peer]["state"]` — bgpmon.py L74 | 固定デフォルトなし。FRR `show bgp summary json` の `state` フィールドをそのまま転写 |
| `peerType` | `"i-BGP"` または `"e-BGP"` | `"i-BGP" if remoteAs == localAs else "e-BGP"` — bgpmon.py L163, L171 | エントリ作成時に決定。bgpmon 15 秒ポーリングで再評価 |

### BGP_PEER_CONFIGURED_TABLE

| フィールド | STATE_DB 初期値 | コード由来 | 備考 |
|-----------|---------------|----------|------|
| (全フィールド) | CONFIG_DB から転写 | `data.items()` — managers_bgp.py L289 | `sorted()` でソート済みのキー・バリューペアをそのまま set |

### 補足

- `NEIGH_STATE_TABLE` はエントリ作成後も `state` / `peerType` 両フィールドが更新される (bgpmon.py L164)。状態が変化しない場合は STATE_DB への書き込みをスキップする (bgpmon.py L159-160)。
- `NEIGH_STATE_TABLE` にエントリが存在しない間 (bgpmon 起動直後、または全ネイバー消失時)、SNMP は該当 MIB オブジェクトを返さない。
- `BGP_PEER_CONFIGURED_TABLE` のフィールドセットは CONFIG_DB `BGP_NEIGHBOR` と `BGP_PEER_RANGE` で異なる。静的ピアには `ip_range` は存在しない。
- bgpmon 起動時 (`__init__`) に `NEIGH_STATE_TABLE|*` を全削除してから再スキャンするため、コンテナ再起動直後は最大 15 秒間エントリが存在しない場合がある。
<!-- /defaults -->

<!-- platform -->
## プラットフォーム差分 (Phase H — コード由来)

`BGP_PEER_CONFIGURED_TABLE` を書き込む `BGPPeerMgrBase.update_state_db()`（managers_bgp.py L271–304）
および `NEIGH_STATE_TABLE` を書き込む `bgpmon.py` には、`switch_type`・`sub_role`・
`DEVICE_METADATA.localhost.type` による分岐が**一切存在しない**。

両テーブルのスキーマ・フィールドはすべてのプラットフォームで同一である。

### 根拠

| 検索対象 | 結果 |
|---------|------|
| `switch_type` in managers_bgp.py | 0 件（分岐なし） |
| `sub_role` in managers_bgp.py | 0 件（分岐なし） |
| `is_chassis()` in managers_bgp.py | 0 件（分岐なし） |
| `localhost/type` | deps 依存ガード登録のみ、値参照なし（L120） |
| bgpmon.py の platform 分岐 | 0 件（分岐なし） |

`localhost/type` は `BGPPeerMgrBase.__init__` の deps リスト（L120）に登録されているが、
これは swsscommon の依存性ガード（キーが CONFIG_DB に存在するまで handler 呼び出しをブロック）
として利用されているだけであり、値による動作の切り替えには使われていない。

### マルチ ASIC 構成での動作（テーブル内容に変化なし）

マルチ ASIC 構成では、bgpmon および bgpcfgd は各 ASIC コンテナ内で独立して動作し、
それぞれの namespace 内 STATE_DB に書き込む。テーブルのスキーマ・フィールドに変化はない。

**SNMP 読み取り側**（`sonic-snmpagent/src/sonic_ax_impl/mibs/vendor/cisco/bgp4.py` L22, L29–30）
のみマルチ ASIC 対応が存在する。`Namespace.init_namespace_dbs()` で全 namespace（asic0, asic1, …）
の STATE_DB 接続リストを生成し、`dbs_keys_namespace()` で全 namespace の
`NEIGH_STATE_TABLE|*` を横断収集して CiscoBgp4MIB を組み立てる。
これは読み取り側の集約動作であり、テーブル自体のスキーマには影響しない。

### 備考: BGP_VOQ_CHASSIS_NEIGHBOR / BGP_INTERNAL_NEIGHBOR との関係

プラットフォーム固有の BGP セッションは `BGP_NEIGHBOR` ではなく
`BGP_VOQ_CHASSIS_NEIGHBOR`（VoQ シャーシ）または `BGP_INTERNAL_NEIGHBOR`（マルチ ASIC / chassis-packet）
テーブルに書き込まれる（minigraph.py によるテーブル振り分け）。
これらのセッションが bgpcfgd で処理される際も、`BGP_PEER_CONFIGURED_TABLE` への
書き込みロジック（`update_state_db`）は同一コードが使用される。
<!-- /platform -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

### BGP_PEER_CONFIGURED_TABLE — 書き込みのみ / 購読者なし

`bgpcfgd` の `BGPPeerMgrBase.update_state_db()` (managers_bgp.py L271-303) が `swsscommon.Table` 経由で直接 STATE_DB へ HSET / DEL を発行する。`swsscommon.Table` は **ProducerStateTable ではない** ため、専用通知チャンネルへの PUBLISH は行わない。

```
bgpcfgd (BGPPeerMgrBase.update_state_db)
  → swsscommon.Table.set() / delete()
    → Redis HSET / DEL (STATE_DB DB=6)
      → BGP_PEER_CONFIGURED_TABLE|<key>
```

keyspace notification (`__keyspace@6__:BGP_PEER_CONFIGURED_TABLE|*`) は STATE_DB では通常無効であり、アクティブに購読するデーモンは **存在しない**。

#### 根拠

- `managers_bgp.py` 内に `subscribe`・`psubscribe`・`keyspace`・`notify` を含む記述はゼロ件
- HLD (`Bgpcfgd-dyn-peer-modification-support.md §1.1`) が「SDN コントローラはポーリングで確認する」設計を明示

#### 消費パターン (ポーリング)

| 利用者 | アクセス方法 |
|--------|------------|
| SDN コントローラ | `EXISTS` / `HGETALL BGP_PEER_CONFIGURED_TABLE|<key>` のポーリング — bgpcfgd による FRR 設定投入完了を検知するため |
| `show` コマンド系 | `sonic-db-cli STATE_DB keys 'BGP_PEER_CONFIGURED_TABLE|*'` などによる手動確認 |

### NEIGH_STATE_TABLE — bgpmon ポーリング書き込み / SNMP 読み取り

`bgpmon` が 15 秒周期で FRR から取得した状態を `NEIGH_STATE_TABLE` へ書き込む。SNMP サブエージェントは `NEIGH_STATE_TABLE|*` を **ポーリング読み取り** して CiscoBgp4MIB に変換する。Redis Pub-Sub / keyspace notification は使用しない。

詳細は `meta/_intermediate/cdb-flow/bgp-state-pubsub.md` を参照。
<!-- /pubsub -->

## 引用元

[^1]: `sonic-buildimage/src/sonic-bgpcfgd/bgpmon/bgpmon.py` (L37-51 BgpStateGet.__init__, L70-76 update_new_peer_states, L154-189 update_neigh_states, L163,171 peerType 判定). <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-bgpcfgd/bgpmon/bgpmon.py>

[^2]: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` (L284-303 update_state_db). <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py>

[^3]: `sonic-net/SONiC/doc/snmp/snmp_ciscobgp4mib.md` (NEIGH_STATE_TABLE スキーマ定義, L27-32). <https://github.com/sonic-net/SONiC/blob/master/doc/snmp/snmp_ciscobgp4mib.md>

[^4]: `sonic-net/SONiC/doc/BGP/Bgpcfgd-dyn-peer-modification-support.md` (BGP_PEER_CONFIGURED_TABLE スキーマ定義, §2.2). <https://github.com/sonic-net/SONiC/blob/master/doc/BGP/Bgpcfgd-dyn-peer-modification-support.md>

[^5]: `sonic-swss-common/common/schema.h` (L437 STATE_BGP_TABLE_NAME, L511 STATE_BGP_PEER_CONFIGURED_TABLE_NAME). <https://github.com/sonic-net/sonic-swss-common/blob/master/common/schema.h>

## 確認コマンド

```bash
# NEIGH_STATE_TABLE の全エントリ確認
sonic-db-cli STATE_DB keys 'NEIGH_STATE_TABLE|*'
sonic-db-cli STATE_DB hgetall 'NEIGH_STATE_TABLE|10.0.0.1'

# BGP_PEER_CONFIGURED_TABLE の全エントリ確認
sonic-db-cli STATE_DB keys 'BGP_PEER_CONFIGURED_TABLE|*'
sonic-db-cli STATE_DB hgetall 'BGP_PEER_CONFIGURED_TABLE|10.0.0.1'

# FRR から直接 BGP ネイバー状態を取得 (bgpmon の参照元と同じコマンド)
vtysh -c 'show bgp summary json'
```
