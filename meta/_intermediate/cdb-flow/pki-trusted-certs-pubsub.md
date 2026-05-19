# pki-trusted-certs pubsub research (Phase G)

## 調査対象

- `sonic-gnmi/gnmi_server/gnsi_certz.go`
- `sonic-swss/` (SECURITY_PROFILES/SECURITY_GLOBAL キーワード検索)
- `sonic-swss-common/` (同上)

## 調査日

2026-05-19

## 調査結果

### 購読者の有無

SECURITY_PROFILES / SECURITY_GLOBAL を購読するプロセスは community master で検出されなかった。

- `sonic-pki.yang` は `sonic-buildimage/src/sonic-yang-models/yang-models/` に未マージ。
- `sonic-swss`, `sonic-swss-common` 内で SECURITY_PROFILES / SECURITY_GLOBAL のキーワード一致なし。
- `sonic-gnmi/gnmi_server/gnsi_certz.go` は `ConfigDBConnector.subscribe()` / `SubscriberStateTable` / `ConsumerStateTable` を使用しない。

### gNSI Certz の DB 使用

gNSI Certz は STATE_DB (`CREDENTIALS|CERT|<profileID>`) に直接 HSET で書き込む（Phase F 参照）。
CONFIG_DB の `SECURITY_PROFILES` / `SECURITY_GLOBAL` テーブルは参照しない。

### 結論

Phase G ブロックは「購読者なし」として記述。
