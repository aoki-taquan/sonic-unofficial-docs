# SNMP_COMMUNITY テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `SNMP_COMMUNITY` テーブル。

## 1. 購読 API — Redis pub/sub なし、sonic-cfggen バッチ読み取り

`SNMP_COMMUNITY` テーブルを消費する主経路は `snmpd.conf.j2` テンプレートであり、
`swsscommon.SubscriberStateTable` / `ConfigDBConnector.subscribe()` / `ConsumerStateTable`
のいずれも**使用していない**。

### 消費経路

| 消費者 | 消費 API | タイミング | evidence |
|--------|----------|-----------|----------|
| `snmpd.conf.j2` (`sonic-cfggen`) | `sonic-cfggen -d` (HGETALL 一括読み取り) | `docker-snmp` コンテナ起動時のみ | `start.sh L23-26` |
| `show snmp community` (sonic-utilities) | `db.cfgdb.get_table('SNMP_COMMUNITY')` | CLI 実行時のみ | `show/main.py L1966` |
| `config snmp community` (sonic-utilities) | `config_db.get_table('SNMP_COMMUNITY')` / `set_entry()` | CLI 実行時のみ | `config/main.py L4384,4412,4440` |

イベントドリブンな通知受信者は存在しない。`SNMP_COMMUNITY` への書き込みは
Redis keyspace 通知を発火させるが、それを受け取って即時処理するデーモンは
SONiC ソース内に存在しない（grep 確認済み）。

## 2. sonic-cfggen 起動フロー (start.sh)

```bash
# docker-snmp/start.sh L17-26
/usr/bin/snmp_yml_to_configdb.py          # snmp.yml → SNMP_COMMUNITY 注入

sonic-cfggen \
    -d \                                   # CONFIG_DB から全テーブルを HGETALL
    -y /etc/sonic/sonic_version.yml \
    -t snmpd.conf.j2,/etc/snmp/snmpd.conf  # テンプレート展開 → ファイル生成
```

1. `snmp_yml_to_configdb.py` が `SNMP_COMMUNITY` へブート時エントリを注入。
2. `sonic-cfggen -d` が CONFIG_DB 全体を読み取り、Jinja2 テンプレートを展開して
   `/etc/snmp/snmpd.conf` を生成。
3. supervisord が `snmpd` を起動（`supervisord.conf.j2 L42-51`、
   `dependent_startup_wait_for=start:exited`）。

snmpd プロセスが起動後に CONFIG_DB を読み直すことはない。

## 3. 設定変更の反映フロー

CONFIG_DB への書き込み後、snmpd への反映は **コンテナ再起動のみ** で行われる。

```
config snmp community add <name> <RO|RW>
  ↓ HSET "SNMP_COMMUNITY|<name>" TYPE "<RO|RW>"    (Redis keyspace 通知発火)
    — 受け取るデーモンなし —
  ↓ systemctl reset-failed snmp.service             (config/main.py:4397-4401)
  ↓ systemctl restart snmp.service
      → docker-snmp コンテナ再起動
      → start.sh 再実行 → sonic-cfggen → snmpd.conf 再生成
      → snmpd 再起動 → 新 community 有効化
```

CLI (`config snmp community add/del/replace`) は DB 書き込み直後に
`systemctl restart snmp.service` を発行するため、CLI 経由では自動反映される。
`sonic-db-cli` / `config load` 等の direct DB 書き込みでは自動再起動なし。

## 4. ConsumerStateTable / NotificationProducer 非使用の確認

- `SNMP_COMMUNITY` を `ConsumerStateTable` / `SubscriberStateTable` で購読する
  コードは SONiC ソース内に存在しない（grep 結果 0 件）。
- `NotificationProducer` で `SNMP_COMMUNITY` 関連の通知を送出する箇所もなし。
- 結論: `SNMP_COMMUNITY` は **CONFIG_DB → sonic-cfggen(バッチ) → snmpd.conf →
  snmpd 起動** の一方向フローで完結し、APPL_DB / STATE_DB の中継パスを持たない。

## 5. 参考行番号

- `sonic-buildimage/dockers/docker-snmp/start.sh`: L17-26
- `sonic-buildimage/dockers/docker-snmp/supervisord.conf.j2`: L42-51
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`: L48-64
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`: L17-49
- `sonic-utilities/config/main.py`: L4384, 4391, 4397-4401, 4412, 4419, 4425-4430, 4440, 4452-4454, 4456-4461
- `sonic-utilities/show/main.py`: L1966, 2063
