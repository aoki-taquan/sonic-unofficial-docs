# TAM テーブル — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-19 (chore/q67-f-phaseB-aclorch-state)
対象ページ: `docs/reference/config-db/tam.md`
対象テーブル: `TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_FEATURE_TABLE` / `TAM_INT_IFA_FLOW_TABLE`

---

<!-- failure -->
## Phase D: 失敗挙動マトリクス

TAM テーブル群の失敗経路は **2 つのレイヤ** に分かれる。(1) Management Framework 経由での設定時に CVL が検出する YANG 制約違反、(2) orchagent（portsorch / HFTelOrch）が SAI 操作を行う際のランタイム失敗。なお、コミュニティ版 orchagent には `TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_*` を直接 CONFIG_DB から購読するハンドラが存在しないため、`sonic-db-cli` による直接書き込みは CVL をバイパスし SAI への反映も起こらない。

### A. CVL バリデーション失敗（Management Framework 経由）

| # | 操作 | 失敗条件 | エラー種別 | ErrAppTag | 結果 | 根拠 |
|---|------|---------|-----------|-----------|------|------|
| 1 | `TAM_COLLECTOR_TABLE` CREATE | `ipaddress-type=ipv6` かつ `ipaddress` が IPv4 形式（`.` 含む）、またはその逆 | `CVL_SEMANTIC_ERROR` | `ipaddres-type-mismatch` | GNMI/REST が `400 Bad Request` を返す。DB への書き込みは行われない | `sonic-mgmt-common/cvl/cvl_must_test.go:443-467` |
| 2 | `TAM_INT_IFA_FLOW_TABLE` CREATE | `acl-table-name` が `ACL_TABLE` に存在しない、または `acl-rule-name` が `ACL_RULE|<acl-table-name>|<acl-rule-name>` として存在しない | `CVL_SEMANTIC_DEPENDENT_DATA_MISSING` | `instance-required` | 同上。エラーメッセージ `"No instance found for '<rule-name>'"` | `sonic-mgmt-common/cvl/cvl_leafref_test.go:214-260` |
| 3 | `TAM_INT_IFA_FLOW_TABLE` CREATE | `collector-name` に指定した名前が `TAM_COLLECTOR_TABLE` に存在しない | `CVL_SEMANTIC_ERROR`（must 制約） | — | 同上 | `sonic-mgmt-common/cvl/cvl_must_test.go:444-461` |
| 4 | `TAM_INT_IFA_FLOW_TABLE.sampling-rate` | 値が範囲外（0 または 10001+） | `CVL_SYNTAX_RANGE` | `"Invalid IFA flow sampling rate."` | 同上 | `sonic-ifa.yang` の range 制約 `1..10000` |

!!! note "CVL は GNMI/REST 専用"
    CVL バリデーションは `sonic-mgmt-common` の Management Framework 経由でのみ発動する。`sonic-db-cli CONFIG_DB hmset` などで直接書き込む場合は上記制約が適用されず、不整合なエントリが DB に残る。orchagent は TAM テーブルを購読しないため、この不整合が SAI に伝播することもない（IFA 機能自体が orchagent 非実装）。

### B. HFTelOrch 初期化失敗（TAM_COLLECTOR_TABLE への間接影響）

`TAM_COLLECTOR_TABLE` は HFTelOrch（High Frequency Telemetry）が SAI TAM Collector オブジェクト生成に参照する。ただし HFTelOrch は CONFIG_DB の `TAM_COLLECTOR_TABLE` を直接購読するのではなく、SAI TAM 能力チェック → 独自の SAI オブジェクト作成という流れで動作する。

| # | 失敗条件 | 検出箇所 | 結果 | ログ |
|---|---------|---------|------|------|
| 5 | `sai_query_stats_st_capability` が `SAI_STATUS_SUCCESS` / `SAI_STATUS_BUFFER_OVERFLOW` 以外 | `HFTelOrch::isSupportedHFTel()` L177 | `HFTel disabled`（HFTelOrch が無効化される）。TAM Collector SAI オブジェクト未作成 | `NOTICE "Streaming stats not supported, HFTel disabled"` |
| 6 | `sai_query_attribute_capability` で `SAI_OBJECT_TYPE_TAM_COLLECTOR` 属性のいずれかが失敗または `create_implemented=false` | `isSupportedHFTel()` L199/205 | 同上 | `NOTICE "HFTel: <attr> capability query failed, HFTel disabled"` / `"HFTel: <attr> create not supported, HFTel disabled"` |
| 7 | `sai_tam_api->set_switch_attribute(SAI_SWITCH_ATTR_TAM_TEL_TYPE_CONFIG_CHANGE_NOTIFY)` 失敗 | `HFTelOrch::HFTelOrch()` L88 | `runtime_error` throw → orchagent プロセス abort → systemd で再起動 | `ERROR "Failed to set SAI_SWITCH_ATTR_TAM_TEL_TYPE_CONFIG_CHANGE_NOTIFY"` |
| 8 | `sai_tam_api->set_switch_attribute(SAI_SWITCH_ATTR_TAM_OBJECT_ID)` 失敗 | `HFTelOrch::HFTelOrch()` L831 | 同上 | `ERROR "Failed to set SAI_SWITCH_ATTR_TAM_OBJECT_ID"` |

### C. portsorch Path Tracing TAM 失敗（TAM_DEVICE_TABLE への間接影響）

`portsorch.cpp` は Path Tracing 機能のために SAI TAM オブジェクトを作成する際、`TAM_DEVICE_TABLE.deviceid` を参照するが、CONFIG_DB から直接読み込む実装は確認できない（`SAI_TAM_INT_ATTR_DEVICE_ID` に固定値 `0` を設定している）。

| # | 失敗条件 | 検出箇所 | 結果 | ログ |
|---|---------|---------|------|------|
| 9 | `sai_tam_api->create_tam_report()` 失敗 | `createPtTam()` `portsorch.cpp:11574` | `handleSaiCreateStatus` → 失敗時 `createAndSetPortPtTam()` が `false` を返す。当該ポートへの Path Tracing TAM 設定未反映 | `ERROR "Failed to create TAM Report object for Path Tracing, rv:%d"` |
| 10 | `sai_tam_api->create_tam_int()` 失敗（SAI_TAM_INT_TYPE_PATH_TRACING） | `createPtTam()` `portsorch.cpp:11619` | 同上 | `ERROR "Failed to create TAM INT object for Path Tracing, rv:%d"` |
| 11 | `sai_tam_api->create_tam()` 失敗 | `createPtTam()` `portsorch.cpp:L11427` | 同上 | `ERROR "Failed to create TAM object for Path Tracing"` |
| 12 | `setPortPtTam()` 失敗（`sai_port_api->set_port_attribute(SAI_PORT_ATTR_TAM_OBJECT)` 失敗） | `createAndSetPortPtTam()` L11436 | `createAndSetPortPtTam()` が `false` を返す。当該ポートの TAM オブジェクト未割り当て | `ERROR "Failed to set port %s TAM object for Path Tracing"` |

!!! note "Path Tracing の TAM と TAM_DEVICE_TABLE の関係"
    portsorch は `TAM_DEVICE_TABLE.deviceid` を CONFIG_DB から読み込まず、`SAI_TAM_INT_ATTR_DEVICE_ID` を初期化時に常に `0` で設定する（`portsorch.cpp:11597-11599`）。`TAM_DEVICE_TABLE` への書き込みは Path Tracing の SAI 挙動に影響しない（IFA パスも orchagent 非実装）。

### D. STATE_DB / ERROR_TABLE への記録

TAM テーブル群に対応する STATE_DB への書き込みはなし。失敗情報は syslog のみに出力される。CVL エラーは GNMI/REST レスポンスのエラーボディとして呼び出し元に返される。

```bash
# orchagent ログ確認（swss コンテナ内）
docker logs swss 2>&1 | grep -E "TAM|HFTel|Path Tracing"
# または syslog
journalctl -u swss | grep -E "TAM|IFA|HFTel"
```

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|------|--------|------|
| `HFTelOrch::isSupportedHFTel` capability check | 8 | `hftelorch.cpp:183-199, 244` |
| `runtime_error` throw（初期化失敗） | 2 | `hftelorch.cpp:89, 831` |
| `createPtTam` SAI 失敗 | 3 | `portsorch.cpp:11574, 11619, 11427` |
| `setPortPtTam` 失敗 | 2 | `portsorch.cpp:11436, 11458` |
| CVL must test (TAM_COLLECTOR ipaddress-type) | 1 | `cvl_must_test.go:443-467` |
| CVL leafref test (TAM_INT_IFA_FLOW leafref failure) | 1 | `cvl_leafref_test.go:214-260` |

<!-- /failure -->
