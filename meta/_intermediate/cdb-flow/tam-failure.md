# TAM テーブル群 失敗挙動調査 (Phase D)

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

### CVL バリデーション失敗（Management Framework 経由）

Management Framework (GNMI/REST) 経由の書込みは CVL（sonic-mgmt-common）が検証を行う。

**TAM_COLLECTOR_TABLE への SET 失敗条件:**
- `ipaddress-type` と `ipaddress` の不整合 — IPv6 アドレス（`:` 含む）で `ipaddress-type=ipv4` を指定、
  または IPv4 アドレス（`.` 含む）で `ipaddress-type=ipv6` を指定した場合、
  YANG `must` 制約（`error-app-tag: ipaddres-type-mismatch`）で CVL がリジェクトする。
  (`sonic-tam.yang: must 制約`)

**TAM_INT_IFA_FLOW_TABLE への SET 失敗条件:**
- `acl-table-name` が `ACL_TABLE` に存在しない — YANG leafref 制約で CVL が拒否する。
- `acl-rule-name` が `ACL_RULE|<acl-table-name>` 下に存在しない — 連鎖 leafref で CVL が拒否する。
- `collector-name` が `TAM_COLLECTOR_TABLE` に存在しない — CVL must 制約で拒否される。
- `sampling-rate` が範囲外（0 または 10001 以上）— YANG range 制約 `error-app-tag "Invalid IFA flow sampling rate."` でリジェクト。
  (`sonic-ifa.yang:73`)

### orchagent 側の失敗挙動（HFTelOrch）

`hftelorch.cpp` は CONFIG_DB の TAM テーブルを直接購読しないが、
SAI 能力チェックの失敗で HFTel 機能が全体的に無効化される経路がある。

**起動時 SAI 能力クエリ失敗（`isSupportedByHFTel()`）:**
- `sai_query_attribute_capability()` が `SAI_STATUS_SUCCESS` 以外を返した場合 — NOTICE ログ出力 → `return false` → HFTel 機能全体を無効化。
  (`hftelorch.cpp:199`)
- 必須 SAI 属性の create/set 能力が欠如している場合（例: `SAI_TAM_COLLECTOR_ATTR_*` create not supported）— NOTICE ログ → HFTel 無効化。
  (`hftelorch.cpp:202-209`)
- `SAI_TAM_TRANSPORT_TYPE_NONE` または `SAI_TAM_BIND_POINT_TYPE_SWITCH` が enum 値として未サポートの場合 — NOTICE ログ → HFTel 無効化。
  (`hftelorch.cpp:244`)

**初期化失敗（コンストラクタ）:**
- `SAI_SWITCH_ATTR_TAM_TEL_TYPE_CONFIG_CHANGE_NOTIFY` 設定失敗 — ERROR ログ + `runtime_error` 例外送出。
  (`hftelorch.cpp:88-89`)
- `SAI_SWITCH_ATTR_TAM_OBJECT_ID` 設定失敗 — ERROR ログ + `runtime_error` 例外送出。
  (`hftelorch.cpp:829-831`)

**doTask() でのタスク処理失敗:**
- 未知のテーブル名 — ERROR ログ (`Unknown table %s`) → `task_failed`。
  (`hftelorch.cpp:623`)
- 未知のオペレーション型 — ERROR ログ (`Unknown operation type %s`) → `task_failed`。
  (`hftelorch.cpp:598, 618`)
- タスク処理例外 — ERROR ログ (`Failed to process the task`) → `task_failed` → 永続スキップ。
  (`hftelorch.cpp:628-633`)

**プロファイル/グループ操作の一時失敗（task_need_retry）:**
- プロファイルが `canBeUpdated()=false`（ストリームが stop 状態でない）— `task_need_retry`。
  (`hftelorch.cpp:275`)
- グループがプロファイル未発見 — `task_need_retry`。
  (`hftelorch.cpp:340-345`)
- グループが stop stream 状態でない — `task_need_retry`。
  (`hftelorch.cpp:362-369`)

### sonic-db-cli 直接書込み時の挙動

`sonic-db-cli` は CVL をバイパスするため、YANG 制約（must / leafref / range）はすべてスキップされる。
正当でない値（型不整合、leafref 未解決、範囲外の `sampling-rate`）もエラーなく書き込まれる。
ただし、orchagent がこれらのテーブルを直接購読しないため、SAI への反映も行われない。
