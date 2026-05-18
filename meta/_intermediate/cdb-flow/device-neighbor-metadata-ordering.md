# DEVICE_NEIGHBOR_METADATA — Phase B 書込み順依存スキャンノート

対象ページ: `docs/reference/config-db/device-neighbor-metadata.md`
対象テーブル: `CONFIG_DB`
  - `DEVICE_NEIGHBOR_METADATA`
Producer: `sonic-cfggen` / minigraph パーサ (`sonic-buildimage/src/sonic-config-engine/minigraph.py`)
Consumer: `bgpcfgd` (`managers_bgp.py`)、`pfcwd` (`pfcwd/main.py`)
スキャン範囲: `minigraph.py:2639-2641`（書込みパス）、`managers_bgp.py:128-140,200-224`（依存宣言・set_handler）、`pfcwd/main.py:97-108`（参照パス）

---

## 検出した順序依存・タイミング依存

### 1. bgpcfgd の依存テーブル登録 — DEVICE_NEIGHBOR_METADATA 先行必須（条件付き）

- `BGPPeerMgrBase.__init__()` (`managers_bgp.py:128-140`) は `check_neig_meta` フラグ（`constants.bgp.use_neighbors_meta`）が真の場合のみ `CFG_DEVICE_NEIGHBOR_METADATA_TABLE_NAME` を `deps` に追加する。
- bgpcfgd の directory メカニズムはこの deps 宣言を元に「DEVICE_NEIGHBOR_METADATA テーブルが directory に到着するまで BGP ピア set_handler を実行しない」制御を行う。
- **順序依存（条件付き強制）**: `constants.bgp.use_neighbors_meta == True` の環境では、DEVICE_NEIGHBOR_METADATA がロードされるまで BGP ピア設定（`BGP_NEIGHBOR` / `BGP_PEER_RANGE` テーブル）の適用が**全件ブロック**される。minigraph 書込みが完了する前に bgpcfgd が起動している場合、BGP セッションは DEVICE_NEIGHBOR_METADATA 到着まで確立されない。
- evidence: `managers_bgp.py:128-131`, `managers_bgp.py:138-140`

### 2. bgpcfgd set_handler — DEVICE_NEIGHBOR_METADATA 内の name 不在で延期

- `BGPPeerMgrBase.set_handler()` (`managers_bgp.py:218-224`) は `check_neig_meta` が真かつ `data['name']` が `neigmeta` に存在しない場合に `log_info(...)` を出力して `return False`（再試行待ち）を返す。
- directory メカニズムが後でテーブルを再処理するため、DEVICE_NEIGHBOR_METADATA への該当エントリ到着後に自動再試行される。
- **順序依存**: BGP ピアエントリが先に CONFIG_DB に書き込まれても、対応する DEVICE_NEIGHBOR_METADATA エントリが存在しない限り BGP セッション設定は適用されない。具体的には minigraph 書込みの完了順序（DEVICE_NEIGHBOR_METADATA → BGP_NEIGHBOR の順序保証）が実運用上の前提となる。
- evidence: `managers_bgp.py:218-224`

### 3. pfcwd — DEVICE_NEIGHBOR ロード後に DEVICE_NEIGHBOR_METADATA を参照（直列依存）

- `pfcwd.get_server_facing_ports()` (`pfcwd/main.py:97-108`) は `DEVICE_NEIGHBOR` テーブルを取得し、各エントリの `name` フィールドをキーとして `DEVICE_NEIGHBOR_METADATA` を参照する。
- DEVICE_NEIGHBOR は取得済みだが DEVICE_NEIGHBOR_METADATA に対応エントリがない場合、`neighbor.get('type', None)` ないし直接参照により `type` 値が None となり、サーバー向けポートとして列挙されない（`'server'` 判定に失敗）。VLAN_MEMBER フォールバックに移行する。
- **順序依存**: pfcwd 起動時点で DEVICE_NEIGHBOR と DEVICE_NEIGHBOR_METADATA が**両方とも完全な状態**で CONFIG_DB に存在することが前提。minigraph は両テーブルを同一 `sonic-cfggen -m` 実行内で生成するため通常は同時到着するが、テーブル単位の書込み順は CONFIG_DB の `hset` 操作順に依存する。
- evidence: `pfcwd/main.py:97-108`

### 4. single-ASIC vs multi-ASIC — 書込み内容の分岐（non-ordering だが前提条件）

- `minigraph.py:2639-2641` の分岐により、DEVICE_NEIGHBOR_METADATA に含まれるエントリの集合が環境によって異なる。
  - single-ASIC: 自ホスト以外の全デバイスを収録
  - multi-ASIC: DEVICE_NEIGHBOR に出現するデバイスのみを収録（間接隣接デバイスは欠落）
- **順序依存なし**（書込み内容の差異）だが、consumer が「全デバイスのメタを参照できる」と仮定している場合に multi-ASIC 環境で想定外の欠落が生じる。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | DEVICE_NEIGHBOR_METADATA ロード → BGP ピア set_handler 実行許可（条件付き） | **強制先行**（`use_neighbors_meta=True` 時） | directory メカニズムが到着後に自動再試行 |
| 2 | DEVICE_NEIGHBOR_METADATA エントリ存在 → 個別 BGP ピア設定適用 | **強制先行** | `return False` で再キュー、エントリ到着後に再処理 |
| 3 | DEVICE_NEIGHBOR ロード → DEVICE_NEIGHBOR_METADATA 参照（pfcwd） | 実質的直列（同一 sonic-cfggen 実行内） | 欠落時は VLAN_MEMBER フォールバック |
| 4 | single/multi-ASIC 環境差異 → 収録エントリ集合の違い | 環境依存（書込み前提条件） | multi-ASIC では間接隣接デバイスのメタが欠落する前提で consumer を設計 |

---

## ページ反映方針

- `<!-- ordering -->` ブロックを「購読者」セクションの直前に挿入する。
- 依存 #1（bgpcfgd 全件ブロック）と #2（個別エントリ不在延期）を主軸に記述。
- 依存 #3（pfcwd）はサブ節で補足。
- 既存の `<!-- defaults -->` / `<!-- cdb-exceptions -->` / `<!-- runtime-trace -->` ブロックは触らない。
