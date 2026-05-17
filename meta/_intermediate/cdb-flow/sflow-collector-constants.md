# SFLOW_COLLECTOR — Phase E ハードコード定数 証跡

ソース: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-sflow.yang`,
`sonic-utilities/config/main.py`, `sonic-swss/cfgmgr/sflowmgr.cpp`

調査日: 2026-05-17

## 抽出定数一覧

### YANG 由来の定数

| 定数名 / 意味 | 値 | 場所 |
|---|---|---|
| `collector_port` YANG デフォルト | `6343` (UDP) | `sonic-sflow.yang` L81: `default 6343;` |
| コレクタ最大数 | `2` | `sonic-sflow.yang` SFLOW_COLLECTOR_LIST: `max-elements 2` |
| `collector_vrf` 許容値 | `"mgmt"` または `"default"` | `sonic-sflow.yang` L91: `pattern "mgmt|default"` |
| `collector_ip` 型 | `inet:ip-address` (IPv4/IPv6) | `sonic-sflow.yang` L73 |
| `collector_port` 型 | `inet:port-number` (0..65535) | `sonic-sflow.yang` L80 |
| コレクタ名最大長 (YANG) | 64 文字 | `sonic-sflow.yang` SFLOW_COLLECTOR_LIST.name: `length 1..64` |

### CLI 由来の定数 (config/main.py)

| 定数名 / 意味 | 値 | 場所 |
|---|---|---|
| コレクタ名最大長 (CLI) | 16 文字 (YANG より厳しい) | `config/main.py:9315`: `if len(name) > 16` |
| `collector_port` CLI デフォルト | `6343` | `config/main.py:9337`: `default=6343` (Click option) |
| `collector_vrf` CLI デフォルト | `"default"` | `config/main.py:9340`: `default='default'` (Click option) |
| コレクタ最大数 (CLI チェック) | `2` | `config/main.py:9354`: `len(collector_tbl) == 2` |

## CLI / YANG 不整合

- コレクタ名最大長: CLI は 16 文字制限 (`config/main.py:9315`)、YANG は 64 文字まで許容 (`sonic-sflow.yang`)。
  CLI バイパス (直接 ConfigDB 書き込み) の場合は 64 文字まで使用可能。
- `collector_port` のデフォルト値 `6343` は YANG / CLI 両方で一致 (IANA sFlow UDP ポート)。

## 備考

- `collector_port` の `6343` は IANA に割り当てられた sFlow UDP ポート番号。
- `collector_vrf` は YANG `must` 制約で `mgmt` 選択時に `MGMT_VRF_CONFIG.vrf_global.mgmtVrfEnabled = 'true'` を強制する。
- 最大 2 コレクタ制限は hsflowd の設計に由来 (実装側での追加サポートなし)。
