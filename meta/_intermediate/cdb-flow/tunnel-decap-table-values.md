# TUNNEL_DECAP_TABLE — 値依存挙動調査メモ

## ソース

- `sonic-swss-common/common/schema.h` (テーブル名定数)
- `sonic-swss/orchagent/tunneldecaporch.cpp`

## フィールド値

### `tunnel_type`

- `IPINIP` のみ (`tunneldecaporch` がハードコードチェック)

### `dscp_mode`

- `uniform`: 外側 DSCP を内側にコピー
- `pipe`: 内側 DSCP を保持

### `ecn_mode`

- `copy_from_outer`: 外側 ECN を内側にコピー
- `standard`: RFC 6040 ECN 処理

### `encap_ecn_mode`

- `standard` のみ対応

### `ttl_mode`

- `uniform`: 外側 TTL を内側にコピー
- `pipe`: 内側 TTL を保持

## 値依存挙動

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `tunnel_type` | `IPINIP` | SAI tunnel + tunnel-term オブジェクトを作成 |
| `tunnel_type` | `IPINIP` 以外 | `"Invalid tunnel type"` を LOG_ERROR してスキップ |
| `dscp_mode` | 有効値以外 | `"Invalid dscp mode"` を LOG_ERROR してスキップ |
| `ecn_mode` | `standard` 以外 | `"Only standard encap ecn mode is supported"` を LOG_ERROR して拒否 |
| `ecn_mode` | 作成後に変更 | SAI create-only のため変更スキップ（WARN ログ）。削除→再作成が必要 |
| `src_ip` | 作成後に変更 | `"cannot modify src ip for existing tunnel"` を LOG_ERROR して拒否 |
| `dst_ip` | カンマ区切りリスト | `TUNNEL_DECAP_TERM_TABLE` で個別に decap term を管理 |

## enum なし明示

- `tunnel_type` / `dscp_mode` / `ecn_mode` / `ttl_mode` は YANG 上 string 型（YANG 未定義のため）。実際の制約は `tunneldecaporch.cpp` のコード判定。
