---
title: ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離）
area: architecture
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/sonic-build-system/build_system_improvements.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli: []
  yang: []
---

!!! warning "裏取りステータス: HLD-only / 古い HLD"
    HLD は Debian Stretch 時代のスナップショット（Python 3.6、docker 18.09 への upgrade を提案）。`SONIC_USE_DOCKER_BUILDKIT` フラグ、`dockers/dockerfile-macros.j2`、`SAIREDIS_DPKG_TARGET=binary-syncd` の取り込み状況は要裏取り。

# ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離）

## 概要

SONiC ビルドは大別すると 2 段階で構成される[^1]:

1. Debian / Python パッケージ コンパイル — 比較的速い
2. **Docker イメージビルド** — 遅い（特に複数ユーザ並列時）

本 HLD は主に第 2 段階に焦点を当て、4 つの最適化を提案する[^1]:

1. Dockerfile の **`COPY` / `RUN` をマージしてレイヤ数を削減**
2. Docker 18.09 + **BuildKit** の有効化
3. `swss` / `swss-common` / `sairedis` の **`dh --parallel`** 並列ビルド
4. `sairedis` の RPC / 非 RPC 分離

## 動作仕様

### 最適化 1: Dockerfile のレイヤ数削減

各 `COPY` / `RUN` 行は新しい Docker レイヤを生成する。`--no-cache --squash` で最終出力を 1 レイヤに潰しているため、**ビルド中の細かいレイヤ分割は無意味なコスト**[^1]。

**Before**: 各 deb パッケージごとに 1 行ずつ `COPY` / `RUN`（SNMP docker で 52 ステップ）

```Dockerfile
COPY debs/libnl-3-200_3.2.27-2_amd64.deb /debs/
COPY debs/libsnmp-base_5.7.3+dfsg-1.5_all.deb /debs/
...
RUN dpkg_apt() { ... }; dpkg_apt /debs/libnl-3-200_3.2.27-2_amd64.deb
...
```

**After**: Jinja で 1 つの `COPY` 命令に展開（20 ステップ）

```Dockerfile
COPY debs/libnl-3-200_3.2.27-2_amd64.deb \
     debs/libsnmp-base_5.7.3+dfsg-1.5_all.deb \
     ...
     /debs/
```

実測（HLD の数値）[^1]:

| 条件 | `target/docker-snmp-sv2.gz` |
|------|------------------------------|
| 旧（52 ステップ）| **27m48s** |
| 新（20 ステップ）| **10m50s** |

ビルド時間はステップ数にほぼ線形（27/10 ≒ 52/20）であり、約 2.7× 高速化される[^1]。

### 開発時に強制するためのマクロ

`dockers/dockerfile-macros.j2` に共通マクロを用意し、新規 `Dockerfile.j2` 作成者が個別 `COPY`/`RUN` を書かないよう誘導する[^1]:

```
copy_files
install_debian_packages
install_python_wheels
```

### 最適化 2: Docker 18.09 + BuildKit

`sonic-slave-stretch` の docker を 18.09 に上げ、`docker build` 時に環境変数 `DOCKER_BUILDKIT=1` を渡す[^1]:

| 条件（最適化 1 適用済み） | 時間 |
|---------------------------|------|
| BuildKit なし | 11m02s |
| BuildKit あり |  4m20s |

最大累積効果で **約 6.5×** の高速化[^1]。

#### `--squash` の不具合（既知）

BuildKit の `--squash` は **base image ごと squash** する不具合があり、SONiC のような派生イメージで **600 MB → 1.5 GB** に膨張する[^1]。HLD はこの段階では `SONIC_USE_DOCKER_BUILDKIT` を **opt-in** とし、ユーザに警告メッセージを出す方針:

```
$ make SONIC_USE_DOCKER_BUILDKIT=y target/sonic-mellanox.bin
warning: using docker buildkit will produce increase image size
 (more details: https://github.com/moby/moby/issues/38903)
```

将来 upstream で修正されたら既定で有効化する想定[^1]。

### 最適化 2 の発展形: bind mount で `COPY debs/` 自体を回避

BuildKit の experimental syntax を使うと、`debs/` を毎回 image にコピーせずに **bind mount で参照** できる[^1]:

```Dockerfile
# syntax = docker/dockerfile:experimental
RUN --mount=type=bind,target=/debs/,source=debs/ dpkg_apt() deb1 deb2 deb3...
```

最適化 1 込みで **3m57s** まで短縮される[^1]。

### 最適化 3: dpkg-buildpackage の並列化

`man dh build` 抜粋[^1]:

> If your package can be built in parallel, please either use compat 10 or pass `--parallel` to dh. Then `dpkg-buildpackage -j` will work.

並列化対応で改善が見込めるパッケージ[^1]:

| パッケージ | Before | After |
|-----------|--------|-------|
| `swss`        | ~7m  | ~2m |
| `swss-common` | 並列化可 | — |
| `sairedis`    | ~20m | ~7m |

### 最適化 4: sairedis の RPC / 非 RPC 分離

`sairedis` は多くのターゲットの依存元で、build を **2 回** 走らせている（RPC 版 + 非 RPC 版）。`ENABLE_SYNCD_RPC != y` の場合 `libthrift` / `saithrift` のビルドは不要[^1]。

`rules/sairedis.mk` で次のように指定:

```make
SAIREDIS_DPKG_TARGET = binary-syncd
```

`ENABLE_SYNCD_RPC` で `libthrift` を条件付き注入する。これにより全体で約 10 分短縮、`sairedis` ターゲット単体は ~3 分まで短縮できる[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/sonic-build-system/build_system_improvements.md#L160-L173 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  - No need to build libthrift, saithrift when 'ENABLE_SYNCD_RPC != y'
  - The debian/rules in sairedis is written in a way that it will built sairedis from scratch twice - non-rpc and rpc version.
  This improvement is achivable by specifying in rules/sairedis.mk: SAIREDIS_DPKG_TARGET = binary-syncd
reasoning: sairedis 2 度ビルドの問題と修正方針の根拠。
-->

### 累積改善

12 CPU のビルドサーバでの実測[^1]:

| 環境 | 全ビルド時間 |
|------|-------------|
| 数ヶ月前（最適化前）| ~6h |
| 現在（最適化 1〜4 適用）| ~2.5h |
| `SONIC_USE_BUILD_KIT=y` 追加 | ~1.5h |

linux kernel をスクラッチビルドした条件での値。

## 設定

### 関連するビルドフラグ

| フラグ | 既定 | 説明 |
|--------|------|------|
| `SONIC_USE_DOCKER_BUILDKIT` | `n` | BuildKit を使う（image size 注意）|
| `ENABLE_SYNCD_RPC` | `n` | RPC 版 sairedis を必要とする場合 |

### 設定例

```bash
make SONIC_USE_DOCKER_BUILDKIT=y target/sonic-mellanox.bin
```

## 制限事項

- **BuildKit `--squash` の image size バグ**: 上流 fix まで opt-in に留める方針[^1]。
- **古い HLD**: Stretch / Python 3.6 / docker 18.09 が前提の文章であり、現行 master では Bookworm / 新 docker への移行が進んでいる可能性が高い。
- **bind mount は experimental**: Dockerfile 冒頭の `# syntax = docker/dockerfile:experimental` が必要[^1]。
- **個別 PR が散在**: sairedis 分離は既に作業中だが当時 PR 化されていない（HLD は issue #333 を参照）[^1]。

## 干渉する機能

- **`dockers/Dockerfile.j2` テンプレート全般**: `copy_files` / `install_debian_packages` 等のマクロに置き換える際、ビルド時のコピー単位が変わるため `COPY` 順序前提のスクリプト（`sonic_debian_extension.sh` 等）と干渉しないか確認が必要。
- **キャッシュ系**: BuildKit はキャッシュ仕様が異なる。レイヤ数削減と組み合わせるとキャッシュヒット率が変わる。
- **`ENABLE_SYNCD_RPC`**: sairedis の RPC 版が必要なテストベンチ等では本最適化と両立する経路を選ぶ。

## トラブルシューティング

- イメージサイズが極端に大きい: `SONIC_USE_DOCKER_BUILDKIT=y` で base image 込み squash されている可能性[^1]。
- BuildKit が効かない: docker version 18.09 以上か確認、`DOCKER_BUILDKIT=1` 環境変数。
- 並列ビルドで失敗: dh compat 10 以上または `dh --parallel` 設定、各 debian/rules で並列実行に対応しているか確認。

## 引用元

[^1]: `sonic-net/SONiC` `doc/sonic-build-system/build_system_improvements.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
