# DASH_PREFIX_TAG_TABLE — Phase E: ハードコード定数調査

生成日: 2026-05-17 (q67-f-dash-prefix-tag3-next)

ソース:
- `sonic-net/sonic-swss-common/common/schema.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss/orchagent/dash/dashtagmgr.cpp`
- `sonic-net/sonic-swss/orchagent/dash/dashaclgroupmgr.cpp`
- `sonic-net/sonic-swss/orchagent/dash/pbutils.cpp`

---

## 調査対象

`DASH_PREFIX_TAG_TABLE` の処理に関係するハードコード定数。YANG / CONFIG_DB スキーマで管理されない定数のみを対象とする。

---

## 1. テーブル名定数 (schema.h)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `APP_DASH_PREFIX_TAG_TABLE_NAME` | `"DASH_PREFIX_TAG_TABLE"` | `DashAclOrch` の TaskMap でテーブル名として登録。`orchdaemon.cpp` でも Consumer 初期化に利用 | `sonic-swss-common/common/schema.h:183` |

関連テーブル名（参照チェーン全体）:

| 定数 | 値 | ソース |
|------|----|--------|
| `APP_DASH_ACL_GROUP_TABLE_NAME` | `"DASH_ACL_GROUP_TABLE"` | `schema.h:177` |
| `APP_DASH_ACL_RULE_TABLE_NAME` | `"DASH_ACL_RULE_TABLE"` | `schema.h:178` |
| `APP_DASH_ACL_IN_TABLE_NAME` | `"DASH_ACL_IN_TABLE"` | `schema.h:175` |
| `APP_DASH_ACL_OUT_TABLE_NAME` | `"DASH_ACL_OUT_TABLE"` | `schema.h:176` |

---

## 2. IP バージョン Enum 値 (pbutils.cpp + protobuf)

`to_sai(IpVersion, ...)` が受理する enum 値（`dash::types::IpVersion`）。proto3 の数値としてのデフォルトは `0` だが拒否される。

| enum 名 | 数値 | SAI 変換先 | ソース |
|--------|------|-----------|--------|
| `IP_VERSION_IPV4` | `1` | `SAI_IP_ADDR_FAMILY_IPV4` | `pbutils.cpp:13-15` |
| `IP_VERSION_IPV6` | `2` | `SAI_IP_ADDR_FAMILY_IPV6` | `pbutils.cpp:16-18` |
| `IP_VERSION_UNSPECIFIED` (proto3 デフォルト) | `0` | 拒否 (`return false`) | `pbutils.cpp:19-21` |

> **重要**: proto3 では、フィールドが明示的にセットされていない場合 enum のデフォルト値 `0` が使用される。`ip_version` を省略した protobuf メッセージは `IP_VERSION_UNSPECIFIED (0)` として届き、orchagent に無音で拒否される。

---

## 3. ACL Rule 生成時のフォールバック定数 (dashaclgroupmgr.cpp)

タグの `prefix_list` が空だった場合、`createRule()` 内の `any_ip` ラムダが group の ip_version に応じて「任意 IP」を表す `sai_ip_prefix_t` を生成する。これは TAG 自身のフィールドではないが、タグ展開の結果に影響する。

```cpp
// dashaclgroupmgr.cpp:28-29
const static vector<uint8_t> all_protocols(
    boost::counting_iterator<int>(0),
    boost::counting_iterator<int>(UINT8_MAX + 1));  // 0〜255 全プロトコル
const static vector<sai_u16_range_t> all_ports = {
    {numeric_limits<uint16_t>::min(),               // 0
     numeric_limits<uint16_t>::max()}};             // 65535
```

| 定数 | 意味 | 適用条件 |
|------|------|---------|
| `all_protocols` | uint8_t 0〜255 (全プロトコル) | ACL rule の `protocol` フィールドが空の場合 |
| `all_ports` | ポート 0〜65535 全範囲 | ACL rule の `src_port` / `dst_port` が空の場合 |

これらは TAG 処理と直接関係しないが、タグから展開された prefix セットが空の場合に `any_ip` ラムダ（`dashaclgroupmgr.cpp:266-270`）で `0.0.0.0/0` または `::/0` 相当の IP prefix が補完されることに注意。

---

## 4. ABORT_IF_NOT マクロ（防御的 assert）

`DashTagMgr::getPrefixes()` と `attach()` / `detach()` で使用される。

```cpp
// dashtagmgr.cpp:107, 117, 131
ABORT_IF_NOT(tag_it != m_tag_table.end(), "Tag %s does not exist", tag_id.c_str());
```

`ABORT_IF_NOT` は `swss::Logger::ABORT_IF_NOT` マクロで、条件が `false` の場合 `SWSS_LOG_THROW` (= `throw runtime_error`) を発生させ orchagent プロセスをクラッシュさせる。

`getPrefixes()` は `DashAclGroupMgr::createRule()` から呼ばれる前に `exists()` チェックを行うため、通常は到達しないが、ロジックバグや並列アクセスで不整合が生じた場合はプロセス停止の原因になる。

---

## 5. ハードコード定数が存在しない項目（スキーマ / YANG で管理済み）

| 項目 | 管理方法 |
|------|---------|
| `ip_version` 許容値 | protobuf enum `IpVersion` (proto definition) |
| `prefix_list` サイズ上限 | 未定義（実装上制限なし、SAI / ASIC 依存） |
| タグ名 (`tag_id`) 文字列フォーマット | 未定義（任意文字列） |
| refcount (`m_groups`) 上限 | 未定義 |
