# DEVICE_NEIGHBOR — Phase H プラットフォーム差調査

対象ページ: `docs/reference/config-db/device-neighbor.md`
調査日: 2026-05-19
ソース: `sonic-buildimage/src/sonic-config-engine/minigraph.py`

---

## 調査方針

`DEVICE_NEIGHBOR` テーブルは orchagent / SAI を経由しないため、ASIC 固有の platform 分岐（`getenv("platform")` 等）は存在しない。プラットフォーム差が生じるのは **minigraph.py によるテーブル生成時** のトポロジ種別（multi-ASIC pizza box / VoQ chassis / DualToR）に起因する差異のみ。

---

## 分岐 1: 非 multi-ASIC（単一 ASIC pizza box）— 通常パス

**ソース**: `minigraph.py:2090`

```python
(neighbors, devices, ...) = parse_png(child, hostname, dpg_ecmp_content)
```

- `parse_png()` は minigraph XML の `<PngDec>` セクションを解析し `neighbors` を返す。
- キーはホスト側ポート名（エイリアス変換済み）、値は `{'name': <peer_hostname>, 'port': <peer_port>}`。
- `DeviceInterfaceLink` と `UnderlayInterfaceLink` タイプのリンクのみ取り込む（`minigraph.py:631-651`）。
- `DeviceMgmtLink` / `DeviceSerialLink` は取り込まない。

**DEVICE_NEIGHBOR_METADATA の生成**:

```python
# minigraph.py:2638-2639
if is_multi_asic() == False or asic_name is None:
    results['DEVICE_NEIGHBOR_METADATA'] = { key:devices[key] for key in devices if key.lower() != hostname.lower() }
```

- 自ホスト以外の **全デバイス** が DEVICE_NEIGHBOR_METADATA に登録される。
- DEVICE_NEIGHBOR に登場しないデバイスも含まれる（スコープが広い）。

---

## 分岐 2: multi-ASIC pizza box（asic_name 指定時）

**ソース**: `minigraph.py:2106`

```python
(neighbors, devices, port_speed_png) = parse_asic_png(child, asic_hostname, hostname)
```

- `parse_asic_png()` が使用される（`parse_png()` ではない）。
- リンクの `<ChassisInternal>` 要素によって外部リンク / 内部リンクを分類する。

### 外部リンク（`ChassisInternal == "false"`）

```python
# parse_asic_external_link() — minigraph.py:727-752
neighbors[port_alias_map[endport]] = {'name': startdevice, 'port': startport}
```

- 外部ネイバー（TOR ルータ等）への接続を DEVICE_NEIGHBOR に登録する。
- ポート名は `port_alias_asic_map` → `port_alias_map` の二段変換でエイリアスを解決する。

### 内部リンク（`ChassisInternal == "true"`）

```python
# parse_asic_internal_link() — minigraph.py:753-778
neighbors[endport] = {'name': startdevice, 'port': startport}
```

- ASIC 間インターコネクト（BackEnd ポート）も DEVICE_NEIGHBOR に登録される。
- BackEnd ASIC では内部リンクのみが DEVICE_NEIGHBOR に登録されるため、`pfcwd start_default` がポート一覧を DEVICE_NEIGHBOR から取得すると BackEnd ASIC のポートを外部ポートとして扱う誤動作が生じる可能性がある。

### DEVICE_NEIGHBOR_METADATA のスコープ限定（multi-ASIC 時）

```python
# minigraph.py:2640-2641
else:
    results['DEVICE_NEIGHBOR_METADATA'] = { key:devices[key] for key in devices if key in {device['name'] for device in neighbors.values()} }
```

- multi-ASIC かつ `asic_name` が指定されている場合、DEVICE_NEIGHBOR の `name` フィールドに登場するデバイスのみが DEVICE_NEIGHBOR_METADATA に登録される。
- 非 multi-ASIC の「全デバイス登録」とは異なる、スコープが狭い登録。
- BGP セッション確立時に `bgpcfgd` は DEVICE_NEIGHBOR_METADATA の存在を確認するため、スコープ差がある。

---

## 分岐 3: VoQ chassis（chassis_type == "VoQ"）

**ソース**: `minigraph.py:85, 178-179, 2061`

```python
CHASSIS_CARD_VOQ = 'VoQ'
...
def is_minigraph_for_chassis(chassis_type):
    if chassis_type in [CHASSIS_CARD_VOQ, CHASSIS_CARD_PACKET]:
        return True
```

VoQ chassis では `chassis_hostname` が非 None となり、追加パース処理が走る（`minigraph.py:2113-2120`）。

### VoQ chassis の DEVICE_NEIGHBOR 生成

VoQ chassis ラインカードでは `asic_hostname` が設定されるため `parse_asic_png()` が使用される（multi-ASIC と同じ分岐）。ただし VoQ 固有の差異がある:

1. **内部 VoQ インターフェイス（cpu/recirc/inband）**: `parse_chassis_deviceinfo_voq_int_intfs()` で別途管理される。これらは DEVICE_NEIGHBOR には登録されない（`voq_internal_intfs = ['cpu', 'recirc', 'inband']`、`minigraph.py:88`）。

2. **`BGP_VOQ_CHASSIS_NEIGHBOR` テーブル**: VoQ chassis では `DEVICE_NEIGHBOR` に加えて、VoQ シャーシ内部の BGP セッション用に `BGP_VOQ_CHASSIS_NEIGHBOR` テーブルが生成される（`minigraph.py:2277`）。DEVICE_NEIGHBOR は外部 BGP neighbor 向けのまま。

3. **Spine chassis frontend ロール（SpineChassisFrontendRouter）**: `parse_spine_chassis_fe()` (`minigraph.py:1719`) が `DEVICE_NEIGHBOR` を参照し、隣接デバイスのタイプが `ChassisBackendRouter` でない（外部ルータ）場合にインターフェイスを VnetFE に enslaved させる。DEVICE_NEIGHBOR の `name` フィールドが vnet 割り当ての判定に使用される。

```python
# minigraph.py:1749-1753
neighbor_router = results['DEVICE_NEIGHBOR'][intf]['name']
if devices[neighbor_router]['type'] != chassis_backend_role:
    phyport_intfs[intf] = {'vnet_name': chassis_vnet}
```

4. **switch_type フィールド**: VoQ chassis では `DEVICE_METADATA.localhost.switch_type = 'voq'` が設定されるが（`minigraph.py:2232-2237`）、DEVICE_NEIGHBOR 自体の内容には影響しない。

---

## 分岐 4: DualToR（ActiveStandby / ActiveActive 冗長構成）

**ソース**: `minigraph.py:2186-2193, 2616-2622, 2786-2812`

DualToR 構成は `PEER_SWITCH` テーブルの有無で判定される:

```python
# minigraph.py:2186-2189
results['PEER_SWITCH'], mux_tunnel_name, peer_switch_ip = get_peer_switch_info(linkmetas, devices)
if bool(results['PEER_SWITCH']):
    results['DEVICE_METADATA']['localhost']['subtype'] = 'DualToR'
```

### DualToR の DEVICE_NEIGHBOR への影響

- **DEVICE_NEIGHBOR 自体の生成ロジックに変化なし**: DualToR でも `parse_png()` → `neighbors` の通常パスで DEVICE_NEIGHBOR が生成される。T0 スイッチとしての外部隣接情報はそのまま登録される。

- **MUX_CABLE テーブルとの関係**: `parse_png()` の `mux_cable_ports` dict（`LogicalLink` タイプのリンクから生成）は DEVICE_NEIGHBOR とは別に MUX_CABLE テーブルへ書き込まれる（`minigraph.py:2617`）。DEVICE_NEIGHBOR は影響を受けない。

- **DEVICE_NEIGHBOR_METADATA**: DualToR 時も非 multi-ASIC の通常パスのため `is_multi_asic() == False or asic_name is None` 分岐が適用され、全デバイスが DEVICE_NEIGHBOR_METADATA に登録される。peer switch（対向 ToR）も含まれる。

- **ActiveActive（Libra/Gemini）構成**: `get_ports_in_active_active()` / `get_mux_cable_entries()` が追加テーブル（MUX_CABLE の `cable_type`）を生成するが、DEVICE_NEIGHBOR は変化しない。

---

## platform 文字列分岐の有無

`minigraph.py` において `getenv("platform")` / `platform` 引数による DEVICE_NEIGHBOR 生成ロジックへの分岐は**存在しない**。`platform` 引数は `get_port_config()` に渡されポート設定の読み込みに使用されるが（`minigraph.py:2064`）、DEVICE_NEIGHBOR の内容には影響しない。

---

## プラットフォーム差サマリ

| 構成 | 生成関数 | DEVICE_NEIGHBOR の内容 | DEVICE_NEIGHBOR_METADATA スコープ |
|------|---------|----------------------|----------------------------------|
| 非 multi-ASIC (pizza box) | `parse_png()` | 外部隣接のみ（DeviceInterfaceLink / UnderlayInterfaceLink） | 全デバイス（自ホスト除く） |
| multi-ASIC pizza box | `parse_asic_png()` | 外部隣接 + 内部リンク（ChassisInternal 分類） | DEVICE_NEIGHBOR に登場するデバイスのみ |
| VoQ chassis ラインカード | `parse_asic_png()` | 外部隣接 + 内部リンク（voq_internal_intfs 除く） | DEVICE_NEIGHBOR に登場するデバイスのみ |
| DualToR | `parse_png()` | 外部隣接のみ（T0 トポロジ通常） | 全デバイス（peer switch 含む） |

---

## Evidence

- `minigraph.py:85-88`: `CHASSIS_CARD_VOQ`, `chassis_backend_role`, `voq_internal_intfs` 定数
- `minigraph.py:178-179`: `is_minigraph_for_chassis()` 判定
- `minigraph.py:599-724`: `parse_png()` — 非 multi-ASIC パス
- `minigraph.py:727-778`: `parse_asic_external_link()`, `parse_asic_internal_link()`
- `minigraph.py:779-839`: `parse_asic_png()` — multi-ASIC / VoQ chassis パス
- `minigraph.py:1719-1782`: `parse_spine_chassis_fe()` — Spine chassis frontend ロール
- `minigraph.py:2064,2066-2070`: `get_port_config()` / `asic_hostname` 解決
- `minigraph.py:2086-2112`: `asic_hostname` 有無による parse_png / parse_asic_png 分岐
- `minigraph.py:2186-2193`: DualToR 判定 / `PEER_SWITCH` テーブル生成
- `minigraph.py:2277`: `BGP_VOQ_CHASSIS_NEIGHBOR` 生成（VoQ 専用）
- `minigraph.py:2616-2622`: MUX_CABLE テーブル生成（DualToR 用）
- `minigraph.py:2631-2641`: DEVICE_NEIGHBOR 確定 / DEVICE_NEIGHBOR_METADATA スコープ分岐
