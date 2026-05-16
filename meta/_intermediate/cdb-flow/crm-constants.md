# CRM Phase E — ハードコード定数抽出

ソース: `sonic-swss/orchagent/crmorch.cpp`
対象ページ: `docs/reference/config-db/crm.md`

## 抽出した定数

### プリプロセッサ定数 (crmorch.cpp L9-17)

```cpp
#define CRM_POLLING_INTERVAL          "polling_interval"
#define CRM_COUNTERS_TABLE_KEY        "STATS"
#define CRM_POLLING_INTERVAL_DEFAULT  (5 * 60)   // = 300 秒
#define CRM_THRESHOLD_TYPE_DEFAULT    CrmThresholdType::CRM_PERCENTAGE
#define CRM_THRESHOLD_LOW_DEFAULT     70
#define CRM_THRESHOLD_HIGH_DEFAULT    85
#define CRM_EXCEEDED_MSG_MAX          10
#define CRM_ACL_RESOURCE_COUNT        256
```

### コンストラクタでの適用 (crmorch.cpp L398-410)

```cpp
CrmOrch::CrmOrch(DBConnector *db, string tableName):
    m_timer(new SelectableTimer(timespec { .tv_sec = CRM_POLLING_INTERVAL_DEFAULT, .tv_nsec = 0 }))
{
    // ...
    m_pollingInterval = chrono::seconds(CRM_POLLING_INTERVAL_DEFAULT);
    for (auto res : crmResTypeNameMap) {
        m_resourcesMap.emplace(res.first, CrmResourceEntry(res.second,
            CRM_THRESHOLD_TYPE_DEFAULT,
            CRM_THRESHOLD_LOW_DEFAULT,
            CRM_THRESHOLD_HIGH_DEFAULT));
    }
}
```

すべてのリソースに同一デフォルト値 (percentage / 70% / 85%) が適用される。

### CrmThresholdType enum (crmorch.cpp L299-303)

| enum 値 | CONFIG_DB 文字列 |
|---------|----------------|
| `CRM_PERCENTAGE` | `"percentage"` |
| `CRM_USED` | `"used"` |
| `CRM_FREE` | `"free"` |

### CrmResourceType enum — crmResTypeNameMap (crmorch.cpp L28-72)

42 リソースタイプ。標準スイッチ系 (IPv4/IPv6/FDB/ACL/NAT/MPLS/SRv6 等) + DASH 系 + TWAMP。
フル一覧は `docs/reference/config-db/crm.md` の `<!-- constants -->` ブロックを参照。

## 差分まとめ

- `<!-- entry-points -->` の「ハードコードデフォルト」を「なし」→ 定数表に更新
- `<!-- constants --> … <!-- /constants -->` ブロックを新規追加
- 他フェーズブロック (cdb-mermaid / cdb-exceptions / value-behavior / runtime-trace / derivation / handler-branching) は変更なし
