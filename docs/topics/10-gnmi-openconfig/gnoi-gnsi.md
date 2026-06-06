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

## API と SONiC 実装状況

gNOI / gNSI の proto には多数の RPC が定義されているが、SONiC の `sonic-gnmi` サーバが実装しているのはその一部に限られる。下表は SONiC 実装 (master) でどの RPC が動くかを基準に整理したもので、`Unimplemented` 列に挙げた RPC は呼んでも `gRPC codes.Unimplemented` を返す。proto に存在しても SONiC で呼ぶと失敗する API があるため、運用ツール側の前提を作るときに注意する。

| gNOI service | SONiC で実装済の RPC | proto 定義のみで未実装 | SONiC 側の到達点 | 参照 [HLD](../../reference/glossary.md#term-hld) |
| --- | --- | --- | --- | --- |
| System | Reboot, RebootStatus, CancelReboot, Time, SetPackage, SwitchControlProcessor, KillProcess | Ping, Traceroute | reboot 系スクリプト、`sonic-installer` (SetPackage 経由)、`supervisorctl` (KillProcess 経由) | [gNOI System](../../management/gnoi-hld-for-system-apis.md) |
| OS | Install, Activate, Verify | (なし) | `sonic-installer` で image インストール | [gNOI OS](../../management/gnoi-hld-for-os-apis.md) |
| File | Stat, Put, Remove, TransferToRemote | Get | local file system、tech-support、log (DBus 経由でホスト側に到達) | [gNOI File / Factory Reset](../../management/gnoi-hld-for-file-and-factory-reset-apis.md) |
| FactoryReset | Start | (なし) | `reset-factory` 系の処理 | [gNOI File / Factory Reset](../../management/gnoi-hld-for-file-and-factory-reset-apis.md) |
| Healthz | Artifact, Acknowledge (Get は debug-data path のみ) | List, Check, Get (debug-data 以外) | container / service の health 状態、core dump など artifact 取り出し | [gNOI Healthz](../../management/gnoi-hld-for-healthz-api.md) |
| gNSI.Certz | Rotate, CanGenerateCSR | AddProfile, DeleteProfile, GetProfileList | server cert / CA / CRL bundle の rotate、profile 単位の証明書束 | [gNSI HLD](../../management/gnsi-hld.md) |
| gNSI.Authz | Rotate | Probe, Get | gRPC method 単位の認可 policy 配布、checkpoint / revert 経由の安全な切替 | [gNSI HLD](../../management/gnsi-hld.md) |
| gNSI.Pathz | Rotate | Probe, Get | gNMI path 単位の認可 policy 配布、ConfigDB metadata への永続化 | [gNSI HLD](../../management/gnsi-hld.md) |

<!-- evidence: sonic-gnmi/gnmi_server/gnoi_system.go L193-L344 で Reboot/RebootStatus/CancelReboot/SetPackage/SwitchControlProcessor/Time/KillProcess を実装、Ping (L295) と Traceroute (L306) は codes.Unimplemented を返す stub -->
<!-- evidence: sonic-gnmi/gnmi_server/gnoi_file.go L20-L138 で Stat/TransferToRemote/Put/Remove を実装、Get (L92) は codes.Unimplemented を返す stub -->
<!-- evidence: sonic-gnmi/gnmi_server/gnoi_healthz.go L190-L326: Artifact (L210) / Acknowledge (L299) は実装、Get (L190) は debug-data path 以外で codes.Unimplemented (L207)、List (L321-322) と Check (L325-326) は codes.Unimplemented を返す stub -->
<!-- evidence: sonic-gnmi/gnmi_server/gnsi_certz.go L162-L171: AddProfile / DeleteProfile / GetProfileList は codes.Unimplemented を返す stub、CanGenerateCSR (L171) と Rotate (L225) は実装 -->
<!-- evidence: sonic-gnmi/gnmi_server/gnsi_authz.go L43-L66: Probe (L43) / Get (L46) は codes.Unimplemented を返す stub、Rotate (L66) は実装 (checkpoint / commit / revert を含む) -->
<!-- evidence: sonic-gnmi/gnmi_server/gnsi_pathz.go L60-L181: Probe (L60) / Get (L64) は codes.Unimplemented を返す stub、Rotate (L181) は実装 -->
<!-- evidence: SONiC/doc/mgmt/gnmi/gnoi_system_hld.md L26 "Removed non-Reboot gNOI APIs" / L34 "The System RPCs covered in this doc include: Reboot, RebootStatus, CancelReboot" — HLD 範囲は Reboot 3 種、その他は後続実装 -->
<!-- evidence: SONiC/doc/mgmt/gnmi/gnoi_file_factory_reset_hld.md L33 "The File RPCs covered in this doc include: Remove" — HLD 範囲は Remove のみ -->

各 API の引数、エラーコード、SONiC 固有の制限事項は対応する HLD に書かれている。HLD は提案単位で分割されているため、たとえば System であれば Reboot 系 (本表の HLD) と SetPackage / SwitchControlProcessor (後続の sonic-gnmi PR で追加) のように、コード上の実装と HLD の範囲が一致しない点に注意する。

## System (reboot / package / process)

[gNOI System APIs](../../management/gnoi-hld-for-system-apis.md) は、reboot 操作と OS package 配布、control processor 切替を扱う。SONiC 側では `Reboot` が `reboot` / `warm-reboot` / `fast-reboot` のいずれかにマップされ、CancelReboot と RebootStatus は delayed reboot のキャンセル・状態確認に使う。SetPackage は SetPackage stream を受けて `sonic-installer` の image upload 相当の処理に流す。KillProcess は systemd 配下の service を `supervisorctl` で再起動・停止する。

System service の `Ping` と `Traceroute` は proto には定義されているが、sonic-gnmi 側では `codes.Unimplemented` を返す stub になっている。NMS から network reachability を測りたい場合は別経路 (SSH + `ping` / `traceroute` など) を使う。

reboot 種別の SONiC 内部設計は章 11 (Reboot / Upgrade / Lifecycle) を参照する。

## OS (install / activate / verify)

[gNOI OS APIs](../../management/gnoi-hld-for-os-apis.md) は、image を upload して install し、次回 boot で activate する、という標準的な lifecycle を SONiC でどう実装するかを定義する。`sonic-installer` が backend で動く。Install と Activate を別 RPC に分けているため、image 検証と切替を独立にスケジュールできる。

## File / FactoryReset

[gNOI File / FactoryReset APIs](../../management/gnoi-hld-for-file-and-factory-reset-apis.md) は、log や tech-support の取り出し、設定 file の配置、factory reset を扱う。SONiC では File service の `Stat` / `Put` / `Remove` / `TransferToRemote` が DBus 経由でホスト側 (`sonic-host-services`) のファイル操作にマップされる。

ただし File service の `Get` (stream による file download) は sonic-gnmi 側では `codes.Unimplemented` を返す stub になっている。NMS から log や tech-support を取り出したい場合は `TransferToRemote` で remote の HTTP / SFTP に push する経路を使う。FactoryReset.Start の対象範囲 (config だけか、ログまでか) は SONiC 側のポリシーで決まる。

Factory reset の SONiC 実装 (`reset-factory` design) は章 11 や reset-factory HLD を参照する。

## Healthz

[gNOI Healthz API](../../management/gnoi-hld-for-healthz-api.md) は、container や service の health 状態を gRPC で問い合わせる。SONiC の実装は「core dump / debug artifact を取り出す入口」に振り切っており、proto 定義の RPC のうち SONiC で実際に動くのは `Artifact` (stream で artifact を返す) と `Acknowledge` (event を確認済みとしてマークする) の 2 つに限られる。

`Get` は debug-data path を含む特定 path (`isDebugData`) のみ実装で、それ以外の component path を渡すと `codes.Unimplemented` を返す。`List` と `Check` は proto には残っているが SONiC では未実装で、`codes.Unimplemented` を返す stub になっている。つまり「障害発生時のスナップショット (core dump 等の artifact) を引き取る」用途は動くが、「健康な component の状態を一覧する」用途は現状の SONiC では gNOI Healthz では実現できない。

<!-- evidence: sonic-gnmi/gnmi_server/gnoi_healthz.go L39 isDebugData / L91 getDebugData により Get は debug-data path のみ処理し、それ以外は L207 で codes.Unimplemented を返す -->

## gNSI: 証明書とポリシー

[gNSI HLD](../../management/gnsi-hld.md) は、SONiC の証明書配布と認可ポリシー配布を gRPC API として扱う。sonic-gnmi で動くのは Certz / Authz / Pathz の 3 service で、いずれも `Rotate` (双方向 stream で配布 → checkpoint → 検証 → commit / revert) に実装が集中している。proto 上は Authz / Pathz に `Probe` (現行 policy を試験評価する) や `Get` (現行 policy を取り出す) があるが、SONiC ではどちらも `codes.Unimplemented` を返す stub のままで、配布した policy は ConfigDB metadata と file 経由でしか取り戻せない。

- **Certz** (`gnsi_certz.go`): server cert / CA chain / CRL bundle を profile 単位で rotate する。`Rotate` stream の中で `GenerateCSR` / `UploadRequest` / `FinalizeRequest` のフェーズを順に流す。`AddProfile` / `DeleteProfile` / `GetProfileList` は proto 上の RPC で SONiC では未実装。`CanGenerateCSR` は実装されており CSR 生成可否の事前確認に使える。
- **Authz** (`gnsi_authz.go`): gRPC method 単位の認可 policy (JSON) を `Rotate` で配布し、`/etc/sonic/gnsi/authz_policy.json` 相当のファイルに保存して checkpoint → commit する。revert 時は checkpoint から policy ファイルを書き戻し、freshness metadata を ConfigDB に記録する。
- **Pathz** (`gnsi_pathz.go`): gNMI path 単位の認可 policy を `Rotate` で配布し、policy ファイルへの保存・metadata の ConfigDB 反映・revert を Authz と同じ pattern で実装している。

Attestation (gNSI Attestz など) と Acctz (audit log) は proto には存在するが sonic-gnmi の master には server 実装が無いため、運用ツール側で「Certz / Authz / Pathz の 3 つだけが現状の gNSI 表面である」前提を持つ必要がある。

## 関連ページ

- [gNOI System APIs](../../management/gnoi-hld-for-system-apis.md)
- [gNOI OS APIs](../../management/gnoi-hld-for-os-apis.md)
- [gNOI File and Factory Reset APIs](../../management/gnoi-hld-for-file-and-factory-reset-apis.md)
- [gNOI Healthz API](../../management/gnoi-hld-for-healthz-api.md)
- [gNSI HLD](../../management/gnsi-hld.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
