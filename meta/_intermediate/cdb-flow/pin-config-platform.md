# P4RT — プラットフォーム差調査

Task F Phase H: `P4RT` テーブル適用時のプラットフォーム/構成差を `p4rt.sh` および `p4rt_vars.j2`（sonic-buildimage `9ea932ec`）から精読した結果。

## 結論

**プラットフォーム差なし**。`P4RT` テーブルは `p4rt.sh` スクリプトが起動時に一回だけ読み込む host-only 設定処理であり、ASIC 種別・multi-asic / chassis 構成・ハードウェアベンダーに依存しない。

## 根拠

### 1. p4rt.sh にプラットフォーム条件分岐なし

`p4rt.sh`（L1–99）を全行精読した結果、以下のキーワードはゼロヒット:

- `hwsku`, `asic`, `platform`, `multi_npu`, `is_multi`, `chassis`, `linecard`, `voq`, `vendor`, `broadcom`, `mellanox`, `nvidia`

スクリプト全体で参照する CONFIG_DB テーブルは `P4RT` と `DEVICE_METADATA["x509"]`（TLS fallback）のみ。DEVICE_METADATA からはプラットフォーム識別フィールドを読まない。

### 2. p4rt_vars.j2 もプラットフォーム参照なし

`p4rt_vars.j2`（L1–5）が参照するのは:

- `P4RT["certs"]` / `P4RT["p4rt_app"]`
- `DEVICE_METADATA["x509"]`（TLS fallback 用）

`DEVICE_METADATA["type"]` / `DEVICE_METADATA["hwsku"]` / `DEVICE_METADATA["platform"]` は一切参照しない。

### 3. ASIC / SAI 非経由

`p4rt.sh` は `exec /usr/local/bin/p4rt ${P4RT_ARGS}` で P4Runtime gRPC サーバを起動する。この処理は:

- SAI API を直接呼ばない（SAI は P4 orch が APPL_DB 経由で間接利用する）
- ASIC capability クエリなし
- SDK / vendor driver 参照なし

CONFIG_DB `P4RT` テーブルの読み込みとバイナリ起動引数変換は、完全に host namespace の Linux プロセス管理レイヤで完結する。

### 4. multi-asic / VOQ chassis 構成での扱い

P4RT 機能（PINS）は現時点で multi-asic SONiC の単一 ASIC 向けを想定した実装であり、`docker-sonic-p4rt` は host namespace で 1 コンテナのみ起動する。`p4rt.sh` は `SONIC_ASIC_ID` / `SONIC_ASIC_COUNT` 等の multi-asic 環境変数を参照しない。複数 ASIC 構成での PINS 対応は現行 HLD（`p4rt_app_hld.md`）にも記述がなく、`p4rt.sh` の実装も単一コンテナ単一バイナリ起動のみを実装している。

### 5. supervisord.conf での確認

`supervisord.conf` の `[program:p4rt]` セクションは `command=/usr/bin/p4rt.sh` を固定しており、プラットフォーム依存の起動条件分岐なし。`start.sh` も `/var/sonic/config_status` の初期化のみで P4RT 特有の処理なし。

## まとめ

P4RT テーブルの読み込み・処理は「CONFIG_DB スナップショット → バイナリ引数変換 → gRPC サーバ起動」という純粋な host OS レイヤの処理。SAI / ASIC ベンダー / multi-asic 分岐は一切存在しない。T0 / T1 / T2 トポロジや ASIC ベンダーに関わらず同一動作をする。
