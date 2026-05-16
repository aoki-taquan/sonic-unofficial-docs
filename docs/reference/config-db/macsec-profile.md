---
title: MACSEC_PROFILE テーブル
description: "MACSEC_PROFILE テーブル — IEEE 802.1AE MACsec のセキュリティプロファイルを定義するテーブル。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-macsec.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MACSEC_PROFILE
    - PORT
  yang:
    - sonic-macsec
  _no_related_cli: true
---

# MACSEC_PROFILE テーブル

## 概要

IEEE 802.1AE MACsec のセキュリティプロファイルを定義するテーブル[^1]。
`PORT.macsec` (port 側の leaf) から名前参照され、`macsecmgrd` / `wpa_supplicant` ベースの MKA (MACsec Key Agreement) 実装が CAK/CKN を読んで MACsec SA を確立する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>MACSEC_PROFILE")]
  DM["macsecmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_DB")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_macsec_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
MACSEC_PROFILE|<name>
```

`<name>`: 1–128 文字。

## フィールド

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `priority` | uint8 | `255` | MKA アクター優先度。**小さいほど key server になりやすい** |
| `cipher_suite` | enum `GCM-AES-128` / `GCM-AES-256` / `GCM-AES-XPN-128` / `GCM-AES-XPN-256` | `GCM-AES-128` | データ暗号化アルゴリズム |
| `primary_cak` | hex 66 文字 (128-bit + KCK) または 130 文字 (256-bit) | — (mandatory) | プライマリ CAK |
| `primary_ckn` | hex 32 / 64 文字 | — (mandatory) | プライマリ CKN |
| `fallback_cak` | hex 66 / 130 文字 | — | プライマリ失敗時のフォールバック CAK |
| `fallback_ckn` | hex 32 / 64 文字 | — | フォールバック CKN |
| `policy` | `integrity_only` / `security` | `security` | 認証のみか暗号化込みか |
| `enable_replay_protect` | boolean | `false` | リプレイ保護の有効化 |
| `replay_window` | uint32 | — | `enable_replay_protect = true` 時のみ意味を持つ |
| `send_sci` | boolean | `true` | 送信フレームに SCI を含める |
| `rekey_period` | uint32 | `0` | 能動的 SAK 再生成周期 [秒]。0 で再生成しない |

## 制約 (YANG `must`)

- `fallback_cak` を設定する場合は `primary_cak` と同じ長さ
- `fallback_ckn != primary_ckn`

## 購読者

- `macsecmgrd` (`sonic-swss` の MacSecMgr)、`macsecorch`
- 配下で `wpa_supplicant` が MKA セッションを実行

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `PORT` (`macsec` フィールドでプロファイル名参照)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-macsec`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-macsec`](../yang/sonic-macsec.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-macsec.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-macsec.yang>

## 関連ページ
- [CONFIG_DB: PORT](port.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `MACSEC_PROFILE|<profile-name>`。
- `cipher_suite`: `GCM-AES-XPN-256`、`priority`: 64、`policy`: `security`、`rekey_period`: `0`（手動）。

### よくある誤設定

- 鍵 (`primary_cak`/`fallback_cak`) を 16/32B 以外で入れると MKA セッションが上がらない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'MACSEC_PROFILE|*'
show macsec
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `policy`

| 値 | 挙動 |
|----|------|
| `security`（デフォルト） | MKA SA 確立 + データ暗号化 |
| `integrity_only` | MKA SA 確立のみ。実データは平文（認証のみ） |
| その他 | `throw std::invalid_argument("Invalid policy : ...")` → `task_invalid_entry`（破棄） |

### `cipher_suite`（CAK 長と連動）

| 値 | CAK 長 | 挙動 |
|----|--------|------|
| `GCM-AES-128`（デフォルト） | 66 hex 文字 | 128-bit AES 暗号化 |
| `GCM-AES-256` | 130 hex 文字 | 256-bit AES 暗号化 |
| `GCM-AES-XPN-128` | 66 hex 文字 | Extended Packet Numbering 付き 128-bit AES |
| `GCM-AES-XPN-256` | 130 hex 文字 | Extended Packet Numbering 付き 256-bit AES |
| CAK 長不一致 | — | `throw std::invalid_argument("Invalid length for cipher_string : ...")` → `task_invalid_entry` |
| その他 | — | `throw std::invalid_argument("Invalid cipher_suite : ...")` → `task_invalid_entry` |

### `rekey_period`

| 値 | 挙動 |
|----|------|
| `0`（デフォルト） | 能動的 SAK 再生成なし（MKA 自然な鍵更新のみ） |
| 正値 | 指定秒数ごとに SAK を再生成（`mka_rekey_period` として `wpa_supplicant` に設定） |

### `enable_replay_protect`

| 値 | 挙動 |
|----|------|
| `false`（デフォルト） | リプレイ保護なし（`macsec_replay_protect = 0`） |
| `true` | リプレイ保護有効。`replay_window` の値も `wpa_supplicant` に渡す（`macsec_replay_window = N`） |

### `send_sci`

| 値 | 挙動 |
|----|------|
| `true`（デフォルト） | 送信フレームに SCI を含める |
| `false` | SCI を含めない（特定機器との相互接続で必要な場合がある） |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-swss/cfgmgr/macsecmgr.cpp -->

| 条件 | 挙動 |
|------|------|
| `policy` に不正値 | `throw std::invalid_argument("Invalid policy : ...")` → `SWSS_LOG_WARN` → `task_invalid_entry`（破棄・再試行なし） |
| `cipher_suite` に不正値または CAK 長不正 | `throw std::invalid_argument("Invalid length for cipher_string : ...")` → task_invalid_entry |
| `fallback_cak` 設定時に `fallback_ckn` なし | `GetValue(ta, fallback_ckn)` が false → フォールバックキー設定スキップ。MKA フォールバック機能が動作しない |
| `wpa_supplicant` 起動失敗 | `SWSS_LOG_WARN("Cannot start the wpa_supplicant of the port '%s' : %s")` → MACsec 無効のままポート継続動作 |
| フィールド値の型変換失敗 | `SWSS_LOG_ERROR("Cannot convert value(%s) in field(%s)")` → デフォルト / 前回値を使用 |
| MACsec 有効化で例外発生 | `SWSS_LOG_WARN("Enable MACsec fail : %s")` → ポートは非暗号化のまま継続 |
| MACsec 無効化失敗 | `SWSS_LOG_WARN("Disable MACsec fail : %s")` → wpa_supplicant プロセスが残留する可能性 |

<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`macsecmgrd` → `MACsecOrch` (APPL_DB 経由) が CONFIG_DB の `MACSEC_PROFILE` テーブルを購読する。

`MACSEC_PROFILE` の key はプロファイル名。`primary_cak` / `fallback_cak` / `cipher_suite` 等のキー情報を保持。

### 段階 2 — CFG→APPL 翻訳

`APP_MACSEC_TABLE` / `APP_MACSEC_PORT_TABLE` 等に書き込み

### 段階 3 — APPL→SAI

`sai_macsec_api` — MACsec セキュリティアソシエーション (SC/SA) を作成/更新

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `macsecmgrd` が検知後 APPL_DB に書き込み。`MACsecOrch` が SAI MACsec オブジェクトを作成/更新。キーロールオーバーは非同期。

**副作用**: MACsec プロファイル変更は該当ポートの MACsec セキュリティアソシエーションを再生成。切り替え中に brief traffic interrupt が発生する可能性がある。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `MACSEC_PROFILE`

### CLI
- `config macsec profile add/del <name> --priority <n> --cipher_suite <suite> --primary_cak <key> --primary_ckn <ckn>`
  - ソース: `sonic-utilities/config/main.py (macsec グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
<!-- /entry-points -->

<!-- side-effects -->
## 副次 DB 書込 (Direction B — orch / mgr が書く先)

> ソース: `sonic-swss/orchagent/macsecorch.cpp`, `sonic-swss/cfgmgr/macsecmgr.cpp`

### STATE_DB

`MACSEC_PROFILE` を読んだ `macsecmgrd` → `MACsecOrch` が以下のテーブルへ書き込む。

| テーブル | キー形式 | 書込フィールド | タイミング |
|----------|----------|----------------|------------|
| `STATE_MACSEC_PORT_TABLE` (`MACSEC_PORT_TABLE`) | `<port_name>` | `max_sa_per_sc`, `state=ok` | `MACsecOrch::createMACsecPort()` 成功時 |
| `STATE_MACSEC_EGRESS_SC_TABLE` | `<port_name>\|<SCI>` | `state=ok` | `MACsecOrch::createMACsecSC()` で egress SC 確立時 |
| `STATE_MACSEC_INGRESS_SC_TABLE` | `<port_name>\|<SCI>` | `state=ok` | `MACsecOrch::createMACsecSC()` で ingress SC 確立時 |
| `STATE_MACSEC_EGRESS_SA_TABLE` | `<port_name>\|<SCI>\|<AN>` | `state=ok` | `MACsecOrch::createMACsecSA()` で egress SA 確立時 |
| `STATE_MACSEC_INGRESS_SA_TABLE` | `<port_name>\|<SCI>\|<AN>` | `state=ok` | `MACsecOrch::createMACsecSA()` で ingress SA 確立時 |

削除は `del()` で対応 — ポート/SC/SA 削除時に各テーブルのエントリを消去する。

### ASIC_DB（SAI 経由）

`macsecorch.cpp` が `sai_macsec_api` を呼び出し、syncd 経由で ASIC_DB に反映される。

| SAI API 呼び出し | 主な属性 | タイミング |
|-----------------|----------|------------|
| `sai_macsec_api->create_macsec()` | `SAI_MACSEC_ATTR_DIRECTION`, `SAI_MACSEC_ATTR_PHYSICAL_BYPASS_ENABLE` | MACsec グローバルオブジェクト初回作成 |
| `sai_macsec_api->create_macsec_port()` | ポート OID, 方向 | MACsecOrch がポートを有効化するとき |
| `sai_macsec_api->create_macsec_sc()` | SC OID, SCI, 方向, 暗号スイート | SC 確立時 |
| `sai_macsec_api->create_macsec_sa()` | `SAI_MACSEC_SA_ATTR_AN`, `SAI_MACSEC_SA_ATTR_SAK`, `SAI_MACSEC_SA_ATTR_SALT`, `SAI_MACSEC_SA_ATTR_AUTH_KEY`, `SAI_MACSEC_SA_ATTR_CONFIGURED_EGRESS_XPN` / `SAI_MACSEC_SA_ATTR_MINIMUM_INGRESS_XPN` | MKA が SA を合意したとき (APP_DB 経由) |
| `sai_macsec_api->remove_macsec_sa()` | SA OID | SA 削除/ロールオーバー時 |
| `sai_macsec_api->set_macsec_sa_attribute()` | `SAI_MACSEC_SA_ATTR_CONFIGURED_EGRESS_XPN` / `SAI_MACSEC_SA_ATTR_MINIMUM_INGRESS_XPN` (XPN 更新) | XPN 再生成が要求されたとき |

### wpa_supplicant 設定書込

`macsecmgrd` が `wpa_cli set_network` コマンドで wpa_supplicant プロセスに MKA パラメータを渡す。書込先はプロセス内ランタイム状態（ファイルではなくソケット経由）。

| wpa_supplicant フィールド | 対応 CONFIG_DB フィールド | 備考 |
|--------------------------|--------------------------|------|
| `macsec_policy` | — | 常に `1` (MACsec 有効) |
| `macsec_integ_only` | `policy` | `integrity_only` → 1, `security` → 0 |
| `mka_cak` | `primary_cak` | CAK を暗号スイートに応じてデコードして渡す |
| `mka_ckn` | `primary_ckn` | そのまま渡す |
| `mka_priority` | `priority` | MKA アクター優先度 |
| `mka_rekey_period` | `rekey_period` | `rekey_period > 0` の場合のみ設定 |
| `macsec_ciphersuite` | `cipher_suite` | GCM-AES-128 / 256 / XPN-128 / XPN-256 |
| `macsec_include_sci` | `send_sci` | `true` → 1, `false` → 0 |
| `macsec_replay_protect` | `enable_replay_protect` | `true` → 1, `false` → 0 |
| `macsec_replay_window` | `replay_window` | `enable_replay_protect=true` の場合のみ設定 |

設定後 `enable_network` を呼び出して MKA セッションを開始する。失敗時は `SWSS_LOG_WARN("Enable MACsec fail : %s")` を記録しポートは非暗号化状態のまま継続する。
<!-- /side-effects -->

<!-- glossary-links-injected: b5626ca1f0f9 -->
