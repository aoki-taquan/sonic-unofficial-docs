# STATE_DB BGP 関連テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/state-bgp.md` の Phase C (暗黙参照) ブロック裏付け資料。

対象テーブル: `BGP_STATE_TABLE` / `BGP_PEER_CONFIGURED_TABLE` (STATE_DB), `BGP_NEIGHBOR_TABLE` / `BGP_RIB_IN_TABLE` / `BGP_RIB_OUT_TABLE` (BMP_STATE_DB)

## スキャン手順

```bash
# bgp_eoiu_marker.py が WarmStart に依存する部分を確認
grep -n "WarmStart\|warm_restart\|isWarmStart" \
    .cache/sonic-sources/sonic-swss/fpmsyncd/bgp_eoiu_marker.py

# fpmsyncd が BGP_STATE_TABLE を読む部分
grep -n "eoiu\|bgpStateTable\|DEVICE_METADATA" \
    .cache/sonic-sources/sonic-swss/fpmsyncd/fpmsyncd.cpp

# bgpcfgd が BGP_PEER_CONFIGURED_TABLE を書く前提テーブルを確認
grep -n "deps\|CONFIG_DB.*CFG_" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py

# BGPPeerMgrBase インスタンスが監視するテーブル
grep -n "BGPPeerMgrBase" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py

# bmpcfgd の CONFIG_DB 購読
grep -n "CONFIG_DB\|BMP_TABLE\|subscribe" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py
```

## 検出された暗黙参照

### 1. BGP_STATE_TABLE — 書込み前提テーブル

`bgp_eoiu_marker.py` が `BGP_STATE_TABLE` を書き込む前提として以下を参照する。

| テーブル / コンポーネント | 参照方向 | 条件 | evidence |
|--------------------------|---------|------|---------|
| `WARM_RESTART` (CONFIG_DB) | WarmStart::checkWarmStart() 経由で読み出し | `isWarmStart()` が false の場合、`bgp_eoiu_marker` サービス全体がスキップされ `BGP_STATE_TABLE` への書き込みは発生しない | bgp_eoiu_marker.py L191-197 |
| STATE_DB `BGP_STATE_TABLE` 自身 | クリア操作の対象（自己参照） | Warm Restart 開始時に `clean_bgp_eoiu_marker()` で既存エントリを削除してから再書込み | bgp_eoiu_marker.py L188, L91-96 |
| FRR bgpd (vtysh `show bgp neighbors json`) | BMP セッション外の EOR 確認 | 全ネイバーの EOR 到達確認に使用。bgpd が応答しない間は `wait_for_bgp_eoiu()` が待機 | bgp_eoiu_marker.py L141-166 |

`fpmsyncd` が `BGP_STATE_TABLE` を読む際の前提:

| テーブル / コンポーネント | 参照方向 | evidence |
|--------------------------|---------|---------|
| `DEVICE_METADATA` (CONFIG_DB, `CFG_DEVICE_METADATA_TABLE_NAME`) | `fpmsyncd` が `SubscriberStateTable` として購読。`routing_mode` / `frr_mgmt_framework_config` 等を参照 | fpmsyncd.cpp L81-83 |
| `WARM_RESTART` (CONFIG_DB, `CFG_WARM_RESTART_TABLE_NAME`) | `getWarmStartHelper().checkAndStart()` 経由でウォームリスタートタイマーを取得 | fpmsyncd.cpp L153-164 |

### 2. BGP_PEER_CONFIGURED_TABLE — 書込み前提テーブル

`bgpcfgd`（`BGPPeerMgrBase`）が `BGP_PEER_CONFIGURED_TABLE` を書き込む前提として以下を参照する。

#### 購読テーブル（キー転写元）

`main.py` L87-92 で `BGPPeerMgrBase` インスタンスが CONFIG_DB の以下のテーブルを購読し、SET/DEL イベントを受けて `BGP_PEER_CONFIGURED_TABLE` へ転写する。

| CONFIG_DB テーブル | peer_type | evidence |
|---|---|---|
| `BGP_NEIGHBOR` (`CFG_BGP_NEIGHBOR_TABLE_NAME`) | `"general"` | main.py:87 |
| `BGP_INTERNAL_NEIGHBOR` (`CFG_BGP_INTERNAL_NEIGHBOR_TABLE_NAME`) | `"internal"` | main.py:88 |
| `BGP_MONITORS` | `"monitors"` | main.py:89 |
| `BGP_PEER_RANGE` | `"dynamic"` | main.py:90 |
| `BGP_VOQ_CHASSIS_NEIGHBOR` | `"voq_chassis"` | main.py:91 |
| `BGP_SENTINELS` | `"sentinels"` | main.py:92 |

#### 前提依存テーブル（`deps` リスト、未到着時はピア追加処理がブロック）

| CONFIG_DB テーブル | キー / フィールド | 用途 | evidence |
|---|---|---|---|
| `DEVICE_METADATA` | `localhost/bgp_asn` | `router bgp <ASN>` コマンド生成 | managers_bgp.py:119, 192 |
| `DEVICE_METADATA` | `localhost/type` | デバイスロール判定 | managers_bgp.py:120 |
| `LOOPBACK_INTERFACE` | `Loopback0` | ルータ ID の IPv4 アドレス取得 | managers_bgp.py:121, 186 |
| `BGP_DEVICE_GLOBAL` | `tsa_enabled` | TSA ルートマップ適用判定 | managers_bgp.py:122 |
| `BGP_DEVICE_GLOBAL` | `idf_isolation_state` | IDF isolation ルートマップ判定 | managers_bgp.py:123 |

条件付き追加依存:

| 条件 | テーブル | evidence |
|---|---|---|
| `use_neighbors_meta = true` のとき | `DEVICE_NEIGHBOR_METADATA` | managers_bgp.py:140 |
| `use_deployment_id = true` のとき | `DEVICE_METADATA.localhost/deployment_id` | managers_bgp.py:143 |
| `peer_type == "internal"` のとき | `LOOPBACK_INTERFACE.Loopback4096` | managers_bgp.py:146 |

FRR bgpd との非同期協調:

`BGP_PEER_CONFIGURED_TABLE` への書き込みは `cfg_mgr.push()` (FRR への `vtysh -f` 設定投入) が成功した後にのみ実行される (managers_bgp.py:239, 353, 444)。FRR が応答不能の場合、STATE_DB への反映も遅延・欠落する。

### 3. BGP_NEIGHBOR_TABLE / BGP_RIB_IN_TABLE / BGP_RIB_OUT_TABLE — BMP テーブルの前提

`bmpcfgd` / `openbmpd` が BMP_STATE_DB テーブルを書き込む前提として以下を参照する。

| テーブル / コンポーネント | 参照方向 | 条件 | evidence |
|--------------------------|---------|------|---------|
| `BMP` (CONFIG_DB, `BMP_TABLE`) | `bmpcfgd` が `subscribe()` で購読。`bgp_neighbor_table` / `bgp_rib_in_table` / `bgp_rib_out_table` フィールドが `"true"` のときのみ対応テーブルを収集する | 常時。`"false"` の場合は `delete_all_by_pattern` でテーブルを全削除する | bmpcfgd.py:82-86 |
| FRR bgpd BMP ソケット | `openbmpd` が bgpd の BMP ポートに TCP 接続。BGP OPEN メッセージ受信後に `BGP_NEIGHBOR_TABLE` エントリを生成する | bgpd との接続が確立しない間はエントリが生成されない | SONiC/doc/bmp/bmp.md L141-166 |
| FRR bgpd UPDATE メッセージ | `openbmpd` が BGP UPDATE を解析して `BGP_RIB_IN_TABLE` / `BGP_RIB_OUT_TABLE` を書く | BGP OPEN 完了後に発生する UPDATE のみ対象 | SONiC/doc/bmp/bmp.md L286-306 |

## まとめ — Phase C 記載対象

| カテゴリ | テーブル / コンポーネント |
|---|---|
| BGP_STATE_TABLE の前提 | `WARM_RESTART` (CONFIG_DB), FRR bgpd EOR 確認, `DEVICE_METADATA` (fpmsyncd 側) |
| BGP_PEER_CONFIGURED_TABLE の転写元 | `BGP_NEIGHBOR` / `BGP_INTERNAL_NEIGHBOR` / `BGP_MONITORS` / `BGP_PEER_RANGE` / `BGP_VOQ_CHASSIS_NEIGHBOR` / `BGP_SENTINELS` |
| BGP_PEER_CONFIGURED_TABLE の前提依存 | `DEVICE_METADATA` / `LOOPBACK_INTERFACE` / `BGP_DEVICE_GLOBAL` |
| BMP テーブルの前提 | `BMP` (CONFIG_DB), FRR bgpd BMP ソケット |
