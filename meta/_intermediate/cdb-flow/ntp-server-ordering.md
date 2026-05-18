# NTP_SERVER テーブル — Phase B 書込み順依存 + Phase C 暗黙参照 中間ファイル

> 生成日: 2026-05-18
> ソース: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang`,
>         `sonic-host-services/scripts/hostcfgd`,
>         `sonic-buildimage/files/image_config/chrony/chrony.conf.j2`,
>         `sonic-buildimage/src/sonic-config-engine/minigraph.py`
> 調査者: Claude (batch #6)

## 調査対象

`docs/reference/config-db/ntp-server.md` の `<!-- ordering -->` ブロック向け書込み順依存の抽出。

## 調査結果

### 1. NTP_KEY 先行必須 — key leafref

`sonic-ntp.yang` L199-203:

```yang
leaf key {
    description "NTP server key ID";
    type leafref {
        path /ntp:sonic-ntp/ntp:NTP_KEY/ntp:NTP_KEY_LIST/ntp:id;
    }
}
```

`NTP_SERVER|<server>.key=<id>` を書き込む前に `NTP_KEY|<id>` が存在しなければ
YANG leafref バリデーションが SET を拒否する。逆方向（DEL）は先に `NTP_SERVER.key` フィールドを
クリア（または `NTP_SERVER` エントリを DEL）してから `NTP_KEY|<id>` を DEL しなければ
dangling 参照になり DEL が失敗する。

### 2. NTP_KEY 登録 → authentication=enabled の順序推奨

`chrony.conf.j2` L124-131 は `NTP.global.authentication == 'enabled'` の場合のみ
`keyfile /etc/chrony/chrony.keys` を chrony.conf に書き込む。
`NTP_KEY` 未登録のまま `NTP.global.authentication=enabled` にすると、chrony.keys が空のまま
chrony が再起動し認証が機能しない（NTP サーバへの接続は試みるが鍵照合で失敗する）。

### 3. NTP_SERVER と NTP_KEY の合算処理

`hostcfgd:2387-2391` の `ntp_srv_key_handler`:

```python
def ntp_srv_key_handler(self, key, op, data):
    self.ntpcfg.ntp_srv_key_update(
        self.config_db.get_table(swsscommon.CFG_NTP_SERVER_TABLE_NAME),
        self.config_db.get_table(swsscommon.CFG_NTP_KEY_TABLE_NAME))
```

`NTP_SERVER` と `NTP_KEY` の変更は同一ハンドラで処理され、どちらが変更されても
両テーブルの全件を合算した上で chrony を再起動する。このため NTP_KEY の変更のみでも
chrony が再起動する副作用がある。

### 4. ブート時の書込みシーケンス

minigraph.py が `results['NTP_SERVER']` に `{server_ip: {'iburst': 'on'}}` を一括投入する
(`minigraph.py:2646`)。この後 `hostcfgd` が `load()` でスナップショットを取得するが、
`load()` は chrony を再起動しない（ブート時の NTP 設定は chrony 起動設定ファイルから読まれる）。
ブート後の最初の CONFIG_DB 変更イベントで初めて chrony restart が発火する。

### 5. max-elements=10 による書込み上限

YANG `max-elements 10` により `NTP_SERVER` エントリは最大 10 件に制限される。
11 件目の SET は YANG バリデーションで拒否される（YANG バリデーション層が SET 時に件数をカウント）。
エントリ削除後は再び SET が可能になる。

## 証拠リンク

- `sonic-ntp.yang`: <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-ntp.yang>
- `hostcfgd`: <https://github.com/sonic-net/sonic-host-services/blob/master/scripts/hostcfgd>
- `chrony.conf.j2`: <https://github.com/sonic-net/sonic-buildimage/blob/master/files/image_config/chrony/chrony.conf.j2>
- `minigraph.py`: <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-config-engine/minigraph.py>
