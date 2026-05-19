# DEVICE_NEIGHBOR_METADATA — Phase E ハードコード定数スキャンノート

対象テーブル: `DEVICE_NEIGHBOR_METADATA`
Consumer: `minigraph.py` (sonic-buildimage), `pfcwd/main.py` (sonic-utilities), `db_migrator.py` (sonic-utilities), `bgpcfgd/managers_bgp.py` (sonic-buildimage), `buffers_config.j2` / `qos_config.j2` (sonic-buildimage)
スキャン範囲: 各ファイルの全行精読

---

## 検出したハードコード定数

### 1. minigraph.py — device type リテラル (sonic-buildimage/src/sonic-config-engine/minigraph.py)

- L51: `backend_device_types = ['BackEndToRRouter', 'BackEndLeafRouter']`
- L53: `dhcp_server_enabled_device_types = ['BmcMgmtToRRouter']`
- L54: `mgmt_device_types = ['BmcMgmtToRRouter', 'MgmtToRRouter', 'MgmtTsToR']`
- L55: `leafrouter_device_types = ['LeafRouter']`
- これらは DEVICE_NEIGHBOR_METADATA の `type` フィールドに書き込まれる値の候補ではなく、DEVICE_METADATA.localhost.type を判定するためのリスト。
  ただし DEVICE_NEIGHBOR_METADATA の `type` フィールドも同じ文字列定数セット（`LeafRouter`, `SpineRouter`, `ToRRouter`, `Server`, `EdgeZoneAggregator` 等）を利用する。

### 2. minigraph.py — slice_type ハードコード値

- L518-519:
  ```python
  elif node.tag == str(QName(ns, "AssociatedSliceStr")) and node.text and "AZNG_Production" in node.text:
      slice_type = "AZNG_Production"
  ```
- `AssociatedSliceStr` に "AZNG_Production" が含まれる場合のみ `slice_type = "AZNG_Production"` と固定値で書き込む。他の値は一切書き込まれない（YANG 定義上は string だが、実装は事実上固定値 or None）。

### 3. pfcwd/main.py — サーバー判定文字列

- L104: `if neighbor and neighbor['type'].lower() == 'server':`
- `'server'` は大文字小文字を区別しない比較（`.lower()`）でハードコード。
- サーバー向けポートがゼロ件の場合 `VLAN_MEMBER` フォールバック（L107）。フォールバック判定に定数なし（空リストチェックのみ）。

### 4. db_migrator.py — EdgeZoneAggregator ケーブル長

- L771: `EDGEZONE_AGG_CABLE_LENGTH = "40m"`
- L772: `if v.get("type") == "EdgeZoneAggregator":`（大文字小文字感受、完全一致）
- L783: `cable_length_table = self.configDB.get_entry("CABLE_LENGTH", "AZURE")` — "AZURE" もハードコード（CABLE_LENGTH テーブルのキー名として固定）

### 5. bgpcfgd/managers_bgp.py — `use_neighbors_meta` / `use_deployment_id` フラグ

- L129-131: `self.check_neig_meta` は `constants['bgp']['use_neighbors_meta']` が True の場合のみ True になる。
  このフラグが False の場合、DEVICE_NEIGHBOR_METADATA は依存テーブルとして登録されず参照もされない（条件分岐のみで定数値なし）。
- フラグ自体のデフォルト値は bgpcfgd の外部定数ファイル（`constants.json` 相当）で管理され、コード内リテラルではない。

### 6. buffers_config.j2 / qos_config.j2 — type 比較文字列

- `buffers_config.j2`: `neighbor_role | lower` を使って大文字小文字非感受で比較。`'LeafRouter'`, `'ToRRouter'`, `'SpineRouter'` がテンプレート内に直接文字列リテラルとして存在。
- `qos_config.j2`: `'ToRRouter' in neighbor_info.type` — 大文字小文字感受、部分一致チェック。`'LeafRouter'`, `'SpineRouter'` も同様に文字列リテラル。

---

## 定数サマリ

| 定数 / リテラル | 値 | 場所 | 用途 |
|---|---|---|---|
| `backend_device_types` | `['BackEndToRRouter', 'BackEndLeafRouter']` | minigraph.py:51 | DEVICE_METADATA.localhost.type 判定 |
| `leafrouter_device_types` | `['LeafRouter']` | minigraph.py:55 | DEVICE_METADATA.localhost.type 判定 |
| `slice_type` 固定値 | `"AZNG_Production"` | minigraph.py:519 | `AssociatedSliceStr` 条件付きハードコード |
| pfcwd サーバー判定 | `'server'` (lower 比較) | pfcwd/main.py:104 | サーバー向けポート分類 |
| EdgeZoneAggregator ケーブル長 | `"40m"` | db_migrator.py:771 | EdgeZone AGG 接続ポートの CABLE_LENGTH 強制値 |
| CABLE_LENGTH キー | `"AZURE"` | db_migrator.py:783 | CABLE_LENGTH テーブルの参照キー |
| EdgeZoneAggregator 型名 | `"EdgeZoneAggregator"` | db_migrator.py:772 | 大文字小文字感受の完全一致 |
| `'ToRRouter'` / `'LeafRouter'` / `'SpineRouter'` | 文字列リテラル | buffers_config.j2, qos_config.j2 | ポートロール分類（buffers/QoS テンプレート） |
