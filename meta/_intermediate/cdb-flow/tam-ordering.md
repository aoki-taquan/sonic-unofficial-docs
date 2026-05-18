# TAM テーブル群 書込み順依存調査 (Phase B)

## 調査対象
- `TAM_DEVICE_TABLE`
- `TAM_COLLECTOR_TABLE`
- `TAM_INT_IFA_FEATURE_TABLE`
- `TAM_INT_IFA_FLOW_TABLE`

## ソース
- `sonic-mgmt-common/cvl/testdata/schema/sonic-tam.yang`
- `sonic-mgmt-common/cvl/testdata/schema/sonic-ifa.yang`
- `sonic-swss/orchagent/high_frequency_telemetry/hftelorch.cpp`

## 調査結果

### TAM_COLLECTOR_TABLE は TAM_INT_IFA_FLOW_TABLE より先に書く必要がある

`sonic-ifa.yang` の `TAM_INT_IFA_FLOW_TABLE` フィールド `collector-name` は string 型（leafref ではない）だが、
CVL が `TAM_COLLECTOR_TABLE` のエントリを参照チェックする実装が
`cvl_leafref_test.go:200-249` で確認されている。
コレクタ名が `TAM_COLLECTOR_TABLE` に存在しないとCVL バリデーションが失敗する。

### ACL_TABLE および ACL_RULE は TAM_INT_IFA_FLOW_TABLE より先

`TAM_INT_IFA_FLOW_TABLE` の `acl-table-name` は `leafref → ACL_TABLE.aclname`、
`acl-rule-name` は `leafref → ACL_RULE.rulename` であり YANG で明示的に定義。
CVL は leafref 解決を行うため、対応する ACL エントリが先に CONFIG_DB に存在していなければならない。

### TAM_INT_IFA_FEATURE_TABLE は依存なし

singleton で他テーブルへの leafref 参照を持たない。任意の順序で書ける。

### TAM_DEVICE_TABLE は依存なし

singleton で `deviceid` のみ保持。任意の順序で書ける。

### orchagent 側の処理経路

コミュニティ edition の orchagent に `TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / 
`TAM_INT_IFA_*` を直接購読するハンドラは存在しない（sonic-swss/orchagent 内で
これらのテーブル名への参照はゼロ）。
`hftelorch.cpp` は SAI TAM オブジェクトを内部的に生成するが、
CONFIG_DB の TAM テーブルを読まない。

TAM テーブルは主に Management フレームワーク（GNMI/REST）経由での設定検証（CVL）と、
将来の IFA 実装向けのスキーマ定義として位置付けられる。
