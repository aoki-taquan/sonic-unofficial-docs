---
title: MGMT_VRF_CONFIG テーブル
description: "MGMT_VRF_CONFIG テーブル — 管理 VRF（OOB 管理トラフィックをデータプレーンから分離する）のグローバル ON/OFF を保持するシングルトンテーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mgmt_vrf.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MGMT_VRF_CONFIG
    - NTP
    - MGMT_INTERFACE
  cli:
    - config vrf
  yang:
    - sonic-mgmt_vrf
---

# MGMT_VRF_CONFIG テーブル

## 概要

管理 [VRF](../../reference/glossary.md#term-vrf)（OOB 管理トラフィックをデータプレーンから分離する）のグローバル ON/OFF を保持するシングルトンテーブル[^1]。`hostcfgd` が監視し、有効化されると Linux カーネル側に `mgmt` という名前の [VRF](../../reference/glossary.md#term-vrf) を作成し、management port (`eth0`) を所属させる。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>MGMT_VRF_CONFIG")]
  DM["vrfmgrd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
MGMT_VRF_CONFIG|vrf_global
```

container 構造のため key は固定文字列 `vrf_global`。

## フィールド

| フィールド | 型 | 既定値 | 説明 |
|-----------|----|--------|------|
| `mgmtVrfEnabled` | boolean | `false` | 管理 [VRF](../../reference/glossary.md#term-vrf) を有効化するか |

## 制約

- フィールドは 1 つのみ。シンプルなトグル
- 他テーブルから `must` で参照される。たとえば `NTP/global/vrf` が `mgmt` のとき本フィールドが `true` でないとバリデーション失敗

## 購読者

- `hostcfgd` (host-services): カーネル `mgmt` VRF の作成・削除、`eth0` の所属切替、関連サービス (snmp, ssh, ntp 等) の VRF 適用

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): [`NTP`](./ntp-global.md)、`MGMT_INTERFACE`、`MGMT_PORT`、`SNMP_AGENT_ADDRESS_CONFIG`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-mgmt_vrf`
- 関連 CLI: `config vrf add mgmt` / `config vrf del mgmt`（CLI ヘルパが本フィールドを書き換える）

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-mgmt_vrf`](../yang/sonic-mgmt_vrf.md)
- CLI: [`config vrf`](../cli/config-vrf.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-mgmt_vrf.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-mgmt_vrf.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `MGMT_VRF_CONFIG|vrf_global`。
- `mgmtVrfEnabled`: `true` で eth0 を `mgmt` VRF に分離。

### よくある誤設定

- mgmt VRF を有効化したのに NTP/[SNMP](../../reference/glossary.md#term-snmp)/SYSLOG 側で vrf 指定を忘れて疎通しない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'MGMT_VRF_CONFIG|vrf_global'
show mgmt-vrf
```
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-swss/cfgmgr/vrfmgr.cpp VrfMgr::doTask / sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mgmt_vrf.yang -->

- **mgmtVrfEnabled=false または in_band_mgmt_enabled=false → SET が DEL として処理**: `vrfmgr.cpp` L257 — 両条件のいずれかが false の場合、SET コマンドが受信されても op を `DEL_COMMAND` に上書きして管理 VRF を削除する。
- **既に VRF が存在する状態での SET → スキップ**: `m_vrfTableMap` に "mgmt" が既に存在する場合、エントリを消費してスキップ（重複 SET 無効化）。
- **存在しない VRF への DEL → スキップ**: `m_vrfTableMap` に "mgmt" が存在しない状態での DEL もスキップ。
- **VRF netdev 作成失敗 → SWSS_LOG_ERROR**: `setLink()` 失敗時に `"Failed to create vrf netdev %s"` をログ。処理は継続されるが netdev が未作成の状態になる。
- **mgmtVrfEnabled のデフォルト = false**: YANG `default false`。エントリが存在しない場合は管理 VRF 無効として扱われる。NTP で `vrf = "mgmt"` を使う場合は先に `true` に設定する必要がある。

<!-- value-behavior -->
## 値依存挙動マトリクス

<!-- evidence: sonic-swss/cfgmgr/vrfmgr.cpp / sonic-host-services/scripts/hostcfgd update_mgmt_vrf() -->

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `mgmtVrfEnabled` | `false` (default) | mgmt VRF を作成しない。eth0 はデフォルト VRF に所属 |
| `mgmtVrfEnabled` | `true` | Linux カーネルに `mgmt` VRF (table ID 6000) を作成。eth0 を mgmt VRF に所属させる |
| `mgmtVrfEnabled` | `false` → `true` 変更 | vrfmgr が VRF netdev 作成 + hostcfgd が `stop chrony` → `restart interfaces-config` → `start chrony` を実行 |
| `mgmtVrfEnabled` | `true` → `false` 変更 | vrfmgr.cpp が SET を DEL_COMMAND に変換して VRF netdev 削除 + サービス再起動 |

enum なし (boolean)。`NTP.vrf=mgmt` は本フィールドが `true` の場合のみ YANG バリデーション通過。
<!-- /value-behavior -->


<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **hostcfgd** (`sonic-host-services/scripts/hostcfgd`): `MGMT_VRF_CONFIG` テーブルを `ConfigDBConnector` で購読。

### 段階 2: CFG → APPL 翻訳

- hostcfgd が `mgmtVrfHandler` を呼び出し、`mgmt` VRF を作成または削除する。
- APP_DB への書き込みは行わない (カーネル直接操作)。

### 段階 3: APPL → SAI

- SAI 経由なし。`ip vrf add mgmt` / `ip vrf del mgmt` をシステムコールで実行。
- `/etc/iproute2/rt_tables` に mgmt VRF エントリを追加。

### 段階 4: タイミング + 副作用

- VRF 作成は即時 (カーネルコール)。eth0 を mgmt VRF に移すまでに一時的な接続断が生じる。
- 副作用: `mgmtVrfEnabled = true` 時に eth0 が mgmt namespace に移動。SSH 接続が一時的に切断される可能性。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

MGMT_VRF_CONFIG テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config vrf add mgmt` / `config vrf del mgmt` — `config/main.py` が `mod_entry('MGMT_VRF_CONFIG', 'vrf_global', {'mgmtVrfEnabled': 'true/false'})` を呼ぶ (sonic-utilities/config/main.py:4107, 4121)

### minigraph / sonic-cfggen

minigraph.py で `MGMT_VRF_CONFIG` は生成されない

### REST / gNMI

sonic-mgmt-common トランスフォーマーなし — REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での MGMT_VRF_CONFIG マイグレーションなし

### ビルド時デフォルト (build-time default)

`files/build_templates/init_cfg.json.j2` にデフォルトなし — CLI でのみ作成

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- glossary-links-injected: ca16c59f26d9 -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

| 派生先フィールド | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| `MGMT_VRF_CONFIG` エントリ全体 | minigraph.py が `<MgmtVrf>` XML ノードを解析したとき | `{'mgmtVrfEnabled': 'true'}` または `{}` (未設定) | `sonic-buildimage/src/sonic-config-engine/minigraph.py:2308` |

`results['MGMT_VRF_CONFIG'] = mvrf` の `mvrf` は XML `MgmtVrf` ノードの有無で決まる。

### Phase 7: 条件付き登録

`MGMT_VRF_CONFIG` は orchagent では処理されない。`vrfmgrd` (`cfgmgr/vrfmgr.cpp`) が CONFIG_DB を購読しカーネル VRF を設定する。条件付き platform 登録なし。

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| minigraph.py MGMT_VRF_CONFIG | 1 | `minigraph.py:2308` |

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

`vrfmgr.cpp` が `MGMT_VRF_CONFIG` を処理する:

| Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `VrfMgr` | `doTask()` | `mgmtVrfEnabled == "true"` | `ip link add mgmt type vrf table 1` でカーネル管理 VRF を作成 | `sonic-swss/cfgmgr/vrfmgr.cpp:257` |
| `VrfMgr` | `doTask()` | `mgmtVrfEnabled == "false"` または未設定 | VRF 削除処理 (`ip link del mgmt`) または スキップ | `sonic-swss/cfgmgr/vrfmgr.cpp` |
| `VrfMgr` | `doTask()` | 値が `"false"` → DEL として強制変換 | `mgmtVrfEnabled=false` の SET は DEL 相当として処理 | `sonic-swss/cfgmgr/vrfmgr.cpp:257` |

> **スキャン証跡**: minigraph.py:2308 および vrfmgr.cpp:257 を確認、3 件分岐抽出 — 誤読なし。

<!-- /handler-branching -->

<!-- ordering -->
## 書込み順序依存・タイミング依存 (Phase B)

<!-- evidence: sonic-swss/cfgmgr/vrfmgr.cpp / sonic-host-services/scripts/hostcfgd MgmtIfaceCfg.update_mgmt_vrf() -->

### MGMT_VRF_CONFIG 作成順序（vrfmgr）

`MGMT_VRF_CONFIG|vrf_global` に `mgmtVrfEnabled=true` を書き込んだ場合、`vrfmgr` の `setLink("mgmt")` は通常 VRF と異なり `ip link add` を実行せず、テーブル ID 6000 を内部 map に登録するのみ（`vrfmgr.cpp:176-183`）。実際の kernel VRF netdev 作成は後続の hostcfgd が `interfaces-config` restart 経由で実施する（責務分離）。

DEL 処理は `STATE_VRF_OBJECT_TABLE` に orchagent が "mgmt" オブジェクトを登録するまでループ待機する（`vrfmgr.cpp:331-335`）。orchagent の処理完了前は `delLink()` が実行されず kernel netdev が残存し続ける。

### kernel netns 順序（hostcfgd）

`update_mgmt_vrf()` (`hostcfgd:1659-1662`) は以下の**固定順序**でサービスを操作し、`eth0` を `mgmt` VRF に所属させる:

```
1. systemctl stop chrony
2. systemctl restart interfaces-config   # eth0 → mgmt VRF への移動
3. systemctl start chrony                # mgmt VRF 内で bind し直し
```

`interfaces-config` restart 失敗時は `subprocess.CalledProcessError` が送出され、chrony は停止したままになる（自動復旧なし）。

`mgmtVrfEnabled=true` 完了後、`/proc/net/route` に eth0 のデフォルトルート (metric 202) が残存していれば追加で削除する（`hostcfgd:1693`）。

### 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | vrfmgr `setLink` → hostcfgd `interfaces-config` → kernel `mgmt` netdev 作成 | 順次非同期 | APP_VRF_TABLE 登録と kernel netdev 作成は別タイミング（中間状態あり） |
| 2 | DEL: STATE_VRF_OBJECT_TABLE orchagent 削除 → vrfmgr `delLink` が unblock | DEL 待機ループ | orchagent 完了待ち；タイムアウトなし |
| 3 | `stop chrony` → `restart interfaces-config` → `start chrony` | 固定強制順序 | 途中失敗で chrony 停止のまま残存（手動 `systemctl start chrony` が必要） |
| 4 | `MGMT_VRF_CONFIG=true` 確立後 → `NTP|global.vrf=mgmt` 設定 | 先行必須 | CLI は YANG reject；DB 直書き時は bypass されるためバリデーション欠如に注意 |
| 5 | 同値再書き込み → silent drop（`interfaces-config` restart なし） | 即時スキップ | 意図的なサービス再起動には値変更（`false`→`true`）が必要 |
| 6 | 起動時: non-warm-restart でも `mgmt` VRF netdev は削除されない | 起動時保護 | `vrfmgr.cpp:73-79` のスキップにより double-create 防止 |

<!-- /ordering -->
