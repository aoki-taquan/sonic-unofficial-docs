# DEVICE_NEIGHBOR — Phase E ハードコード定数

## テーブル名文字列リテラル

| リテラル / 定数名 | 値 | 用途 | evidence |
|-----------------|-----|------|---------|
| `DEVICE_NEIGHBOR_TABLE_NAME` (ecnconfig) | `"DEVICE_NEIGHBOR"` | `ecnconfig` が `get_table()` に渡すテーブル名。`DEVICE_NEIGHBOR` のキー集合をポート一覧として使用 | `ecnconfig:93` |
| `get_table('DEVICE_NEIGHBOR')` (pfcwd) | `"DEVICE_NEIGHBOR"` | `pfcwd start_default` が外部ポート一覧を取得するテーブル名。文字列リテラルで直接指定 | `pfcwd/main.py:413` |
| `get_table("DEVICE_NEIGHBOR")` (show interfaces) | `"DEVICE_NEIGHBOR"` | `show interfaces expected` が隣接情報を読み出すテーブル名 | `show/interfaces/__init__.py:316` |
| `results['DEVICE_NEIGHBOR']` (minigraph) | `"DEVICE_NEIGHBOR"` | `sonic-cfggen` が CONFIG_DB へ書き込む際に使用する dict キー | `minigraph.py:2637` |

## フィールド名文字列リテラル（minigraph 生成時）

minigraph.py は `DeviceInterfaceLink` 型リンクを処理し、エントリを以下の 2 フィールド固定で生成する:

| フィールド | リテラル | evidence |
|-----------|---------|---------|
| `name` | `'name'` | 隣接ホスト名を格納するキー。`neighbors[port] = {'name': ..., 'port': ...}` | `minigraph.py:649,655` |
| `port` | `'port'` | 隣接側ポート名を格納するキー。同上 | `minigraph.py:649,655` |

`mgmt_addr`・`local_port`・`type` は minigraph 経由では DEVICE_NEIGHBOR テーブルに書き込まれない（DEVICE_NEIGHBOR_METADATA 側に書かれる）。

## YANG 長さ制約

| フィールド | 制約 | YANG ソース |
|-----------|------|------------|
| `peer_name` | `length 1..255` | `sonic-device_neighbor.yang:35-36` |
| `name` | `length 1..255` | `sonic-device_neighbor.yang:42-43` |
| `port` | `length 1..255` | `sonic-device_neighbor.yang:61-62` |
| `type` | `length 1..255` | `sonic-device_neighbor.yang:68-69` |
| `mgmt_addr` | `inet:ip-address` 型（IPv4/IPv6） | `sonic-device_neighbor.yang:46` |
| `local_port` | leafref → `PORT_LIST.name`（長さ制約は PORT 側） | `sonic-device_neighbor.yang:52-55` |

## リンク種別フィルタリング文字列（minigraph）

`minigraph.py` は `DeviceInterfaceLinks` セクションのリンクをフィルタリングする際に以下の文字列リテラルをハードコードで比較する:

| 文字列 | 用途 | evidence |
|--------|------|---------|
| `"DeviceInterfaceLink"` | DEVICE_NEIGHBOR に取り込む対象リンク種別 | `minigraph.py:631,636` |
| `"UnderlayInterfaceLink"` | 同上（DEVICE_NEIGHBOR へ取り込む） | `minigraph.py:636` |
| `"DeviceMgmtLink"` | 管理リンク — DEVICE_NEIGHBOR へは **取り込まない** | `minigraph.py:636,648,655` |
| `"DeviceSerialLink"` | シリアルリンク — DEVICE_NEIGHBOR へは取り込まない | `minigraph.py:610` |

`DeviceMgmtLink` 以外の `DeviceInterfaceLink` / `UnderlayInterfaceLink` だけが `neighbors` dict（= DEVICE_NEIGHBOR の元データ）に追加される。

## エラーメッセージ文字列リテラル

| コンポーネント | 文字列 | evidence |
|--------------|--------|---------|
| `minigraph.py` | `"Warning: ignore interface '%s' in DEVICE_NEIGHBOR as it is not in the port_config.ini"` | `minigraph.py:2635` |
| `ecnconfig` | `"No active ports detected in table '{}'"` | `ecnconfig:287` |
| `show interfaces` | `"DEVICE_NEIGHBOR information is not present."` | `show/interfaces/__init__.py:318` |
| `managers_bgp.py` | `"DEVICE_NEIGHBOR_METADATA is not ready for neighbor '%s' - '%s'"` | `managers_bgp.py:222` |

## ポートソート定数（ecnconfig）

`ecnconfig` は `DEVICE_NEIGHBOR.keys()` から取得したポート一覧を以下のキー関数でソートする:

```python
self.ports_key.sort(
    key = lambda k: int(k[8:]) if "BP" not in k else int(k[11:]) + 1024
)
```

- `k[8:]`: `"Ethernet"` の 8 文字をスキップして数値部分を取得
- `"BP"` 含む場合: バックプレーンポート（`Ethernet-BPxy`）は数値に `1024` を加算してソート末尾へ
- これらはコードハードコードで YANG 未定義

evidence: `ecnconfig:291-294`

## ポート description 生成フォーマット（minigraph）

minigraph.py はポートに `description` が設定されていない場合、DEVICE_NEIGHBOR の情報から以下のフォーマットで自動設定する:

```python
port['description'] = "%s:%s" % (neighbors[port_name]['name'], neighbors[port_name]['port'])
```

形式: `<隣接ホスト名>:<隣接ポート名>`（コロン区切り、ハードコード）

evidence: `minigraph.py:2465`
