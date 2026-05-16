---
title: KDUMP テーブル
description: "KDUMP テーブル — Linux kernel crash dump (kdump) の設定。KDUMP|config の単一 container。hostcfgd がこの container を購読し、/etc/default/kdump-tools の生成・kdump-config の起動を実施する。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-kdump.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - KDUMP
  cli:
    - config kdump
  yang:
    - sonic-kdump
---

# KDUMP テーブル

## 概要

Linux kernel crash dump (kdump) の設定。`KDUMP|config` の単一 container[^1]。`hostcfgd` がこの container を購読し、`/etc/default/kdump-tools` の生成・`kdump-config` の起動を実施する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>KDUMP")]
  DM["hostcfgd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
KDUMP|config
```

(list ではなく単一 container)

## 主要フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `enabled` | boolean | kdump メカニズムの有効化 |
| `memory` | string | crash kernel に確保するメモリ。`512M-2G:64M,2G-:128M` 形式または絶対値 (`512M`) |
| `num_dumps` | uint8 (1..9) | 保持する core file 数 |
| `remote` | boolean | リモート (SSH) ダンプ転送の有効化 |
| `ssh_string` | string | リモート ssh 接続文字列 (`user@host` パターン) |
| `ssh_path` | string | リモート ssh 秘密鍵パス |

## 購読者

- `hostcfgd` (`docker-config-engine`): [CONFIG_DB](../../reference/glossary.md#term-config_db) → `/etc/default/kdump-tools`

## 関連 CONFIG_DB / YANG / CLI

- 関連 CLI: `config kdump enable/disable/memory/num_dumps/remote/add ssh_string`、`show kdump`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-kdump`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-kdump`](../yang/sonic-kdump.md)
- CLI: [`config kdump`](../cli/config-kdump.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-kdump.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-kdump.yang>

## 関連ページ
- [HLD: kdump](../../system/kdump.md)
- [CLI: config kdump](../cli/config-kdump.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `KDUMP|config`。
- `enabled`: `true`、`memory`: `0M-2G:256M,2G-:512M`、`num_dumps`: `3`。

### よくある誤設定

- memory が小さすぎると kdump kernel が起動できず crash dump が取れない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'KDUMP|config'
show kdump config
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

このテーブルに strict な enum フィールドはない。boolean と文字列フィールドで動作が決まる。

### `enabled`

| 値 | 挙動 |
|----|------|
| `true` | kdump 有効化。grub パラメータ変更のため次回 reboot 後に有効化 |
| `false` | kdump 無効化（デフォルト） |

### `remote`

| 値 | 挙動 |
|----|------|
| `true` | SSH 経由リモートダンプ転送。`ssh_string` / `ssh_path` の設定が必要 |
| `false` | ローカル保存のみ（デフォルト） |

### `memory`（文字列書式）

| 書式 | 挙動 |
|------|------|
| `512M-2G:64M,2G-:128M`（範囲形式） | 実装メモリに応じて確保量を変える |
| `512M`（絶対値形式） | 固定サイズ確保 |
| 小さすぎる値 | kdump kernel 起動失敗（DB には書けるが YANG 経由時のみ検証あり） |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-utilities/config/kdump.py -->

| 条件 | 挙動 |
|------|------|
| `enabled` 変更は即時反映されない | grub エントリ変更のため次回 reboot 後に有効化。現行カーネルへの影響なし |
| `memory` の値が小さすぎる | DB には書けるが kdump kernel 起動失敗（コード上のバリデーションなし、YANG 経由時のみ検証） |
| `num_dumps` が 0 以下 | CLI は `int` として受け取るが下限チェックなし。hostcfgd が `kdump-config` にそのまま渡すため動作は実装依存 |
| SSH key の不正フォーマット | `is_valid_ssh_key()` で検証 → エラーメッセージ出力して DB 書き込み中断 |
| remote 未 enable 状態で remote サーバ設定 | `"Remote feature is not enabled. Please enable the remote feature first."` を表示して中断 |
| SSH path の不正フォーマット | `is_valid_ssh_path()` で検証 → エラーメッセージ出力して DB 書き込み中断 |

<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`hostcfgd` の `KdumpHandler` が CONFIG_DB の `KDUMP` テーブルを購読する。

`KDUMP` の key は `config` (単一エントリ)。`enabled` / `memory` / `num_dumps` フィールドを持つ。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — `kdump-tools` の設定ファイルを更新)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を検知後、`/etc/default/kdump-tools` を書き換え。`kdump-tools` の設定は次回サービス再起動またはシステム再起動で反映。

**副作用**: `enabled: true` にしてもシステム再起動なしでは kdump カーネルがロードされない。`num_dumps` 変更は次回 coredump 発生時から適用。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `KDUMP`

### CLI
- `config kdump enable/disable`
- `config kdump memory <size>`
- `config kdump num-dumps <n>`
  - ソース: `sonic-utilities/config/kdump.py`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `init_cfg.json.j2` の `KDUMP` セクションでデフォルト値 (`enabled: false`, `memory: 0M-2G:256M,2G-4G:320M,...`) が注入

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- `hostcfgd` の kdump ハンドラが kernel crashkernel 設定と同期
<!-- /entry-points -->

<!-- cross-refs -->
## 暗黙参照 (Phase C)

### DEVICE_METADATA への暗黙参照

`KDUMP|config|enabled` のデフォルト値はビルド時プラットフォーム識別子 (`sonic_asic_platform`) で分岐する。
`cisco-8000` プラットフォームでは `enabled: true` がデフォルトになり、他プラットフォームでは `false`。
これは `DEVICE_METADATA|localhost|platform` に対応するビルド時設定であり、`init_cfg.json.j2` 経由で注入される。

また `hostcfgd` 起動時に `/proc/cmdline` の `crashkernel=` パラメータを確認し、存在する場合は
`KDUMP|config|enabled` と `KDUMP|config|memory` を CLI 設定より優先して自動上書きする
(`sonic-host-services/scripts/hostcfgd:1179-1207`)。

### FEATURE テーブルとの関係

`KDUMP` テーブルは `FEATURE` テーブルの管理対象外。kdump は独立した Docker コンテナを持たず、
`docker-config-engine` コンテナ内の `hostcfgd` が `KDUMP` テーブルを直接購読・処理する。
`FEATURE|<name>` の `state` フィールドによる有効化フローは存在しない。

```
KDUMP (CONFIG_DB) 変更
  → hostcfgd.kdump_handler()           # subscribe('KDUMP', ...)
  → KdumpCfg.kdump_update()
  → sonic-kdump-config (--enable/--disable/--memory/--num_dumps/--ssh_string/--ssh_path/--remote)
  → /etc/default/kdump-tools 更新
  → 次回システム再起動で反映
```

| 暗黙参照元 | 参照先 | 種別 |
|-----------|--------|------|
| `KDUMP|config|enabled` デフォルト | `DEVICE_METADATA|localhost|platform` (cisco-8000 判定) | ビルド時条件分岐 |
| `KDUMP|config|enabled/memory` | `/proc/cmdline` の `crashkernel=` | 起動時自動上書き |
| `KDUMP` 全フィールド | `hostcfgd` (docker-config-engine) | ランタイム購読 (FEATURE 非管理) |

<!-- /cross-refs -->

<!-- platform -->
## プラットフォーム差異 (Phase H)

### ブートローダー別 `crashkernel` 書き込みパス

`sonic-kdump-config` はブートローダーを自動検出し、`crashkernel=` パラメータの書き込み先を切り替える。

| ブートローダー | 判定条件 | `crashkernel` 書き込み先 |
|--------------|---------|------------------------|
| GRUB (x86_64 汎用) | `/host/grub/grub.cfg` 存在 | `/host/grub/grub.cfg` |
| Aboot (Arista) | `/host/machine.conf` に `aboot_platform` を含む | `/host/image-<version>/kernel-cmdline` |
| U-Boot (ARM 系) | `fw_printenv` コマンドが存在 | `fw_setenv` 経由で `linuxargs` を更新 |
| 非対応 | 上記以外 | `"Feature not supported on this platform"` を出力して中断 |

### ASIC ベンダー別デフォルト値

`init_cfg.json.j2` のビルド時テンプレートで `sonic_asic_platform` に基づいて `enabled` デフォルトが分岐する。

| `sonic_asic_platform` | `KDUMP|config|enabled` デフォルト |
|-----------------------|--------------------------------|
| `cisco-8000` | `"true"` (デフォルト有効) |
| その他 (broadcom, mellanox, vs 等) | `"false"` (デフォルト無効) |

`memory` / `num_dumps` のデフォルト (`"0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-:448M"` / `"3"`) はプラットフォーム非依存。

### KVM / 仮想プラットフォーム (VS) の差異

KVM/QEMU 環境を考慮した `ata_piix.prefer_ms_hyperv=0` パラメータが `/etc/default/kdump-tools` の `KDUMP_CMDLINE_APPEND` にデフォルトで含まれる。実機 ASIC プラットフォームでは `ata_piix` ドライバが存在しないため無害に無視される。

### ARM (U-Boot) プラットフォームの特殊処理

U-Boot 環境では `fw_printenv`/`fw_setenv` で `linuxargs` の `crashkernel=` を更新する。アーキテクチャ固有のデフォルト `crashkernel` 値はコード上に存在せず、CONFIG_DB の `memory` 値をそのまま使用する。

### デバイス固有の `crashkernel` (installer.conf)

一部デバイスは `ONIE_PLATFORM_EXTRA_CMDLINE_LINUX` で固有の `crashkernel` を持つ。CONFIG_DB の `memory` 変更時は `sonic-kdump-config` が上書きする。

| デバイス | `crashkernel` 初期値 |
|---------|-------------------|
| Celestica `cel_ds1000` | `0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-:448M` |
| Nexthop `5010` / `4010` | `512M` (絶対値固定) |
| Nokia `ixr7250e` 各 SKU | `8G-:1G` (高メモリ帯のみ) |

<!-- /platform -->

<!-- glossary-links-injected: b5626ca1f0f9 -->
