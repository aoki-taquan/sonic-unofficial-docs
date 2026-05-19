# P4RT テーブル — Phase F 副次 DB 書込スキャンノート

対象テーブル: `P4RT`
Consumer: `p4rt.sh` (sonic-buildimage/dockers/docker-sonic-p4rt/)
スキャン範囲: `p4rt.sh` L1–99、`p4rt_vars.j2` L1–5
スキャン日: 2026-05-19

---

## スキャン結果

`p4rt.sh` は `sonic-cfggen -d -t p4rt_vars.j2` で CONFIG_DB を一回読み込むだけであり、
DB への書き戻しは一切行わない。

### DB 副次書込有無

| DB | 書込有無 | 根拠 |
|----|---------|------|
| APPL_DB | なし | `p4rt.sh` に `sonic-db-cli` / `ProducerStateTable` 等の DB 書込コードなし |
| STATE_DB | なし | 同上 |
| COUNTERS_DB | なし | 同上 |
| ASIC_DB / FLEX_COUNTER_DB / LOGLEVEL_DB | なし | SAI 非経由（Linux コンテナ起動スクリプト） |

### ファイルシステムへの副次書き換え（DB 外）

| 対象 | 操作 | 発動条件 | ソース |
|------|------|---------|--------|
| `${P4RT_UNIX_SOCKET}` のディレクトリ | `mkdir -p $(dirname ${UNIX_SOCKET})` で自動作成 | `p4rt_unix_socket` フィールドが設定されているとき | `p4rt.sh:L92–94` |
| `save_forwarding_config_file` パス | p4rt バイナリが起動後に転送設定を書き込む（`--save_forwarding_config_file=<path>` 経由） | `save_forwarding_config_file` フィールドが設定されているとき | `p4rt.sh:L84–87`（バイナリ内実装） |

### p4rt バイナリが管理する APPL_DB 書込（間接）

`p4rt` バイナリ自体は gRPC 経由で受信した P4Runtime リクエストを APPL_DB `P4RT_*` テーブルへ書き込む。
ただしこれは CONFIG_DB `P4RT` テーブルの読込に伴う直接の副次書込ではなく、外部コントローラからの
gRPC リクエストドリブンの書込であり、`p4rt.sh` の副次書込とは区別する。
