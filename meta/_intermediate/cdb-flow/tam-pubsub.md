# TAM テーブル群 — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_FEATURE_TABLE` / `TAM_INT_IFA_FLOW_TABLE`。

## 1. 直接購読者の欠如（open-source master ブランチ）

`sonic-swss/orchagent/orchdaemon.cpp` および `sonic-swss/orchagent/*.cpp` の全体を grep した結果、`TAM_DEVICE_TABLE`・`TAM_COLLECTOR_TABLE`・`TAM_INT_IFA_FEATURE_TABLE`・`TAM_INT_IFA_FLOW_TABLE` を `SubscriberStateTable` / `ConsumerStateTable` で購読するコードは**存在しない**。

orchagent 内で TAM CONFIG_DB テーブルを直接購読する Orch クラスは現在の master に存在しない。

- `portsorch.cpp` の Path Tracing TAM は `TAM_DEVICE_TABLE` を CONFIG_DB から読まず、ハードコード値（`SAI_TAM_INT_ATTR_DEVICE_ID = 0`）を使用する（`portsorch.cpp:11597-11598`）。
- `hftelorch.cpp` は HFTel プロファイル/グループ系 CONFIG_DB テーブルを購読するが、`TAM_COLLECTOR_TABLE` を直接購読しない（内部で独自 SAI TAM オブジェクトを作成する）。

## 2. CVL による入力時バリデーション（gNMI / REST 経由書き込み）

TAM テーブルへの書き込みが gNMI（`sonic-gnmi`）または REST（`sonic-mgmt-framework`）経由で行われる場合、`sonic-mgmt-common` の CVL（Config Validation Library）が以下の YANG 制約を検証する:

- `TAM_INT_IFA_FLOW_TABLE.acl-table-name` → `ACL_TABLE` の leafref 解決
- `TAM_INT_IFA_FLOW_TABLE.acl-rule-name` → `ACL_RULE` の leafref 解決
- `TAM_COLLECTOR_TABLE` の存在確認（`IFA_FLOW_TABLE.collector-name` の参照）

CVL は Redis に直接接続して leafref を解決するが、これは書き込み時の同期バリデーションであり、CONFIG_DB の keyspace 通知購読とは異なる。

## 3. CLI 書き込み経路

| 経路 | 方式 | 備考 |
|------|------|------|
| `sonic-cfggen` / `config` CLI | `ConfigDBConnector.set_entry()` → `HSET` | CONFIG_DB への直接書き込み |
| gNMI / YANG | CVL バリデーション後に Redis `HSET` | `sonic-mgmt-common` 経由 |
| REST API | 同上 | `sonic-mgmt-framework` 経由 |

`ProducerStateTable` による channel publish は行われない。

## 4. 下流への伝播なし

`TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_*` テーブルへの SET は:
- APPL_DB に転送されない
- NotificationProducer では通知されない
- orchagent は現状これらのテーブルを購読しない

ただし将来的（または platform-specific build）に IFA orch が実装された場合は `SubscriberStateTable` 経由で CONFIG_DB を購読することが期待される構造となっている（YANG モデルのフィールド設計から推定）。

## 5. 参考ソース

- `sonic-swss/orchagent/orchdaemon.cpp`（TAM 関連 TableConnector 登録なし）
- `sonic-swss/orchagent/portsorch.cpp:11597-11598`（`SAI_TAM_INT_ATTR_DEVICE_ID = 0` ハードコード）
- `sonic-swss/orchagent/hftelorch.cpp:760-790`（TAM_COLLECTOR_TABLE を読まない独自 TAM オブジェクト生成）
- `sonic-mgmt-common/cvl/testdata/schema/sonic-tam.yang`（CVL バリデーション対象）
- `sonic-mgmt-common/cvl/testdata/schema/sonic-ifa.yang:56-61`（ACL leafref）
