---
title: DHCP_SERVER_IPV4 テーブル
description: "DHCP_SERVER_IPV4 テーブル — 組み込み DHCPv4 サーバ機能の VLAN/IF 単位設定を保持する。dhcpservd（sonic-dhcp-server パッケージ）が kea-dhcp4 の設定を生成、起動する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - DHCP_SERVER_IPV4
    - DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS
    - VLAN
  cli:
    - config dhcp_server
  yang:
    - sonic-dhcp-server-ipv4
---

# DHCP_SERVER_IPV4 テーブル

## 概要

組み込み DHCPv4 サーバ機能の [VLAN](../../reference/glossary.md#term-vlan)/IF 単位設定を保持する[^1]。`dhcpservd`（`sonic-dhcp-server` パッケージ）が `kea-dhcp4` の設定を生成、起動する。`DEVICE_METADATA.localhost.dhcp_server` で全体有効化が制御される。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>DHCP_SERVER_IPV4")]
  DM["dhcpservd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
DHCP_SERVER_IPV4|<name>
```

`<name>` は [VLAN](../../reference/glossary.md#term-vlan) 名 (`Vlan<id>`) または [SmartSwitch](../../reference/glossary.md#term-smartswitch) の bridge 参照 (`MID_PLANE_BRIDGE.GLOBAL.bridge`) の union。

## フィールド一覧

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `name` (key) | string `Vlan<id>` または bridge 名 | ✅ | DHCP 提供 IF |
| `gateway` | ipv4-address | - | クライアントへ通知するゲートウェイ |
| `lease_time` | uint32 (1..2^32-1) | ✅ | リース時間 [秒] |
| `mode` | enum `PORT` | ✅ | IP 割当モード |
| `netmask` | ipv4-address-no-zone | ✅ | サブネットマスク |
| `customized_options` | leaf-list leafref `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS.name` | - | カスタムオプション参照リスト |
| `state` | `admin_mode` (`enabled`/`disabled`) | ✅ | サーバ有効化 |

## 関連サブテーブル

- `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS|<name>`: option ID / type / value のテンプレ
- `DHCP_SERVER_IPV4_PORT|<vlan>|<port>`: ポート単位の IP プール
- `DHCP_SERVER_IPV4_RANGE|<name>`: アドレスレンジ
- `DHCP_SERVER_IPV4_IP|<vlan>|<port>`: 静的予約

詳細は [YANG](../../reference/glossary.md#term-yang) モジュール `sonic-dhcp-server-ipv4` を直参照。

<!-- value-behavior -->
## 値依存挙動マトリクス

### `state` (admin_mode: enabled/disabled)

| 値 | 挙動 |
|----|------|
| `enabled` | dhcpservd が kea-dhcp4 サーバを起動し DHCP DISCOVER に応答 |
| `disabled` | kea-dhcp4 を停止。クライアントへの応答なし |

### `mode` (enum: PORT)

| 値 | 挙動 |
|----|------|
| `PORT` | ポート単位で IP を割り当て（DHCP_SERVER_IPV4_PORT テーブルで定義）。現在は PORT のみサポート |
| その他 | YANG enum 違反で reject |

### `lease_time` (uint32, 必須)

| 値 | 挙動 |
|----|------|
| 1 以上 | kea-dhcp4 のリース有効期間（秒）として設定 |
| 0 | YANG range 違反（1 以上必須）で reject |

### `customized_options` (leaf-list leafref)

| 値 | 挙動 |
|----|------|
| 存在する DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS.name | kea-dhcp4 設定にカスタムオプションを追加 |
| 存在しない option 名 | YANG leafref 違反で reject |

> DEVICE_METADATA.dhcp_server が未設定の場合、dhcpservd 自体が起動しないため state の設定は無効。

<!-- /value-behavior -->

## 購読者

- `dhcpservd` (`sonic-dhcp-server` 内)
- `dhcprelayd` （`DHCP_RELAY` 側と排他関係）

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `VLAN`、`VLAN_INTERFACE`、`DEVICE_METADATA` (`dhcp_server`)、`DHCP_RELAY` 系
- 関連 CLI: `config dhcp_server ipv4 add/del/range/port`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-dhcp-server-ipv4`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-dhcp-server-ipv4`](../yang/sonic-dhcp-server.md)
- CLI: `config dhcp_server`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-dhcp-server-ipv4.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: NAT / DHCP Relay / Time-DNS Services](../../topics/16-nat-dhcp-dns/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `DHCP_SERVER_IPV4|<name>`。
- `state`: `enabled`、`gateway`: subnet GW、`lease_time`: `3600`、`mode`: `PORT`。

### よくある誤設定

- [VLAN](../../reference/glossary.md#term-vlan) に紐付けず DHCP_SERVER_IPV4_PORT エントリも無いと DISCOVER が応答されない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'DHCP_SERVER_IPV4|*'
show dhcp_server ipv4 info
```
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| consumer | 条件 | 挙動 |
|---|---|---|
| dhcp_cfggen | standard option の `type` が期待型と不一致 | `LOG_WARNING` を出力して**期待型を優先**して処理継続（dhcp_cfggen.py:133-137） |
| dhcp_cfggen | `type` が `SUPPORT_DHCP_OPTION_TYPE` 外 | `LOG_ERR` を出力してそのオプションエントリをスキップ、他は継続（dhcp_cfggen.py:140-143） |
| dhcp_cfggen | `validate_str_type(option_type, value)` 失敗 | `LOG_ERR` を出力してそのオプションをスキップ（dhcp_cfggen.py:144-147） |
| dhcp_cfggen | `type=string` かつ `value` が 253 文字超 | `LOG_ERR` を出力してそのオプションをスキップ（dhcp_cfggen.py:148-150） |
| dhcp_cfggen | `ips` と `ranges` の両方を同時指定 | `LOG_WARNING: "...contains both ips and ranges, skip"` を出力してそのポートをスキップ（dhcp_cfggen.py:418-421） |
| dhcp_cfggen | `ranges` で指定した range 名が DHCP_SERVER_IPV4_RANGE に存在しない | `LOG_WARNING: "Range %s is not in range table, skip"` を出力してその range をスキップ（dhcp_cfggen.py:452-454） |
| dhcprelayd | `state=enabled` でも VLAN が VLAN テーブルに存在しない | dhcrelay の起動対象から除外（dhcprelayd.py:97-98） |

> **Evidence**: [sonic-buildimage](../../reference/glossary.md#term-sonic-buildimage) `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:133-454`; `dhcp_utilities/dhcprelayd/dhcprelayd.py:94-98`
<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`dhcpservd` (`sonic-dhcp-server`) が CONFIG_DB の `DHCP_SERVER_IPV4` テーブルを購読する。

`DHCP_SERVER_IPV4` は SONiC 独自の DHCP server 機能 (sonic-dhcp-server)。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — Linux カーネルの DHCP サーバ機能)

### 段階 4 — タイミングと副作用

**適用タイミング**: `dhcpservd` が CONFIG_DB の `DHCP_SERVER_IPV4` を購読。変化検知後 DHCP server 設定を更新。新規設定は次回 DHCP discover から有効。

**副作用**: subnet / pool 変更は新規 DHCP リクエストから適用。既存 lease には影響しない (lease 期限まで)。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `DHCP_SERVER_IPV4`

### CLI
- `config dhcp-server ipv4 add/del <gateway>`
- `config dhcp-server ipv4 enable/disable <gateway>`
  - ソース: `sonic-utilities/config/main.py (dhcp-server グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
<!-- /entry-points -->

<!-- ordering -->
## 書込み順依存 (Phase B)

### 他テーブル先行必須

| 先行テーブル | 理由 | 違反時の挙動 |
|---|---|---|
| `VLAN` / `VLAN_INTERFACE|<name>|<ipv4_prefix>` | `dhcp_cfggen.generate()` が VLAN_INTERFACE から IPv4 サブネットを取得してから DHCP 設定を生成。未設定だと `_parse_port()` でそのインタフェースをスキップ | kea-dhcp4 起動するが VLAN のサブネット定義なし→ DISCOVER 無応答（`dhcp_cfggen.py:432-433`） |
| `VLAN_MEMBER|<vlan>|<port>` | PORT モードでポートが VLAN メンバーとして登録されていないと `_parse_port()` で `"Port %s is not in %s"` 警告を出しスキップ | そのポートへの IP プール割当なし |
| `FEATURE|dhcp_server state=enabled` | CLI の `dhcp_server` グループ入口で feature 有効チェック。dhcpservd 自体も feature 有効でなければ起動しない | CLI コマンドすべて `ctx.fail()` で終了（`dhcp_server.py:54`） |
| `DHCP_SERVER_IPV4_RANGE|<name>` | `ranges` 参照の `DHCP_SERVER_IPV4_PORT` を書く前に range エントリが必須。CLI bind は range 存在チェック済み | CLI `ctx.fail()`; 直接 DB 書込み時は `LOG_WARNING` でそのレンジのプールをスキップ（`dhcp_cfggen.py:452-454`） |
| `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS|<name>` | `customized_options` leafref を書く前にオプションエントリが必須。CLI option bind は存在チェック済み | CLI `ctx.fail()`; 直接 DB 書込み時は `LOG_WARNING` でそのオプションをスキップ（`dhcp_cfggen.py:213-215`） |

**推奨書込み順序**:

```
# 1. VLAN / IF / Member
SET VLAN|<name>
SET VLAN_INTERFACE|<name>|<ipv4_prefix>
SET VLAN_MEMBER|<name>|<port>

# 2. DHCP サブリソース（range / option）
SET DHCP_SERVER_IPV4_RANGE|<range_name>   # ranges 利用時
SET DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS|<opt_name>  # customized_options 利用時

# 3. DHCP メインエントリ（state=disabled で投入）
SET DHCP_SERVER_IPV4|<name>  state=disabled  ...

# 4. ポート-IP/レンジ バインド
SET DHCP_SERVER_IPV4_PORT|<name>|<port>

# 5. 有効化（最後に state=enabled）
SET DHCP_SERVER_IPV4|<name>  state=enabled
```

### SET 後 DEL の順序依存

| シナリオ | 問題 | 安全な手順 |
|---|---|---|
| `state=enabled` エントリをいきなり DEL | dhcpservd が即再生成して kea-dhcp4 SIGHUP。既存リースはリース期限まで有効のまま残る（新規割当は停止） | 先に `state=disabled` を SET してから DEL |
| `DHCP_SERVER_IPV4_RANGE` を使用中に DEL | CLI は参照中の range を `ctx.fail()` で拒否。`--force` で強制 DEL すると次回 generate 時にそのレンジが kea-dhcp4 設定から消える | `unbind` → `range del` の順で実施 |
| `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS` を参照中に DEL | CLI は参照中のオプションを `ctx.fail()` で拒否 | `option unbind` → `option del` の順で実施 |

### Notification / SIGHUP 経路と反映タイミング

CONFIG_DB 書込み → dhcpservd `Select()` (最大 5000 ms ポーリング) → `dump_dhcp4_config()` (全量 generate) → `kea-dhcp4.conf` 上書き → SIGHUP → kea-dhcp4 再読込。1 変更につき 1 回の SIGHUP が発生する。設定変更は次回 DHCP DISCOVER から有効。

### warm-reboot

dhcpservd は stateless（CONFIG_DB から毎回全量 generate）。再起動時に `start()` → `dump_dhcp4_config()` → SIGHUP を自動実行するため、CONFIG_DB が整合していれば再起動後も自動復元される。kea-lease.csv (`/var/lib/kea/kea-lease.csv`) は永続化されており既存リース情報は引き継がれる。

> **Evidence**: sonic-buildimage `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:65-100,190-270,381-465`; `dhcpservd.py:39-68,89-100`; `common/dhcp_db_monitor.py:160-347`; `dockers/docker-dhcp-server/cli/config/plugins/dhcp_server.py:54-106,250-313,356-444`
<!-- /ordering -->

<!-- glossary-links-injected: 75921d013977 -->
