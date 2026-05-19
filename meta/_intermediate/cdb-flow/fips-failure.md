# fips — Phase D failure-behavior 調査メモ

slug: fips
phase: D (failure-behavior)
date: 2026-05-19

## 調査対象ソース

- `sonic-host-services/scripts/hostcfgd` — `FipsCfg` クラス (L1753–1846)

## 主要失敗経路

### load() フェーズ
- `FIPS|global` が空 → skip + return (サイレント)
- `/proc/cmdline` 読み取り失敗 → `__init__` から例外伝播、hostcfgd 起動失敗
- `/etc/sonic/fips.json` JSON 不正 → `json.JSONDecodeError` 伝播、DEFAULT_FIPS_RESTART_SERVICES フォールバックなし

### update_noneenforce_config()
- `/etc/fips/` ディレクトリ作成失敗 → 例外伝播。STATE_DB config_datetime 未書込み
- `fips_enable` ファイル書込み失敗 → OpenSSL FIPS モード切替なし

### restart()
- `cur_enforced=True` → サービス再起動スキップ (正常系フォールバック)
- `config_datetime > mtime` → 二重再起動防止スキップ
- `systemctl -o json` 空 → サイレントスキップ
- 個別サービス restart 失敗 → 例外ハンドリングなし、後続サービス未再起動

### update_enforce_config()
- bootloader 取得失敗 → 例外伝播、grub 未更新
- `set_fips()` 失敗 → grub 未更新、`update_noneenforce_config()` は先行実行済みのため非一貫状態

## 重大な注意点

1. サービス再起動部分失敗がサイレントなため、SSH/telemetry/restapi の再起動失敗を手動確認が必要
2. `update_enforce_config()` 失敗時、OpenSSL FIPS enable は変更されるが bootloader enforce は未反映という非一貫状態になる
