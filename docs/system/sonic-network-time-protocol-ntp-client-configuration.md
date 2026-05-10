---
title: SONiC NTP client（chrony / NTP_SERVER / mgmt VRF）
area: system
verification: discrepancy-found
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/ntp/ntp-design.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - NTP
    - NTP_SERVER
    - NTP_KEY
    - MGMT_VRF_CONFIG
  cli:
    - config ntp
    - show ntp
  yang:
    - sonic-ntp
---

!!! warning "裏取りステータス: discrepancy-found"
    本 HLD は `ntpd` 時代の設計。SONiC は近年 `chrony` への移行が完了している。

!!! note "Verifier 注記（2026-05-10）"
    実コード裏取り: 現行 master では **chrony が採用されている**。`sonic-buildimage/files/image_config/chrony/` に `chrony.conf.j2` / `chrony.keys.j2` / `chronyd-starter.sh` が存在し、`sonic-config-engine/tests/sample_output/` でも chrony.conf が生成テスト対象になっている。yang は `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` に `NTP / NTP_SERVER / NTP_KEY` を確認。本 HLD（`doc/ntp/ntp-design.md`）の `ntpd` / `/etc/ntp.conf` ベース記述は **歴史的設計**として読むべきで、運用コンフィグは chrony に置き換わっている。

# SONiC NTP client（chrony / NTP_SERVER / mgmt VRF）

## 概要

SONiC のシステム時刻は外部 NTP サーバから同期する[^1]。本 HLD は CONFIG_DB の **`NTP` / `NTP_SERVER` / `NTP_KEY`** を真実源として、`hostcfgd` が `/etc/ntp.conf` (or `/etc/chrony/chrony.conf`) を rendering する設計を扱う。

主要な観点:

- **server リスト**: `iburst` / `prefer` / 認証鍵参照
- **mgmt VRF / data VRF**: NTP のクエリは大抵 mgmt VRF。`MGMT_VRF_CONFIG` の `ntp_enabled` が連動
- **認証**: NTP shared key（symmetric MD5/SHA）または NTS（chrony）
- **source IP / interface**: VRF / loopback の選択

## 動作仕様

```mermaid
flowchart LR
    CFG[CONFIG_DB\nNTP / NTP_SERVER / NTP_KEY / MGMT_VRF_CONFIG] --> HC[hostcfgd]
    HC --> CONF[/etc/ntp.conf or\n/etc/chrony/chrony.conf]
    HC --> SVC[ntp / chronyd service]
    SVC --> SRV[(NTP servers)]
    SVC --> CLOCK[Linux system clock]
    CLOCK --> APP[全 SONiC service\n(syslog / counters / cert valid 等)]
```

`hostcfgd` は CONFIG_DB の変化に追従して config を再生成し、サービスを reload する。

### 関連 CONFIG_DB

| Table | 説明 |
|-------|------|
| `NTP|global` | source-interface、source IP、enable、authentication 有効化 |
| `NTP_SERVER|<address>` | iburst / prefer / key id |
| `NTP_KEY|<id>` | 鍵（種別、key value） |
| `MGMT_VRF_CONFIG` | `ntp_enabled` の判定 |

### 関連 CLI

| Command | 用途 |
|---------|------|
| `config ntp add <server>` | server 追加 |
| `config ntp del <server>` | 削除 |
| `config ntp source-interface <if>` | 送信元 interface |
| `show ntp` | 同期状態 |

### 設定例

```bash
config ntp add 192.0.2.10
config ntp add 198.51.100.4
config ntp source-interface Loopback0
show ntp
```

## 制限事項

- **mgmt VRF と data VRF の混在**: 同時に両方から NTP を引きたい場合は対応 daemon の機能差に注意
- **TLS / NTS**: ntpd は素の NTP / shared-key、chrony は NTS 対応。HLD と現行実装の差で利用できる機構が変わる
- **時刻ジャンプ**: 起動直後・大幅ずれ時のステップ調整は他 service（cert 検証・log timestamp）に副作用
- **systemd-timesyncd**: SONiC では使わない方針

## 干渉する機能

- **migration-to-chrony**: chrony 移行 HLD（同 area）。本ページの ntpd 表現と差分が出る部分
- **MGMT_VRF**: NTP query の経路を決める
- **secure-boot / cert**: 証明書有効期間判定が時刻に依存
- **logging / TWAMP / sFlow**: タイムスタンプ精度が下流機能の品質に直結

## トラブルシューティング

- `show ntp` が unsynchronized → server 到達性、VRF、firewall、ntp daemon の動作確認
- 時刻が大きくずれる → 起動直後のステップ調整有無、`tinker step` 等の設定
- 認証エラー → key id と鍵値が一致しているか、daemon 種別による hash アルゴリズム差

## 引用元

[^1]: `sonic-net/SONiC` `doc/ntp/ntp-design.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- 現行 master の NTP daemon（ntpd vs chrony）の選定状況確認
- hostcfgd の NTP config rendering 経路（jinja テンプレート）の現行実装確認
- CONFIG_DB NTP / NTP_SERVER / NTP_KEY スキーマと sonic-yang-models 取り込み確認
- config ntp / show ntp CLI の sonic-utilities 取り込み確認
- mgmt VRF と data VRF 経路の同時利用が現行実装でどう扱われているか確認
- chrony 移行 HLD と本 HLD の重複・置換関係の現行整理状況
-->
