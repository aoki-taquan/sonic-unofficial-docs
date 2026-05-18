# DEVICE_NEIGHBOR_METADATA — Phase C 暗黙参照テーブル スキャンノート

対象ページ: `docs/reference/config-db/device-neighbor-metadata.md`
対象テーブル: `CONFIG_DB DEVICE_NEIGHBOR_METADATA`
スキャン範囲:
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:218-224`（bgpcfgd set_handler）
- `sonic-buildimage/files/build_templates/buffers_config.j2:81-82,209-210`（バッファ設定テンプレート）
- `sonic-buildimage/files/build_templates/qos_config.j2:107-108,150-151`（QoS 設定テンプレート）
- `sonic-utilities/pfcwd/main.py:97-108`（pfcwd サーバー向けポート判定）
- `sonic-utilities/show/interfaces/__init__.py:315-340`（show interfaces neighbor expected）
- `sonic-utilities/scripts/db_migrator.py:765-790`（EdgeZone Aggregator マイグレーション）

---

## 検出した暗黙参照

### 1. bgpcfgd — DEVICE_NEIGHBOR / DEVICE_METADATA と組み合わせて BGP テンプレートを決定

`BGPPeerMgrBase.set_handler()` (`managers_bgp.py:218-224`) は BGP_NEIGHBOR エントリの `name` フィールドをキーとして
DEVICE_NEIGHBOR_METADATA を読み出し、`kwargs['CONFIG_DB__DEVICE_NEIGHBOR_METADATA']` として Jinja2 テンプレートに渡す。
テンプレート内では `type` / `hwsku` / `deployment_id` 等を参照して eBGP セッション設定を分岐させる。

依存テーブル: `CONFIG_DB BGP_NEIGHBOR` (キー転写), `CONFIG_DB DEVICE_METADATA|localhost` (deployment_id 参照条件)

### 2. buffers_config.j2 — DEVICE_NEIGHBOR + DEVICE_NEIGHBOR_METADATA でケーブル長とキュー数を決定

`buffers_config.j2:81-82` は `DEVICE_NEIGHBOR[port].name` をキーとして `DEVICE_NEIGHBOR_METADATA` の `type` を参照し、
`switch_role + '_' + neighbor_role` の組み合わせで `ports2cable` マップからケーブル長を決定する。

`buffers_config.j2:209-210` は `SYSTEM_DEFAULTS.tunnel_qos_remap.status == 'enabled'` かつ
`DEVICE_METADATA['localhost'].type == 'LeafRouter'` の場合に、隣接ノードの `type == 'ToRRouter'` を確認して
extra queues ポートリストを構築する。また `DEVICE_METADATA['localhost'].subtype == 'DualToR'` かつ
隣接ノードの `type == 'LeafRouter'` でも同様のポートリストを構築する。

依存テーブル: `CONFIG_DB DEVICE_NEIGHBOR` (ポート→デバイス名マップ), `CONFIG_DB DEVICE_METADATA|localhost` (type/subtype), `CONFIG_DB SYSTEM_DEFAULTS` (tunnel_qos_remap 条件)

### 3. qos_config.j2 — DEVICE_NEIGHBOR + DEVICE_NEIGHBOR_METADATA でアップリンク/ダウンリンクポートリストを構築

`qos_config.j2:107-108` は各アクティブポートについて `DEVICE_NEIGHBOR[port].name` が DEVICE_NEIGHBOR_METADATA に
存在する場合に `neighbor_info.type` を読み出す。`local_router_type` と `neighbor_info.type` の組み合わせにより
ポートを `PORT_DOWNLINK` / `PORT_UPLINK` に分類する（LeafRouter ↔ ToRRouter/SpineRouter、ToRRouter ↔ LeafRouter）。

`qos_config.j2:150-151` は buffers_config.j2 と同様の tunnel_qos_remap + LeafRouter/DualToR 条件チェック。

依存テーブル: `CONFIG_DB DEVICE_NEIGHBOR`, `CONFIG_DB DEVICE_METADATA|localhost`

### 4. pfcwd — DEVICE_NEIGHBOR 経由で DEVICE_NEIGHBOR_METADATA の type を参照

`pfcwd.get_server_facing_ports()` (`pfcwd/main.py:97-108`) は DEVICE_NEIGHBOR の各エントリの `name` をキーとして
DEVICE_NEIGHBOR_METADATA を `get_entry()` で参照し、`type.lower() == 'server'` の場合にサーバー向けポートとして列挙する。

依存テーブル: `CONFIG_DB DEVICE_NEIGHBOR` (ポート→name マップ)

### 5. show interfaces neighbor expected — DEVICE_NEIGHBOR と組み合わせて近隣情報を表示

`show/interfaces/__init__.py:315-340` は `DEVICE_NEIGHBOR` と `DEVICE_NEIGHBOR_METADATA` を両方取得し、
`DEVICE_NEIGHBOR[port]['name']` をキーに `DEVICE_NEIGHBOR_METADATA[device]` の `lo_addr` / `mgmt_addr` / `type` 等を表示する。

依存テーブル: `CONFIG_DB DEVICE_NEIGHBOR`

### 6. db_migrator — EdgeZone Aggregator タイプ判定で DEVICE_NEIGHBOR と組み合わせ

`db_migrator.update_edgezone_aggregator_config()` (`db_migrator.py:765-790`) は DEVICE_NEIGHBOR_METADATA の
`type == 'EdgeZoneAggregator'` エントリを列挙し、DEVICE_NEIGHBOR で対応インターフェースを特定して
CABLE_LENGTH テーブルを更新する。

依存テーブル: `CONFIG_DB DEVICE_NEIGHBOR`, `CONFIG_DB CABLE_LENGTH`

---

## 暗黙参照サマリ

| # | 参照元 | 参照先テーブル | 参照フィールド | 用途 | 証跡 |
|---|--------|-------------|--------------|------|------|
| 1 | `bgpcfgd BGPPeerMgrBase.set_handler` | `BGP_NEIGHBOR` (キー), `DEVICE_METADATA\|localhost` | `type`, `hwsku`, `deployment_id` | BGP セッション Jinja2 テンプレートへの渡し | `managers_bgp.py:218-224` |
| 2 | `buffers_config.j2` | `DEVICE_NEIGHBOR`, `DEVICE_METADATA\|localhost`, `SYSTEM_DEFAULTS` | `type` | ケーブル長決定・extra queues ポートリスト構築 | `buffers_config.j2:81-82,209-210` |
| 3 | `qos_config.j2` | `DEVICE_NEIGHBOR`, `DEVICE_METADATA\|localhost` | `type` | アップリンク/ダウンリンクポートリスト分類 | `qos_config.j2:107-108,150-151` |
| 4 | `pfcwd get_server_facing_ports` | `DEVICE_NEIGHBOR` | `type` | サーバー向けポート判定（Server 型） | `pfcwd/main.py:97-108` |
| 5 | `show interfaces neighbor expected` | `DEVICE_NEIGHBOR` | `lo_addr`, `mgmt_addr`, `type` 等 | CLI 表示 | `show/interfaces/__init__.py:315-340` |
| 6 | `db_migrator update_edgezone_aggregator_config` | `DEVICE_NEIGHBOR`, `CABLE_LENGTH` | `type` | EdgeZone Aggregator インターフェースの CABLE_LENGTH 更新 | `db_migrator.py:765-790` |

---

## ページ反映方針

- `<!-- cross-refs -->` ブロックを `<!-- /ordering -->` の直後に挿入する。
- DEVICE_NEIGHBOR との密結合（全消費者が DEVICE_NEIGHBOR と組み合わせて参照）を主軸に記述。
- buffers/qos テンプレートによるポート分類の役割（`type` フィールドが SONiC のトポロジ認識を支配する）を明示する。
