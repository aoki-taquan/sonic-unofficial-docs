# pki-trusted-certs — Phase B ordering 調査メモ

## 調査対象

- `sonic-mgmt-common/cvl/testdata/schema/sonic-pki.yang`
- `sonic-mgmt-common/cvl/testdata/schema/sonic-security-global.yang`
- `sonic-mgmt-common/cvl/cvl_test.go:2506-2537`
- `sonic-gnmi/gnmi_server/gnsi_certz.go:126-141,134-138,688-715`

## 検出された順序依存

### CVL leafref / instance-in-use (CONFIG_DB 操作順序)

`sonic-security-global.yang` の `security_profile` leaf は `SECURITY_PROFILES_LIST/profile-name` への leafref。
- SET 時: 参照先プロファイルが存在しないと CVL `invalid-value` エラー
- DEL 時: 参照元 (`SECURITY_GLOBAL|global`) が残っている間はプロファイル削除を CVL が `instance-in-use` でブロック

安全な操作順序:
1. `SECURITY_PROFILES|<profile>` 作成
2. `SECURITY_GLOBAL|global` の `security_profile` 設定
3. `SECURITY_GLOBAL|global` の `security_profile` 削除
4. `SECURITY_PROFILES|<profile>` 削除

### gNSI Certz STATE_DB 書込み順序

`NewGNSICertzServer()` (`gnsi_certz.go:113-160`):
1. `loadCertzMetadata` でメタデータロード (失敗時は `bootstrapDefaultProfile` でデフォルトプロファイル生成)
2. 全プロファイルに対して固定順序で `writeEntityFreshness`:
   - Cert → TrustBundle → CrlBundle → AuthPolicy
3. `saveCertzMetadata` でメタデータ保存

途中でプロセスが落ちると STATE_DB に一部エンティティのフレッシュネスのみが記録された中間状態が残る。

## 注記

community master では `SECURITY_PROFILES` を消費するハンドラが未実装のため、CONFIG_DB 書込み順序が runtime 動作に影響する経路は現時点で存在しない。CVL バリデーション層のみで有効な制約。
