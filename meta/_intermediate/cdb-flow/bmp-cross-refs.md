# BMP — 暗黙参照 (Phase C cross-refs)

調査対象ソース:
- `sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

---

## 検出された暗黙参照

### 1. BMP_STATE_DB.BGP_NEIGHBOR* (書込先・間接)

- 参照種別: **間接 populate（openbmpd 経由）**
- `bmpcfgd.py` L41: `bgp_neighbor_table` フラグが `true` の場合、openbmpd 再起動後に openbmpd が `BMP_STATE_DB` へ `BGP_NEIGHBOR|<peer>` エントリを非同期書き込み
- `bmpcfgd.py` L63: `reset_bmp_table()` で `delete_all_by_pattern(BMP_STATE_DB, 'BGP_NEIGHBOR*')` — CONFIG_DB 変更の都度クリア
- 関係: `CONFIG_DB.BMP.bgp_neighbor_table=true` → openbmpd → `BMP_STATE_DB.BGP_NEIGHBOR*`

### 2. BMP_STATE_DB.BGP_RIB_IN_TABLE* (書込先・間接)

- 参照種別: **間接 populate（openbmpd 経由）**
- `bmpcfgd.py` L42: `bgp_rib_in_table` フラグが `true` の場合、openbmpd が `BMP_STATE_DB` へ `BGP_RIB_IN_TABLE|<peer>` エントリを書き込む
- `bmpcfgd.py` L64: reset 時に `delete_all_by_pattern(BMP_STATE_DB, 'BGP_RIB_IN_TABLE*')`

### 3. BMP_STATE_DB.BGP_RIB_OUT_TABLE* (書込先・間接)

- 参照種別: **間接 populate（openbmpd 経由）**
- `bmpcfgd.py` L43: `bgp_rib_out_table` フラグが `true` の場合、openbmpd が `BMP_STATE_DB` へ `BGP_RIB_OUT_TABLE|<peer>` エントリを書き込む
- `bmpcfgd.py` L65: reset 時に `delete_all_by_pattern(BMP_STATE_DB, 'BGP_RIB_OUT_TABLE*')`

### 4. CONFIG_DB.BGP_NEIGHBOR (読取・間接)

- 参照種別: **間接参照（openbmpd がデータソースとして利用）**
- `bmpcfgd.py` 自体は `BGP_NEIGHBOR` テーブルを直接読まないが、`bgp_neighbor_table=true` 時に openbmpd が `BGP_NEIGHBOR` の peer リストを BMP dump の対象として利用する
- `frrcfgd.py` L89: `BGP_NEIGHBOR` を `bgpd` プロセスへ反映。frrcfgd と bmpcfgd は独立して動作し、BMP が監視する peer はこの `BGP_NEIGHBOR` テーブルで定義される

### 5. CONFIG_DB.BGP_GLOBALS (読取・間接)

- 参照種別: **間接参照（frrcfgd が BGP セッション文脈を提供）**
- `frrcfgd.py` L81: `BGP_GLOBALS` を `bgpd` プロセスへ反映。BMP が動作するには FRR BGP セッションが確立している必要があり、BGP_GLOBALS で定義された AS・router-id 等が前提となる
- `bmpcfgd.py` は `BGP_GLOBALS` を直接読まないが、FRR BMP プラグインは BGP セッション文脈（BGP_GLOBALS 由来の AS番号・peer 情報）を BMP メッセージ内に含める

### 6. CONFIG_DB.DEVICE_METADATA.bgp_asn (読取・間接)

- 参照種別: **間接参照（FRR テンプレート経由）**
- `bgpd.main.conf.j2` L94: `DEVICE_METADATA['localhost']['bgp_asn']` が未設定または `"none"` / `"null"` の場合、`router bgp` ブロックが生成されず `bmp targets sonic-bmp` が FRR に注入されない
- BMP 機能の有効化は `DEVICE_METADATA|localhost.bgp_asn` の設定を前提とする
- `bmpcfgd.py` は `DEVICE_METADATA` を直接参照しないが、FRR テンプレートを通じた暗黙の依存が存在する
- evidence: `dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2:94-136`

---

## frrcfgd.py の BMP 関連確認

`frrcfgd.py` 全行を grep した結果:
- `bmp` / `BMP` 文字列のヒット: **0件**
- BMP テーブルの直接購読: **なし**
- frrcfgd は BGP_GLOBALS / BGP_NEIGHBOR 等の BGP 設定を FRR bgpd に反映する役割のみ

BMP の設定注入は `bgpd.main.conf.j2` テンプレートで起動時にハードコードされ、`bmpcfgd` が openbmpd のライフサイクルのみを管理する設計。

---

## 暗黙参照マトリクス（サマリ）

| 参照先 | 種別 | 方向 | 直接/間接 | ソース |
|--------|------|------|-----------|--------|
| `BMP_STATE_DB.BGP_NEIGHBOR*` | State テーブル | BMP → BMP_STATE_DB | 間接（openbmpd） | bmpcfgd.py L63 |
| `BMP_STATE_DB.BGP_RIB_IN_TABLE*` | State テーブル | BMP → BMP_STATE_DB | 間接（openbmpd） | bmpcfgd.py L64 |
| `BMP_STATE_DB.BGP_RIB_OUT_TABLE*` | State テーブル | BMP → BMP_STATE_DB | 間接（openbmpd） | bmpcfgd.py L65 |
| `CONFIG_DB.BGP_NEIGHBOR` | CONFIG テーブル | BGP_NEIGHBOR → BMP dump | 間接（openbmpd peer リスト） | bmpcfgd.py L41, frrcfgd.py L89 |
| `CONFIG_DB.BGP_GLOBALS` | CONFIG テーブル | BGP_GLOBALS → FRR context | 間接（FRR BGP セッション前提） | frrcfgd.py L81 |
| `CONFIG_DB.DEVICE_METADATA.bgp_asn` | CONFIG テーブル | DEVICE_METADATA → FRR bmp targets 注入の前提 | 間接（FRR j2 テンプレート） | bgpd.main.conf.j2 L94-136 |
