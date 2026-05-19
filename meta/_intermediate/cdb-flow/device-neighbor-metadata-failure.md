# device-neighbor-metadata 失敗挙動調査メモ (Phase D)

## 調査対象ソース

- `sonic-utilities/pfcwd/main.py:97-108` — `get_server_facing_ports()`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:128-140,219-224` — `BGPPeerMgrBase.__init__`, `add_peer`
- `sonic-utilities/scripts/db_migrator.py:765-790` — `update_edgezone_aggregator_config()`

## 主要失敗パス

### bgpcfgd directory ブロック (失敗 #1)
`use_neighbors_meta == True` のとき CFG_DEVICE_NEIGHBOR_METADATA_TABLE_NAME を deps に追加。
テーブル未到達時は SET ハンドラがブロックされる。directory 到着後に自動再処理。

### bgpcfgd 個別エントリ不在 (失敗 #2)
`data['name'] not in neigmeta` で `return False`。`log_info` 出力のみ。
エントリ到着後に再処理（directory メカニズム経由）。

### pfcwd KeyError (失敗 #3, #4)
`candidates[port]['name']` または `neighbor['type']` が欠落すると `KeyError`。
try-catch なし → pfcwd 起動シーケンス中断。プロセス再起動後に再試行。

### pfcwd サーバーポート 0 件フォールバック (失敗 #5)
`type.lower() == 'server'` に合致なし → `VLAN_MEMBER` フォールバック。サイレント継続。

### db_migrator 早期 return (失敗 #6)
EdgeZoneAggregator 型なし → 早期 return。CABLE_LENGTH 変更なし。冪等。

### qos_config.j2 大文字小文字不一致 (失敗 #7)
`'ToRRouter' in neighbor_info.type` は大文字小文字区別あり。不一致時はアップリンク/ダウンリンク
分類が行われずサイレントに正しくない QoS 設定が生成される。
