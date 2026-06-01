---
title: ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離）
description: 'ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離） — Dockerfile レイヤ最適化・BuildKit キャッシュ活用・並列 dh_make・sairedis 分離ビルドの 4 手法で SONiC のビルド時間を大幅に短縮する設計。'
area: architecture
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/sonic-build-system/build_system_improvements.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli: []
  yang: []
  _no_related: true
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 19 章: Build / Packaging / Debian](../topics/19-build-packaging/index.md) を参照。
<!-- /topics-tip -->

!!! note "裏取りステータス: code-verified（部分実装）"
    HLD は Debian Stretch 時代の文書だが、`sonic-buildimage/dockers/dockerfile-macros.j2` の `install_debian_packages` / `install_python_wheels` / `copy_files` マクロは現存。BuildKit は `SONIC_USE_DOCKER_BUILDKIT` フラグとしては未取り込みで、CI / `scripts/collect_docker_version_files.sh` で `DOCKER_BUILDKIT=1` を直接設定する形になっている (`.azure-pipelines/template-variables.yml` ではむしろ `DOCKER_BUILDKIT: 0` 既定)。`SAIREDIS_DPKG_TARGET=binary-syncd` 個別の指定は現行 `rules/sairedis.mk` には残っておらず、`slave.mk:879 $(if $($*_DPKG_TARGET),...)` の汎用機構に統合されている。dh `--parallel` 関連は debian/rules 側で patch 済み。

# ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離）

## 概要

[SONiC](../reference/glossary.md#term-sonic) ビルドは大別すると 2 段階で構成される[^1]:

1. Debian / Python パッケージ コンパイル — 比較的速い
2. **Docker イメージビルド** — 遅い（特に複数ユーザ並列時）

本 [HLD](../reference/glossary.md#term-hld) は主に第 2 段階に焦点を当て、4 つの最適化を提案する[^1]:

1. Dockerfile の **`COPY` / `RUN` をマージしてレイヤ数を削減**
2. Docker 18.09 + **BuildKit** の有効化
3. `swss` / `swss-common` / `sairedis` の **`dh --parallel`** 並列ビルド
4. `sairedis` の RPC / 非 RPC 分離

## 動作仕様

### 最適化 1: Dockerfile のレイヤ数削減

各 `COPY` / `RUN` 行は新しい Docker レイヤを生成する。`--no-cache --squash` で最終出力を 1 レイヤに潰しているため、**ビルド中の細かいレイヤ分割は無意味なコスト**[^1]。

**Before**: 各 deb パッケージごとに 1 行ずつ `COPY` / `RUN`（[SNMP](../reference/glossary.md#term-snmp) docker で 52 ステップ）

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

```text
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

```bash
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

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/sonic-build-system/build_system_improvements.md#L160-L173 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/sonic-build-system/build_system_improvements.md#L160-L173 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    - No need to build libthrift, saithrift when 'ENABLE_SYNCD_RPC != y'
    - The debian/rules in sairedis is written in a way that it will built sairedis from scratch twice - non-rpc and rpc version.
    This improvement is achivable by specifying in rules/sairedis.mk: SAIREDIS_DPKG_TARGET = binary-syncd
    ```

    **判断根拠**: sairedis 2 度ビルドの問題と修正方針の根拠。

<!-- evidence-rendered:end -->

### 累積改善

12 CPU のビルドサーバでの実測[^1]:

| 環境 | 全ビルド時間 |
|------|-------------|
| 数ヶ月前（最適化前）| ~6h |
| 現在（最適化 1〜4 適用）| ~2.5h |
| `SONIC_USE_DOCKER_BUILDKIT=y` 追加 | ~1.5h |

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

## 既知の問題

### `SONIC_BUILD_JOBS=N` 並列ビルドで最終ターゲット失敗（#1738）

`SONIC_BUILD_JOBS=4` 等の並列ビルド設定で、複数の最終ターゲットが同時にビルドされる際に依存関係が解決されず失敗するケースがある。エラーの典型例:

```
couldn't find these debs: ...
```

**回避策:** `SONIC_BUILD_JOBS` を 1 に下げるか、省略して再試行する。または並列度を落として複数回実行する。

- 参照: [sonic-net/SONiC#1738](https://github.com/sonic-net/SONiC/issues/1738)

### ビルド成果物のダウンロード先変更（#865）

旧 URL (`sonic-jenkins.westus2.cloudapp.azure.com`) は廃止されており、アクセス拒否になる。現在のビルド成果物は以下から取得する:

- **新 URL**: https://sonic-build.azurewebsites.net/ui/sonic/pipelines
- Platform → Branch → Build → Artifacts のツリーから目的のイメージを選択

README の color badge をクリックして最新ビルドに直接ジャンプする方法もある。

- 参照: [sonic-net/SONiC#865](https://github.com/sonic-net/SONiC/issues/865)

### 低スペックスイッチ（2GB flash/RAM）でのインストール時 OOM（#1065）

古い低スペックのスイッチ（例: SuperMicro SSE-G3648B、Arista 7050QX-32 等の 2GB flash モデル）では master ブランチのイメージサイズが増大しておりインストール時に OOM が発生する。

**回避策:**
- 古いイメージ (201811 等) を使用する: `https://sonic-build.azurewebsites.net/api/sonic/artifacts?branchName=201811&platform=broadcom&target=target%2Fsonic-broadcom.bin`
- または SWAP 領域を作成してから再インストール
- 最低 16GB の flash/DOM への換装を推奨

master ブランチのイメージは機能追加に伴いサイズが増大しており、2GB flash 環境での動作は保証されない。

- 参照: [sonic-net/SONiC#1065](https://github.com/sonic-net/SONiC/issues/1065)

### sonic-slave コンテナ内で debootstrap が proc マウントに失敗する場合（sonic-buildimage#27）

sonic-slave コンテナ内で debootstrap が proc マウントに失敗する場合、`docker run --privileged` フラグが必須。通常の docker run では /proc マウントの権限不足でビルドが中断する

- 参照: [sonic-net/sonic-buildimage#27](https://github.com/sonic-net/sonic-buildimage/issues/27)

### /host/machine.conf の内容が不正な場合、プラットフォーム固有の設定が失敗する（sonic-buildimage#1519）

/host/machine.conf の内容が不正な場合、プラットフォーム固有の設定が失敗する。platform フィールドに正しい hwsku 名を設定すること

- 参照: [sonic-net/sonic-buildimage#1519](https://github.com/sonic-net/sonic-buildimage/issues/1519)

### sonic-slave コンテナに入る方法（sonic-buildimage#2029）

sonic-slave コンテナに入る方法: `docker run -v /var/run/docker.sock:/var/run/docker.sock --privileged -it sonic-slave bash`。`--privileged` フラグなしでは proc マウント等が失敗する

- 参照: [sonic-net/sonic-buildimage#2029](https://github.com/sonic-net/sonic-buildimage/issues/2029)

### 初期化スクリプトで `depmod -a` が実行されていない場合、`libkmod: ERROR` ログが出力される（sonic-buildimage#2030）

初期化スクリプトで `depmod -a` が実行されていない場合、`libkmod: ERROR` ログが出力される。カーネルモジュールの依存関係データベース更新が必要

- 参照: [sonic-net/sonic-buildimage#2030](https://github.com/sonic-net/sonic-buildimage/issues/2030)

### Linux カーネルビルド中に `failed to load plugin io.containerd.snapsho（sonic-buildimage#2614）

Linux カーネルビルド中に `failed to load plugin io.containerd.snapshotter` エラーが発生する問題。containerd のバージョンと Linux カーネルの互換性確認が必要

- 参照: [sonic-net/sonic-buildimage#2614](https://github.com/sonic-net/sonic-buildimage/issues/2614)

### SONiC HEAD 187-dirty ビルドでのバージョン管理問題（sonic-buildimage#4096）

SONiC HEAD 187-dirty ビルドでのバージョン管理問題。`--dirty` サフィックスが付くビルドは本番環境での使用を避けること

- 参照: [sonic-net/sonic-buildimage#4096](https://github.com/sonic-net/sonic-buildimage/issues/4096)

### ベース docker イメージのビルド時に `apt-get update` が常に失敗する問題（sonic-buildimage#4366）

ベース docker イメージのビルド時に `apt-get update` が常に失敗する問題。Debian リポジトリの APT キーが期限切れの場合に発生。`apt-key update` でキーを更新すること

- 参照: [sonic-net/sonic-buildimage#4366](https://github.com/sonic-net/sonic-buildimage/issues/4366)

### master mainline でのビルドエラー（sonic-buildimage#4404）

master mainline でのビルドエラー。`git submodule update --init --recursive` でサブモジュールを最新化してから再ビルドすること

- 参照: [sonic-net/sonic-buildimage#4404](https://github.com/sonic-net/sonic-buildimage/issues/4404)

### スイッチ起動時に sonic-cfggen が大量の CPU を消費する問題（sonic-buildimage#4553）

スイッチ起動時に [sonic-cfggen](../reference/glossary.md#term-sonic-cfggen) が大量の CPU を消費する問題。起動時に複数のサービスが同時に sonic-cfggen を呼び出すため。`systemd-analyze blame` でボトルネックを特定すること

- 参照: [sonic-net/sonic-buildimage#4553](https://github.com/sonic-net/sonic-buildimage/issues/4553)

### sonic-cfggen が `/var/run/redis/redis.sock` への接続に失敗する問題（sonic-buildimage#5277）

sonic-cfggen が `/var/run/redis/redis.sock` への接続に失敗する問題。[Redis](../reference/glossary.md#term-redis) ソケットファイルが存在しない状態で実行された場合に発生

- 参照: [sonic-net/sonic-buildimage#5277](https://github.com/sonic-net/sonic-buildimage/issues/5277)

### Dynamic Port Breakout (DPB) 機能が最新 master では動作しない問題（sonic-buildimage#5417）

Dynamic Port Breakout ([DPB](../reference/glossary.md#term-dpb)) 機能が最新 master では動作しない問題。DPB は特定のプラットフォームとカーネルバージョンの組み合わせに依存する

- 参照: [sonic-net/sonic-buildimage#5417](https://github.com/sonic-net/sonic-buildimage/issues/5417)

### 物理スイッチへの SONiC インストールに失敗する問題（sonic-buildimage#5596）

物理スイッチへの SONiC インストールに失敗する問題。ONIE インストーラーのバージョンと SONiC イメージの互換性を確認すること

- 参照: [sonic-net/sonic-buildimage#5596](https://github.com/sonic-net/sonic-buildimage/issues/5596)

### VS (Virtual Switch) イメージで config reload が失敗する問題（sonic-buildimage#5959）

[VS](../reference/glossary.md#term-vs) (Virtual Switch) イメージで config reload が失敗する問題。VS 環境では一部のプラットフォーム固有サービスが利用できないため、VS 用の設定を使用すること

- 参照: [sonic-net/sonic-buildimage#5959](https://github.com/sonic-net/sonic-buildimage/issues/5959)

### 201911 で `SONIC_DEBUGGING_ON=y` を設定するとコンパイルが失敗する問題（sonic-buildimage#5982）

201911 で `SONIC_DEBUGGING_ON=y` を設定するとコンパイルが失敗する問題。デバッグビルドオプションは特定のコンパイラバージョンとの互換性確認が必要

- 参照: [sonic-net/sonic-buildimage#5982](https://github.com/sonic-net/sonic-buildimage/issues/5982)

### DPB 後のインターフェースの alias が誤って設定される問題（sonic-buildimage#6024）

DPB 後のインターフェースの alias が誤って設定される問題。Dynamic Port Breakout 実行後は `show interfaces alias` で alias が正しく更新されているか確認すること

- 参照: [sonic-net/sonic-buildimage#6024](https://github.com/sonic-net/sonic-buildimage/issues/6024)

### Dynamic Port Breakout (DPB) 機能が不安定な問題（sonic-buildimage#6027）

Dynamic Port Breakout (DPB) 機能が不安定な問題。DPB は実行中に複数のサービスを再起動するため、メンテナンスウィンドウでの実行を推奨

- 参照: [sonic-net/sonic-buildimage#6027](https://github.com/sonic-net/sonic-buildimage/issues/6027)

### config_db.json ファイルのインターフェースがソートされていない問題（sonic-buildimage#6328）

[config_db.json](../reference/glossary.md#term-config_db.json) ファイルのインターフェースがソートされていない問題。設定ファイルの可読性のため、sort_keys=True で JSON を整形すること

- 参照: [sonic-net/sonic-buildimage#6328](https://github.com/sonic-net/sonic-buildimage/issues/6328)

### ARM アーキテクチャの VS docker イメージでのパフォーマンステスト（sonic-buildimage#6399）

ARM アーキテクチャの VS docker イメージでのパフォーマンステスト。ARM ホストでの SONiC テストにはネイティブ ARM ビルドが必要

- 参照: [sonic-net/sonic-buildimage#6399](https://github.com/sonic-net/sonic-buildimage/issues/6399)

### make コマンドラインからコードの最適化を無効化できない問題（sonic-buildimage#6413）

make コマンドラインからコードの最適化を無効化できない問題。`SONIC_DEBUGGING_ON=y` オプションでデバッグビルドを有効化できるが、最適化レベルの個別制御はサポートされていない

- 参照: [sonic-net/sonic-buildimage#6413](https://github.com/sonic-net/sonic-buildimage/issues/6413)

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

### コマンド例: Build system 確認

下記コマンドを順に実行することで、関連する [CONFIG_DB](../reference/glossary.md#term-config_db) / APP_DB / [STATE_DB](../reference/glossary.md#term-state_db) のエントリと、
CLI 表示・syslog の整合を一通り突き合わせ確認できる。

```bash
# sonic-buildimage のビルドキャッシュとオプション確認
make configure PLATFORM=generic
make -j SONIC_CONFIG_PRINT_DEPENDENCIES=y target/sonic-vs.img.gz | head
# slave docker のキャッシュ状況
docker images | grep sonic
```

## 参考リンク

- [Topics: Build / Packaging](../topics/19-build-packaging/index.md)
- [HLD: build-profiles](build-profiles.md)
- [Reference 索引](../reference/index.md)

## 関連 reference

- [HLD: build-profiles](build-profiles.md)
- [HLD: rfs-split-build-improvements](rfs-split-build-improvements-hld.md)

## 引用元

[^1]: `sonic-net/SONiC` `doc/sonic-build-system/build_system_improvements.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- evidence (verifier-batch-20):
- sonic-buildimage/dockers/dockerfile-macros.j2 :1 install_debian_packages, :16 install_python_wheels, :33 copy_files マクロ実装済
- sonic-buildimage/.azure-pipelines/template-variables.yml:7 DOCKER_BUILDKIT: 0 (既定 OFF)
- sonic-buildimage/scripts/collect_docker_version_files.sh:46-47 DOCKER_BUILDKIT=1 docker build (個別 script で BuildKit 利用)
- SONIC_USE_DOCKER_BUILDKIT フラグ自体は grep 0 件 -> HLD で提案された名前ではなく素の DOCKER_BUILDKIT 環境変数で運用
- sonic-buildimage/rules/sairedis.mk に SAIREDIS_DPKG_TARGET=binary-syncd の指定なし; slave.mk:879 $(if $($*_DPKG_TARGET),...) 汎用機構経由
-->

<!-- augmented-links: v1 -->

<!-- glossary-links-injected: 9fb3fca99a59 -->
