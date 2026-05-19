# CONFIG_DB 副次 DB 書込分析: NTP_KEY — Phase F

生成日: 2026-05-19

## 調査対象

- `sonic-host-services/scripts/hostcfgd` — `NtpCfg` クラス (L1272–1407)
- `sonic-buildimage/files/image_config/chrony/chrony-config.sh`
- `sonic-buildimage/files/image_config/chrony/chrony.keys.j2`

## 調査方針

`NTP_KEY` テーブルの変更を受信する `NtpCfg.ntp_srv_key_update()` 内で、
Redis DB (`APPL_DB` / `STATE_DB` / `COUNTERS_DB` / `ASIC_DB` / `FLEX_COUNTER_DB`) へ
書き込む `set(` / `hset(` / `ProducerStateTable` / `NotificationProducer` の呼出を探索。

## grep 結果

```
grep -n "set(\|hset(\|Producer\|Notification\|state_db\|counters_db\|asic_db\|flex" \
  sonic-host-services/scripts/hostcfgd \
  | grep -A5 -B5 "NtpCfg\|ntp_srv_key\|NTP_KEY" → 0 ヒット
```

`NtpCfg.__init__()` (L1282–1309) は以下のみを保持:
- `self.config_db` (ConfigDBConnector — 読み取り専用参照)
- `self.cache` (dict — インメモリ only)
- `self.CHRONY_RESTART = ['systemctl', 'restart', 'chrony']`

書き込み系 DB コネクタ (ProducerStateTable / NotificationProducer / SonicV2Connector
for APPL_DB/STATE_DB/ASIC_DB/FLEX_COUNTER_DB/COUNTERS_DB) のメンバ変数なし。

## 副次 DB 書込: なし

| 対象 DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | `NtpCfg` 内に Producer/Table の書込呼出 0 件 (`hostcfgd:1272-1407`) |
| STATE_DB | なし | `NtpCfg` は `state_db_conn` を保持しない |
| COUNTERS_DB | なし | `hostcfgd` 全体に COUNTERS_DB への書込参照なし |
| ASIC_DB | なし | SAI 非経由。NTP_KEY を購読する orchagent なし |
| FLEX_COUNTER_DB | なし | NTP は SAI カウンタを持たない |
| LOGLEVEL_DB | なし | — |

## ファイルシステムへの副次書込（DB 外）

`ntp_srv_key_update()` は `run_cmd(['systemctl', 'restart', 'chrony'])` を呼び出す。
chrony 再起動トリガにより systemd が `ntp-config.service` のテンプレート再生成と
`chrony` の再起動を順次実行する。

これにより以下のホスト OS ファイルが書き換えられる:

| 書込先ファイル | 生成コマンド | 根拠 |
|---|---|---|
| `/etc/chrony/chrony.keys` | `sonic-cfggen -d -t /usr/share/sonic/templates/chrony.keys.j2` | `chrony-config.sh:10` |
| `/etc/chrony/chrony.conf` | `sonic-cfggen -d -t /usr/share/sonic/templates/chrony.conf.j2` | `chrony-config.sh:9` |

`chrony.keys.j2` は NTP_KEY 全件を走査し、`type` / `value` が有効なエントリのみ
`<id> <TYPE> <base64-decoded-value>[ trusted_str]` 形式で出力する (`chrony.keys.j2:15-17`)。
NTP_SERVER.trusted == 'yes' のサーバ IP リストが `trusted_str` として各行末に付与される。

## 結論

`NTP_KEY` 変更の副次作用は Redis DB への書込を持たず、ファイルシステム
(`/etc/chrony/chrony.keys`、`/etc/chrony/chrony.conf`) の再生成と `chrony` サービス
再起動のみに閉じる。これは `AaaCfg` / `SshServer` / `PamLimitsCfg` と同パターン。
