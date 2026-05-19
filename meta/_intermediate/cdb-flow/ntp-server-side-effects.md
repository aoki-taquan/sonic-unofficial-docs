# NTP_SERVER — Phase F (side-effects) スキャンノート

## ソース

- `sonic-host-services/scripts/hostcfgd` (NtpCfg クラス L1272-1407)
- `sonic-host-services/scripts/caclmgrd` (ACL_SERVICES, L96-100)

## DB 書込みスキャン結果

`NtpCfg.ntp_srv_key_update()` (L1366-1406) を全行精読:
- ProducerTable / Table.set() 呼び出し: **0件**
- STATE_DB 書き込み: **0件** (NtpCfg は state_db_conn を保持しない)
- APPL_DB 書き込み: **0件**
- COUNTERS_DB 書き込み: **0件**

## ホスト OS への副次作用

1. `chrony.conf.j2` テンプレート再生成 → `/etc/chrony/chrony.conf`
2. `chrony.keys.j2` テンプレート再生成 → `/etc/chrony/chrony.keys`
3. `systemctl restart chrony` 実行 (L1280, L1398)

## caclmgrd との関係

`caclmgrd` は NTP を `ACL_SERVICES` 定義 (L96-100) に持つが、
`NTP_SERVER` テーブルを直接 subscribe しない。
`FEATURE` テーブルと `MGMT_INTERFACE` の変更をトリガーに iptables ルールを生成する。
NTP_SERVER 変更が caclmgrd の iptables 更新を直接トリガーすることはない。

## キャッシュ設計の意図

chrony restart 失敗時はキャッシュを更新しない (L1402 return により L1404-1406 未到達)。
次回イベントでキャッシュ差分が残り、自動再処理が保証される意図的設計。
