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
