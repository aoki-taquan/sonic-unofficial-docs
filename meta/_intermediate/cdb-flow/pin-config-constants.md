# P4RT テーブル — Phase E ハードコード定数スキャンノート

対象テーブル: `P4RT`
Consumer: `p4rt.sh` (sonic-buildimage/dockers/docker-sonic-p4rt/)
スキャン範囲: `p4rt.sh` L1–99 全行、`p4rt_vars.j2` L1–5 全行
スキャン日: 2026-05-19

---

## 検出したハードコード定数

### 1. 終了コード定数

| 定数名 | 値 | 用途 | ソース |
|--------|----|------|--------|
| `EXIT_P4RT_VARS_FILE_NOT_FOUND` | `1` | `p4rt_vars.j2` テンプレートが不在の場合の終了コード | `p4rt.sh:L3` |

### 2. ファイルシステムパス定数

| 定数名 | 値 | 用途 | ソース |
|--------|----|------|--------|
| `P4RT_VARS_FILE` | `/usr/share/sonic/templates/p4rt_vars.j2` | `sonic-cfggen` に渡す Jinja2 テンプレートパス（`readonly` 宣言）| `p4rt.sh:L4` |
| (リテラル) | `/usr/local/bin/p4rt` | P4Runtime gRPC サーババイナリの絶対パス（`exec` で直接指定）| `p4rt.sh:L99` |

### 3. YANG / スキーマ定数なし

- `P4RT` テーブルには専用 YANG モデルが存在しない。YANG `default` 文による定数は 0 件。
- フィールドデフォルトはすべてバイナリ内部で保持されており、スクリプト側には明示的なデフォルト値定数が存在しない（各フィールドは `// empty` フォールバックで引数なしとなる）。

### 4. jq フィールドアクセスパターン（定数相当）

- `'.server_crt // empty'` / `'.server_key // empty'` 等の jq フィルタ文字列はスクリプト内にリテラルとして埋め込まれているが、これらはフィールド名参照であり値定数ではない。
- バイナリ起動引数名（`--p4rt_grpc_port=`、`--use_insecure_server_credentials` 等）もスクリプト内にハードコードされているが、CONFIG_DB フィールドとの対応を定義するものであり、設定値ではない。

## 総括

`p4rt.sh` におけるハードコード定数は最小限：
1. 終了コード `EXIT_P4RT_VARS_FILE_NOT_FOUND=1`
2. テンプレートパス `P4RT_VARS_FILE=/usr/share/sonic/templates/p4rt_vars.j2`
3. バイナリパス `/usr/local/bin/p4rt`

これらはすべて静的パス/コードであり、CONFIG_DB の `P4RT` テーブル設定値とは独立している。ユーザが変更できるパラメータは存在しない。
