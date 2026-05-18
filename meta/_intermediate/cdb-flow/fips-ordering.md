# FIPS — Phase B 書込み順依存 (調査メモ)

対象ページ: `docs/reference/config-db/fips.md`
調査日: 2026-05-18
調査者: batch326

## 調査ソース

- `sonic-host-services/scripts/hostcfgd` (`FipsCfg` クラス, L1753-1847)
- 起動ロード順序: `hostcfgd` main `load()` L2262-2275

## 検出された順序依存

1. **起動時ロード順** — hostcfgd は `load_independent_config()` 完了後に `fipscfg.load(fips_cfg)` を実行する (L2271)。SSH など先行 unit が FIPS なしで一瞬起動する場合がある。

2. **enforce 変更の遅延反映** — `enforce=true` は次回 boot image の grub パラメータのみ書き換える (L1838-1846)。現行 kernel には即時影響なし。`reboot` が必要。

3. **enable SET → ファイル書込み → サービス再起動** — `update_noneenforce_config()` が `/etc/fips/fips_enable` を書き、その後 `restart()` でサービスを再起動する (L1795-1835)。`cur_enforced=true` 時は `restart()` をスキップ。

4. **二重再起動防止** — `FIPS_STATS|state.config_datetime` (STATE_DB) と `/etc/fips/fips_enable` の mtime を比較して不要な再起動を防止 (L1821-1824)。

5. **restart_services リスト** — `read_config()` が `/etc/sonic/fips.json` を先読みして決定 (L1765-1769)。ファイルが無い場合は `DEFAULT_FIPS_RESTART_SERVICES = ['ssh', 'telemetry.service', 'restapi']` を使用 (L103)。

## 結論

FIPS はシングルトンテーブルでフィールド間の書込み順序依存はないが、`enforce` の適用が次回起動まで遅延する点と、サービス再起動の二重実行防止ロジックが運用上重要な順序制約となる。
