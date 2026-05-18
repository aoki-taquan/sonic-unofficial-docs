# RESTAPI テーブル — 書込み順依存 (Phase B) 調査メモ

調査日: 2026-05-18
対象ファイル: docs/reference/config-db/restapi.md

## 調査ソース

- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/supervisord.conf`
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/rest-server.sh`
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/mgmt_vars.j2`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` L2689-2702
- `sonic-utilities/scripts/db_migrator.py` L608-619

## コンテナ起動シーケンス

supervisord.conf より:

```
1. rsyslogd 起動 (priority=1)
2. start.sh 実行 (priority=2, wait_for=rsyslogd:running)
   └─ FEATURE テーブル確認・前処理
3. rest-server.sh 実行 (priority=3, wait_for=start:exited)
   └─ mgmt_vars.j2 テンプレート展開
   └─ RESTAPI|certs / RESTAPI|config 読込み
   └─ DEVICE_METADATA|x509 フォールバック読込み
   └─ rest_server バイナリ起動
```

## 主要な書込み順依存

1. minigraph.py が RESTAPI を書き込む（FEATURE テーブルと同じタイミング）
2. DEVICE_METADATA|x509 が先に書き込まれていると、RESTAPI|certs 未設定時にフォールバック参照される
3. db_migrator.py が 既存エントリ未設定時のみ書き込む（既存エントリが優先）
4. rest-server.sh は `start:exited` 待機後に起動 → CONFIG_DB への書込みが必ず先行
