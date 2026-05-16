# DEVICE_NEIGHBOR — Phase A: device op state 関連フィールドのコード由来デフォルト

## 調査方法

1. フィールド列挙: YANG `sonic-device_neighbor.yang` (buildimage) + `sonic-device-neighbor.yang` (sonic-mgmt-common)
2. エントリ grep 1回: `grep -rln "DEVICE_NEIGHBOR" .cache/sonic-sources/`
3. consumer 全行精読: `pfcwd/main.py`, `ecnconfig`, `show/interfaces/__init__.py`, `lldpmgrd`, `managers_bgp.py`, `minigraph.py`

対象ファイル:
- `sonic-utilities/pfcwd/main.py:97-108,405-416`
- `sonic-utilities/scripts/ecnconfig:93,282-287`
- `sonic-utilities/show/interfaces/__init__.py:310-365`
- `sonic-buildimage/dockers/docker-lldp/lldpmgrd:12-14,74-78`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:139-140,219-224`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py:649,2631-2641`

---

## 1. DEVICE_NEIGHBOR が「外部ポート (external port) 一覧」として機能するメカニズム

### 1-1. pfcwd における外部ポート判定

`pfcwd start_default` (pfcwd/main.py:413) は:

```python
external_ports = list(self.config_db.get_table('DEVICE_NEIGHBOR').keys())
bp_ports = get_bp_ports(self.config_db)
active_ports = natsorted(set(external_ports + bp_ports))
```

- DEVICE_NEIGHBOR の **key 集合** = 外部ポート一覧として扱う
- バックプレーンポート（`PORT.role == 'Int'` かつ `admin_status == 'up'`）と union して `active_ports` を構成
- テーブルが空 → `external_ports = []` → バックプレーンポートのみが `active_ports` になる（外部ポートなしの扱い）

### 1-2. pfcwd のサーバー向けポート判定

`get_server_facing_ports()` (pfcwd/main.py:97-108):

```python
candidates = db.get_table('DEVICE_NEIGHBOR')
for port in candidates:
    neighbor = db.get_entry('DEVICE_NEIGHBOR_METADATA', candidates[port]['name'])
    if neighbor and neighbor['type'].lower() == 'server':
        server_facing_ports.append(port)
if not server_facing_ports:
    server_facing_ports = [p[1] for p in db.get_table('VLAN_MEMBER')]
```

- `DEVICE_NEIGHBOR.keys()` でポートを列挙し、DEVICE_NEIGHBOR_METADATA の `type` が `server` のポートをサーバー向けと判定
- サーバー向けポートが **0 件** の場合は `VLAN_MEMBER` のポートにフォールバック（`pfcwd/main.py:106-107`）

### 1-3. ecnconfig における外部ポート一覧

`ecnconfig` (ecnconfig:93,282-287) は非 multi-ASIC 環境で:

```python
port_table = self.config_db.get_table(DEVICE_NEIGHBOR_TABLE_NAME)
self.ports_key = list(port_table.keys())
if len(self.ports_key) == 0:
    raise Exception("No active ports detected in table '{}'".format(DEVICE_NEIGHBOR_TABLE_NAME))
```

- DEVICE_NEIGHBOR が空 → **Exception** を raise して動作停止（pfcwd と異なり例外）
- multi-ASIC 環境では代わりに `SYSTEM_PORT_TABLE` を使用する（ブランチ分岐）

---

## 2. lldpmgrd における DEVICE_NEIGHBOR 非購読（dead consumer）

`lldpmgrd` のソース (lldpmgrd:12-14) に明示:

```python
# TODO: Also listen for changes in DEVICE_NEIGHBOR and PORT tables in
#       Config DB and update LLDP config upon changes.
```

実際の subscribe 対象:
- `APP_PORT_TABLE_NAME` (APPL_DB) — port oper_status 変化
- `CFG_MGMT_INTERFACE_TABLE_NAME` (CONFIG_DB) — 管理 IP 変化
- `CFG_DEVICE_METADATA_TABLE_NAME` (CONFIG_DB) — hostname 変化

DEVICE_NEIGHBOR は**まったく購読されていない**。lldpmgrd の処理に DEVICE_NEIGHBOR の内容は影響しない。

---

## 3. `show interfaces neighbor expected` における表示ロジック

`show/interfaces/__init__.py:310-365`:

```python
neighbor_dict = db.cfgdb_clients[namespace].get_table("DEVICE_NEIGHBOR")
neighbor_metadata_dict = db.cfgdb_clients[namespace].get_table("DEVICE_NEIGHBOR_METADATA")
```

表示カラム: `LocalPort | Neighbor | NeighborPort | NeighborLoopback | NeighborMgmt | NeighborType`

データソース:
- `LocalPort`: DEVICE_NEIGHBOR の key
- `Neighbor`: `DEVICE_NEIGHBOR[port]['name']`
- `NeighborPort`: `DEVICE_NEIGHBOR[port]['port']`
- `NeighborLoopback`: `DEVICE_NEIGHBOR_METADATA[device]['lo_addr']`（欠落時は文字列 `'None'`）
- `NeighborMgmt`: `DEVICE_NEIGHBOR_METADATA[device]['mgmt_addr']`（欠落時は文字列 `'None'`）
- `NeighborType`: `DEVICE_NEIGHBOR_METADATA[device]['type']`（欠落時は文字列 `'None'`）

注意点:
- DEVICE_NEIGHBOR が None → `"DEVICE_NEIGHBOR information is not present."` 表示で即 return
- DEVICE_NEIGHBOR_METADATA が None → `"DEVICE_NEIGHBOR_METADATA information is not present."` 表示で即 return
- 両テーブルがある場合でも `neighbor_dict[interfacename]` が KeyError → `"No neighbor information available for interface {}"` 表示

---

## 4. bgpcfgd における DEVICE_NEIGHBOR_METADATA 依存待機

`managers_bgp.py:139-140,219-224`:

- `check_neig_meta = True` の場合、`CFG_DEVICE_NEIGHBOR_METADATA_TABLE_NAME` が依存テーブルとして登録される
- BGP neighbor の `set_handler` で `data['name']` が DEVICE_NEIGHBOR_METADATA に不在の場合 → `return False`（延期処理）
- テーブル到着後に自動再処理（`deps` 登録による directory メカニズム）

DEVICE_NEIGHBOR 本体は bgpcfgd の依存対象ではなく、DEVICE_NEIGHBOR_METADATA のみが依存登録される。

---

## 5. フィールド別コード由来デフォルトまとめ

| フィールド | YANG default | コード由来挙動 | カテゴリ |
|-----------|-------------|----------------|---------|
| `peer_name` (key) | なし（必須） | pfcwd / ecnconfig が key 集合を外部ポート一覧として使用。空テーブル → pfcwd: 外部ポートなし / ecnconfig: Exception | 複合必須制約 |
| `name` | なし | bgpcfgd: DEVICE_NEIGHBOR_METADATA に不在 → `return False` 延期。lldpmgrd は参照しない（dead consumer） | 前提条件依存 + dead consumer |
| `port` | なし | `show interfaces neighbor expected` で直接参照。欠落時 KeyError → "No neighbor information available" 表示 | silent drop 候補 |
| `mgmt_addr` | なし | DEVICE_NEIGHBOR テーブルの `mgmt_addr` を参照する consumer なし（dead field）。show コマンドは DEVICE_NEIGHBOR_METADATA 側を参照 | dead field |
| `local_port` | なし（leafref → PORT.name） | pfcwd が key（peer_name）を外部ポートとして使用するため、local_port と key が実質同値。テーブル空 → pfcwd が外部ポートなしと判定 / ecnconfig が Exception | YANG leafref + 副作用 |
| `type` | なし（string 制約なし） | DEVICE_NEIGHBOR の `type` を直接参照する consumer はコードベース上で確認できない。pfcwd は DEVICE_NEIGHBOR_METADATA 側の `type` を参照（dead field 候補） | dead field 候補 |

---

## 6. テーブル空時の consumer 別挙動まとめ

| consumer | テーブル空時の挙動 | エラー種別 |
|---------|-----------------|---------|
| pfcwd start_default | `external_ports = []` → バックプレーンポートのみで active_ports 構成 | サイレント（動作継続） |
| pfcwd get_server_facing_ports | サーバー向けポート 0 件 → VLAN_MEMBER にフォールバック | サイレント（フォールバック） |
| ecnconfig (非 multi-ASIC) | `Exception("No active ports detected...")` raise | 例外（動作停止） |
| show interfaces neighbor expected | `"DEVICE_NEIGHBOR information is not present."` 表示して return | ユーザー表示のみ |
| bgpcfgd | DEVICE_NEIGHBOR を直接参照しない | 影響なし |
| lldpmgrd | DEVICE_NEIGHBOR を購読しない（TODO 状態） | 影響なし |

---

## Evidence

- `sonic-utilities` `pfcwd/main.py:97-108,405-416`
- `sonic-utilities` `scripts/ecnconfig:93,282-287`
- `sonic-utilities` `show/interfaces/__init__.py:310-365`
- `sonic-buildimage` `dockers/docker-lldp/lldpmgrd:12-14`
- `sonic-buildimage` `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:139-140,219-224`
- `sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-device_neighbor.yang`
- `sonic-mgmt-common` `cvl/testdata/schema/sonic-device-neighbor.yang`
