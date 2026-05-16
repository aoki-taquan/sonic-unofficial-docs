# cluster フィールド 暗黙参照スキャン (Phase C)

`docs/reference/config-db/cluster.md` の Phase C (暗黙参照) ブロック裏付け資料。

対象フィールド:
- `DEVICE_METADATA|localhost.cluster`
- `DEVICE_NEIGHBOR_METADATA|<device>.cluster`

## スキャン手順

```bash
# 1. cluster フィールドを直接読む箇所
grep -rn "\.cluster\|\[.cluster.\]" \
  .cache/sonic-sources/sonic-buildimage/src/ \
  --include="*.py" --include="*.j2" --include="*.cpp" | grep -v test

# 2. DEVICE_NEIGHBOR_METADATA を subscribe / read するデーモンが cluster を使うか
grep -rn "neigmeta\|DEVICE_NEIGHBOR_METADATA\[" \
  .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/ --include="*.j2"

# 3. swss_vars.j2 / buffers_config.j2 / qos_config.j2 で cluster フィールドの参照
grep -n "cluster" \
  .cache/sonic-sources/sonic-buildimage/files/build_templates/buffers_config.j2 \
  .cache/sonic-sources/sonic-buildimage/files/build_templates/qos_config.j2 \
  .cache/sonic-sources/sonic-buildimage/files/build_templates/swss_vars.j2
```

## 検出結果

### CONFIG_DB 消費側

`cluster` フィールドを **直接読む** デーモン・スクリプトはコードベース全体で確認されなかった。

`DEVICE_NEIGHBOR_METADATA` テーブル全体を subscribe するデーモンとして `bgpcfgd` (`managers_bgp.py:140`) が存在するが、参照するのは `name` フィールドの存在確認 (ready チェック) のみであり (`managers_bgp.py:221-222`)、`cluster` フィールドには一切アクセスしない。

`buffers_config.j2` / `qos_config.j2` は `DEVICE_NEIGHBOR_METADATA[...].type` フィールドを参照するが、`cluster` フィールドは参照しない（grep 結果: 0 件）。

`swss_vars.j2` も `cluster` を参照しない（grep 結果: 0 件）。

| 参照候補 | cluster 参照 | 参照フィールド (実際) | evidence |
|---------|-------------|-------------------|---------|
| `bgpcfgd managers_bgp.py` | **なし** | `name` (ready check のみ) | `managers_bgp.py:220-222` |
| `bgpcfgd templates/*.j2` | **なし** | — | grep 0 件 |
| `buffers_config.j2` | **なし** | `.type` | `buffers_config.j2:83,209-210` |
| `qos_config.j2` | **なし** | `.type` | `qos_config.j2:107-116,150-151` |
| `swss_vars.j2` | **なし** | — | grep 0 件 |
| `hostcfgd` | **なし** | — | grep 0 件 |
| `orchagent` | **なし** | — | grep 0 件 |

### 書き込み経路（再確認）

`cluster` フィールドを書き込むのは `minigraph.py` のみ。

| 書き込み元 | 対象テーブル | evidence |
|-----------|------------|---------|
| `minigraph.py:668` | `DEVICE_NEIGHBOR_METADATA|<device>` | `minigraph.py:662-668` |
| `minigraph.py:811` | `DEVICE_NEIGHBOR_METADATA|<device>` (chassis 用途) | `minigraph.py:806-811` |
| `minigraph.py:2172` | `DEVICE_METADATA|localhost` | `minigraph.py:2170-2172` |

### test コードによる存在確認

`test_minigraph_case.py:207-217` に `test_minigraph_cluster()` があり、`DEVICE_METADATA['localhost']['cluster']` が `'DB5PrdApp11'` であることを assert している。これは minigraph→DB の書き込みが正しく機能することのリグレッションテスト。`test_chassis_cfggen.py` でも複数箇所で `'cluster': 'TestbedForstr-sonic'` が期待値として用いられており、chassis 環境における `DEVICE_NEIGHBOR_METADATA` への書き込みも確認されている。

## まとめ — `cluster.md` Phase C 記載対象

| カテゴリ | 対象 | 種別 |
|---|---|---|
| 共依存 CONFIG_DB テーブル | **なし** | cluster フィールドは独立 |
| ランタイム消費デーモン | **なし** | 書き込み専用フィールド |
| 隣接テーブル参照 | `DEVICE_METADATA` / `DEVICE_NEIGHBOR_METADATA` (親テーブル) | cluster フィールドを介した相互参照なし |
| テスト確認 | `test_minigraph_case.py` / `test_chassis_cfggen.py` | 書き込み正確性の回帰テスト |

`cluster` フィールドは **write-only** の性質を持つ — minigraph XML → CONFIG_DB への一方向伝達のみであり、デーモンがランタイムで読み出して動作を変える経路は存在しない。
