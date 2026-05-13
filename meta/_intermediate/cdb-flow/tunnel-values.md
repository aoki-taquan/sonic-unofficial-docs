# TUNNEL — 値依存挙動調査メモ

## ソース

- `sonic-tunnel.yang` (sonic-buildimage@9ea932ec)
- `sonic-swss/cfgmgr/tunnelmgr.cpp`
- `sonic-swss/orchagent/tunneldecaporch.cpp`

## enum / pattern 値

### `tunnel_type`

- `IPINIP` のみ有効（YANG pattern）。それ以外はエラー

### `dscp_mode`

- `uniform`: 外側ヘッダの DSCP を内側パケットにコピー
- `pipe`: 内側ヘッダの DSCP を保持

### `ecn_mode`

- `copy_from_outer`: 外側ヘッダの ECN を内側にコピー
- `standard`: RFC 6040 準拠 ECN 処理

### `encap_ecn_mode`

- `standard` のみ（YANG pattern 制約）

### `ttl_mode`

- `uniform`: 外側 TTL を内側にコピー
- `pipe`: 内側 TTL を保持

## 値依存挙動

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `tunnel_type` | `IPINIP` | tunnelmgrd が APPL_DB へ通知。`tunneldecaporch` が SAI tunnel 作成 |
| `tunnel_type` | `IPINIP` 以外 | tunnelmgrd キャッシュには追加されるが APPL_DB に通知されない |
| `src_ip` | 未設定 (空) | P2MP (ワイルドカード) decap term 作成。全 IPinIP を受け入れる |
| `src_ip` | `PEER_SWITCH` に未登録の IP | YANG leafref 違反で書き込み拒否 |
| `ecn_mode` | 設定後に変更 | SAI create-only 属性のため変更不可。削除→再作成が必要 |
| key (`mux_tunnel`) | `MuxTunnel[0-9]+` 以外 | YANG pattern 違反で書き込み拒否 |
