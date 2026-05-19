# FIPS — 暗黙参照テーブル調査 (Phase C)

## 調査対象

- `sonic-host-services/scripts/hostcfgd` (FipsCfg クラス L1753-1846)

## 結論

`FipsCfg` が参照する **他の CONFIG_DB テーブルは存在しない**。FIPS ハンドラは完全に独立しており、`FIPS` テーブル単体を購読・読取りするだけである。ただし以下の外部リソース（STATE_DB / ファイルシステム / bootloader）への暗黙依存がある。

## STATE_DB 書き込み / 読み取り

| キー | 方向 | 用途 | evidence |
|------|------|------|----------|
| `FIPS_STATS\|state` → `config_datetime` | 書込み (`hset`) | FIPS 設定変更のタイムスタンプを記録 | hostcfgd:1792 |
| `FIPS_STATS\|state` → `config_datetime` | 読取り (`hget`) | 前回再起動済みかを mtime と比較して二重再起動を防止 | hostcfgd:1821 |

## ファイルシステム暗黙参照

| ファイルパス | 定数名 | 参照方向 | 用途 | evidence |
|------------|--------|----------|------|----------|
| `/proc/cmdline` | `PROC_CMDLINE` | 読取り | `sonic_fips=1` または `fips=1` が現行 kernel に設定されているかを確認 (`cur_enforced` フラグ) | hostcfgd:1771-1773 |
| `/etc/sonic/fips.json` | `FIPS_CONFIG_FILE` | 読取り | 再起動対象サービスリスト (`restart_services`) を上書きするオプション設定 | hostcfgd:1766-1769 |
| `/etc/fips/fips_enable` | `OPENSSL_FIPS_CONFIG_FILE` | 読取り + 書込み | OpenSSL FIPS モード有効化フラグ (`0` / `1`) を管理 | hostcfgd:1797-1809 |

## bootloader 暗黙参照

`update_enforce_config()` は `sonic_installer.bootloader` を経由して次回起動用 grub エントリを操作する。

| 操作 | メソッド | 用途 | evidence |
|------|----------|------|----------|
| 次回起動イメージ取得 | `loader.get_next_image()` | 操作対象の boot image を決定 | hostcfgd:1840 |
| FIPS enforce 状態確認 | `loader.get_fips(image)` | 既に同じ enforce 設定ならスキップ | hostcfgd:1841-1843 |
| FIPS enforce 書込み | `loader.set_fips(image, enforce)` | grub に `sonic_fips=1` / `fips=1` パラメータを付与・除去 | hostcfgd:1846 |

## 関連 CONFIG_DB テーブル — 参照なし（意図的分離）

AAA / TACPLUS / SSH_SERVER など同 `hostcfgd` プロセスが扱う他テーブルは、FIPS ハンドラから直接読み出されない。FipsCfg は `__init__` 引数として `state_db_conn` のみを受け取り（hostcfgd:1759）、`config_db` への直接参照を持たない設計になっている。
