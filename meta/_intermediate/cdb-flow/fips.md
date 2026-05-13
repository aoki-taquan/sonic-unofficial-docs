# CONFIG_DB 例外条件分析: FIPS

## Consumer

- `sonic-installer` (`sonic-utilities/sonic_installer/main.py`): `set-fips` / `get-fips` コマンドが grub/bootloader 設定を書き換える。CONFIG_DB の `FIPS|global` を直接読み書きする hostcfgd ハンドラは確認できず、bootloader 経由でのみ有効化される。
- `hostcfgd` 系: FIPS テーブルを subscribe する hostcfgd コードは sonic-host-services に明示的には存在しない。有効化は再起動後の kernel コマンドラインパラメータ変更で実現。

## 例外条件

### 1. 非 FIPS 認証イメージで enable=true → 起動時 crypto モジュールが欠如
- ソース: `sonic_installer/main.py` L691-702
- FIPS 有効化は grub エントリへの `fips=1` 追加で行われる。FIPS 非対応カーネル/イメージ上では一部 OpenSSL アルゴリズムが提供されず SSH / TLS が起動しない場合がある。
- 証拠: `bootloader.set_fips(image, enable=enable_fips)` — 値は次回起動時に反映。

### 2. CONFIG_DB 変更は次回起動まで無効
- ソース: `sonic_installer/main.py` — bootloader 経由変更のため現行稼働中カーネルには即座に影響しない。
- `enable=false` → `true` に変えても `reboot` なしでは crypto 制限は開始されない。

### 3. YANG スキーマバリデーション
- `enable` は `true`/`false` 文字列のみ許容（YANG pattern 制約）。それ以外の文字列は `mgmt-framework` / `sonic-cfggen` の YANG 検証で reject される（CONFIG_DB には書かれない）。
