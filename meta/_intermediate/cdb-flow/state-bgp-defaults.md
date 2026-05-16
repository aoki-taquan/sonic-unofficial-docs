# Phase A: STATE_DB BGP 関連テーブル — フィールドのコード由来デフォルト調査

## 対象テーブル

STATE_DB には BGP 関連として以下 5 テーブルが定義されている。

| 定数名 | テーブル名 | DB |
|-------|-----------|-----|
| `STATE_BGP_TABLE_NAME` | `BGP_STATE_TABLE` | STATE_DB |
| `STATE_BGP_SESSION_TRACKER_TABLE_NAME` | `BGP_SESSION_TRACKER_TABLE` | STATE_DB |
| `STATE_BGP_PEER_CONFIGURED_TABLE_NAME` | `BGP_PEER_CONFIGURED_TABLE` | STATE_DB |
| `BMP_STATE_BGP_NEIGHBOR_TABLE` | `BGP_NEIGHBOR_TABLE` | BMP_STATE_DB |
| `BMP_STATE_BGP_RIB_IN_TABLE` | `BGP_RIB_IN_TABLE` | BMP_STATE_DB |
| `BMP_STATE_BGP_RIB_OUT_TABLE` | `BGP_RIB_OUT_TABLE` | BMP_STATE_DB |

ソース: `sonic-swss-common/common/schema.h` L437, L502, L511, L557-559

---

## 1. BGP_STATE_TABLE (STATE_DB)

### キー構造

```
BGP_STATE_TABLE|{family}|eoiu
```
- `family`: `"IPv4"` / `"IPv6"`
- サブキー: 常に `eoiu` 固定

ソース: `sonic-swss/doc/swss-schema.md` L1159, `fpmsyncd/bgp_eoiu_marker.py` L84

### フィールド

| フィールド | 型 | デフォルト/初期値 | コード由来 |
|-----------|----|-----------------|-----------|
| `state` | enum string | `"unknown"` | `bgp_eoiu_marker.py` L80, L200: `set_bgp_eoiu_marker("IPv4", "unknown")` で初期化。値域: `"unknown"` / `"reached"` / `"consumed"` |
| `timestamp` | string | (書き込み時刻) | `bgp_eoiu_marker.py` L86-87: `strftime("%Y-%m-%d %H:%M:%S", gmtime())` で生成。形式: `"YYYY-MM-DD HH:MM:SS"` |

### `state` の遷移

| 値 | セット元 | タイミング |
|----|---------|----------|
| `"unknown"` | `bgp_eoiu_marker.py` | warm restart 開始直後 (clean 後に再セット) |
| `"reached"` | `bgp_eoiu_marker.py` | 全 BGP ピアの EOR 受信完了後 |
| `"consumed"` | `fpmsyncd.cpp` | fpmsyncd が reconciliation 用途で参照後に更新 (schema.md 記載、ただし fpmsyncd.cpp 内では直接 write は確認できず read のみ) |

ソース:
- `sonic-swss/fpmsyncd/bgp_eoiu_marker.py` L80-88, L188-208
- `sonic-swss/fpmsyncd/fpmsyncd.cpp` L54-72, L91 (`Table bgpStateTable(&stateDb, STATE_BGP_TABLE_NAME)`)
- `sonic-swss/doc/swss-schema.md` L1155-1180

### 定数

| 定数 | 値 | ファイル |
|-----|-----|---------|
| `DEFAULT_EOIU_HOLD_INTERVAL` | `3` 秒 | `fpmsyncd.cpp` L51 |
| `DEFAULT_ROUTING_RESTART_INTERVAL` | `120` 秒 | `fpmsyncd.cpp` L46 |

---

## 2. BGP_PEER_CONFIGURED_TABLE (STATE_DB)

### キー構造

```
BGP_PEER_CONFIGURED_TABLE|{vrf}|{peer_name}
```
- default VRF の場合: `BGP_PEER_CONFIGURED_TABLE|{peer_name}` (vrf を省略)
- ソース: `bgpcfgd/managers_bgp.py` L280-283

### フィールド

dynamic peer の場合:
| フィールド | 型 | 必須/任意 | 説明 |
|-----------|----|---------|------|
| `ip_range` | list/string | 必須 | 動的ピアの listen range IP リスト |
| `name` | string | 必須 | ピア名 |
| `peer_asn` | string | 任意 | ピアの ASN |
| `src_address` | string | 任意 | セッション送信元 IP |

ソース: `SONiC/doc/BGP/Bgpcfgd-dyn-peer-modification-support.md` L82-90, `managers_bgp.py` L287-290

**デフォルト値**: なし。CONFIG_DB `BGP_PEER_RANGE` / `BGP_NEIGHBOR` の値をそのまま転記する (`managers_bgp.py` L289: `state_peer_table.set(key, list(sorted(data.items())))`)

書き込み元: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- SET: L289 `state_peer_table.set(key, list(sorted(data.items())))`
- DEL: L294 `state_peer_table.delete(key)`

---

## 3. BGP_SESSION_TRACKER_TABLE (STATE_DB)

schema.h で定義のみ (`L502`)。コード中での実際の書き込みコードは `.cache/sonic-sources` 内では確認不可 (shallow clone 対象外か未実装の可能性)。HLD も見当たらない。

---

## 4. BGP_NEIGHBOR_TABLE (BMP_STATE_DB)

### キー構造

```
BGP_NEIGHBOR_TABLE|{peer_ip}
```

### フィールド

| フィールド | 型 | サンプル値 | 説明 |
|-----------|----|----------|------|
| `peer_addr` | IP string | `"10.0.0.23"` | ピア IP アドレス |
| `peer_asn` | string | `"65200"` | ピア AS 番号 |
| `peer_rd` | string | `"0:0"` | ピア Route Distinguisher |
| `remote_port` | string | `"179"` | ピアのポート番号 (BGP = 179) |
| `local_ip` | IP string | `"10.0.0.22"` | ローカル IP アドレス |
| `local_asn` | string | `"65100"` | ローカル AS 番号 |
| `local_port` | string | `"40760"` | ローカルポート番号 |
| `sent_cap` | string | `"MPBGP (1) : ..."` | 送信 BGP capabilities |
| `recv_cap` | string | `"MPBGP (1) : ..."` | 受信 BGP capabilities |

デフォルト値: なし。FRR/BMP daemon が BGP OPEN メッセージから直接書き込む。

ソース:
- `SONiC/doc/bmp/bmp.md` L141-166 (redis-cli HGETALL 実例)
- `sonic-utilities/show/main.py` L2550-2573 (CLI 参照フィールド)
- `sonic-utilities/tests/show_bmp_test.py` L26-41 (テストフィクスチャ)

---

## 5. BGP_RIB_IN_TABLE / BGP_RIB_OUT_TABLE (BMP_STATE_DB)

### キー構造

```
BGP_RIB_IN_TABLE|{nlri}|{peer_ip}
BGP_RIB_OUT_TABLE|{nlri}|{peer_ip}
```
- `nlri`: ネットワークプレフィックス (例: `"192.172.80.128/25"`)
- `peer_ip`: BGP ピア IP アドレス

### フィールド (RIB_IN / RIB_OUT 共通)

| フィールド | 型 | サンプル値 | デフォルト |
|-----------|----|----------|----------|
| `origin` | string | `"igp"` | FRR から転記 |
| `as_path` | string | `"65100 64600 65534"` | FRR から転記 |
| `as_path_count` | string | `"3"` | FRR から転記 |
| `origin_as` | string | `"65534"` | FRR から転記 |
| `next_hop` | IP string | `""` または IP | FRR から転記、未設定時は空文字 |
| `local_pref` | string | `"0"` | FRR から転記、デフォルト `"0"` |
| `community_list` | string | `""` | FRR から転記、未設定時は空文字 |
| `ext_community_list` | string | `""` | FRR から転記、未設定時は空文字 |
| `large_community_list` | string | `""` | FRR から転記、未設定時は空文字 |
| `originator_id` | string | `""` | FRR から転記、未設定時は空文字 |

ソース:
- `SONiC/doc/bmp/bmp.md` L167-209 (redis-cli HGETALL 実例)
- `sonic-utilities/tests/show_bmp_test.py` L70-130 (テストフィクスチャ)
- `sonic-utilities/show/main.py` L2583-2648 (CLI 参照フィールド)

---

## 調査まとめ

| テーブル | DB | デフォルト値 | 書き込み元プロセス |
|---------|-----|------------|----------------|
| `BGP_STATE_TABLE` | STATE_DB | `state="unknown"` / `timestamp=現在時刻` | `bgp` docker 内 `bgp_eoiu_marker` (warm restart 時のみ) |
| `BGP_PEER_CONFIGURED_TABLE` | STATE_DB | なし (CONFIG_DB から転記) | `bgpcfgd` (managers_bgp.py) |
| `BGP_SESSION_TRACKER_TABLE` | STATE_DB | 不明 | 不明 (実装確認不可) |
| `BGP_NEIGHBOR_TABLE` | BMP_STATE_DB | なし (FRR/BMP から直接) | `bmp` docker (openbmpd) |
| `BGP_RIB_IN_TABLE` | BMP_STATE_DB | `local_pref="0"`, 各リスト=`""` | `bmp` docker (openbmpd) |
| `BGP_RIB_OUT_TABLE` | BMP_STATE_DB | `local_pref="0"`, 各リスト=`""` | `bmp` docker (openbmpd) |
