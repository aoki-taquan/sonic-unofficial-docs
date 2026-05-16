---
title: LLDP_PORT テーブル
description: "LLDP_PORT テーブル — LLDP_PORT は ポート単位の LLDP 設定 を保持する CONFIG_DB テーブル。lldp (lldpd / lldpmgrd) コンテナが CONFIG_DB から読み、各物理ポートで LLDP を有効化するか、また RX / TX どちらのモードで動かすかを決める。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-lldp.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - LLDP_PORT
    - LLDP
    - PORT
  cli:
    - config lldp
    - show lldp
  yang:
    - sonic-lldp
---

# LLDP_PORT テーブル

## 概要

`LLDP_PORT` は **ポート単位の [LLDP](../../reference/glossary.md#term-lldp) 設定** を保持する [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル[^1]。`lldp` (lldpd / lldpmgrd) コンテナが [CONFIG_DB](../../reference/glossary.md#term-config_db) から読み、各物理ポートで [LLDP](../../reference/glossary.md#term-lldp) を有効化するか、また RX / TX どちらのモードで動かすかを決める。

`LLDP` (グローバル) テーブルが `hello_time` / `multiplier` / `system_name` / `system_description` 等のシャーシ全体の設定を持つのに対し、本テーブルはポート単位の上書き設定。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>LLDP_PORT")]
  DM["lldpmgrd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
LLDP_PORT|<ifname>
```

- `<ifname>`: `PORT.name` への leafref (例: `Ethernet0`)

## フィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|----------|------|
| `ifname` (key) | leafref → `PORT.name` | - | 対象ポート |
| `enabled` | boolean | `true` | このポートで [LLDP](../../reference/glossary.md#term-lldp) を有効化するか |
| `mode` | enum `RECEIVE`/`TRANSMIT` | - | LLDP フレームの RX/TX モード |

`enabled` と `mode` は `sonic-lldp` の `lldp_mode_config` grouping から `uses` されている共通フィールド。`mode` を省略した場合は lldpd のデフォルト (双方向) で動作する実装が多い。

## 制約

- `ifname` は `PORT_LIST.name` への leafref のため、存在しないポートは validation でエラー。
- `mode` は `RECEIVE` または `TRANSMIT` のみ。`BOTH` などの値は無く、双方向は `mode` を未指定にすることで表現する。

## 購読者

- `lldpmgrd` (`docker-lldp`): [CONFIG_DB](../../reference/glossary.md#term-config_db) → `lldpcli` コマンドに変換し `lldpd` に投入
- `lldpd`: 実際の LLDPDU 送受信

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `LLDP` (グローバル設定), `PORT`, `DEVICE_NEIGHBOR` (静的隣接)
- 関連 CLI: `config lldp interface enable/disable`, `show lldp neighbors`, `show lldp table`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-lldp`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-lldp`](../yang/sonic-lldp.md)
- CLI: `config lldp` / [`show lldp`](../cli/show-lldp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-lldp.yang` (revision 2021-07-08). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-lldp.yang>

## 関連ページ
- [YANG: sonic-lldp](../yang/sonic-lldp.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `LLDP_PORT|<Ethernet>`。
- `admin_status`: `rx_and_tx`。`description` を物理配線管理用に活用する。

### よくある誤設定

- LLDP を `disabled` にしている port は DEVICE_NEIGHBOR 自動学習されないため minigraph と乖離する。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'LLDP_PORT|*'
show lldp table
```
<!-- /ops-hint -->

<!-- defaults -->
## コード由来デフォルト

`LLDP_PORT` の per-port フィールドは YANG `default` 文と lldpmgrd / `lldpd.conf.j2` のハードコードで決まる。

### field: `enabled`

**コード由来デフォルト**: `true` (YANG `default`)

```yang
// sonic-buildimage/src/sonic-yang-models/yang-models/sonic-lldp.yang:24-31
grouping lldp_mode_config {
    leaf enabled {
        type boolean;
        default true;
        description "Enable LLDP on this port";
    }
```

`LLDP_PORT` は `lldp_mode_config` を `uses` するため、フィールド省略時は `true` 扱い。`config lldp interface <port> disable` で `false` に切り替わるまでは LLDP TX/RX が有効。

### field: `mode`

**コード由来デフォルト**: 未設定 (= lldpd 組み込みの双方向 rx+tx)

`sonic-lldp.yang` の `mode` には `default` 文がなく、enum も `RECEIVE` / `TRANSMIT` の 2 値のみ (`BOTH` は存在しない)。`mode` 未指定時は lldpmgrd が `lldpcli configure ports ... lldp status` を発行しないため、lldpd の組み込みデフォルト (双方向送受信) が有効になる。

### field: portidsubtype (per-port の暗黙デフォルト)

**コード由来デフォルト (per-port)**: `local <PORT.alias>` (alias 空時は port name)

```python
# sonic-buildimage/dockers/docker-lldp/lldpmgrd:156
lldpcli_cmd = ["lldpcli", "configure", "ports", port_name, "lldp",
               "portidsubtype", "local", port_alias]
```

`port_alias` は `PORT.alias` を参照し、空/None の場合は `port_name` (例: `Ethernet0`) を fallback (lldpmgrd:147-150)。

**コード由来デフォルト (起動時グローバル)**: `ifname`

```jinja2
{# sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2:30-31 #}
{# Use ifname globally to avoid MAC-as-Port-ID; lldpmgrd sets alias per port later. #}
configure lldp portidsubtype ifname
```

lldpd 起動初期は `ifname` (linux iface 名)、その後 lldpmgrd が CONFIG_DB の `PORT.alias` を読んで per-port で `local <alias>` に上書きする二段構成。

### field: `description`

**コード由来デフォルト**: なし (空のまま `lldpcli` に渡されない)

```python
# sonic-buildimage/dockers/docker-lldp/lldpmgrd:152-162
port_desc = port_table_dict.get("description")
# ...
if port_desc:
    lldpcli_cmd += ["description", port_desc]
else:
    self.log_info("Unable to retrieve description for port '{}'. "
                  "Not adding port description".format(port_name))
```

`description` が空/未設定なら lldpcli の description 引数を省略。lldpd は description 無しで LLDPDU を送信。

### 特殊ポートのスキップ

inband / recirc / backplane prefix を持つポートは `LLDP_PORT` エントリがあっても lldpmgrd が lldpcli への変換をスキップする (`lldpmgrd:141-142`)。CONFIG_DB に書いても lldpd には反映されない。

!!! note "interval / ttl は本テーブルの対象外"
    LLDPDU 送出周期 (`hello_time`) や保持時間 (`multiplier`、ttl = hello_time × multiplier) は per-port ではなく **グローバル `LLDP` テーブル** のフィールド。YANG では `hello_time` の `default 30`、`multiplier` の `default 4` が定義されている (`sonic-lldp.yang:53,66`)。詳細はグローバル `LLDP` テーブルのページを参照。

<!-- /defaults -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `enabled`

| 値 | 挙動 |
|----|------|
| `true`（デフォルト） | このポートで LLDP フレームの送受信を有効化 |
| `false` | LLDP 送受信を停止。`DEVICE_NEIGHBOR` 自動学習が発生せず minigraph との乖離リスク |

### `mode`

| 値 | 挙動 |
|----|------|
| `RECEIVE` | RX のみ。送信しないため自ノードが対向スイッチのトポロジーに映らない |
| `TRANSMIT` | TX のみ。受信しないため対向の LLDP 情報を学習しない |
| 未設定 | `lldpd` デフォルト（双方向）。`BOTH` 等の値は存在しない |
| 不正値 | `lldpcli` がエラー。CONFIG_DB には書けるが `lldpd` に反映されない |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-buildimage/dockers/docker-lldp/lldpmgrd -->

| 条件 | 挙動 |
|------|------|
| `admin_status` に不正値 | `lldpcli configure ports ... lldp status <value>` が失敗。CONFIG_DB にはバリデーションなしで書けるが lldpd には反映されない |
| `admin_status=disabled` | LLDP フレームの送受信停止。`DEVICE_NEIGHBOR` テーブルへの自動学習が発生せず minigraph との乖離が生じる |
| 実在しないポート名でエントリ投入 | lldpd に対応ポートが存在しないため設定無視。エントリは CONFIG_DB に残存 |
| `description` の反映タイミング | lldpmgrd のポーリング周期（数秒）に依存する非同期反映 |

<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`lldpmgrd` が CONFIG_DB の `LLDP_PORT` テーブルを購読する。

`LLDP_PORT` の key は `<port>` (例: `Ethernet0`)。ポート毎の LLDP 動作 (rx/tx/rxtx/disabled) を設定。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — `lldpd` デーモンの設定を更新)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `lldpmgrd` が検知後、`lldpcli` コマンドで `lldpd` に設定を注入。即時反映。

**副作用**: LLDP port 設定変更は次回 LLDP PDU 送受信から反映。`lldp_enable` 変更でポート毎に LLDP を有効/無効化可能。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `LLDP_PORT`

### CLI
- `config lldp <port> enable/disable`
- `config lldp portdesc <port> <description>`
- `config lldp portid-subtype <port> <subtype>`
  - ソース: `sonic-utilities/config/main.py (lldp グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- sonic-mgmt-common lldp_app.go 経由 (OpenConfig LLDP)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
<!-- /entry-points -->

<!-- glossary-links-injected: 1c2f663967b9 -->
