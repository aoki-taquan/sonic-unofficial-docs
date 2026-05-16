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
  - repo: sonic-net/sonic-swss
    path: orchagent/macsecorch.cpp
    ref: master
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

<!-- platform -->
## プラットフォーム差異

### Gearbox PHY 搭載ポート vs. NPU ネイティブポート

MACsec の SAI オブジェクト操作対象は、ポートに Gearbox PHY が接続されているかどうかで切り替わる。

| 条件 | MACsec オブジェクト対象 | カウンタ管理 |
|------|------------------------|-------------|
| `gearbox_phy_t.macsec_supported == true` | PHY 側の line-side port (`port.m_line_side_id`) と PHY の switch ID を使用 | `m_gb_macsec_sa_stat_manager` / `m_gb_macsec_flow_stat_manager` / `m_gb_macsec_counters_map` |
| PHY なし、または `macsec_supported == false` | NPU 側の port (`port.m_port_id`) とグローバル switch ID (`gSwitchId`) を使用 | `m_macsec_sa_stat_manager` / `m_macsec_flow_stat_manager` / `m_macsec_counters_map` |

PHY が接続されていても `macsec_supported` が `false` の場合、`MACsecOrch` は NPU 側へフォールバックし、ログに `"backend=NPU (phy marked unsupported)"` を出力する。

**コード証跡** (`macsecorch.cpp:363, 409, 2539, 2547, 2555, 2563`):
```cpp
force_npu = !phy->macsec_supported;
if (!force_npu && port->m_line_side_id != SAI_NULL_OBJECT_ID)
    m_port_id = port->m_line_side_id;  // PHY 側を使用
else
    m_port_id = port->m_port_id;       // NPU 側へフォールバック
```

### SAI MACsec capability クエリ

初期化時に以下の SAI ケーパビリティを実行時にクエリし、ASIC ベンダーの実装状態に応じて動作を変える。

| SAI ケーパビリティ | 用途 | 非対応時の挙動 |
|-------------------|------|--------------|
| `SAI_ACL_TABLE_ATTR_FIELD_MACSEC_SCI` の `create_implemented` | ACL テーブルで SCI フィールドのマッチを使うかどうか | `saiAclFieldSciMatchSupported = false` にして SCI ACL マッチを無効化 |
| `SAI_MACSEC_ATTR_SCI_IN_INGRESS_MACSEC_ACL` | Ingress ACL で SCI をキーとするか、Flow ごとに複数 ACL エントリを使うかを判定 | get 失敗時は `task_failed` を返しポート有効化を中断 |
| `SAI_MACSEC_ATTR_MAX_SECURE_ASSOCIATIONS_PER_SC` | SC ごとの最大 SA 数 (2 or 4) | サポートなし時はデフォルト `4` を使用 |

**コード証跡** (`macsecorch.cpp:672–681, 1302–1345`):
```cpp
// ACL SCI フィールドサポート確認
sai_query_attribute_capability(..., SAI_ACL_TABLE_ATTR_FIELD_MACSEC_SCI, &capability);
if (capability.create_implemented == false)
    saiAclFieldSciMatchSupported = false;

// SA per SC 数のクエリ (非対応時デフォルト 4)
attr.id = SAI_MACSEC_ATTR_MAX_SECURE_ASSOCIATIONS_PER_SC;
status = sai_macsec_api->get_macsec_attribute(...);
if (status != SAI_STATUS_SUCCESS)
    m_max_sa_per_sc = 4;  // デフォルトにフォールバック
```

### POST (Power-On Self-Test) 対応差異

`SAI_MACSEC_ATTR_ENABLE_POST` / `SAI_SWITCH_ATTR_MACSEC_POST_STATUS` は ASIC ベンダー依存の POST 機能。

| POST 状態 | `STATE_DB.MACSEC_POST_STATUS` 値 | 動作 |
|-----------|----------------------------------|------|
| `switch-level-post-in-progress` | ASIC 全体レベルで POST が進行中。Switch 初期化時に有効化済み | `SAI_SWITCH_ATTR_MACSEC_POST_STATUS` をポーリングして pass/fail を記録 |
| `macsec-level-post-in-progress` | MACsec オブジェクト初期化時に POST を有効化する方式 | `SAI_MACSEC_ATTR_ENABLE_POST = true` を egress/ingress オブジェクト作成時に付与 |
| 上記以外 | POST 非対応 ASIC | POST 通知サブスクリプションを設定しない |

POST 未対応 ASIC (SAI が本属性を実装しない環境) では `m_enable_post = false` のままとなり、MACsec オブジェクト初期化時の `SAI_MACSEC_ATTR_ENABLE_POST` 設定がスキップされる。

**コード証跡** (`macsecorch.cpp:695–728, 1246–1251, 1278–1283`):
```cpp
if (m_enable_post) {
    attr.id = SAI_MACSEC_ATTR_ENABLE_POST;
    attr.value.booldata = true;
    attrs.push_back(attr);
}
```

### Physical Bypass モード

egress / ingress 両方の MACsec オブジェクト作成時に `SAI_MACSEC_ATTR_PHYSICAL_BYPASS_ENABLE = true` を設定する。これは ASIC が MACsec をバイパスする初期状態を確保するためであり、MKA ネゴシエーション完了後に SA が確立されてから暗号化が有効になる流れを保証する。

**コード証跡** (`macsecorch.cpp:1242–1244, 1274–1276`):
```cpp
attr.id = SAI_MACSEC_ATTR_PHYSICAL_BYPASS_ENABLE;
attr.value.booldata = true;
```

### 非対応 / スコープ外

- ベンダー固有 ASIC ドライバの内部実装差（SAI 抽象化で隠蔽）
- ベンダー版 SONiC（NVIDIA Cumulus / Edgecore ECNOS 等）はスコープ外
- master ブランチ以外のバックポート差異はスコープ外
<!-- /platform -->

<!-- glossary-links-injected: b5626ca1f0f9 -->
