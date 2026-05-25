---
title: 内部実装
description: 内部実装 — build / packaging / application extension の内部実装は「sonic-buildimage
  は何を吐き出すか」「sonic-package-manager (SPM) はどう extension を載せるか」「image install 後にどう dockeriz…
area: topics
verification: meta
last_verified: 2026-05-11
sources: []
related:
  cli:
  - show techsupport
  - show platform
  - show version
  - show acl
  - config acl
  config_db:
  - FEATURE
  - CRM
  - ACL_RULE
  - ACL_TABLE
  - CHASSIS_MODULE
  - MID_PLANE_BRIDGE
  - DPU
  yang:
  - sonic-crm
  - sonic-system-defaults
---

# 内部実装

build / packaging / application extension の内部実装は「[sonic-buildimage](../../reference/glossary.md#term-sonic-buildimage) は何を吐き出すか」「sonic-package-manager (SPM) はどう extension を載せるか」「image install 後にどう dockerize されるか」の三層で見ます。docker-base / sonic-slave / sonic-build-hooks の関係を押さえると、ビルド時間とイメージサイズの分析が楽になります。

## データフロー（ビルド）

```mermaid
flowchart TB
  SRC["sonic-buildimage tree<br/>+ submodules"] --> SLAVE["sonic-slave-* docker<br/>build container"]
  SLAVE --> DEBS["*.deb<br/>per-package build"]
  SLAVE --> DOCKERS["docker images<br/>swss/syncd/bgp/..."]
  DEBS --> ROOTFS[rootfs squashfs]
  DOCKERS --> ROOTFS
  ROOTFS --> ONIE["onie-installer.bin<br/>or *.bin / *.swi"]
  ONIE -->|sonic-installer| HOST[/"host/image-*"/]
  HOST --> RUNTIME[runtime SONiC]
```

## データフロー（ランタイム / SPM）

```mermaid
flowchart LR
  CLI[sonic-package-manager install] --> MANIFEST["package manifest<br/>JSON"]
  MANIFEST --> REG[docker registry pull]
  REG --> SPM[sonic-package-manager]
  SPM --> FEATURE[("CONFIG_DB<br/>FEATURE table")]
  SPM --> SVC["/etc/systemd/system/*.service<br/>render"]
  FEATURE --> HOSTCFGD[hostcfgd]
  HOSTCFGD --> SYSTEMD[systemd start docker]
```

## 主要コンポーネントの責務

| コンポーネント | 主実体 | 責務 |
| --- | --- | --- |
| `sonic-slave-bullseye` / `sonic-slave-bookworm` | `dockers/sonic-slave-*/` | ビルド用 docker。すべての .deb と docker image を slave 内で作る |
| `Makefile.work` / `slave.mk` | top-level Makefile | submodule 配下の .deb / docker target を解決 |
| `sonic-build-hooks` | `src/sonic-build-hooks/` | サードパーティバイナリの取得、check sums、license の hook |
| `sonic-buildimage/files/build_templates/` | jinja2 | docker compose / systemd unit / supervisord conf を生成 |
| `sonic-package-manager` (SPM) | `src/sonic-package-manager/` | extension package のライフサイクル管理（install / upgrade / remove / list） |
| `hostcfgd` (`src/sonic-host-services/`) | `hostcfgd.py` | FEATURE table を見て systemd service の enable/disable と reload |
| `fwutil` / `sonic-installer` | python CLI | image install、show / next / cleanup |

## SPM / FEATURE table

`FEATURE` テーブルが SPM とランタイムの接続点です。

```yaml
CONFIG_DB:FEATURE|<name>
  state: "enabled|disabled|always_enabled|always_disabled"
  auto_restart: "enabled|disabled"
  high_mem_alert: "enabled|disabled"
  set_owner: "kube|local"
```

`set_owner = kube` は Kubernetes 経由デプロイ（k8s based feature management）の hint で、`local` はホスト systemd 管理です。

## SAI / Redis pub/sub の使用

ビルド・パッケージング系には [SAI](../../reference/glossary.md#term-sai) 属性も [Redis](../../reference/glossary.md#term-redis) pub/sub も基本ありません（ビルド時にコードを SAI 越しに動かさない）。例外:

- ランタイムで SPM が FEATURE table を書き、[hostcfgd](../../reference/glossary.md#term-hostcfgd) が [CONFIG_DB](../../reference/glossary.md#term-config_db) を subscribe して service を起動する経路は Redis pub/sub を使います。
- `sonic-installer` は image partition の操作のみで Redis 不要。

## Redis テーブル参照関係

```yaml
CONFIG_DB:
  FEATURE, DEVICE_METADATA (image_type / hwsku)
STATE_DB:
  FEATURE (state は CONFIG_DB、runtime state は STATE_DB)
```

## 既知の実装上の制約

- ビルドは **slave docker の rebuild が高頻度で必要**で、初回 build に 1〜2 時間かかります。`make -j` 並列度は host のメモリと swap に強く依存します。
- submodule の SHA を上げると `make configure` の再走が必要で、incremental ではなく毎回 deb 系を作り直すケースがある（`*.flag` の依存解決が conservative）。
- SPM の extension は **公式ビルドの [SONiC](../../reference/glossary.md#term-sonic) イメージ（PR build 含む）に対してのみテスト**されており、外部派生ビルドでの互換性は保証されません。manifest の `min-version` を確認してください。
- `set_owner = kube` 系の機能は SONiC master でも実験的扱いの箇所があり、`feature` の状態遷移が Kubernetes 側の expected とずれることがあります。
- `sonic-buildimage` のターゲット platform は `PLATFORM=<vendor>` 環境変数で切替えますが、複数 platform を同時にビルドする supported workflow は無いに等しく、CI 側で逐次 build しています。
- application extension の docker image は SONiC の base layer に依存していると更新時にサイズが膨らみ、`/host` の空き容量に注意が必要です。

## ビルドキャッシュと incremental build

`sonic-buildimage` は package ごとに `.flag` ファイルでビルド完了を記録します。submodule の HEAD SHA が変わると、その submodule 由来のすべての `.deb` と参照する docker image が rebuild 対象になります。incremental 化のために以下が用意されています。

| 機構 | 目的 |
| --- | --- |
| `SONIC_DPKG_CACHE_METHOD=cache` | `.deb` の hash-key ベースキャッシュ（`/sonic/target/cache/`） |
| `BLDENV` の固定 | slave 側 OS バージョン（bullseye / bookworm）を固定して再利用 |
| `SONIC_BUILD_JOBS` | 並列度の制御。host CPU/RAM に応じて調整 |
| `NOSTRETCH` 等の Make 変数 | 不要 platform deb のスキップ |

キャッシュは個別開発者環境では効果が大きい一方、PR build（GitHub Actions）では基本クリーンビルドであり、CI 時間の大半は slave docker の起動と deb の sequential build に費やされます。

## docker image の階層

ランタイムの SONiC docker image は階層を持ちます。

```text
docker-base-<bullseye/bookworm>
  └─ docker-config-engine
       └─ docker-swss
       └─ docker-syncd-<vendor>
       └─ docker-bgp
       └─ docker-teamd
       └─ docker-pmon
       └─ docker-snmp
       └─ docker-telemetry
       └─ docker-mux
```

`docker-config-engine` が共通の python / sonic-py-common / supervisord 設定を持ち、機能 container はそれを base にして個別バイナリと supervisord conf を足します。新規 extension は `docker-base-<os>` から派生させる選択も可能ですが、サイズ削減のためには既存階層への mount が推奨されます。

## 関連ページ

- [Build profiles](../../architecture/build-profiles.md)
- [Build system improvements](../../architecture/build-system-improvements.md)
- [RFS split build improvements](../../architecture/rfs-split-build-improvements-hld.md)
- [SONiC application extension infrastructure](../../architecture/sonic-application-extension-infrastructure.md)
- [SONiC application extension guide](../../management/sonic-application-extension-guide.md)
- [sonic-package-manager CLI](../../reference/cli/sonic-package-manager.md)
- [SONiC optional feature control enhancement](../../system/sonic-optional-feature-control-enhancement.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
