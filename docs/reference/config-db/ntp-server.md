---
title: NTP_SERVER テーブル
description: "NTP_SERVER テーブル — 上流 NTP サーバまたは pool を保持する。hostcfgd の NtpHandler が /etc/chrony/chrony.conf（または ntp.conf）を再生成し、サービスを再起動する。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-ntp.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - NTP_SERVER
    - NTP_KEY
    - NTP
    - VRF
    - MGMT_VRF_CONFIG
  cli:
    - config ntp
  yang:
    - sonic-ntp
---

# NTP_SERVER テーブル

## 概要

上流 NTP サーバまたは pool を保持する[^1]。`hostcfgd` の `NtpHandler` が `/etc/chrony/chrony.conf`（または `ntp.conf`）を再生成し、サービスを再起動する。`max-elements 10` でサーバ数上限がある。`NTP_KEY` で対称鍵を、`NTP|global` で client 全体設定を保持する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>NTP_SERVER")]
  DM["ntp-config"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
NTP_SERVER|<server_address>
```

`<server_address>` は IP address または DNS hostname。

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `server_address` (key) | `inet:host` | ✅ | - | サーバアドレス |
| `association_type` | enum `server`/`pool` | - | `server` | server 単体 / pool 群 |
| `iburst` | `on-off` | - | `on` | iburst aggressive polling |
| `key` | leafref `NTP_KEY.id` | - | - | 認証鍵 ID |
| `resolve_as` | `inet:host` | - | - | 名前解決された IP |
| `admin_state` | `admin_mode` | - | `enabled` | サーバの有効化 |
| `trusted` | `yes-no` | - | `no` | 認証時にこのサーバのみで時刻同期する |
| `version` | uint8 (3..4) | - | `4` | NTP プロトコルバージョン |

## 関連サブテーブル

- `NTP|global` (container, single-instance):
    - `src_intf` (leaf-list): 送信元 IF（PORT / PORTCHANNEL / LOOPBACK / MGMT_PORT / `eth0` の union）
    - `vrf` (`mgmt`/`default`): NTP を有効化する VRF。`mgmt` 指定には `MGMT_VRF_CONFIG.mgmtVrfEnabled = true` 必須 (`must`)
    - `authentication` (`admin_mode`、default `disabled`)
    - `dhcp` (`admin_mode`、default `enabled`)
    - `server_role` (`admin_mode`、default `enabled`)
    - `admin_state` (`admin_mode`、default `enabled`)
- `NTP_KEY|<id>` (key: id, 1..65535):
    - `trusted` (yes-no, default `no`)
    - `value` (string 1..64, encrypted)
    - `type` (enum md5/sha1/sha256/sha384/sha512, default md5)

## 購読者

- `hostcfgd` `NtpHandler`: chrony / ntp 設定の更新

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `NTP`、`NTP_KEY`、`VRF`、`MGMT_VRF_CONFIG`、`PORT`、`LOOPBACK_INTERFACE`、`MGMT_PORT`
- 関連 CLI: `config ntp add/del`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-ntp`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-ntp`](../yang/sonic-ntp.md)
- CLI: [`config ntp`](../cli/config-ntp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-ntp.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-ntp.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: NAT / DHCP Relay / Time-DNS Services](../../topics/16-nat-dhcp-dns/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `NTP_SERVER|<ip-or-hostname>`。
- `iburst`: `on`（初期同期高速化）。
- `association_type`: `server`。

### よくある誤設定

- 1 つだけサーバ登録すると障害時に時刻が drift。3 つ以上推奨。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'NTP_SERVER|*'
show ntp
chronyc sources
```
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang NTP_SERVER container -->

- **NTP_SERVER エントリは最大 10 件 → YANG が制限**: `max-elements 10`。11 件目以降は YANG バリデーションで拒否される。
- **server_address が不正形式 → YANG が拒否**: `type inet:host`。ホスト名または IP アドレス (IPv4/IPv6) のみ許可。
- **version が 3-4 以外 → YANG が拒否 (デフォルト 4)**: `range "3..4"` / `error-message "Failed NTP version"` / `default 4`。NTPv1・v2 は明示的に禁止されている。
- **association_type のデフォルト = "server"**: `default server`。NTP プール (pool) を使用する場合は明示的に `association_type = pool` を設定する必要がある。
- **iburst のデフォルト = "on"**: `default on`。起動直後に iburst パケットを送信して同期を高速化。無効化は明示的に `iburst = off` を設定する。
- **key が存在しない ID を参照 → YANG leafref 違反**: `leaf key` は `leafref` で `NTP_KEY_LIST/id` を参照。存在しない key ID を指定すると YANG バリデーションで拒否される。
- **admin_state のデフォルト = "enabled"**: `default enabled`。フィールドを省略してもサーバは有効として ntpd/chrony に渡される。
- **trusted のデフォルト = "no"**: `default no`。NTP 認証有効時にこのサーバのみを信頼する場合は `trusted = yes` を設定する。

<!-- value-behavior -->
## 値依存挙動マトリクス

<!-- evidence: sonic-host-services/scripts/hostcfgd ntp_srv_key_update() / sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang -->

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `association_type` | `server` (default) | chrony.conf に `server <addr>` として追記 |
| `association_type` | `pool` | chrony.conf に `pool <addr>` として追記。DNS ラウンドロビンで複数 IP を使用 |
| `iburst` | `on` (default) | 起動直後に iburst パケットを送信して高速同期 |
| `iburst` | `off` | 通常ポーリング間隔で同期開始 |
| `admin_state` | `enabled` (default) | サーバを chrony.conf に含める |
| `admin_state` | `disabled` | サーバを chrony.conf から除外 |
| `trusted` | `no` (default) | chrony で通常の優先度 |
| `trusted` | `yes` | chrony の `prefer` オプション相当。当該サーバを優先同期先に |
| `version` | `4` (default) | NTPv4 を使用 |
| `version` | `3` | NTPv3 を使用。古い NTP サーバとの互換向け |
| `key` | NTP_KEY.id 参照 | chrony.conf に `key <id>` オプションを付与。`NTP.authentication=enabled` と組み合わせて認証 |
| エントリ数 | 11件目以上 | YANG max-elements=10 でバリデーション拒否 |

enum: `association_type`=server/pool、`iburst`=on/off、`admin_state`=enabled/disabled、`trusted`=yes/no。変更は `systemctl restart chrony` をトリガー。
<!-- /value-behavior -->


<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **hostcfgd**: `NTP_SERVER` テーブルを `ConfigDBConnector` で購読。

### 段階 2: CFG → APPL 翻訳

- hostcfgd の `ntpHandler` が `ntp.conf` の `server` ディレクティブを更新し ntpd 再起動。
- APP_DB への書き込みなし。

### 段階 3: APPL → SAI

- SAI 経由なし。ntpd が指定サーバへ UDP 123 番で到達可能であることが前提。

### 段階 4: タイミング + 副作用

- サーバ変更後 ntpd 再起動まで数秒。新サーバとの初期同期に数分かかる場合あり。
- 副作用: mgmt VRF を使用する場合は `ip vrf exec mgmt ntpq` で状態確認が必要。

<!-- /runtime-trace -->

<!-- glossary-links-injected: b5626ca1f0f9 -->
