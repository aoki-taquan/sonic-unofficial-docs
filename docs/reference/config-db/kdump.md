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

<!-- failure -->
## 失敗挙動

<!-- evidence: sonic-utilities/scripts/sonic-kdump-config -->

### crashkernel メモリ確保失敗

| 失敗条件 | 挙動 |
|---------|------|
| `memory` 値が小さすぎる（例: `32M`）でリブート | kdump カーネルがロードされず `/sys/kernel/kexec_crash_size = 0`。`show kdump status` は `Not Ready` を表示。CONFIG_DB の値は変更されない |
| 物理メモリ不足で crashkernel 確保不可 | 同上。エラーログはカーネルブート時にのみ出力。`sonic-kdump-config` スクリプトは `get_crash_kernel_size()` で `"0"` を返して例外を呑み込む（`sonic-kdump-config:94-99`） |
| `locate_image()` が `-1` 返却（イメージ名不一致） | `lines[-1]`（最終行）を誤って更新。クラッシュなしだが無効エントリが書き込まれる（`sonic-kdump-config:655-683`） |

### systemd / kdump-config サービス起動失敗

| 失敗条件 | 挙動 |
|---------|------|
| `/etc/default/kdump-tools` の `USE_KDUMP` 書き換え失敗 | `print_err("Error while writing USE_KDUMP into ...")` → `sys.exit(1)`。CONFIG_DB の巻き戻しなし（`sonic-kdump-config:483-496`） |
| `kdump-config unload` が非ゼロ終了 | `print_err("Error Unable to unload the Kdump kernel ...")` → `sys.exit(1)` |
| `kdump-config load` が非ゼロ終了 | `print_err("Error: Unable to reload kdump configuration")` → `sys.exit(1)`（`sonic-kdump-config:713-716`） |
| リモート設定時 `kdump-config set-remote` 失敗 | `print_err("Error: Unable to set remote crash dump configuration")` → `sys.exit(1)` |

いずれも CONFIG_DB への巻き戻しは行われない。`enabled: true` が DB に残ったまま kdump サービスが停止する不整合が生じる。

### 不正 num_dumps 値

| 失敗条件 | 挙動 |
|---------|------|
| `num_dumps = 0` | CLI は下限チェックなし。`KDUMP_NUM_DUMPS=0` が `/etc/default/kdump-tools` に書き込まれる。kdump-tools はローテーションを無制限として扱う可能性がある（`sonic-kdump-config:521-529`） |
| `num_dumps` が負値 | 同様に下限チェックなし。`KDUMP_NUM_DUMPS=-1` が書き込まれ動作は実装依存 |
| YANG 検証（`uint8` range `1..9`）は mgmt-framework 経由時のみ有効 | CLI / `sonic-kdump-config` 直接呼び出しではバイパスされる |

<!-- /failure -->

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

<!-- ordering -->
## 書込み順依存・起動順序

### kernel crashkernel 予約順序

`crashkernel=` パラメータは **GRUB / U-Boot / Aboot のブートローダ設定** に埋め込まれ、次のリブート時にカーネルが予約メモリを確保する。

```
[1] config kdump enable / hostcfgd kdump_update()
      └─ sonic-kdump-config --enable
           └─ kdump_enable() 関数
                ├─ grub.cfg / kernel-cmdline / uboot-env に crashkernel=<memory> を追記
                │    (sonic-buildimage/files/image_config/kdump/kdump-tools 設定をベースに)
                └─ write_use_kdump(1)  →  USE_KDUMP=1 を /etc/default/kdump-tools へ書込み

[2] システムリブート
      └─ ブートローダが crashkernel= を kernel cmdline に渡す
           └─ 物理メモリの一部が crash kernel 用に予約される
                (/sys/kernel/kexec_crash_size > 0 になる)

[3] kexec_load（kdump-tools パッケージ提供の kdump-config load）
      └─ crash kernel イメージを予約メモリへロード
           └─ /usr/sbin/kdump-config load
                (hostcfgd の kdump_update() 内で
                 crash_kernel_in_cmdline != None の場合に実行)
```

evidence: `sonic-utilities/scripts/sonic-kdump-config` `kdump_enable()` L640-715、`sonic-host-services/scripts/hostcfgd` `KdumpCfg.kdump_update()` L1225-1270

### systemd kdump.service 起動順序

hostcfgd の `load()` は `wait_till_system_init_done()` 完了後に `kdumpCfg.load(kdump)` を呼ぶ。これにより kdump の初期化はシステム基盤サービスが stable になった後に実施される。

```
systemd target: sonic.target
  └─ hostcfgd.service (docker-config-engine)
       ├─ __init__()
       │    ├─ KdumpCfg.__init__()
       │    │    └─ init_kdump_config_from_cmdline()
       │    │         └─ /proc/cmdline に crashkernel= が存在する場合
       │    │              → CONFIG_DB KDUMP|config を上書き (enabled=true, memory=<値>)
       │    │              → update_config_from_proc_cmdline = True フラグセット
       │    └─ (他のハンドラ初期化)
       │
       ├─ load_independent_config()   ← AAA/TACACS/RADIUS のみ（kdump はここに含まれない）
       │
       ├─ wait_till_system_init_done()   ← systemctl is-system-running --wait
       │
       └─ load()                         ← system init 完了後
            ├─ kdumpCfg.load(init_data['KDUMP'])
            │    └─ CONFIG_DB の値がデフォルト未設定なら mod_entry でデフォルト埋め
            │         └─ kdump_update("config", data)
            │              ├─ sonic-kdump-config --enable / --disable
            │              ├─ sonic-kdump-config --memory <size>
            │              ├─ sonic-kdump-config --num_dumps <n>
            │              ├─ sonic-kdump-config --ssh_string <str>
            │              ├─ sonic-kdump-config --ssh_path <path>
            │              └─ sonic-kdump-config --remote
            │
            └─ register_callbacks()
                 └─ config_db.subscribe('KDUMP', kdump_handler)
                      └─ 変更イベント → kdumpCfg.kdump_update(key, data)
```

evidence: `sonic-host-services/scripts/hostcfgd` L2160-2280、L2393-2395、L2468

### 起動順依存の要点

| 依存関係 | 詳細 |
|---------|------|
| **crashkernel 予約はリブート必須** | `enabled=true` を DB に書いても現行カーネルでは kdump が動作しない。grub/U-Boot へのパラメータ追記 → リブート → kexec_load が完了して初めて有効化 |
| **/proc/cmdline 先読みによる DB 上書き** | hostcfgd 起動時に `init_kdump_config_from_cmdline()` が `/proc/cmdline` を参照し、`crashkernel=` が既に存在する場合は CONFIG_DB を `enabled=true` に強制上書きする。これが完了する前に `kdump_update()` が呼ばれると `update_config_from_proc_cmdline` フラグにより最初の更新がスキップされる |
| **system init 完了待機** | `load()` は `wait_till_system_init_done()` 後に実行される。kdump が依存するファイルシステム (`/host/grub/grub.cfg` 等) が安定してからでないと `kdump_enable()` が失敗する |
| **ssh_string / ssh_path の適用タイミング** | `/etc/default/kdump-tools` への SSH 設定書き込みは即時だが、実際のリモートダンプ有効化は次回リブート後のカーネルロード時 |

<!-- /ordering -->

<!-- defaults -->
## コード由来の暗黙デフォルト

YANG に `default` 句は一切ない。デフォルト値はすべて実装コードに埋め込まれており、3 層（init_cfg.json.j2 / hostcfgd ハードコード / sonic-kdump-config フォールバック）が独立して存在する。

### フィールド別デフォルト一覧

| フィールド | YANG default | init_cfg.json.j2 | hostcfgd ハードコード | sonic-kdump-config fallback |
|---|---|---|---|---|
| `enabled` | なし | `"false"` (cisco-8000 のみ `"true"`) | `"false"` | — |
| `memory` | なし | `"0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-:448M"` | `"0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-16G:448M,16G-32G:768M,32G-:1G"` | `"0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-:448M"` |
| `num_dumps` | なし | `"3"` | `"3"` | `3` (int) |
| `remote` | なし | 記載なし | `"false"` | `False` |
| `ssh_string` | なし | 記載なし | `"user@localhost"` (プレースホルダー) | `None` |
| `ssh_path` | なし | 記載なし | `"/a/b/c"` (プレースホルダー) | `None` |

### 重要な暗黙挙動

**プラットフォーム依存 + 暗黙 reset (`enabled`)**:
hostcfgd 起動時に `/proc/cmdline` を読み、`crashkernel=` が存在する場合は `enabled` を `"true"` に強制書き戻し・DB 更新する（`init_kdump_config_from_cmdline()`）。CONFIG_DB に `"false"` を設定していても上書きされる。これはブートローダーで crashkernel を設定済みのプラットフォーム（cisco-8000 等）で発生する。

**YANG-実装 discrepancy (`memory`)**:
`memory` の初期値が 3 箇所で異なる。`init_cfg.json.j2` は 2 段階（`8G-:448M` 止まり）、hostcfgd は 4 段階（`16G-32G:768M,32G-:1G` を含む）、`sonic-kdump-config` の `get_kdump_memory()` は init_cfg と同じ 2 段階。高メモリ環境（16GB 超）では hostcfgd 経由と init_cfg 経由で異なる予約量になる。

**silent substitution (`ssh_string`, `ssh_path`)**:
CONFIG_DB に値が未設定の場合、hostcfgd は `"user@localhost"` / `"/a/b/c"` をフォールバックとして sonic-kdump-config に渡す。これらはプレースホルダー値だがエラーにならず `/etc/default/kdump-tools` に書き込まれる。

**YANG-実装 discrepancy (`ssh_string` 検証)**:
検証ルールが 3 系統で異なる。YANG パターン（`[a-zA-Z0-9._%+-]+@...`、ユーザー名先頭に `_` 等を許容）、CLI `is_valid_ssh_key()`（`username.isalnum()` のみ、英数字限定）、sonic-kdump-config `SSH_STRING_RE`（`[a-zA-Z0-9][a-zA-Z0-9._%+-]*@...`、先頭英数字必須）。直接 DB 書き込みでは YANG 制約もバイパスされる。

**partial failure (`ssh_path`)**:
CLI `add_ssh_path` は `os.path.exists()` で実在チェックするが、sonic-kdump-config `write_ssh_path()` はパターン検証のみで存在チェックなし。DB 直接書き込みや hostcfgd フォールバック（`"/a/b/c"`）経由では存在しないパスが `/etc/default/kdump-tools` に書き込まれる。

**dead consumer (YANG `num_dumps` 範囲制約)**:
YANG は `range "1 .. 9"` を定義するが、CLI `config kdump num_dumps` は `type=int` のみで範囲チェックなし。0 や 10 以上の値も DB に書き込み可能。sonic-yang-mgmt を経由する REST/gNMI 経由時のみ YANG 範囲検証が有効。

<!-- /defaults -->

<!-- glossary-links-injected: b5626ca1f0f9 -->
