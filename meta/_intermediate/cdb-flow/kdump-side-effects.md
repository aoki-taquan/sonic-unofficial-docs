# KDUMP — 副次ファイル書込 (Phase F)

> 対象ページ: `docs/reference/config-db/kdump.md`
> ソース: `sonic-utilities/scripts/sonic-kdump-config`

## 抽出根拠

`sonic-kdump-config` は CONFIG_DB の `KDUMP|config` エントリを読み取り、以下のシステムファイルを直接書き換える。これらは「DB → ファイルシステム」方向の副次書込 (Direction B) であり、SAI/APPL_DB を経由しない。

## 書込先ファイル一覧

| ファイル | 書込内容 | 関数 | 条件 |
|---------|---------|------|------|
| `/etc/default/kdump-tools` | `USE_KDUMP=1` または `USE_KDUMP=0` | `write_use_kdump()` | `enabled` フィールド変更時 |
| `/etc/default/kdump-tools` | `KDUMP_NUM_DUMPS=<n>` | `write_num_dumps()` | `num_dumps` フィールド変更時 |
| `/etc/default/kdump-tools` | `SSH=<ssh_string>` / `#SSH` コメントアウト | `write_kdump_remote()` | `remote` フィールド変更時 |
| `/etc/default/kdump-tools` | `SSH_KEY=<ssh_path>` | `write_ssh_path()` | `ssh_path` フィールド変更時 |
| `/host/grub/grub.cfg` | `crashkernel=<memory>` 追加/更新/削除 | `kdump_enable()` / `kdump_disable()` | `enabled` 変更時（GRUB プラットフォーム） |
| `/host/image-<ver>/kernel-cmdline` | `crashkernel=<memory>` 追加/更新/削除 | 同上 | Aboot プラットフォームのみ |
| U-Boot 環境変数 | `crashkernel=<memory>` / `crashkernel=0` (`fw_setenv`) | `modify_crashkernel_param_uboot_env()` | U-Boot プラットフォームのみ |

## 外部コマンド呼び出し

| コマンド | タイミング | 関数呼出箇所 |
|---------|----------|------------|
| `/usr/sbin/kdump-config load` | `enabled=true` かつ `crashkernel` が `/proc/cmdline` に既存 | `kdump_enable()` 末尾 |
| `/usr/sbin/kdump-config unload` | `enabled=false` への変更で `USE_KDUMP=0` 書込成功後 | `write_use_kdump()` 内 |
| `/usr/sbin/kdump-config set-remote <ssh_string> <ssh_path>` | `remote=true` でリモート設定を構成 | `kdump_enable()` の remote ブランチ |

## 生成ブロック (docs/reference/config-db/kdump.md に挿入済み)

```markdown
<!-- side-effects -->
## 副次ファイル書込 (Direction B)

`sonic-kdump-config` スクリプト (`sonic-utilities/scripts/sonic-kdump-config`) が CONFIG_DB 変更を契機に、以下のシステムファイルを書き換える。

<!-- evidence: sonic-utilities/scripts/sonic-kdump-config -->

| 書込先ファイル | フィールド / 操作 | トリガー条件 |
|--------------|----------------|------------|
| `/etc/default/kdump-tools` | `USE_KDUMP=1` / `USE_KDUMP=0` | `enabled` 変更時 (`write_use_kdump()`) |
| `/etc/default/kdump-tools` | `KDUMP_NUM_DUMPS=<n>` | `num_dumps` 変更時 (`write_num_dumps()`) |
| `/etc/default/kdump-tools` | `SSH=<ssh_string>` / `#SSH` コメントアウト | `remote` 変更時 (`write_kdump_remote()`) |
| `/etc/default/kdump-tools` | `SSH_KEY=<ssh_path>` | `ssh_path` 変更時 (`write_ssh_path()`) |
| `/host/grub/grub.cfg` | `crashkernel=<memory>` をカーネルコマンドラインに追加/更新/削除 | `enabled=true` → `kdump_enable()` / `enabled=false` → `kdump_disable()` |
| `/host/image-<ver>/kernel-cmdline` | `crashkernel=<memory>` (Aboot プラットフォーム用) | 上記と同条件（Aboot 環境のみ） |
| U-Boot 環境変数 (`fw_setenv`) | `crashkernel=<memory>` / `crashkernel=0` | 上記と同条件（U-Boot プラットフォームのみ） |

### 外部コマンド呼び出し

| コマンド | タイミング |
|---------|----------|
| `/usr/sbin/kdump-config load` | `enabled=true` かつ `crashkernel` が `/proc/cmdline` に反映済みの場合 |
| `/usr/sbin/kdump-config unload` | `enabled=false` に変更し `USE_KDUMP=0` 書込成功後 |
| `/usr/sbin/kdump-config set-remote <ssh_string> <ssh_path>` | `remote=true` でリモート設定を構成する場合 |

### 備考

- `grub.cfg` への `crashkernel` 追記は **次回 reboot 後** に有効化。現行カーネルへの即時反映はされない。
- `/etc/default/kdump-tools` は `hostcfgd` 経由ではなく `sonic-kdump-config` が直接 `sed -i` で書き換える。
- `num_dumps` 変更は `/etc/default/kdump-tools` の `KDUMP_NUM_DUMPS` を更新するが、有効化は次回 crash 発生時。

<!-- /side-effects -->
```
