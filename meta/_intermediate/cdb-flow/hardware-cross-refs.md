# HARDWARE テーブル — Phase C 暗黙参照調査

## 調査目的

`HARDWARE|ACCESS_LIST` の暗黙参照・共依存コンポーネントを特定する。

## 調査結果

### community sonic-swss (orchagent)

`grep -rn 'COUNTER_MODE\|LOOKUP_MODE\|TCAM_SHARING\|HARDWARE.*ACCESS_LIST' sonic-swss/` — **0 件**。
`aclorch.cpp` に `HARDWARE` テーブルの参照なし。

### sonic-gnmi

testdata (`testdata/db_dump.json`) にのみ `HARDWARE|ACCESS_LIST` と `HARDWARE_TABLE|ACCESS_LIST` が出現。
gNMI の本番コード (`go/` ディレクトリ) には参照なし。

### sonic-mgmt-common

`tools/test/dbinit.py:88-90` に `HARDWARE|ACCESS_LIST` の書き込みが存在するが、テスト初期化スクリプトのみ。
translib の transformer コード (`go/`) には `HARDWARE` テーブルへの参照なし (community リポジトリ内)。

### sonic-utilities

`HARDWARE`, `COUNTER_MODE`, `LOOKUP_MODE`, `TCAM_SHARING` の参照 0 件。

### ACL_TABLE / ACL_RULE との関係

`HARDWARE|ACCESS_LIST` は設計上 ACL ハードウェアモードを設定するためのテーブルだが、
community `aclorch.cpp` は ACL_TABLE / ACL_RULE のみを購読し HARDWARE テーブルは無視する。
leafref 定義も YANG モジュールも存在しないため、ACL_TABLE・ACL_RULE との間に実装上の結合はない。

## 結論

HARDWARE テーブルは **dead consumer** であり、community コードパスにおいて他テーブルへの
leafref 参照も、他コンポーネントからの暗黙依存も存在しない。
暗黙参照は「存在しないことの確認」として記録する。
