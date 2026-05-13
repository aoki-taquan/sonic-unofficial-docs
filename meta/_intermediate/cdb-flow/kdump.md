# CONFIG_DB 例外条件分析: KDUMP

## Consumer

- `config kdump` コマンド (`sonic-utilities/config/kdump.py`): CONFIG_DB の `KDUMP|config` を直接 `mod_entry()` で書く。
- `hostcfgd` (`sonic-host-services`): `KDUMP` テーブルを subscribe し、`kdump-config` コマンド経由でカーネルパラメータを設定する。

## 例外条件

### 1. enabled の変更は再起動後に反映
- ソース: `config/kdump.py` L51, L66
- `enabled=true/false` は `mod_entry()` で即座に CONFIG_DB に書かれるが、実際の kdump kernel 予約は次回起動後に grub で有効になる。
- 運用中に `enable` → `disable` しても crash 時には旧設定で動作する。

### 2. memory 値は文字列の YANG pattern 検証のみ
- ソース: `config/kdump.py` L77-82
- `memory` フィールドは `"0M-2G:256M,2G-:512M"` 形式の文字列として CONFIG_DB に保存。形式検証は YANG / mgmt-framework 経由時のみ実施。CLI から直接書く場合はバリデーション無し。
- 小さすぎる値（例 `32M`）でも DB には書けるが kdump kernel 起動が失敗する。

### 3. num_dumps が 0 以下 → kdump ローテーションが無制限になる可能性
- ソース: `config/kdump.py` L91-98 (`type=int`)
- CLI は `int` 型として受け取るが 0 以下の値を CLI 上で拒否しない場合がある。hostcfgd がそのまま `kdump-config` へ渡すと動作が実装依存。

### 4. remote kdump: SSH key / path の検証
- ソース: `config/kdump.py` L176-178, L212-214
- `is_valid_ssh_key()` / `is_valid_ssh_path()` で検証し、エラー時は `click.echo(f"Error: {validation_error}")` して処理中断。DB には書かれない。

### 5. remote feature 未 enable 状態での remote 設定 → エラー
- ソース: `config/kdump.py` L172
- `remote_enabled=false` の状態で remote kdump サーバ等を設定しようとすると `"Remote feature is not enabled. Please enable the remote feature first."` を表示して中断。
