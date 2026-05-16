# BMP — プラットフォーム差調査

Task F Phase H: `BMP` テーブル適用時のプラットフォーム/構成差を `sonic-bmpcfgd` (`bmpcfgd.py`)、`sonic-buildimage` の BMP 関連アセット、および `frrcfgd.py` から精読した結果。

## 結論

**プラットフォーム差なし**。BMP 機能は `INCLUDE_SYSTEM_BMP=y`（`rules/config` デフォルト）でビルドされた `docker-sonic-bmp` コンテナとして全プラットフォームに一様に提供される。プラットフォーム固有の分岐は `bmpcfgd.py`・ビルドルール・コンテナ設定のいずれにも存在しない。

## 根拠

### 1. `INCLUDE_SYSTEM_BMP` はグローバルデフォルト `y` のみ

`rules/config` L162–163:
```makefile
# INCLUDE_SYSTEM_BMP - build docker-sonic-bmp for system bmp support
INCLUDE_SYSTEM_BMP = y
```

`platform/*/` 以下のどの `.mk` ファイルもこのフラグを上書きしない（`find platform -name '*.mk' | xargs grep -l INCLUDE_SYSTEM_BMP` が 0 ヒット）。したがってプラットフォーム間でビルド差はなく、全ターゲットで `docker-sonic-bmp` が生成・インストールされる。

### 2. `bmpcfgd.py` に ASIC / プラットフォーム分岐なし

`bmpcfgd.py`（全 98 行）には:
- `device_info` / `sonic_platform` / `is_multi_npu()` / `asic_id` / `namespace` への参照が一切ない
- ベンダー固有コードパスなし
- CONFIG_DB を 1 つ（host namespace）購読するだけ

### 3. `frrcfgd.py` に BMP 関連コードなし

`sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` 全体に "bmp" / "BMP" の文字列が 0 ヒット。BMP 設定は `frrcfgd` を経由せず、`bmpcfgd` が直接 `supervisorctl` で `openbmpd` を制御する。

### 4. `docker-sonic-bmp` コンテナはプラットフォーム非依存

`dockers/docker-sonic-bmp/Dockerfile.j2` のベースは `docker-config-engine-bookworm` のみ。ASIC SDK や SAI ライブラリへの依存はなく、`supervisord.conf` も platform 条件分岐なしでフラット定義。

### 5. multi-asic / VOQ chassis 構成での扱い

`bmpcfgd` は host CONFIG_DB の `BMP` テーブルを購読。`asicN` namespace への CONFIG_DB 接続や iteration は実装されていない。multi-asic 環境でも BMP は host-level BGP プロセス（FRR `bgpd`）が稼働する単一コンテナ向けのサイドカーとして動作し、line card ごとの分割制御機構はない。

### 6. SAI 非経由・ASIC 非依存

BMP は TCP で BMP collector に BGP テーブルダンプを送るアプリケーション層プロトコル。SAI を経由せず、ASIC ベンダーの SDK に依存しない。Broadcom / Mellanox / Barefoot / Centec 等のいずれのプラットフォームでも動作は同一。

## まとめ

BMP 経路は ASIC SDK・SAI・multi-asic namespace に依存しない host-level なデーモン制御処理。`INCLUDE_SYSTEM_BMP=y` がデフォルトで全プラットフォームに適用され、プラットフォーム固有の上書きは存在しない。よって `<!-- platform -->` ブロックは「プラットフォーム差なし・根拠付き」として記載する。
