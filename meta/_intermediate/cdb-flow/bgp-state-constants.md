# STATE_DB BGP 状態テーブル — Phase E: ハードコード定数調査

## 調査対象ファイル

- `sonic-buildimage/src/sonic-bgpcfgd/bgpmon/bgpmon.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-swss-common/common/schema.h`
- `sonic-snmpagent/src/sonic_ax_impl/mibs/vendor/cisco/bgp4.py`

---

## ハードコード定数一覧

### テーブル名 (schema.h)

| C マクロ名 | 文字列値 | ソース行 |
|-----------|---------|---------|
| `STATE_BGP_PEER_CONFIGURED_TABLE_NAME` | `"BGP_PEER_CONFIGURED_TABLE"` | `schema.h:511` |
| `STATE_BGP_TABLE_NAME` | `"BGP_STATE_TABLE"` | `schema.h:437` |

`NEIGH_STATE_TABLE` は schema.h マクロなし。`bgpmon.py:51,157,179` にリテラルとしてハードコード。

### state フィールド文字列 (FRR 由来 — bgpmon.py がそのまま転写)

| 値 | 意味 | SNMP 整数 |
|----|------|----------|
| `"Idle"` / `"Idle (Admin)"` | セッション停止中 | 1 |
| `"Connect"` | TCP 接続試行中 | 2 |
| `"Active"` | TCP 接続待機中 | 3 |
| `"OpenSent"` | OPEN 送信済み | 4 |
| `"OpenConfirm"` | OPEN 確認待ち | 5 |
| `"Established"` | セッション確立済み | 6 |
| `"Clearing"` | 解除中 (FRR 独自) | — |

bgpmon.py は FRR `show bgp summary json` の `peers[peer]["state"]` をそのまま転写。bgpmon.py 自体にこれらの文字列定義はない。SNMP 側の STATE_CODE マッピングは `bgp4.py` で定義。

### peerType フィールド文字列 (bgpmon.py)

| 値 | 条件 | ソース |
|----|------|--------|
| `"i-BGP"` | `remoteAs == localAs` | `bgpmon.py:163,171` |
| `"e-BGP"` | `remoteAs != localAs` | `bgpmon.py:163,171` |

### 操作種別文字列 (managers_bgp.py — BGPPeerMgrBase.update_state_db)

| 値 | 用途 | 呼び出し元 |
|----|------|-----------|
| `"SET"` | ネイバー追加 / admin state 変更 | `managers_bgp.py:239,353,443` |
| `"DEL"` | ネイバー削除 | `managers_bgp.py:487` |

VRF `"default"` 時の key 分岐ロジック: `managers_bgp.py:280`（文字列リテラル `"default"`）。

### ポーリング・バッチ定数 (bgpmon.py)

| 定数 | 値 | ソース |
|------|----|--------|
| `PIPE_BATCH_MAX_COUNT` | **50** | `bgpmon.py:35` |
| ポーリング間隔 | **15** 秒 | `bgpmon.py:203` |
| FRR 変化なし時 sleep | **1** 秒 | `bgpmon.py:109,115` |

### ハードコードされたパス・コマンド文字列 (bgpmon.py)

| 値 | 用途 | ソース |
|----|------|--------|
| `"/var/log/frr/frr.log"` | FRR ログタイムスタンプ監視 | `bgpmon.py:61` |
| `"show bgp summary json"` | vtysh BGP 状態取得コマンド | `bgpmon.py:80` |

---

## 特記事項

1. **NEIGH_STATE_TABLE に schema.h マクロなし** — `BGP_PEER_CONFIGURED_TABLE` とは異なり、`NEIGH_STATE_TABLE` は `swsscommon` マクロで保護されていない。テーブル名変更時のリファクタリングリスクあり。
2. **state 文字列は FRR バージョン依存** — bgpmon は FRR の `show bgp summary json` 出力をそのまま転写するため、FRR バージョンアップで state 文字列が変わった場合、SNMP MIB の STATE_CODE マッピング (`bgp4.py`) が壊れる可能性がある。
3. **`"Clearing"` は SNMP 非対応** — FRR 独自の過渡状態で、`bgp4.py` の STATE_CODE に定義がなく、SNMP では unknown として扱われる。
4. **ポーリング間隔 15 秒はハードコード** — CONFIG_DB / YANG で調整する手段は存在しない。
