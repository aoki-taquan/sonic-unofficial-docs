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

<!-- ordering -->
## 書込み順依存 (Phase B — BGP_PEER_CONFIGURED_TABLE)

STATE_DB `BGP_PEER_CONFIGURED_TABLE` への書き込みは `BGPPeerMgrBase.update_state_db()` が担い、**FRR への設定 push が完了した直後にのみ**実行される。これはテーブルを「FRR 設定投入完了」の確認フラグとして利用する SDN コントローラ向けの設計上の制約である。

### SET: FRR push 成功後にのみ STATE_DB へ書き込む

`add_peer()` では FRR コマンドを `apply_op`（= `cfg_mgr.push`）で送信した直後に `update_state_db(..., "SET")` を呼ぶ。テンプレートのレンダリングエラー (`jinja2.TemplateError`) が発生した場合は `return True` するが `update_state_db` は呼ばれず、STATE_DB には書き込まれない（FRR も未設定のまま）。<!-- evidence: managers_bgp.py:229-239 -->

### admin_status 変更: FRR push 成功確認後に SET

`apply_admin_status()` は `apply_op` の戻り値 (`ret_code`) が `True` のときのみ `update_state_db(..., "SET")` を実行する。`apply_op` は内部で `cfg_mgr.push` を呼び常に `True` を返すため、push が例外なく完了した場合に STATE_DB が更新される。<!-- evidence: managers_bgp.py:341-356 -->

### DEL: FRR push 成功後に STATE_DB からエントリを削除

`del_handler()` は `no neighbor <addr>` を FRR に push し（`apply_op`）、`ret_code=True` を確認してから `update_state_db(..., "DEL")` を呼ぶ。DEL 側の `update_state_db` は `state_peer_table.get(key)` で存在確認してから `delete(key)` を呼ぶため、既に不在の場合は `log_warn` のみで実際には何もしない。<!-- evidence: managers_bgp.py:485-488, 292-295 -->

### DEL 前の listen range 除去（dynamic ピアのみ）

`peer_type` が `dynamic` または `sentinels` の場合、`del_handler` は FRR 10.1 以降の要件として `no bgp listen range ...` を先に発行し、その後で `no neighbor`（ピアグループ削除）を発行する。STATE_DB への DEL はピアグループ削除の後になる。<!-- evidence: managers_bgp.py:461-472 -->

### config reload 時の一時的全削除

`config reload` 処理（`sonic-utilities/config/main.py:1613`）は `BGP_PEER_CONFIGURED_TABLE|*` を全削除する。bgpcfgd 再起動後に CONFIG_DB を replay して各ネイバーを FRR に再投入し、成功後に各エントリを SET する。reload 中（数秒〜数十秒）はエントリが存在しない状態になる。<!-- evidence: config/main.py:1613 -->

### NEIGH_STATE_TABLE との関係

`NEIGH_STATE_TABLE`（書き込み元: bgpmon）と `BGP_PEER_CONFIGURED_TABLE`（書き込み元: bgpcfgd）は独立したデーモンが管理するため、両テーブル間の書込み順序依存はない。bgpmon は起動時に `NEIGH_STATE_TABLE|*` を全削除してから再スキャンするが、これは `BGP_PEER_CONFIGURED_TABLE` に影響しない。<!-- evidence: bgpmon.py:51 -->

### 書込み順依存サマリ

| # | 依存関係 | 対象操作 | 違反時の挙動 |
|---|----------|---------|------------|
| 1 | FRR push（ネイバー追加） → STATE_DB SET | add_peer / SET handler | テンプレートエラー時は STATE_DB 未書込（FRR も未設定） |
| 2 | FRR push（admin_status 変更） → STATE_DB SET | change_admin_status | apply_op 例外時は STATE_DB 未更新 |
| 3 | FRR `no neighbor` → STATE_DB DEL | del_handler / DEL handler | FRR 除去前に SDN 参照するとエントリがまだ存在 |
| 4 | FRR `no listen range` → FRR `no neighbor` → STATE_DB DEL | del_handler (dynamic のみ) | listen range 除去なしに削除すると FRR 10.1 以降はエラー |
| 5 | config reload → 全削除 → bgpcfgd 再投入 | config reload | reload 中は SDN 向けにエントリが存在しない |

> 中間調査詳細: `meta/_intermediate/cdb-flow/bgp-state-ordering.md`
<!-- /ordering -->

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
