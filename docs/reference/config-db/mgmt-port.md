---
title: MGMT_PORT テーブル
description: "MGMT_PORT テーブル — 帯域外管理 (out-of-band) ポート (eth0, eth1, ...) の物理プロパティを保持する。hostcfgd が読み出して Linux 側の /etc/network/interfaces を更新する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mgmt_port.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MGMT_PORT
    - MGMT_INTERFACE
  cli:
    - config interface
  yang:
    - sonic-mgmt_port
---

# MGMT_PORT テーブル

## 概要

帯域外管理 (out-of-band) ポート (`eth0`, `eth1`, ...) の物理プロパティを保持する[^1]。`hostcfgd` が読み出して Linux 側の `/etc/network/interfaces` を更新する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>MGMT_PORT")]
  DM["mgmt-framework"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
MGMT_PORT|<name>
```

`<name>` は正規表現 `eth([1-3][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[0-9])` に合致する管理 IF 名（例: `eth0`）。

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | string `eth\d+` | ✅ | - | 管理 IF 名 |
| `speed` | uint16 (`10`/`100`/`1000`) | - | - | 速度 [Mbps] |
| `autoneg` | string `on`/`off` | - | - | 自動ネゴシエーション |
| `alias` | string | - | - | 別名 |
| `description` | string | - | - | 説明 |
| `mtu` | uint16 (1500..9216) | - | `1500` | MTU |
| `admin_status` | `admin_status` | - | `up` | 管理状態 |

## 購読者

- `hostcfgd`: `/etc/network/interfaces` への展開、`ifconfig` / `ethtool` 系操作
- `sonic-host-services`

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `MGMT_INTERFACE`（IP 設定）、`MGMT_VRF_CONFIG`（mgmt [VRF](../../reference/glossary.md#term-vrf)）
- 関連 CLI: `config interface speed/mtu eth0 ...`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-mgmt_port`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-mgmt_port`](../yang/sonic-mgmt_port.md)
- CLI: [`config interface`](../cli/config-interface.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-mgmt_port.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-mgmt_port.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `MGMT_PORT|eth0`。
- `admin_status`: `up`、`alias`: `eth0`、`description`: 任意の説明。

### よくある誤設定

- MGMT_PORT を down にすると SSH 経由で復旧不能になり物理 console が必要になる。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'MGMT_PORT|eth0'
show management_interface address
```
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mgmt_port.yang -->

- **speed が 10/100/1000 以外 → YANG が拒否**: `range "10|100|1000"` で管理ポートの速度を制約。Mbps 単位で指定し、それ以外の値は YANG バリデーションで拒否される。
- **autoneg が "on"/"off" 以外 → YANG が拒否**: `pattern "on|off"` による制約。
- **MTU が 1500-9216 の範囲外 → YANG が拒否 (デフォルト 1500)**: `range "1500..9216"` / `default 1500`。フィールド省略時は 1500 バイトとして扱われる。
- **admin_status のデフォルト = "up"**: `default up`。省略時は管理ポートが有効状態として扱われる。
- **インターフェース名の制約**: `pattern 'eth([1-3][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[0-9])'`。eth0 系のみ許可され、不正名は YANG バリデーションで拒否される。

<!-- value-behavior -->
## 値依存挙動マトリクス

<!-- evidence: sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mgmt_port.yang / sonic-host-services/scripts/hostcfgd -->

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `admin_status` | `up` (default) | eth0 を管理状態 UP に設定 |
| `admin_status` | `down` | eth0 を管理状態 DOWN に設定。OOB 管理が切断される |
| `speed` | `10`/`100`/`1000` | ethtool で該当速度を強制設定 |
| `speed` | 未設定 | ethtool 速度設定なし (autoneg 任せ) |
| `autoneg` | `on` | ethtool でオートネゴシエーション有効化 |
| `autoneg` | `off` | ethtool でオートネゴシエーション無効化。speed 指定を推奨 |
| `mtu` | 1500 (default) | eth0 MTU を 1500 に設定 |
| `mtu` | 1501..9216 | eth0 MTU を指定値に設定 (Jumbo frame) |

enum: `admin_status` = `up`/`down`。
<!-- /value-behavior -->


<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **hostcfgd** (`sonic-host-services/scripts/hostcfgd`): `MGMT_PORT` テーブルを `ConfigDBConnector` で購読。
- スレッド: hostcfgd メインループ内で `subscribe` コールバック登録。

### 段階 2: CFG → APPL 翻訳

- hostcfgd が `MGMT_PORT` エントリを受け取り、`/etc/network/interfaces.d/` 向け設定断片を `j2` テンプレートで生成。
- CFG→APP_DB への書き込みは行わない (カーネル直接設定)。

### 段階 3: APPL → SAI

- SAI 経由なし。`ifconfig`/`ethtool` を syscall で直接発行して eth0 の speed/MTU/admin_status を設定。
- 再起動時は `ifupdown2` が `/etc/network/interfaces` を読み込んでカーネル設定を復元。

### 段階 4: タイミング + 副作用

- CONFIG_DB への書き込み後、hostcfgd コールバックは数秒以内にカーネル設定を反映する。
- サービス再起動 (`systemctl restart networking`) が必要な場合もある。
- 副作用: eth0 admin down 時に SSH セッションが切断される可能性がある。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

MGMT_PORT テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config interface mgmt ...` — なし (管理ポートは通常 minigraph/sonic-cfggen で投入)

### minigraph / sonic-cfggen

**minigraph.py** `parse_device_desc_xml()` が管理インターフェース名と速度を抽出し `results['MGMT_PORT']` に投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py:2281–2296)

### REST / gNMI

sonic-mgmt-common の MGMT_PORT トランスフォーマーなし — REST/gNMI 書き込みは未実装

### db_migrator

db_migrator.py での MGMT_PORT マイグレーションなし

### ビルド時デフォルト (build-time default)

`files/build_templates/init_cfg.json.j2` に MGMT_PORT エントリなし (JSON 手動定義 or minigraph 由来)

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

MGMT_PORT へのプログラム書き込みは minigraph 経由が唯一の実装経路
<!-- /entry-points -->

<!-- glossary-links-injected: b5626ca1f0f9 -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

| 派生先フィールド | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| `MGMT_PORT` エントリ全体 | minigraph.py が XML `ManagementIPInterfaces` を解析したとき | `{'alias': alias, 'admin_status': 'up'}` | `sonic-buildimage/src/sonic-config-engine/minigraph.py:2294` |
| `admin_status` | minigraph.py 固定値 | `"up"` (常時) | `minigraph.py:2294` |
| `speed` | `port_speeds_default` dict にエイリアスが存在する場合のみ | platform 定義のデフォルト速度 (例 `1000`) | `minigraph.py:2295-2296` |

### Phase 7: 条件付き登録

`MGMT_PORT` は orchagent では処理されない。`portmgrd` 系が CONFIG_DB の変更を受けてカーネル管理ポートを設定する。条件付き platform 登録なし。

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| minigraph.py MGMT_PORT 設定 | 3 | `minigraph.py:2281,2294-2296` |

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

> **訂正 (Phase A 調査)**: `portmgr.cpp` / `portmgrd` は `CFG_PORT_TABLE_NAME`（= `"PORT"`、データポート）のみを購読し、`MGMT_PORT` テーブルは処理しない (`sonic-swss/cfgmgr/portmgrd.cpp:28`)。以下は実際の MGMT_PORT コンシューマ。

| Handler | 処理内容 | 効果 | evidence |
|---|---|---|---|
| `mgmt_oper_status.py` | CONFIG_DB 全フィールドを STATE_DB へ同期 + `/sys/class/net/<port>/operstate` を読み oper_status を更新 | STATE_DB `MGMT_PORT_TABLE\|eth0` の更新 | `sonic-buildimage/files/image_config/monit/mgmt_oper_status.py:16-51` |
| `lldpd.conf.j2` | `alias` フィールドを参照 | LLDP portidsubtype local に alias 値を設定 | `sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2:17-18` |
| `sonic-snmpagent` | `alias` フィールドを読み取り (`get('alias', if_name)`) | SNMP MIB インタフェーステーブルに alias を返却、未設定時は if_name (eth0) をフォールバック | `sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py:270` |

> **スキャン証跡**: minigraph.py:2281-2296 確認。admin_status は常時 "up" で固定であることを確認 — 誤読なし。portmgrd.cpp:28 確認、CFG_PORT_TABLE_NAME="PORT" のみ購読。

<!-- /handler-branching -->

<!-- defaults -->
## 暗黙デフォルト・コード由来フォールバック (Phase A)

<!-- evidence: sonic-buildimage/src/sonic-config-engine/minigraph.py / sonic-buildimage/files/image_config/monit/mgmt_oper_status.py / sonic-swss/cfgmgr/portmgr.h / sonic-buildimage/files/image_config/interfaces/interfaces.j2 / sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py -->

| フィールド | 種別 | 暗黙デフォルト / 挙動 | ソース |
|---|---|---|---|
| `admin_status` | YANG default + ハードコード注入 | YANG default `up`。minigraph は常時 `"up"` を注入。フィールド省略時も YANG が `up` を返す | `sonic-mgmt_port.yang:74`, `minigraph.py:2294` |
| `mtu` | dead write | YANG default `1500`。STATE_DB へは同期されるが `/etc/network/interfaces` に展開されず eth0 の実 MTU は変化しない | `sonic-mgmt_port.yang:68`, `interfaces.j2` (MGMT_PORT.mtu 参照なし) |
| `speed` | dead write + プラットフォーム依存 | minigraph が HwSku の `ManagementInterface/Speed` 要素から取得した場合のみ書き込む。フィールドが存在しても ethtool による実際の速度変更は行われない | `minigraph.py:1683-1690, 2295-2296` |
| `autoneg` | dead field | YANG 定義あり、実装コンシューマなし。設定しても eth0 の autoneg は変化しない | `sonic-mgmt_port.yang:46-51` (コンシューマなし) |
| `description` | dead field | YANG 定義あり、実装コンシューマなし | `sonic-mgmt_port.yang:57-60` (コンシューマなし) |
| `alias` | implicit fallback | 省略時: SNMP MIB が `if_name` (例: `eth0`) をフォールバック返却。LLDP は portidsubtype を `mgmt_if.port_name` にフォールバック | `sonic-snmpagent/mibs/__init__.py:270`, `lldpd.conf.j2:19` |

### YANG-実装 discrepancy

- **`portmgr.cpp` は MGMT_PORT を処理しない**: `portmgrd` は `PORT`（データポート）テーブルのみを購読。Phase 8 の旧記述は誤り。`DEFAULT_ADMIN_STATUS_STR="down"` / `DEFAULT_MTU_STR="9100"` はデータポート専用定数でありマネジメントポートには無関係 (`sonic-swss/cfgmgr/portmgr.h:14-15`)。
- **`mtu` / `speed` / `autoneg` の書き込み→読み取り非対称**: CONFIG_DB に書き込んでも eth0 の物理設定に反映するコードが存在しない。YANG バリデーションは通過するが実効性がない (silent accept / dead write)。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`MGMT_PORT` は orchagent / SAI を経由しない。Consumer は `mgmt_oper_status.py`（monit スクリプト）と `lldpd.conf.j2` のみであり、書込み順依存は CONFIG_DB → STATE_DB の一方向で完結する。

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | CONFIG_DB 起動完了 → MGMT_PORT 書込み | 強制先行 | minigraph / 手動投入は CONFIG_DB 起動後のみ実行される |
| 2 | MGMT_PORT エントリ存在 → STATE_DB `MGMT_PORT_TABLE` 更新 | **強制先行** | エントリが存在しない場合 `mgmt_oper_status.py` は STATE_DB を更新せず `LOG_DEBUG` で終了 (`mgmt_oper_status.py:17-19`) |
| 3 | MGMT_PORT と MGMT_INTERFACE の同時書込み (minigraph 経由) | 同一関数内で同期 | REST/gNMI は MGMT_PORT を書き込まないため、非 minigraph 経路では各テーブルが個別に書き込まれる可能性がある |
| 4 | orchagent / SAI 依存 | **なし** | `portmgrd.cpp:28` は `CFG_PORT_TABLE_NAME`（= `"PORT"`）のみ購読。MGMT_PORT は SAI 経由なし |

### 主要な制約詳細

**MGMT_PORT エントリ不在時の STATE_DB 非更新 (依存 #2)**: `mgmt_oper_status.py` は冒頭で `db.keys(db.CONFIG_DB, 'MGMT_PORT|*')` を確認し、キーが存在しない場合は `syslog LOG_DEBUG` を出力して即座に `sys.exit(0)` する。このため CONFIG_DB に MGMT_PORT エントリが投入される前は `STATE_DB MGMT_PORT_TABLE` が空のままとなり、`show management_interface address` や SNMP MIB が旧ステータスを返す可能性がある (evidence: `mgmt_oper_status.py:16-19`)。

**minigraph による MGMT_PORT + MGMT_INTERFACE のアトミック書込み (依存 #3)**: `minigraph.py:2281-2308` では `results['MGMT_PORT']`・`results['MGMT_INTERFACE']`・`results['MGMT_VRF_CONFIG']` を同一関数 `parse_device_desc_xml()` 内で生成し、`sonic-cfggen` が CONFIG_DB へ一括書込みする。この経路では 3 テーブルの書込み順はほぼ同時であり実用上の問題は生じない。一方、REST/gNMI 経路では MGMT_PORT トランスフォーマーが未実装であるため (`sonic-mgmt-common`)、MGMT_PORT への書込みは minigraph または手動 CLI のみとなっている。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

> 調査証跡: `meta/_intermediate/cdb-flow/mgmt-port-cross-refs.md`

MGMT_PORT は orchagent / SAI を経由しない。他テーブル・他設定ファイルへの実装上の依存は `lldpd.conf.j2` と `sonic-snmpagent` の 2 系統に集中する。

| 参照元 | 参照先 DB / テーブル | 方向 | 契機 | 根拠コード |
|--------|---------------------|------|------|-----------|
| `lldpd.conf.j2` | `CONFIG_DB MGMT_PORT[name].alias` | READ | LLDP デーモン設定ファイル生成時。`alias` が存在すれば `configure ports eth0 lldp portidsubtype local <alias>` を生成。`alias` 未設定時は `mgmt_if.port_name`（`eth0`）をフォールバック使用 | `lldpd.conf.j2:17-20` |
| `lldpd.conf.j2` | `CONFIG_DB MGMT_INTERFACE` (pfx_filter) | READ | `mgmt_if.port_name` を解決するために MGMT_INTERFACE を先読み。MGMT_INTERFACE が空の場合 LLDP 管理 IF ブロック自体が生成されない | `lldpd.conf.j2:2-12` |
| `mgmt_oper_status.py` | `CONFIG_DB MGMT_PORT\|*` | READ | 管理ポートキーを列挙し `STATE_DB MGMT_PORT_TABLE\|<port>` へ全フィールドを同期。エントリ不在時は STATE_DB を更新せず終了 | `mgmt_oper_status.py:16-37` |
| `sonic_ax_impl/mibs/__init__.py` | `CONFIG_DB MGMT_PORT\|*` | READ | SNMP MIB の `if_alias_map` 構築。`alias` フィールドを取得し、省略時は `if_name`（`eth0`）をフォールバック | `mibs/__init__.py:256-270` |
| `sonic_ax_impl/mibs/__init__.py` | `STATE_DB MGMT_PORT_TABLE\|*` | READ | oper_status および speed / alias を SNMP OID テーブルへ展開 | `mibs/__init__.py:196-202` |

!!! note "MGMT_INTERFACE との連動"
    `lldpd.conf.j2` は MGMT_PORT の `alias` を参照する前に **MGMT_INTERFACE** テーブルをループして `port_name` を取得する。
    MGMT_INTERFACE が未設定の場合、MGMT_PORT の `alias` フィールドは LLDP 設定に反映されない（テンプレートブロック自体がスキップされる）。

!!! note "SNMP は CONFIG_DB を直接参照"
    `sonic_ax_impl` は STATE_DB の `MGMT_PORT_TABLE` だけでなく、CONFIG_DB の `MGMT_PORT` も直接参照して `alias` を取得する。
    STATE_DB の同期（`mgmt_oper_status.py`）が遅延している場合でも、SNMP の `alias` 返却は CONFIG_DB から即座に取得されるため影響を受けない。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

<!-- evidence: sonic-buildimage/files/image_config/monit/mgmt_oper_status.py / sonic-host-services/scripts/hostcfgd MgmtIfaceCfg -->

`MGMT_PORT` は orchagent / SAI を経由しないため、失敗経路は `mgmt_oper_status.py`（monit）と `hostcfgd`（MgmtIfaceCfg）の 2 系統に限定される。

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| CONFIG_DB に `MGMT_PORT|*` キーが存在しない | `mgmt_oper_status.py:17` | STATE_DB 更新なし・`sys.exit(0)` で正常終了扱い | `LOG_DEBUG "No management interface found"` | `mgmt_oper_status.py:17-19` |
| `mgmt_oper_status.py` 内でその他例外発生 | `mgmt_oper_status.py:49` | `STATE_DB MGMT_PORT_TABLE|<port>.oper_status = "unknown"` に上書き後 `sys.exit(1)` | `LOG_ERR "mgmt_oper_status exception : <e>"` | `mgmt_oper_status.py:49-51` |
| `MGMT_INTERFACE` 変更後の `systemctl restart interfaces-config` 失敗 | `hostcfgd MgmtIfaceCfg.update_mgmt_iface():1638` | 早期 return。`self.iface_config_data` キャッシュ未更新。`/etc/network/interfaces` 再生成されず eth0 設定が古いまま残る | `LOG_ERR "Failed to restart management interface services"` | `hostcfgd:1638-1641` |
| `MGMT_VRF_CONFIG` 変更後の VRF サービス再起動失敗（`chrony` stop / `interfaces-config` restart / `chrony` start）| `hostcfgd MgmtIfaceCfg.update_mgmt_vrf():1663` | 早期 return。`self.mgmt_vrf_enabled` キャッシュ未更新。VRF 状態が不整合のまま残る | `LOG_ERR "Failed to restart management vrf services"` | `hostcfgd:1663-1666` |
| `mgmt_oper_status.py` が `/sys/class/net/<port>/operstate` を読めない (`subprocess` エラー) | `mgmt_oper_status.py:42-44` | 例外経路に fallback → `oper_status = "unknown"` が STATE_DB に書き込まれ `sys.exit(1)` | `LOG_ERR "mgmt_oper_status exception : ..."` | `mgmt_oper_status.py:49-51` |

### DEL 処理における失敗経路

| 失敗条件 | 結果 | evidence |
|---|---|---|
| MGMT_PORT エントリ DEL 後に `mgmt_oper_status.py` が実行された場合 | `db.keys(CONFIG_DB, 'MGMT_PORT|*')` が空 → STATE_DB 更新なし。古い `MGMT_PORT_TABLE` エントリが STATE_DB に残存する可能性あり | `mgmt_oper_status.py:16-19` |

### 補足

- **monit 定期実行**: `mgmt_oper_status.py` は `monit` が定期的に呼び出すスクリプトであり、失敗時 (`sys.exit(1)`) は monit がアラートを生成する。
- **SAI 非経由のため rollback 機構なし**: MGMT_PORT はデータポート (`PORT`) と異なり orchagent の retry キューに入らない。`interfaces-config` restart 失敗は手動介入（`systemctl restart interfaces-config`）で復旧が必要。
- **`oper_status = "unknown"` の意味**: `mgmt_oper_status.py` が例外で終了した場合にのみ設定される値。通常の `up`/`down` と区別して監視することを推奨する。

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

<!-- evidence: sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mgmt_port.yang / sonic-buildimage/files/image_config/monit/mgmt_oper_status.py / sonic-buildimage/files/image_config/config-setup/config-setup.conf / sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py / sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2 -->

| 定数名 | 値 | 型 | 定義場所 | 説明 |
|--------|----|----|---------|------|
| `speed` 許容値 | `10`/`100`/`1000` | YANG `range` 制約 | `sonic-mgmt_port.yang:39` | 管理ポート速度の有効値。Mbps 単位。この 3 値以外は YANG バリデーションで拒否される。 |
| `mtu` デフォルト | `1500` | YANG `default` | `sonic-mgmt_port.yang:68` | MTU のデフォルト値。`mtu` フィールド省略時に YANG が返す値。ただし実際の eth0 MTU への反映コードは未実装（dead write）。 |
| `mtu` 許容範囲 | `1500..9216` | YANG `range` 制約 | `sonic-mgmt_port.yang:66` | MTU の最小・最大値。1500 未満または 9216 超は YANG バリデーションで拒否。 |
| `admin_status` デフォルト | `"up"` | YANG `default` | `sonic-mgmt_port.yang:74` | 管理状態のデフォルト値。`admin_status` 省略時は `up` として扱われる。minigraph も常時 `"up"` をハードコードで注入する（`minigraph.py:2294`）。 |
| `autoneg` 許容値 | `"on"`/`"off"` | YANG `pattern` 制約 | `sonic-mgmt_port.yang:46-51` | `on` または `off` のみ有効。それ以外は YANG バリデーションで拒否。コンシューマが存在しないため設定しても eth0 の autoneg は変化しない（dead field）。 |
| インターフェース名パターン | `eth([1-3][0-9]{3}\|[1-9][0-9]{2}\|[1-9][0-9]\|[0-9])` | YANG `pattern` 制約 | `sonic-mgmt_port.yang:32-36` | 管理 IF 名の正規表現制約。`eth0`–`eth3999` の範囲を許可。不正名は YANG バリデーションで拒否。 |
| STATE_DB キープレフィックス | `"MGMT_PORT_TABLE\|"` | 文字列定数 | `mgmt_oper_status.py:25` | STATE_DB への同期先テーブル名。`"MGMT_PORT_TABLE\|{port}"` の形式でフィールドを書き込む。 |
| `KEEP_BASIC_TABLES` | `["MGMT_PORT", "MGMT_INTERFACE", "MGMT_VRF_CONFIG", "PASSW_HARDENING"]` | JSON 配列定数 | `config-setup.conf:4` | factory reset / config erase 時も保持するテーブルリスト。MGMT_PORT はこのリストに含まれるため、設定初期化後も管理ポート設定が残存する。 |
| SNMP `alias` フォールバック | `if_name`（例: `"eth0"`）| 文字列フォールバック | `sonic_ax_impl/mibs/__init__.py:270` | SNMP MIB が `alias` フィールドを取得する際、フィールド省略時は `if_name` をフォールバック値として返す。`if_entry.get('alias', if_name)` で実装。 |
| LLDP ポート ID タイプフォールバック | `mgmt_if.port_name`（`eth0`）| 文字列フォールバック | `lldpd.conf.j2:20` | `MGMT_PORT.alias` が存在しない場合、LLDP の `configure ports eth0 lldp portidsubtype local` に `mgmt_if.port_name`（= `eth0`）をフォールバック使用。 |

### 補足

- `mtu=1500` は YANG デフォルトとして定義されているが、`interfaces.j2` テンプレートや hostcfgd の MGMT_PORT コンシューマが MTU を eth0 に適用するコードは存在しない。実際の eth0 MTU はカーネルのデフォルト（通常 1500）または platform 固有の設定に依存する。
- `speed` / `autoneg` フィールドは YANG 定義があり YANG バリデーションは通過するが、これらを参照して ethtool を実行するコンシューマが存在しないため **dead write** である（Phase A 調査で確認済み）。
- `KEEP_BASIC_TABLES` に MGMT_PORT が含まれることで、`config erase` 後も eth0 の基本設定が保持され管理アクセスが維持される設計になっている。

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

<!-- evidence: sonic-buildimage/files/image_config/monit/mgmt_oper_status.py / sonic-host-services/scripts/hostcfgd MgmtIfaceCfg / sonic-swss/cfgmgr/portmgrd.cpp -->

`MGMT_PORT` エントリの SET/DEL に起因してコードが副次的に書き込む DB は **STATE_DB の `MGMT_PORT_TABLE`** のみ。APPL_DB・ASIC_DB・COUNTERS_DB・FLEX_COUNTER_DB への書込みは一切存在しない。

| 副次 DB | テーブル | 書込条件 | ソース |
|---------|---------|---------|--------|
| STATE_DB | `MGMT_PORT_TABLE\|<port>` | `mgmt_oper_status.py` が monit 定期実行される都度（CONFIG_DB に `MGMT_PORT|*` エントリが存在する場合） | `mgmt_oper_status.py:30-34, 39-44` |
| APPL_DB | なし | — | `MgmtIfaceCfg.update_mgmt_iface()` は `systemctl restart interfaces-config` のみ発行 |
| ASIC_DB | なし | — | `portmgrd.cpp:28` は `CFG_PORT_TABLE_NAME`（= `"PORT"`）のみ購読。MGMT_PORT は SAI 非経由 |
| COUNTERS_DB | なし | — | — |
| FLEX_COUNTER_DB | なし | — | — |

### STATE_DB への書込み詳細

`mgmt_oper_status.py` が monit によって定期的に呼び出されると、以下の処理が実行される。

1. CONFIG_DB `MGMT_PORT|*` のキーを列挙。エントリ不在なら `LOG_DEBUG` を出力して `sys.exit(0)`（STATE_DB 書込なし）。
2. 存在する各ポートについて CONFIG_DB フィールドを STATE_DB `MGMT_PORT_TABLE|<port>` へ差分コピー（`oper_status` フィールドを除く）。
3. `/sys/class/net/<port>/operstate` を読み取り、前回値と異なれば `STATE_DB MGMT_PORT_TABLE|<port>.oper_status` を更新。

```
STATE_DB MGMT_PORT_TABLE|eth0
  alias        ← CONFIG_DB MGMT_PORT|eth0.alias
  admin_status ← CONFIG_DB MGMT_PORT|eth0.admin_status
  speed        ← CONFIG_DB MGMT_PORT|eth0.speed (設定時のみ)
  oper_status  ← /sys/class/net/eth0/operstate の実測値
```

### DEL 時の残存動作

`MGMT_PORT|eth0` が DEL されると `mgmt_oper_status.py` は CONFIG_DB のキーを空と判定して STATE_DB を更新せず終了する。既存の `STATE_DB MGMT_PORT_TABLE|eth0` エントリは削除されず残存する（ゴースト状態）。monit の次回実行でも CONFIG_DB が空のままであれば同様にスキップされるため、手動削除が必要になる（`sonic-db-cli STATE_DB del 'MGMT_PORT_TABLE|eth0'`）。

詳細 grep スキャン結果は `meta/_intermediate/cdb-flow/mgmt-port-side-effects.md` を参照。

<!-- /side-effects -->

<!-- pubsub -->
## Phase G: CONFIG_DB Subscribe 機構 (通信メカニズム)

`MGMT_PORT` テーブルに対する CONFIG_DB の通信メカニズムを整理する。結論を先に述べると、**event-driven な subscribe consumer は存在しない**。唯一の変化検知は monit による定期 polling である。

### hostcfgd — MGMT_PORT は購読対象外

`hostcfgd` (`sonic-host-services/scripts/hostcfgd`) は起動時に複数テーブルを `ConfigDBConnector.subscribe()` で購読するが、`MGMT_PORT` は対象に含まれない。

```python
# hostcfgd L2485 — MGMT_INTERFACE は購読する
self.config_db.subscribe('MGMT_INTERFACE', make_callback(self.mgmt_intf_handler))

# hostcfgd L2496-2497 — MGMT_VRF_CONFIG は購読する
self.config_db.subscribe(swsscommon.CFG_MGMT_VRF_CONFIG_TABLE_NAME,
                         make_callback(self.mgmt_vrf_handler))

# MGMT_PORT への subscribe() 呼び出しは存在しない
```

`MGMT_PORT` フィールドのほとんど（`speed`, `autoneg`, `mtu`, `description`）が Phase A 調査で確認した dead write であり、即時コールバックが不要なため、event-driven な購読は実装されていない。

### mgmt_oper_status.py — monit による polling 読み取り

`MGMT_PORT` テーブルへの唯一の実効的な読み取り処理は `mgmt_oper_status.py` が行うが、これは subscribe ではなく**one-shot polling** モデルである。

```python
# sonic-buildimage/files/image_config/monit/mgmt_oper_status.py:12-17
db = SonicV2Connector(use_unix_socket_path=True)
db.connect('CONFIG_DB')
db.connect('STATE_DB')
mgmt_ports_keys = db.keys(db.CONFIG_DB, 'MGMT_PORT|*')
```

- `listen()` / `subscribe()` を呼ばず、**単発の key スキャン + get_all() で完結**する。
- monit デーモンが定期的にスクリプトを起動する（polling 間隔は monit 設定依存）。
- 処理内容: CONFIG_DB `MGMT_PORT|<port>` フィールドを STATE_DB `MGMT_PORT_TABLE|<port>` へ差分コピーし、`/sys/class/net/<port>/operstate` を読んで `oper_status` を更新する。

### その他のコンシューマ — 静的・オンデマンド読み取り

| コンポーネント | 機構 | 対象フィールド | タイミング |
|---|---|---|---|
| `lldpd.conf.j2` | 起動時テンプレート展開（sonic-cfggen） | `alias` | docker lldp 起動時のみ |
| `sonic-snmpagent` | SNMP GET 要求時の on-demand 読み取り | `alias` | SNMP polling 要求時 |
| `mgmt_oper_status.py` | monit による定期 one-shot polling | 全フィールド → STATE_DB | monit 定期実行（数十秒間隔） |

### 通信フロー全体図

```
CONFIG_DB MGMT_PORT|eth0 (SET/DEL)
  │
  ├─ [event-driven subscribe: なし]
  │    hostcfgd は MGMT_PORT を購読しない
  │
  ├─ [polling] monit → mgmt_oper_status.py (定期実行)
  │    SonicV2Connector.keys('MGMT_PORT|*')
  │    → get_all(CONFIG_DB, 'MGMT_PORT|eth0')
  │    → STATE_DB MGMT_PORT_TABLE|eth0 へ差分コピー
  │    → /sys/class/net/eth0/operstate → STATE_DB oper_status 更新
  │
  ├─ [静的] docker lldp 起動時
  │    sonic-cfggen + lldpd.conf.j2 → alias フィールド参照
  │
  └─ [on-demand] sonic-snmpagent SNMP GET 要求時
       alias フィールド参照 (get('alias', if_name) でフォールバック)
```

> **注**: `MGMT_PORT` は CONFIG_DB に書き込まれても即時の event-driven コールバックを持つ consumer がいない。変化の伝搬は次回 monit 実行まで遅延する（最大 monit チェック間隔）。`admin_status` / `speed` / `autoneg` / `mtu` を変更しても、eth0 の物理設定への即時反映はない（Phase A の dead write 確認と整合）。

<!-- /pubsub -->

<!-- platform -->
## プラットフォーム差 (Phase H)

`MGMT_PORT` の処理は SAI を一切経由しないため、ASIC 種別によるプラットフォーム差はない。ただし `speed` フィールドの有無は **HwSku（platform）依存** であり、以下に示す観点でプラットフォーム間に動作差が生じる。詳細根拠は [`meta/_intermediate/cdb-flow/mgmt-port-platform.md`](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/meta/_intermediate/cdb-flow/mgmt-port-platform.md) を参照。

### A. speed フィールドの有無 — HwSku 依存

`minigraph.py:parse_deviceinfo()` (L1675–1711) が minigraph XML の `<DeviceInfo><ManagementInterfaces><ManagementInterface><Speed>` 要素を読み込み、`port_speeds_default[alias]` に格納する。この値が存在する場合のみ `speed` フィールドが `MGMT_PORT` エントリに挿入される。

```python
# minigraph.py:2295-2296
if alias in port_speeds_default:
    results['MGMT_PORT'][name]['speed'] = port_speeds_default[alias]
```

| 状況 | `speed` フィールド | 典型例 |
|---|---|---|
| HwSku の ManagementInterface に Speed 定義あり | 挿入される（例: `"1000"`） | 多くの T0/T1 プラットフォーム |
| HwSku の ManagementInterface に Speed 定義なし | フィールド省略（CONFIG_DB に存在しない） | chassis linecard 等 (`test_chassis_cfggen.py:116` — `speed` なしを確認) |

### B. ASIC 種別 — 影響なし

| 観点 | 結果 | 根拠 |
|---|---|---|
| ASIC 種別 (Broadcom / Mellanox / Marvell / Innovium 等) | 影響なし | MGMT_PORT は SAI 非経由。eth0 は Linux netdev であり ASIC と独立 |
| `portmgrd` の購読対象 | MGMT_PORT を**購読しない** | `portmgrd.cpp:28` — `CFG_PORT_TABLE_NAME`（= `"PORT"`）のみ購読 |

### C. multi-asic 構成 — host-scoped で影響なし

`MGMT_PORT` は host 側 CONFIG_DB (namespace = `""`) に置かれ、`asic0..N` namespace には存在しない。`mgmt_oper_status.py` も host CONFIG_DB の `MGMT_PORT|*` のみを参照し asic namespace を iterate しない（`mgmt_oper_status.py:16–22`）。

### D. VOQ chassis (supervisor / line card) — 各 host 独立

VOQ chassis 構成でも supervisor と各 line card が独立した eth0 を持ち、それぞれの host CONFIG_DB に MGMT_PORT エントリが置かれる。chassis 集中管理機構はなく、`admin_status="up"` のハードコード注入も各 host で同じ動作。

### E. SmartSwitch DPU — MGMT_PORT 自体は通常通り

`interfaces.j2` の DPU 条件分岐（DHCP フォールバック抑制）は `MGMT_INTERFACE` テーブルが空のときの話であり、`MGMT_PORT` テーブル自体の処理には影響しない。SmartSwitch DPU でも minigraph 由来の `MGMT_PORT` エントリは通常通り CONFIG_DB に投入される。

<!-- /platform -->
