# cluster フィールド — Phase B 書込み順依存スキャンノート

対象フィールド: `DEVICE_METADATA|localhost.cluster` / `DEVICE_NEIGHBOR_METADATA|<device>.cluster`
Consumer: `bgpcfgd (managers_bgp.py, managers_device_global.py)`, `swss_vars.j2`
ソース: `sonic-buildimage/src/sonic-config-engine/minigraph.py`, `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/`
スキャン範囲: `minigraph.py:493,514-515,662-668,2170-2172`, `bgpcfgd/managers_bgp.py`, `bgpcfgd/managers_device_global.py`

---

## 検出した順序依存・タイミング依存

### 1. minigraph パース順序 — DEVICE_METADATA は DEVICE_NEIGHBOR_METADATA より先に書き込まれる

- `minigraph.py` の `parse_minigraph()` 関数は `parse_device()` でデバイスリストを処理した後、`DEVICE_METADATA|localhost.cluster` を書き込む (minigraph.py:2170-2172)。
- `DEVICE_NEIGHBOR_METADATA` の `cluster` は `parse_device()` ループ内で各デバイスエントリを処理する際に書き込まれる (minigraph.py:662-668)。
- **順序依存**: `sonic-cfggen` が minigraph XML を処理する場合、`DEVICE_METADATA|localhost` に `cluster` が書き込まれる前に `DEVICE_NEIGHBOR_METADATA` エントリが処理される可能性がある（`parse_device` ループが `2170` より前に実行）。両フィールドは同一 `sonic-cfggen` 呼び出し内で書き込まれるため、**通常は原子的に完了**する。
- evidence: `minigraph.py:493,514-515,662-668,2170-2172`

### 2. bgpcfgd の DEVICE_METADATA 依存順序 — cluster フィールドは bgpcfgd が直接消費しない

- `bgpcfgd` は `DEVICE_METADATA|localhost` から `bgp_asn` / `type` / `deployment_id` を参照するが、`cluster` フィールドは直接参照しない (managers_bgp.py:119-143)。
- `managers_device_global.py` は `DEVICE_METADATA|localhost.type` を参照するが `cluster` は参照しない (managers_device_global.py:33,53-54)。
- **順序依存なし (bgpcfgd)**: `cluster` フィールドの書き込みタイミングは bgpcfgd の動作に影響を与えない。

### 3. swss_vars.j2 テンプレート展開 — DEVICE_METADATA 全フィールドが事前書き込み必要

- `swss_vars.j2` は Jinja2 テンプレート展開時に `DEVICE_METADATA|localhost` の全フィールドを参照する可能性がある。
- `cluster` フィールドが存在しない場合は空文字列として処理される（Jinja2 の `default('')` パターン）。
- **順序依存**: `swss_vars.j2` の展開は `sonic-cfggen` による CONFIG_DB 書き込み**後**に行われる。テンプレート展開前に `cluster` フィールドが書き込まれていれば問題なし。minigraph パース時に `<ClusterName>` が存在しない場合はフィールド自体が不在となり、Jinja2 は空文字列でフォールバックする。
- evidence: `bgpcfgd/managers_bgp.py:119-143`, `bgpcfgd/managers_device_global.py:33-54`

### 4. DEL / 上書き挙動 — minigraph 再適用時

- `sonic-cfggen -m minigraph.xml --write-to-db` を再実行した場合、既存の `cluster` フィールドは上書きされる。
- `if cluster:` (truthy) の条件により、`<ClusterName>` が空文字列または存在しない場合は `DEVICE_METADATA|localhost.cluster` が**書き込まれない**（古い値が DB に残る可能性あり）。
- **順序依存**: minigraph 再適用で `cluster` を削除したい場合は、`sonic-db-cli CONFIG_DB hdel 'DEVICE_METADATA|localhost' cluster` を手動実行する必要がある。自動的な DEL は行われない。
- evidence: `minigraph.py:2170-2172`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `DEVICE_NEIGHBOR_METADATA.cluster` パース → `DEVICE_METADATA.cluster` 書き込み | minigraph パース内で同一呼び出し（通常は問題なし） | `sonic-cfggen` が原子的に処理 |
| 2 | `cluster` フィールド → bgpcfgd | 依存なし | bgpcfgd は `cluster` フィールドを参照しない |
| 3 | `DEVICE_METADATA` 全体書き込み → swss_vars.j2 展開 | 書き込み後に展開 | `cluster` 不在時は空文字列フォールバック |
| 4 | minigraph 再適用で `cluster` 削除 | 自動削除なし | 手動 `hdel` が必要 |
