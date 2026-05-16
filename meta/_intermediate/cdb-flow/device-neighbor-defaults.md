# DEVICE_NEIGHBOR Phase A — フィールドごとのコード由来の暗黙デフォルト

## 調査方法

1. フィールド列挙: YANG `sonic-device_neighbor.yang` (buildimage) + `sonic-device-neighbor.yang` (sonic-mgmt-common)
2. エントリ grep 1回: `grep -rln "DEVICE_NEIGHBOR" .cache/sonic-sources/`
3. consumer 全行精読: minigraph.py / lldpmgrd / pfcwd/main.py / show/interfaces/__init__.py / bgpcfgd/managers_bgp.py / ecnconfig

---

## フィールド別 implicit default / コード由来挙動

### `peer_name` (key)

| 検出種類 | 内容 |
|---------|------|
| 書込み順依存 | minigraph.py は key = local port 名（`Ethernet0` 等）で書き込む。peer_name は隣接ホスト名ではなくローカルポート名に相当する（minigraph.py:649 `neighbors[endport]`）|
| silent drop | port_config.ini に存在しないインターフェイス名は `del neighbors[nghbr]` で黙って削除される（minigraph.py:2636）|

### `name` (隣接ホスト名)

| 検出種類 | 内容 |
|---------|------|
| 前提条件依存 | bgpcfgd は `data['name']` が DEVICE_NEIGHBOR_METADATA に存在しない場合 `return False` でピア追加を中断する（managers_bgp.py:221-223）。YANG は leafref 制約なし（YANG-実装 discrepancy）|
| 暗黙 fallback なし | フィールドが欠落していると bgpcfgd テンプレートレンダリングで KeyError → bgpcfgd は peer 追加スキップ（lldpmgrd は name を参照しないため影響なし）|
| dead-field (lldpmgrd) | lldpmgrd の TODO コメントに「DEVICE_NEIGHBOR を subscribe していない」と明記。現行 lldpmgrd は DEVICE_NEIGHBOR を一切読まない（lldpmgrd:12-14）|

### `mgmt_addr` (隣接管理 IP)

| 検出種類 | 内容 |
|---------|------|
| dead-field (主要 consumer) | DEVICE_NEIGHBOR テーブルの `mgmt_addr` を実際に参照するコードパスはコードベース上で確認不可。show interfaces expected では `neighbor_metadata_dict[device]['mgmt_addr']` を参照するが、これは DEVICE_NEIGHBOR_METADATA 側のフィールド|
| YANG default 外 fallback | `mgmt_addr` が存在しない場合でも consumer はエラーを出さない（show/interfaces/__init__.py:342-345 で `if 'mgmt_addr' in ...` ガード付き）|

### `local_port` (leafref → PORT.name)

| 検出種類 | 内容 |
|---------|------|
| YANG leafref 必須制約 | 存在しない PORT.name を指定するとバリデーションで reject（buildimage YANG）|
| YANG-実装 discrepancy | sonic-mgmt-common の YANG では `local_port` が `PORT_LIST.ifname` への leafref になっているが、buildimage YANG では `PORT_LIST.name` への leafref で属性名が異なる|
| pfcwd の外部ポート判定 | `pfcwd start_default` は `DEVICE_NEIGHBOR.keys()` を「外部ポート一覧」として使用。テーブルが空の場合は外部ポートが 0 件となり全ポートが内部扱いになる（pfcwd/main.py:413-416）|
| ecnconfig のポート一覧 | `ecnconfig` は非 multi-ASIC 環境で `DEVICE_NEIGHBOR.keys()` をポート一覧として使用。テーブルが空だと Exception を raise（ecnconfig:282-287）|

### `port` (隣接側ポート名)

| 検出種類 | 内容 |
|---------|------|
| YANG-実装 discrepancy | buildimage YANG: `string(1..255)` で自由文字列。sonic-mgmt-common YANG: `PORT_LIST.ifname` への leafref（隣接側ポートまで leafref 検証する設計だが buildimage では未適用）|
| 暗黙 fallback なし | show interfaces expected で直接 `neighbor_dict[port]['port']` を参照。存在しない場合 KeyError → try/except で "No neighbor information available" メッセージを表示して継続（show/interfaces/__init__.py:346-348）|

### `type` (隣接機器タイプ)

| 検出種類 | 内容 |
|---------|------|
| YANG-実装 discrepancy | buildimage YANG: `string(1..255)` で制約なし。sonic-mgmt-common YANG: `enum { ToRRouter; LeafRouter; }` で enum 制約あり（2値のみ許可）|
| pfcwd consumer の implicit 読み取り | `pfcwd get_server_facing_ports()` は `DEVICE_NEIGHBOR_METADATA['type'].lower() == 'server'` で判定（DEVICE_NEIGHBOR の `type` ではなく METADATA 側を参照）|
| 暗黙 fallback なし | `type` が存在しないエントリを bgpcfgd テンプレートが参照する場合は未定義だが、テンプレート側でガードされる運用が一般的|

---

## 複合必須制約

- minigraph 経由生成では `name` + `port` は必ず両方セットされる（minigraph.py:649 `{'name': ..., 'port': ...}`）
- `mgmt_addr` + `type` + `local_port` は optional フィールドであり、minigraph 由来エントリに存在しない場合がある
- `local_port` は minigraph 経由では key（peer_name）と同値になる（key がローカルポート名のため）

---

## 書込み順依存

- minigraph.py は `neighbors` を `DEVICE_NEIGHBOR` に書く前に port_config.ini と照合してフィルタリングする（2631-2636）
- DEVICE_NEIGHBOR_METADATA の生成は DEVICE_NEIGHBOR の後に同一スクリプト内で実行される（2637-2641）
- multi-ASIC 環境では DEVICE_NEIGHBOR_METADATA のスコープが異なる: non-multi-ASIC は「自ホスト以外の全 device」、multi-ASIC は「DEVICE_NEIGHBOR に登場する device のみ」（2638-2641）

---

## サマリ: 主要 discrepancy / fallback

| # | フィールド | 種類 | 内容 |
|---|-----------|------|------|
| 1 | `name` | dead-field (lldpmgrd) | lldpmgrd は DEVICE_NEIGHBOR 全体を読まない（TODO 状態） |
| 2 | `mgmt_addr` | dead-field | DEVICE_NEIGHBOR の mgmt_addr を参照する consumer がない |
| 3 | `type` | YANG-実装 discrepancy | buildimage=自由文字列 / sonic-mgmt-common=enum(2値) |
| 4 | `port` | YANG-実装 discrepancy | buildimage=自由文字列 / sonic-mgmt-common=PORT leafref |
| 5 | `local_port` | YANG-実装 discrepancy | leafref 先属性名が buildimage=`name` / mgmt-common=`ifname` で相違 |
| 6 | `name` | 前提条件依存 | bgpcfgd は DEVICE_NEIGHBOR_METADATA に name が存在しないとピア追加中断 |
| 7 | `local_port` (テーブル全体) | silent drop+fallback | テーブル空 → pfcwd が外部ポートなしと判定 / ecnconfig は例外 |
| 8 | `peer_name` (key) | silent drop | port_config.ini にないポートは warning 出力後に黙って削除 |

## Evidence

- `sonic-buildimage` `src/sonic-config-engine/minigraph.py:649,2631-2641`
- `sonic-buildimage` `dockers/docker-lldp/lldpmgrd:12-14` (TODO コメント、DEVICE_NEIGHBOR 非購読)
- `sonic-utilities` `pfcwd/main.py:98-108,413-416`
- `sonic-utilities` `show/interfaces/__init__.py:316-360`
- `sonic-utilities` `scripts/ecnconfig:282-287`
- `sonic-buildimage` `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:219-224`
- `sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-device_neighbor.yang`
- `sonic-mgmt-common` `cvl/testdata/schema/sonic-device-neighbor.yang`
