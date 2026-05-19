# NTP_GLOBAL — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-19 (chore/q67-f-batch912)

ソース:
- `sonic-net/sonic-host-services/scripts/hostcfgd` (NtpCfg L1272–1406, MgmtVrfCfg L1650–1669)
- `sonic-net/sonic-buildimage/files/image_config/chrony/chronyd-starter.sh`
- `sonic-net/sonic-buildimage/files/image_config/chrony/chrony.conf.j2`
- `sonic-net/sonic-buildimage/files/image_config/chrony/chrony.keys.j2`

## 調査メモ

### hostcfgd NtpCfg ハンドラの失敗経路

`systemctl restart chrony` の実行失敗はすべて `except Exception` でキャッチされ、`LOG_ERR` ログ出力後に `return` する。
三つのハンドラがそれぞれ独立して try/except を持つ:

1. `handle_ntp_source_intf_chg` (L1324-1328): chrony restart 失敗 → LOG_ERR → return (キャッシュ更新なし)
2. `ntp_global_update` (L1356-1361): chrony restart 失敗 → LOG_ERR → return (L1364 の cache 更新に到達しない)
3. `ntp_srv_key_update` (L1397-1402): chrony restart 失敗 → LOG_ERR → return (L1405-1406 の cache 更新に到達しない)

### キャッシュ不整合の詳細

`ntp_global_update` でキャッシュ未更新が発生した場合:
- CONFIG_DB には新しい値が書かれているが `self.cache['global']` には古い値が残る
- 次回同一値の SET イベントが来ると `cache.get('global', {}) == data` が true → no-op
- 復旧するには異なる値を書いてから元の値を戻す必要がある

`ntp_srv_key_update` でキャッシュ未更新が発生した場合:
- `self.cache['servers']` / `self.cache['keys']` が古い値のまま
- 次回の NTP_SERVER / NTP_KEY 変更イベントで差分が検出され再処理される → 自然復旧

### STATE_DB ステータスの非存在

NTP はホスト側デーモン (chrony) との連携のみ。orchagent / SAI は無関係。
STATE_DB への書き込みは一切存在しない。
