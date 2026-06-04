---
title: gNOI / gNSI
description: gNOI / gNSI — gNOI (gRPC Network Operations Interface) は、設定読み書き (gNMI)
  の隣で reboot / OS install / file transfer / factory reset / healthz といった操作 RPC を担当し、gNSI
  (gRPC Network Security Interface) が証明書配布・認可・attestation を担う。SONiC では telemetry container
  内の gNMI server に同居する。
area: topics
verification: meta
last_verified: 2026-06-04
sources:
- repo: sonic-net/SONiC
  path: doc/mgmt/gnmi/gnoi_system_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/SONiC
  path: doc/mgmt/gnmi/gnoi_os_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/SONiC
  path: doc/mgmt/gnmi/gnoi_file_factory_reset_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/SONiC
  path: doc/mgmt/gnmi/gnoi_healthz_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/SONiC
  path: doc/mgmt/gnmi/gnsi.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/gnoi.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/gnoi_system.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/gnoi_os.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/gnoi_file.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/gnoi_reset.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/gnoi_healthz.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/gnsi_certz.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/gnsi_authz.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/gnsi_pathz.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
related:
  cli:
  - config warm_restart
  config_db:
  - TELEMETRY
  - GNMI
  yang:
  - sonic-gnmi
  - sonic-telemetry
---

# gNOI / gNSI

[gNOI](../../reference/glossary.md#term-gnoi) (gRPC Network Operations Interface) は、設定読み書き ([gNMI](../../reference/glossary.md#term-gnmi)) の隣で「操作」を担当する。reboot、OS install、file transfer、factory reset、health check のような operational action を、ベンダー非依存の API として呼べるようにする。gNSI (gRPC Network Security Interface) は、その隣で証明書配布、認証ポリシー、attestation のような security action を担当する。

[SONiC](../../reference/glossary.md#term-sonic) の gNOI / gNSI 実装は、telemetry container 内の同じプロセスで gNMI と一緒に動く。API ごとに SONiC のどの service / script を呼んでいるかを押さえると、障害時の切り分けが速い。

## API と SONiC service の対応

| gNOI service | 主な API | SONiC 側の到達点 | 参照 [HLD](../../reference/glossary.md#term-hld) |
| --- | --- | --- | --- |
| System | Reboot, RebootStatus, CancelReboot, Time, Ping, Traceroute, SetPackage, SwitchControlProcessor | `reboot`、reboot-cause、`sonic-installer` | [gNOI System](../../management/gnoi-hld-for-system-apis.md) |
| OS | Install, Activate, Verify | `sonic-installer` で image インストール | [gNOI OS](../../management/gnoi-hld-for-os-apis.md) |
| File | Get, Put, Stat, Remove, TransferToRemote | local file system、tech-support、log | [gNOI File / Factory Reset](../../management/gnoi-hld-for-file-and-factory-reset-apis.md) |
| FactoryReset | Start | `reset-factory` 系の処理 | [gNOI File / Factory Reset](../../management/gnoi-hld-for-file-and-factory-reset-apis.md) |
| Healthz | Get, List, Acknowledge, Artifact, Check | container / service の health 状態 | [gNOI Healthz](../../management/gnoi-hld-for-healthz-api.md) |
| gNSI | CertZ / Authz / Pathz など | 証明書、認証ポリシー、attestation | [gNSI HLD](../../management/gnsi-hld.md) |

各 API の引数、エラーコード、SONiC 固有の制限事項は対応する HLD に書かれている。たとえば Reboot は warm/fast/cold の指定をどの SONiC reboot に対応させるか、Healthz の component 階層をどう SONiC service に割り当てるかが、それぞれの HLD で具体化されている。

## System (reboot / package / process)

[gNOI System APIs](../../management/gnoi-hld-for-system-apis.md) は、reboot 操作と OS package 配布、control processor 切替を扱う。SONiC 側では `Reboot` が `/usr/local/bin/reboot` 経由か、warm/fast の場合は別経路で走る。CancelReboot、RebootStatus は delayed reboot のキャンセル・状態確認に使う。

reboot 種別の SONiC 内部設計は章 11 (Reboot / Upgrade / Lifecycle) を参照する。

## OS (install / activate / verify)

[gNOI OS APIs](../../management/gnoi-hld-for-os-apis.md) は、image を upload して install し、次回 boot で activate する、という標準的な lifecycle を SONiC でどう実装するかを定義する。`sonic-installer` が backend で動く。Install と Activate を別 RPC に分けているため、image 検証と切替を独立にスケジュールできる。

## File / FactoryReset

[gNOI File / FactoryReset APIs](../../management/gnoi-hld-for-file-and-factory-reset-apis.md) は、log や tech-support の取り出し、設定 file の配置、factory reset を扱う。File.Get / Put のパス権限と、Factory Reset の対象範囲 (config だけか、ログまでか) は SONiC 側のポリシーで決まる。

Factory reset の SONiC 実装 (`reset-factory` design) は章 11 や reset-factory HLD を参照する。

## Healthz

[gNOI Healthz API](../../management/gnoi-hld-for-healthz-api.md) は、container や service の health 状態を gRPC で問い合わせる。SONiC で container health を集約する仕組みと組み合わせて、特定の component の status / artifact (たとえば core dump、log) を取れるように設計されている。NMS から「障害発生時のスナップショット取得」を自動化したいときの入口になる。

## gNSI: 証明書とポリシー

[gNSI HLD](../../management/gnsi-hld.md) は、SONiC の証明書配布、認証ポリシー、attestation を gRPC API として扱う。CertZ で server cert / CA を配布し、Authz で gRPC 認可ポリシーを配布し、Pathz で path 単位のアクセス制御を配布する。CLI / 手動オペレーションを置き換えて、複数 device の security posture を一括管理できるようにするための層である。

## 関連ページ

- [gNOI System APIs](../../management/gnoi-hld-for-system-apis.md)
- [gNOI OS APIs](../../management/gnoi-hld-for-os-apis.md)
- [gNOI File and Factory Reset APIs](../../management/gnoi-hld-for-file-and-factory-reset-apis.md)
- [gNOI Healthz API](../../management/gnoi-hld-for-healthz-api.md)
- [gNSI HLD](../../management/gnsi-hld.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
