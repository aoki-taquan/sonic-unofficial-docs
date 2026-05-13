# peer-switch 例外条件エビデンス

## 調査ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-peer-switch.yang`
- `sonic-linkmgrd` (DualToR mux manager)

## 例外条件まとめ

### スキーマ検証 (YANG)
- `PEER_SWITCH_LIST` は `max-elements 1`。2 件以上 SET を試みると YANG validate で reject。
- `address_ipv4` は `inet:ipv4-address` 型。フォーマット不正は reject。
- `peer_switch` (key) は `stypes:hostname` 型 (最大 63 文字、英数字とハイフン)。

### consumer 例外動作
- `linkmgrd` はこのテーブルを起動時に 1 回読み込み; 実行中の動的変更は反映されない可能性がある (再起動要)。
- `address_ipv4` 未設定の場合、linkmgrd はピアへの到達確認ができず MUX 切り替え不可。
- エントリ 0 件の場合、DualToR 機能が無効扱いになる (linkmgrd の初期化ログで警告)。
