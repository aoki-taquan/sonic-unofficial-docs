---
title: 内部実装
description: 内部実装 — ここではデータプレーン側のセキュリティ、特に MACsec / MKA とその ASIC・Gearbox 側の境界、起動時の
  SAI POST を扱います。control plane の AAA 系は アーキテクチャ で完結しており、本ページではリンクの暗号と完全性に話を限定します。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/switching/macsec-sonic-high-level-design-document.md
- docs/switching/sonic-hld-deterministic-macsec-backend-selection-for-gearbox-ports.md
- docs/switching/sonic-sai-post-support-for-macsec.md
related:
  cli:
  - config aaa
  - show aaa
  - show acl
  - config acl
  config_db:
  - AAA
  - RADIUS
  - COPP_GROUP
  - COPP_TRAP
  - ACL_RULE
  - ACL_TABLE
  - TACPLUS
  yang:
  - sonic-copp
---

# 内部実装

ここではデータプレーン側のセキュリティ、特に [MACsec](../../reference/glossary.md#term-macsec) / MKA とその [ASIC](../../reference/glossary.md#term-asic)・Gearbox 側の境界、起動時の [SAI](../../reference/glossary.md#term-sai) POST を扱います。control plane の [AAA](../../reference/glossary.md#term-aaa) 系は [アーキテクチャ](architecture.md) で完結しており、本ページではリンクの暗号と完全性に話を限定します。

## MACsec の control / data plane 境界

MACsec はリンク単位の L2 暗号化規格で、[SONiC](../../reference/glossary.md#term-sonic) では大きく二つの世界に分けて実装されています。

- Control plane: MKA（MACsec Key Agreement）と SAK 配布。ホスト側の `wpa_supplicant` ベースのプロセスが担当し、`macsecmgr` が `CONFIG_DB` と仲介します。
- Data plane: SAI MACsec object（SC、SA、フィルタ）と、ASIC または Gearbox PHY 上の暗号エンジン。

全体設計と既存ページの呼び出し方は [MACsec HLD](../../switching/macsec-sonic-high-level-design-document.md) に集約されています。[CONFIG_DB](../../reference/glossary.md#term-config_db) から SAI までのデータフロー、cipher suite、replay protection の取り扱いはこの [HLD](../../reference/glossary.md#term-hld) を起点に読み進めます。

```mermaid
flowchart LR
  CFG[(CONFIG_DB MACSEC_*)] --> MGR[macsecmgr]
  MGR --> MKA[wpa_supplicant MKA]
  MGR --> ORCH[macsecorch]
  ORCH --> SAI[(SAI MACsec object)]
  SAI --> ASIC[ASIC or Gearbox PHY]
  MKA -. SAK install .-> ORCH
```

## Gearbox port での backend 選択

[NPU](../../reference/glossary.md#term-npu) 側と Gearbox PHY 側のどちらに MACsec engine を寄せるかは、プラットフォームごとに異なります。SONiC は両方を抽象化するため、決定的に backend を選ぶ仕組みが [deterministic MACsec backend selection for gearbox ports HLD](../../switching/sonic-hld-deterministic-macsec-backend-selection-for-gearbox-ports.md) で導入されています。設定の意図が「NPU で暗号する」「PHY で暗号する」のどちらなのかが、運用時の counter 配置や trouble shooting の起点を決めます。

## SAI POST

起動時に MACsec engine が正しく動作するかを確認する Power-On Self Test は、[SAI POST support for MACsec](../../switching/sonic-sai-post-support-for-macsec.md) で扱われます。MACsec を有効化したリンクで「鍵は配布されたのに通信が落ちる」という症状を切り分ける際、SAI POST の結果は最初に当たる材料です。本機能はプラットフォーム実装依存が大きいため、ベンダーの SAI ドライバ側のサポート状況を必ず確認します。

## control plane との接続点

MACsec の有効化は AAA や SSH のような login 系ポリシーとは独立に運用しますが、鍵のローテーションや障害時の bypass ポリシーは管理面 [ACL](../../reference/glossary.md#term-acl) や [CoPP](../../reference/glossary.md#term-copp) の設計と組み合わせて考えるべきです。CoPP の枠組みは [ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md) を参照してください。

platform 側の信頼チェーン（OpenSSL FIPS、secure boot、secure upgrade）は [発展トピック](advanced.md) で扱います。

## データフロー（AAA / management security 側）

MACsec 以外の AAA（TACACS+ / [RADIUS](../../reference/glossary.md#term-radius) / PAM / NSS / SSH）の制御パスも合わせて整理します。

```mermaid
flowchart LR
  CFG[("CONFIG_DB<br/>TACPLUS/RADIUS/AAA/MGMT_USER")] --> HOSTCFGD[hostcfgd]
  HOSTCFGD --> PAM["/etc/pam.d/*"]
  HOSTCFGD --> NSS["/etc/nsswitch.conf"]
  HOSTCFGD --> SSHD["/etc/ssh/sshd_config"]
  HOSTCFGD --> TACPLUS["/etc/tacplus_nss.conf"]
  USER[login] --> PAM
  PAM --> NSS
  NSS --> SERVER["TACACS+ / RADIUS server"]
```

`hostcfgd` (`src/sonic-host-services/scripts/hostcfgd`) が CONFIG_DB の `TACPLUS`、`RADIUS`、`AAA`、`MGMT_USER` を読み、PAM / NSS / sshd_config を render する Jinja template を持ちます。

## 主要 daemon / コンポーネントの責務

| コンポーネント | 主実体 | 責務 |
| --- | --- | --- |
| `macsecmgr` (`cfgmgr/macsecmgr.cpp`) | `MACsecMgr::doTask` | CONFIG_DB の MACSEC_PROFILE / MACSEC_INTERFACE を読み、wpa_supplicant config を生成 |
| `MACsecOrch` (`orchagent/macsecorch.cpp`) | `MACsecOrch::doTask` | [APPL_DB](../../reference/glossary.md#term-appl_db) から SAI MACsec object に展開 |
| `wpa_supplicant` (MKA mode) | open source wpa_supplicant | MKA peer 探索、SAK 生成・配布 |
| `hostcfgd` | python | AAA / SSH / SYSLOG 系の host 設定 render |
| `mgmt-framework` | [YANG](../../reference/glossary.md#term-yang) / REST | management plane 認証統合 |

## SAI 属性使用一覧（MACsec）

| object | 属性 |
| --- | --- |
| `SAI_OBJECT_TYPE_MACSEC` | `SAI_MACSEC_ATTR_DIRECTION = INGRESS/EGRESS` |
| `SAI_OBJECT_TYPE_MACSEC_PORT` | `SAI_MACSEC_PORT_ATTR_PORT_ID`、`SWITCH_SWITCHING_MODE` |
| `SAI_OBJECT_TYPE_MACSEC_FLOW` | `SAI_MACSEC_FLOW_ATTR_MACSEC_DIRECTION` |
| `SAI_OBJECT_TYPE_MACSEC_SC` | `SAI_MACSEC_SC_ATTR_MACSEC_SCI`、`AN`、`CIPHER_SUITE`、`ENCRYPTION_ENABLE`、`REPLAY_PROTECTION_ENABLE`、`REPLAY_PROTECTION_WINDOW` |
| `SAI_OBJECT_TYPE_MACSEC_SA` | `SAI_MACSEC_SA_ATTR_SAK`、`SALT`、`AUTH_KEY`、`MACSEC_SSCI`、`CONFIGURED_EGRESS_XPN`、`MINIMUM_INGRESS_XPN` |
| `SAI_OBJECT_TYPE_PORT_SERDES` | MACsec 有効時の SI（Gearbox backend） |

`SAI_MACSEC_SA_ATTR_SAK` の wrap は SAK distribution の最終段で SAI に渡される。鍵生成は wpa_supplicant 側。

## Redis テーブル参照関係

```yaml
CONFIG_DB:
  MACSEC_PROFILE, MACSEC_INTERFACE,
  TACPLUS, TACPLUS_SERVER, RADIUS, RADIUS_SERVER,
  AAA, MGMT_USER, USER_LIST,
  PASSWD_HARDENING
APPL_DB:
  MACSEC_INGRESS_SA_TABLE, MACSEC_EGRESS_SA_TABLE,
  MACSEC_INGRESS_SC_TABLE, MACSEC_EGRESS_SC_TABLE, MACSEC_PORT_TABLE
STATE_DB:
  MACSEC_INGRESS_SA_TABLE, MACSEC_EGRESS_SA_TABLE (運用状態)
COUNTERS_DB:
  COUNTERS:<macsec-sc-oid>, COUNTERS:<macsec-flow-oid>
ASIC_DB:
  MACSEC, MACSEC_PORT, MACSEC_FLOW, MACSEC_SC, MACSEC_SA
```

## ZMQ / Redis pub/sub

- ZMQ は使わない。
- `wpa_supplicant` と `macsecmgr` は Unix socket（wpa_ctrl）で通信。[Redis](../../reference/glossary.md#term-redis) 経由ではない。
- AAA 認証（PAM → TACACS+/RADIUS）は同期 RPC で、Redis を経由しない。

## 既知の実装上の制約

- MACsec SAK の rekey 頻度（key lifetime）は wpa_supplicant の設定で、頻度を上げすぎると ASIC 側で `SA install` が間に合わず短時間 drop が発生する。
- `MACSEC_SA_ATTR_SAK` の wrap キーは平文で SAI まで渡る設計のため、[syncd](../../reference/glossary.md#term-syncd) / SAI のメモリ保護が信頼境界。コア dump に鍵が出るリスクは HLD 範囲。
- Gearbox backend 選択は装置依存で、deterministic 選択 HLD があっても全ベンダ実装が揃っているとは限らない。
- SAI POST は MACsec engine の起動確認のみで、運用中の rekey 失敗や cipher suite mismatch は捕捉しない。
- TACACS+ の `command` authorization は host CLI 経由のみで、`gnmi` / REST API 経路では別途 RBAC 設定が必要。
- FIPS モードは OpenSSL の library 切替に依存し、libssl のバージョン整合と FIPS module の有無で「FIPS にしたつもりが効いていない」事故が起きやすい。

## AAA の認証フロー詳細

SONiC の AAA は **PAM + NSS** を起点に、TACACS+ / RADIUS / LDAP / local を順序通り問い合わせます。

```mermaid
flowchart LR
  USER["ssh / CLI login"] --> SSHD["sshd / login"]
  SSHD --> PAM[PAM]
  PAM --> AAACTL["hostcfgd 生成<br/>/etc/pam.d/* + /etc/nsswitch.conf"]
  PAM -->|primary| TACACS[libpam-tacplus]
  PAM -->|fallback| LOCAL["/etc/shadow"]
  TACACS -->|fail| RADIUS[libpam-radius-auth]
  TACACS -->|authz| TACAUTHZ[command authorization]
  TACAUTHZ --> AUDIT[("STATE_DB / journald")]
```

順序と authz policy は `CONFIG_DB:AAA` テーブルから `hostcfgd` が `/etc/pam.d/common-auth-sonic` 等を render することで反映されます。`gnmi` や REST API の認証は PAM を経由しない別経路（gNSI authz、token-based）であり、TACACS+ の `command` authorization は host CLI のみに効きます。

<!-- glossary-links-injected: ae6c3c279b05 -->
