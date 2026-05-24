---
title: config save / load / reload / replace / qos reload
description: 'config save / load / reload / replace / qos reload — ここでは SONiC の config
  永続化と全体差し替え の中核となる以下の 5 コマンドをまとめる:'
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/sonic-utilities
  path: config/main.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
  - DEVICE_METADATA
  cli:
  - config save
  - config load
  - config reload
  - config replace
  - config qos reload
  yang: []
---

# config save / load / reload / replace / qos reload

## 概要

ここでは [SONiC](../../reference/glossary.md#term-sonic) の **config 永続化と全体差し替え** の中核となる以下の 5 コマンドをまとめる:

- `config save` ... 現 [CONFIG_DB](../../reference/glossary.md#term-config_db) を JSON ファイルに dump
- `config load` ... ファイルを [CONFIG_DB](../../reference/glossary.md#term-config_db) に書く (既存の状態を保持しつつ merge)
- `config reload` ... [CONFIG_DB](../../reference/glossary.md#term-config_db) をクリアしてからファイルを再ロード (services 再起動含む)
- `config replace` ... 現在の config と target config の **差分のみ** を当てる minimum-disruption replace
- `config qos reload` ... [QoS](../../reference/glossary.md#term-qos) 関連 (buffer / scheduler / queue / wred 等) を再生成

すべて `config/main.py` 内 (`@config.command()` 直付け) で定義される[^1]。

## 各コマンドの詳細

### `config save [-y] [<filename>]`

**用法**:

```bash
config save [-y|--yes] [<filename>]
```

**動作**:
multi-asic 環境では `num_asic + 1` 個のファイル (host + namespace 0..N-1) を必要とする。`<filename>` をカンマ区切りで指定すると namespace 数と一致する数を期待する。1 ファイルだけ指定した場合は `multiasic_save_to_singlefile` で 1 ファイルに集約保存する経路に入る。

各ファイルは `sonic-cfggen -d --print-data > <file>` (host) または `-n <ns> -d --print-data > <file>` で生成し、最後に `sort_dict` でキーをソートして再書き込みする[^2]。デフォルトは `/etc/sonic/config_db.json` (host) と `/etc/sonic/config_db<ns>.json` (per-asic)。

`-y` 不指定時は `Existing files will be overwritten, continue?` を `_abort_if_false` callback で確認する (ここでは prompt が **常に表示される** 実装)。

### `config load [-y] [<filename>]`

CONFIG_DB を **クリアせずに**、指定ファイル (またはデフォルト) を `sonic-cfggen --write-to-db` で書き込む。既存エントリは merge されるため、削除された設定は残ったまま。multi-asic 時の `<filename>` 仕様は `save` と同じ (1 / num_asic+1 のいずれか)。

### `config reload [-y] [-l] [-n] [-f] [-t {config_db|config_yang}] [-b] [<filename>]`

**用法**:

```bash
config reload [-y] [-l|--load-sysinfo] [-n|--no_service_restart] [-f|--force]
              [-t|--file_format <config_db|config_yang>] [-b|--bypass-lock] [<filename>]
```

**動作**:
1. 起動チェック ... `--force` が無ければ `_is_system_starting()` と `_swss_ready()` を確認。NG なら exit code 1。
2. ロック取得 ... `try_lock(SYSTEM_RELOAD_LOCK, timeout=0)` デコレータが `/etc/sonic/reload.lock` を取り、二重起動を防ぐ。`--bypass-lock` で迂回可。
3. 確認プロンプト ... `--yes` が無ければ `Clear current config and reload config in <fmt> from the file(s) <files> ?` を表示。
4. 全 services の停止 → CONFIG_DB の **全テーブル削除** → ファイルを書き戻し → services 再起動。
5. `--no_service_restart` を付ければ services 再起動を省略。

`config save` で保存した JSON とは異なる前提のファイル (例: minigraph の途中変換結果) を渡すとデータプレーンが無効化される可能性が高いので、**通常は `config save` で出したものを `reload` する**。

### `config replace <target-file-path> [-f <fmt>] [-d] [-n] [-i <path>] [-v]`

**用法**:

```bash
config replace <target-file-path>
    [-f|--format CONFIGDB|SONICYANG]
    [-d|--dry-run]
    [-n|--ignore-non-yang-tables]
    [-i|--ignore-path <jsonpointer>]
    [-v|--verbose]
```

**動作**:
target を読み込み、`GenericUpdater().replace(...)` が現在の CONFIG_DB との **JSON Patch (RFC 6902) を計算**して適用する。同じテーブル間で差分が無ければ touch しないため、[ACL](../../reference/glossary.md#term-acl) は変わらないが [BGP](../../reference/glossary.md#term-bgp) だけ変えるといった部分更新でも DHCP services は再起動されない[^3]。`replace` 系は `apply-patch` / `rollback` と同じ generic_config_updater 機構の上に乗る。

target file には **完全な config 全体** を渡す必要がある (`**WARNING** The target config file should be the whole config, not just the part intended to be updated.`)。

### `config qos reload [--ports <list>] [--no-dynamic-buffer] [--no-delay] [--dry_run <file>] [--json-data <json>] [--verbose]`

**動作**:
1. `--ports` 指定時は `_qos_update_ports` が指定 port のみ [QoS](../../reference/glossary.md#term-qos) 設定を再描画 (差分 reload)。
2. 通常は `_clear_qos` で `BUFFER_*` / `QUEUE` / `SCHEDULER` / `PORT_QOS_MAP` / `WRED_PROFILE` 等を一旦削除。
3. namespace ごとに `buffers_dynamic.json.j2` / `buffers.json.j2` + `qos.json.j2` を `sonic-cfggen` で render し、CONFIG_DB に書き戻す。
4. `--no-dynamic-buffer` を付けると mellanox / barefoot 系でも static buffer に固定し、`DEVICE_METADATA.localhost.buffer_model` を `traditional` 相当に書き換える。
5. `--dry_run <file>` でファイルに書き出して終わり (CONFIG_DB は変更しない)。`--json-data` で render 入力に追加情報を渡せる。

**`config reload` の最後に `config qos reload --no-dynamic-buffer --no-delay` が呼ばれる**ため、`reload` 後は [QoS](../../reference/glossary.md#term-qos) が必ずテンプレートから再生成される。

## 関連する CONFIG_DB

| テーブル | キー | コマンド |
|----------|------|----------|
| `DEVICE_METADATA` | `localhost` | `config qos reload` (`buffer_model` を `dynamic` / `traditional`) |
| 全テーブル | - | `config reload` (一旦削除 → 再注入) |

## 注意

- `config save` → ファイルを sort して書き戻すため、手書き JSON を `save` 経由で経由させると **キー順が変わる**。`git diff` で純粋な差分を見たい場合は注意。
- `config reload` は **CONFIG_DB を完全に置き換える**。`config save` していない一時的な設定変更は失われる。
- `config replace` の `--format SONICYANG` 指定時は [YANG](../../reference/glossary.md#term-yang) モデルバリデーションが有効で、不適合な値は `--ignore-non-yang-tables` 等で個別に逃がす必要がある。
- `config load` は merge なので、**削除した設定は CONFIG_DB に残る**。クリーンな状態にしたいなら必ず `config reload` を使う。

<!-- cli-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CLI["config save"]
  SC["sonic-cfggen<br/>(config CLI のみ)"]
  CLI --> SC
  CDB0[("CONFIG_DB<br/>DEVICE_METADATA")]
  SC --> CDB0
  DM0["SwitchOrch"]
  CDB0 --> DM0
```

!!! note "凡例"
    config 系 (CLI → CONFIG_DB → daemon) のミニ図。テーブル → daemon 対応は `docs/reference/config-db-orch-map.md` から機械生成。
<!-- /cli-mermaid -->

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`DEVICE_METADATA`](../config-db/device-metadata.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `config save` (`config/main.py` L1789-L1849)、`config load` (L1851-L1910)、`config reload` (L2108-L2290)、`config replace` (L1981-L2036)、`config qos reload` (L3652-L3740) の各エントリポイント。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py>

[^2]: `save` の sort 処理 (`config/main.py` L1845-L1849)。

[^3]: `replace` 内部の `GenericUpdater().replace(...)` 呼び出し (`config/main.py` L1981-L2036)。`generic_config_updater/` 配下に JSON Patch ベースの差分計算実装がある。

<!-- ops-hint -->
## 運用ヒント

### 典型的な利用シーン

- 設定変更後に永続化したい場合は `config save` を実行する (`/etc/sonic/config_db.json` 上書き)。
- マイナーな差分のみ適用したい場合は `config replace --dry-run` で JSON Patch を確認してから本適用する。
- フル再ロードが必要な場合 (services 含む) は `config reload` を使う。事前に `config save` 推奨。

### よくある落とし穴

- `config reload` は CONFIG_DB を **全削除** してから再注入するため、save 未済の一時設定は失われる。
- `config load` は merge 動作で、削除済みエントリは復元されない。クリーンに戻したい場合は `config reload` を使う。
- `config reload` は `/etc/sonic/reload.lock` で多重起動を防ぐ。前回 reload が異常終了した場合は `--bypass-lock` での解除を検討。
- `config qos reload` は `BUFFER_*` / `QUEUE` / `SCHEDULER` / `WRED_PROFILE` などを一旦削除して再生成するため、手動カスタマイズした QoS は失われる。

### 関連する show / debug

```bash
show runningconfiguration all
sonic-db-cli CONFIG_DB keys '*'
ls -l /etc/sonic/reload.lock
```
<!-- /ops-hint -->

<!-- cli-sibling -->
### 関連 CLI コマンド

- [`show mgmt-vrf`](show-mgmt-vrf.md) — show mgmt-vrf サブコマンド
- [`show muxcable`](show-muxcable.md) — show muxcable サブコマンド
- [`show running config`](show-running-config.md) — show runningconfiguration / startupconfiguration サブコマンド
- [`config dhcp relay`](config-dhcp-relay.md) — config dhcp_relay / dhcpv4_relay サブコマンド
- [`config muxcable`](config-muxcable.md) — config muxcable サブコマンド

<!-- /cli-sibling -->

<!-- glossary-links-injected: 8ba32e5aa69d -->
