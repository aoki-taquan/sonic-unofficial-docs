# LDAP_SERVER 値依存挙動分析

## 数値フィールド

### priority (uint8 1..8)
- 1〜8: サーバ選択優先度（大きいほど先）
- 重複: CLI 上でチェックなし → nslcd 内部挿入順依存でフェイルオーバ順序不定
- 9 件目以降: YANG スキーマ最大数制約で exit_with_error 拒否

### LDAP|global フィールド
- version (1..3): LDAP プロトコルバージョン。3 が推奨
- port: 389（LDAP）/ 636（LDAPS）で動作が異なる（TLS 有無）
- bind_timeout (1..120): デフォルト 5 秒。未設定時は YANG default 適用
- timeout: 未設定時は nslcd のデフォルト使用

## 文字列フィールド

### bind_password
- SPACE / `#` / `,` 含む: YANG pattern 検証 → exit_with_error で拒否
- 正常値: /etc/nslcd.conf の bindpw ディレクティブに書き込み

### base_dn
- 未設定: nslcd.conf に base ディレクティブが書かれずユーザ検索失敗 → 認証不可

## 結論
enum なし（優先度・タイムアウトは数値、バインド情報は文字列）。特殊値: priority 重複・base_dn 未設定が運用上の重要な条件。
