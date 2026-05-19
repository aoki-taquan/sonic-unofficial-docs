# RESTAPI — 副次 DB 書込 (Phase F) 解析メモ

対象: CONFIG_DB `RESTAPI|config` / `RESTAPI|certs`

ソース確認:
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/rest-server.sh`
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/supervisord.conf`
- `sonic-host-services/scripts/hostcfgd`
- `sonic-utilities/config/main.py`

## 1. RESTAPI テーブルの副次書込パターン — 「書込なし」パターン

`RESTAPI` テーブルへの書込は `rest-server.sh` 起動スクリプト経由で `rest_server` プロセスに反映されるが、
CONFIG_DB への書込が他の DB（APPL_DB / STATE_DB / ASIC_DB）への副次書込を直接引き起こすことは**ない**。

```
CONFIG_DB RESTAPI|config (SET/DEL)
  └─ 変更はファイルシステム・他 DB へは伝播しない
  └─ rest-server コンテナ再起動時に sonic-cfggen が一括読み取り
```

## 2. rest-server.sh の一括読み取りモデル

`rest-server.sh` は起動時に `sonic-cfggen -d -t $MGMT_VARS_FILE` を **一度だけ** 実行し、
CONFIG_DB から `RESTAPI|config` と `DEVICE_METADATA|x509` の値を取得して
`rest_server` プロセスの起動引数に組み込む (`rest-server.sh:13-66`)。

起動後は CONFIG_DB を購読せず、`RESTAPI` テーブルの変更は実行中の `rest_server` には届かない。
設定変更を反映するにはコンテナ再起動が必要。

## 3. FIPS モード変更による間接的なサービス再起動

`hostcfgd` は FIPS 設定変更時に `DEFAULT_FIPS_RESTART_SERVICES` リストに含まれる
サービスを再起動する (`hostcfgd:103`)。`restapi` がそのリストに含まれる:

```python
# hostcfgd:103
DEFAULT_FIPS_RESTART_SERVICES = ['ssh', 'telemetry.service', 'restapi']
```

これは `RESTAPI` テーブル変更による副次処理ではなく、`FIPS_CFG` テーブル変更を受けた
`hostcfgd` が副次的に `restapi` サービスを再起動するというフロー。
`RESTAPI` テーブルの変更自体はこの経路を引き起こさない。

## 4. rest_server 実行時の書込（Config 変更とは独立）

起動中の `rest_server` は REST API / gNMI リクエストを受けて APPL_DB へのトランザクションを
書き込むことがあるが、これは `RESTAPI` テーブルへの書込が引き起こすものではなく、
外部からの REST/gNMI リクエストが引き起こすものである。`RESTAPI|config` フィールド変更の
直接的な副次 DB 書込は**存在しない**。

## 結論

| 対象 | 副次書込の有無 | 理由 |
|------|-------------|------|
| APPL_DB | なし | `rest-server.sh` は起動時一括読み取りのみ |
| STATE_DB | なし | RESTAPI 変更を購読するデーモンなし |
| ASIC_DB | なし | SAI 非経由 |
| ファイルシステム | なし | 起動引数として適用されるのみ |
| サービス再起動 | なし (直接) | `RESTAPI` 変更は再起動をトリガーしない。手動での `config reload` が必要 |
