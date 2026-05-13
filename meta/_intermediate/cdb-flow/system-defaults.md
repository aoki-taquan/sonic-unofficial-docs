# SYSTEM_DEFAULTS 例外条件調査メモ

ソース:
- `sonic-buildimage/src/sonic-config-engine/config_samples.py` (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-swss/orchagent/muxorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 抽出した例外条件

1. **エントリ不在時のデフォルト補完** — `config_samples.py` の `get_sonic_gne()` は
   `"SYSTEM_DEFAULTS"` キーが data に存在しない場合に空の dict `{}` を代わりに挿入する。
   テーブル自体がない場合でも downstream ロジックが KeyError を起こさないよう設計されている。

2. **`tunnel_qos_remap` の存在チェック** — `muxorch` が `SYSTEM_DEFAULTS` テーブルから
   `tunnel_qos_remap` を読み取り、`status == "enabled"` のときのみ QoS remap を有効化する。
   エントリが存在しない場合は "disabled" として扱われる（デフォルト安全側）。

3. **`synchronous_mode` / `dhcp_server` 等** — 各機能コードが `hget` / `get_entry` で個別参照する。
   エントリが存在しない場合は機能が既定値（通常 disabled）で動作する。
   フィールドの型違反は YANG の `admin_mode` enum 制約で DB 書き込み時に弾かれる。

4. **実行時変更は非対応のエントリあり** — `tunnel_qos_remap` のように起動時に一度だけ参照されるパラメーターは、
   実行中に CONFIG_DB を書き換えてもサービス再起動なしには反映されない。
