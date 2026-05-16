# DASH_PREFIX_TAG_TABLE フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: APP_DB `DASH_PREFIX_TAG_TABLE` (ZMQ 経由で CONFIG_DB 相当の役割)

## 調査対象ファイル

- `sonic-swss/orchagent/dash/dashtagmgr.cpp` (`from_pb`, `DashTagMgr::create`, `update`)
- `sonic-swss/orchagent/dash/dashtagmgr.h` (DashTag 構造体定義)
- `sonic-swss/orchagent/dash/dashaclorch.cpp` (`taskUpdateDashPrefixTag`)
- `sonic-swss/orchagent/dash/pbutils.cpp` (`to_sai` IpVersion / IpPrefix / prefix_list 変換)
- `sonic-swss/tests/dash/test_dash_acl.py` (`create_prefix_tag` テストヘルパー)
- `sonic-utilities/dump/plugins/dash_prefix_tag.py` (Dump プラグイン)

---

## テーブル構造

`DASH_PREFIX_TAG_TABLE` は protobuf エンコード (`pb` フィールド) でデータを受信する。
`PbWorker<PrefixTag>` が `dashaclorch.cpp:111` で購読を設定し、
`taskUpdateDashPrefixTag` → `from_pb(data, tag)` → `DashTagMgr::create/update` の順に処理される。

`PrefixTag` protobuf メッセージのフィールド (`dashtagmgr.cpp:11,16` から逆引き):

```cpp
// dashtagmgr.cpp:9-22
bool from_pb(const dash::tag::PrefixTag& data, DashTag& tag)
{
    if (!to_sai(data.ip_version(), tag.m_ip_version))
        return false;
    if(!to_sai(data.prefix_list(), tag.m_prefixes))
        return false;
    return true;
}
```

フィールド一覧:
- `ip_version`: `dash::types::IpVersion` enum (IP_VERSION_IPV4 / IP_VERSION_IPV6)
- `prefix_list`: `repeated IpPrefix` (ip + mask の繰り返し)

---

## フィールド別 暗黙デフォルト

### `ip_version`

**コード由来デフォルト**: なし (必須フィールド扱い)

```cpp
// dashtagmgr.cpp:11-13
if (!to_sai(data.ip_version(), tag.m_ip_version))
{
    return false;  // 変換失敗でエントリ全体を拒否
}
```

proto3 の enum デフォルト値は `0` だが、`to_sai(pbutils.cpp:9-24)` は
`IP_VERSION_IPV4 (1)` / `IP_VERSION_IPV6 (2)` のみを受け付け、
それ以外 (proto3 デフォルト値 `0 = IP_VERSION_UNSPECIFIED` 含む) は `false` を返す。

つまり `ip_version` が未設定 / 不正値の場合は `from_pb` が `false` → `task_failed` が返り、
タグエントリ全体が登録されない。**実質的に必須フィールド**。

更新時は `ip_version` の変更が禁止される (`dashtagmgr.cpp:61-65`):
```cpp
if (tag.m_ip_version != new_tag.m_ip_version)
{
    SWSS_LOG_WARN("'ip_version' changing is not supported for tag %s", tag_id.c_str());
    return task_failed;
}
```

### `prefix_list`

**コード由来デフォルト**: 空リスト (登録は成功する)

```cpp
// dashtagmgr.cpp:16-19
if(!to_sai(data.prefix_list(), tag.m_prefixes))
    return false;
```

`pbutils.cpp:74-93` の `to_sai(RepeatedPtrField<IpPrefix>, vector<sai_ip_prefix_t>)` は
空リストの場合 `sai_prefixes.clear()` → 即 `return true`。
エントリの登録は成功し、prefixes は空ベクタになる。

更新時 (`dashtagmgr.cpp:68`):
```cpp
tag.m_prefixes = new_tag.m_prefixes;
```
新しい prefix リストで上書き。空リストによる全削除も許容される。

---

## 制約・特殊挙動

| 条件 | 挙動 |
|------|------|
| `ip_version` が未設定 (proto3 デフォルト `0`) | `to_sai` が `false` → `task_failed` でエントリ拒否 |
| `ip_version` が不正値 | 同上 |
| `prefix_list` が空 | 登録成功、空の prefix セット |
| 既存タグの `ip_version` を変更しようとした場合 | `SWSS_LOG_WARN` + `task_failed` |
| タグが ACL rule から参照中に `remove` | `task_need_retry` (m_groups が空でない) |
| タグが未存在で `remove` | `task_success` (idempotent、警告ログのみ) |

---

## 調査結論

`DASH_PREFIX_TAG_TABLE` のフィールドは 2 つのみ (`ip_version`, `prefix_list`)。

- `ip_version`: proto3 デフォルト値 (`0`) は orchagent が reject するため **実質必須**。コントローラは必ず `IP_VERSION_IPV4` または `IP_VERSION_IPV6` を明示する必要がある。
- `prefix_list`: 空リストを許容するが、空タグは ACL マッチに使えないため、通常は 1 件以上の prefix を含む。コード上のデフォルトは「空」。

いずれも SAI 属性への直接マッピングは行わず、タグは orchagent 内メモリ (`m_tag_table`) にのみ保持される (SAI DASH ACL group の prefix 集合として参照される)。
