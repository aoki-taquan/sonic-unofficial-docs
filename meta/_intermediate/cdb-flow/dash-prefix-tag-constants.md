# DASH_PREFIX_TAG_TABLE — Phase E ハードコード定数調査

調査日: 2026-05-17
対象テーブル: APP_DB `DASH_PREFIX_TAG_TABLE`

## 調査対象ファイル

- `sonic-swss-common/common/schema.h` — テーブル名マクロ
- `sonic-swss/orchagent/dash/dashtagmgr.h` — DashTag 構造体定義
- `sonic-swss/orchagent/dash/dashtagmgr.cpp` — create/update/remove/attach/detach
- `sonic-swss/orchagent/dash/dashaclorch.cpp` — PbWorker 登録・taskUpdateDashPrefixTag
- `sonic-swss/orchagent/dash/pbutils.cpp` — IpVersion/IpPrefix to_sai 変換
- `sonic-swss/orchagent/orchdaemon.cpp` — DashAclOrch 登録

---

## 1. テーブル名定数

| マクロ名 | 値 | ソース |
|---|---|---|
| `APP_DASH_PREFIX_TAG_TABLE_NAME` | `"DASH_PREFIX_TAG_TABLE"` | `schema.h:183` |

このマクロは `dashaclorch.cpp:111-112` の `PbWorker<PrefixTag>::makeMemberTask()` および `orchdaemon.cpp:1372` の `dash_acl_tables` 初期化リストで使用される。

---

## 2. IpVersion enum 定数 (protobuf 側 / pbutils.cpp)

| Protobuf 定数 | 数値 | SAI マッピング | ソース |
|---|---|---|---|
| `dash::types::IP_VERSION_IPV4` | `1` | `SAI_IP_ADDR_FAMILY_IPV4` | `pbutils.cpp:13-14` |
| `dash::types::IP_VERSION_IPV6` | `2` | `SAI_IP_ADDR_FAMILY_IPV6` | `pbutils.cpp:16-17` |
| (proto3 デフォルト / `IP_VERSION_UNSPECIFIED`) | `0` | 対応なし → `to_sai()` が `false` を返し拒否 | `pbutils.cpp:19-20` |

proto3 ルールにより、`ip_version` フィールドを省略すると数値 `0` が使用される。orchagent は `0` を受理しないため、コントローラは必ず `IP_VERSION_IPV4 (1)` または `IP_VERSION_IPV6 (2)` を明示しなければならない。

---

## 3. DashTag 内部構造体フィールド (dashtagmgr.h)

| フィールド名 | 型 | 意味 |
|---|---|---|
| `m_ip_version` | `sai_ip_addr_family_t` | `SAI_IP_ADDR_FAMILY_IPV4` / `SAI_IP_ADDR_FAMILY_IPV6` |
| `m_prefixes` | `std::vector<sai_ip_prefix_t>` | プレフィックス集合（空ベクタが許容される） |
| `m_groups` | `std::unordered_set<std::string>` | このタグを参照している ACL group ID 集合（参照カウント用、削除ガードに使用） |

---

## 4. SAI IP アドレスファミリ定数

| SAI 定数 | 値 | 用途 |
|---|---|---|
| `SAI_IP_ADDR_FAMILY_IPV4` | 列挙値 | IPv4 タグの内部表現 |
| `SAI_IP_ADDR_FAMILY_IPV6` | 列挙値 | IPv6 タグの内部表現 |

`sai_ip_addr_family_t` は SAI ヘッダで定義される enum。orchagent は protobuf の `ip_version` 値をこの SAI enum に変換して内部管理する (`pbutils.cpp:9-24`)。

---

## 5. orchdaemon 登録コンテキスト

`orchdaemon.cpp:1371-1378` にて `DashAclOrch` は以下の 5 テーブルを一括購読する:

```cpp
vector<string> dash_acl_tables = {
    APP_DASH_PREFIX_TAG_TABLE_NAME,   // L1372
    APP_DASH_ACL_IN_TABLE_NAME,       // L1373
    APP_DASH_ACL_OUT_TABLE_NAME,      // L1374
    APP_DASH_ACL_GROUP_TABLE_NAME,    // L1375
    APP_DASH_ACL_RULE_TABLE_NAME      // L1376
};
DashAclOrch *dash_acl_orch = new DashAclOrch(m_dpu_appDb, dash_acl_tables, ...);  // L1378
```

`DASH_PREFIX_TAG_TABLE` は ACL 系テーブルの中で最初に列挙されており、`DashAclOrch` が単一の Orch インスタンスで全 ACL テーブルを購読する設計になっている。

---

## 6. ハードコード制限値

以下はコード上に明示的な定数定義はないが、実装上の固定制限として機能する:

| 制限 | 実装上の根拠 | 実質値 |
|---|---|---|
| `ip_version` 変更禁止 | `dashtagmgr.cpp:61-65` の `if (tag.m_ip_version != new_tag.m_ip_version)` チェック | タグ作成後は不変 |
| prefix_list の上限 | コード上の明示制限なし。SAI / ASIC 実装依存 | 実装定義 |
| タグ名長の制限 | コード上の明示制限なし。APP_DB キーサイズ制限に従う | 実装定義 |

---

## 調査結論

`DASH_PREFIX_TAG_TABLE` のハードコード定数は少数で構造がシンプル:

1. **テーブル名マクロ** `APP_DASH_PREFIX_TAG_TABLE_NAME = "DASH_PREFIX_TAG_TABLE"` (schema.h:183)
2. **IpVersion enum** — proto3 値 `1 (IPV4)` / `2 (IPV6)` のみ受理。`0 (UNSPECIFIED)` は拒否 (pbutils.cpp:9-24)
3. **DashTag 構造体** — 3 フィールド (`m_ip_version`, `m_prefixes`, `m_groups`)。SAI に直接マッピングされない orchagent 内メモリオブジェクト
4. 設定可能な上限値・タイムアウト・デフォルトポートといった「運用系定数」はなし（DASH タグは pure ソフトウェア管理、SAI 書き込みなし）
