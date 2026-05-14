# subnet-decap — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`SUBNET_DECAP`

## 段階 1: Consumer 登録

- **orchagent / SubnetDecapOrch**: `SUBNET_DECAP` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- SubnetDecapOrch がサブネット範囲とデカプセルアクションを解析。APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- orchagent が `sai_tunnel_api` または `sai_acl_api` でサブネット単位のデカプセルルールを設定。

## 段階 4: タイミング + 副作用

- 設定反映は orchagent 処理後数 ms 以内。
- 副作用: サブネット範囲の重複があると ACL リソース競合が発生する可能性。
