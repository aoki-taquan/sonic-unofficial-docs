# dash-acl — Phase E: コード由来の固定定数

調査対象: `orchagent/dash/dashaclgroupmgr.cpp`, `dashaclgroupmgr.h`, `dashaclorch.cpp`

## ファイルスコープ静的定数 (dashaclgroupmgr.cpp:28-29)

```cpp
// 全プロトコル (0〜255) の静的定数ベクタ
const static vector<uint8_t> all_protocols(
    boost::counting_iterator<int>(0),
    boost::counting_iterator<int>(UINT8_MAX + 1));  // 256 要素

// 全ポート範囲 (0〜65535) の静的定数
const static vector<sai_u16_range_t> all_ports = {
    {numeric_limits<uint16_t>::min(), numeric_limits<uint16_t>::max()}};  // {0, 65535}
```

これらは `translation unit` 内のファイルスコープ静的変数で、プロセス起動時に一度だけ初期化される。

## ステージ番号 enum (dashaclgroupmgr.h:19-26)

```cpp
enum class DashAclStage
{
    STAGE1, STAGE2, STAGE3, STAGE4, STAGE5,
};
```

- 有効値は `1`〜`5` のみ
- `lexical_convert` (dashaclorch.cpp:43-73) がキー文字列 `"1"`〜`"5"` を enum に変換
- 範囲外の文字列 (例: `"0"`, `"6"`) は `invalid_argument` をスローして `task_failed`

## 方向 enum (dashaclgroupmgr.h:28-32)

```cpp
enum class DashAclDirection { IN, OUT };
```

`DASH_ACL_IN_TABLE` → `DashAclDirection::IN`, `DASH_ACL_OUT_TABLE` → `DashAclDirection::OUT` と対応。

## DashAclRule::Action enum (dashaclgroupmgr.h:37-40)

```cpp
struct DashAclRule {
    enum class Action { ALLOW, DENY };
    ...
};
```

protobuf `ACTION_PERMIT` → `Action::ALLOW`, それ以外 → `Action::DENY`。

## SAI ステージマップ (dashaclgroupmgr.cpp:96-118)

`getSaiStage()` 内の静的 `std::map<tuple<...>, sai_attr_id_t>` が 20 エントリ。
`{方向, IPファミリ, ステージ}` の 3 次元キーを SAI ENI 属性 ID に 1:1 マッピング。

## DashAclGroup 初期値 (dashaclgroupmgr.h:67-88)

```cpp
struct DashAclGroup {
    sai_object_id_t m_dash_acl_group_id = SAI_NULL_OBJECT_ID;  // 作成前は NULL
    int m_rule_count = 0;                                        // ルール数カウンタ
    ...
};
```

`m_rule_count == 0` のグループへのバインドは `task_failed`（dashaclgroupmgr.cpp:451-454）。

## CRM リソースタイプ

| グループ ip_version | グループ CRM タイプ | ルール CRM タイプ |
|---|---|---|
| `SAI_IP_ADDR_FAMILY_IPV4` | `CRM_DASH_IPV4_ACL_GROUP` | `CRM_DASH_IPV4_ACL_RULE` |
| `SAI_IP_ADDR_FAMILY_IPV6` | `CRM_DASH_IPV6_ACL_GROUP` | `CRM_DASH_IPV6_ACL_RULE` |

グループ作成/削除時に `incCrmDashAclUsedCounter` / `decCrmDashAclUsedCounter` を呼び出す。
ルール作成時も同様にルール用 CRM カウンタをインクリメント。
グループ削除時の `decCrmDashAclUsedCounter` はグループ配下のルールカウンタもリセットするため、ルール個別の decrement は不要（コメント: "Will also delete/zero out ACL rule count for this group"）。

## app_db テーブル名定数

`DashAclOrch::doTask()` (dashaclorch.cpp:103-113) の TaskMap が参照するテーブル名マクロ:

| 定数名 | 値 (APP_DB テーブル名) |
|---|---|
| `APP_DASH_ACL_IN_TABLE_NAME` | `DASH_ACL_IN_TABLE` |
| `APP_DASH_ACL_OUT_TABLE_NAME` | `DASH_ACL_OUT_TABLE` |
| `APP_DASH_ACL_GROUP_TABLE_NAME` | `DASH_ACL_GROUP_TABLE` |
| `APP_DASH_ACL_RULE_TABLE_NAME` | `DASH_ACL_RULE_TABLE` |
| `APP_DASH_PREFIX_TAG_TABLE_NAME` | `DASH_PREFIX_TAG_TABLE` |

これらは swss-common の `schema.h` で定義される。
