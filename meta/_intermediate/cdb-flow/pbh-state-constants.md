# STATE_DB PBH_CAPABILITIES — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/pbh/pbhcap.cpp` (C++ 側 define 定数 + STATE_DB 接続パラメータ)
- `sonic-swss/orchagent/pbh/pbhschema.h` (フィールド名文字列定数)
- `sonic-swss-common/common/schema.h` (テーブル名定数 `STATE_PBH_CAPABILITIES_TABLE_NAME`)
- `sonic-utilities/config/plugins/pbh.py` (Python 側定数ミラー)

---

## 1. STATE_DB 接続パラメータ (pbhcap.cpp L35–36)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PBH_STATE_DB_NAME` | `"STATE_DB"` | `DBConnector` 初期化時の DB 名。静的メンバ `PbhCapabilities::stateDb` に使用 | `pbhcap.cpp:35` |
| `PBH_STATE_DB_TIMEOUT` | `0` (ms) | DB 接続タイムアウト (0 = ブロッキング、タイムアウトなし) | `pbhcap.cpp:36` |
| `STATE_PBH_CAPABILITIES_TABLE_NAME` | `"PBH_CAPABILITIES"` | `Table` オブジェクト初期化時のテーブル名 | `sonic-swss-common/common/schema.h:419` |

---

## 2. プラットフォーム識別定数 (pbhcap.cpp L20–23)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PBH_PLATFORM_ENV_VAR` | `"ASIC_VENDOR"` | ベンダー識別に使う環境変数名。`parsePbhAsicVendor()` が `getenv()` で読み取る | `pbhcap.cpp:20` |
| `PBH_PLATFORM_GENERIC` | `"generic"` | Generic プラットフォームの識別文字列。未設定時の fallback 値 | `pbhcap.cpp:21` |
| `PBH_PLATFORM_MELLANOX` | `"mellanox"` | Mellanox プラットフォームの識別文字列。`parsePbhAsicVendor()` で大文字小文字区別なしで照合 | `pbhcap.cpp:22` |
| `PBH_PLATFORM_UNKN` | `"unknown"` | ログ出力専用の未知プラットフォーム文字列。分岐には使用されない | `pbhcap.cpp:23` |

---

## 3. STATE_DB キー名定数 (pbhcap.cpp L25–28)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PBH_TABLE_CAPABILITIES_KEY` | `"table"` | `PBH_CAPABILITIES\|table` サブキー名。テーブルレベル能力の書き込み・読み取りに使用 | `pbhcap.cpp:25` |
| `PBH_RULE_CAPABILITIES_KEY` | `"rule"` | `PBH_CAPABILITIES\|rule` サブキー名 | `pbhcap.cpp:26` |
| `PBH_HASH_CAPABILITIES_KEY` | `"hash"` | `PBH_CAPABILITIES\|hash` サブキー名 | `pbhcap.cpp:27` |
| `PBH_HASH_FIELD_CAPABILITIES_KEY` | `"hash-field"` | `PBH_CAPABILITIES\|hash-field` サブキー名 | `pbhcap.cpp:28` |

---

## 4. フィールド操作能力文字列定数 (pbhcap.cpp L30–33)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PBH_FIELD_CAPABILITY_ADD` | `"ADD"` | STATE_DB に書き込まれる能力トークン。`toStr()` でセットをカンマ連結 | `pbhcap.cpp:30` |
| `PBH_FIELD_CAPABILITY_UPDATE` | `"UPDATE"` | 同上 | `pbhcap.cpp:31` |
| `PBH_FIELD_CAPABILITY_REMOVE` | `"REMOVE"` | 同上 | `pbhcap.cpp:32` |
| `PBH_FIELD_CAPABILITY_UNKN` | `"UNKNOWN"` | 未知能力値のフォールバック文字列。`pbhFieldCapabilityMap` に未登録値が来た場合 | `pbhcap.cpp:33` |

> **補足**: `toStr()` はフィールド能力セットを `std::set<PbhFieldCapability>` → ソート順でカンマ連結文字列に変換する。`std::set` は昇順ソートされるため出力は `"ADD,REMOVE,UPDATE"` ではなく enum の宣言順 `"ADD,UPDATE,REMOVE"` になる（`PbhFieldCapability::ADD=0, UPDATE=1, REMOVE=2` の順）。

---

## 5. フィールド名文字列定数 (pbhschema.h)

STATE_DB に書き込まれるフィールドキー名の C++ 定数。対応する Python 定数 (`pbh.py`) と完全一致する。

### table / rule 関連

| C++ 定数 | 値 | Python 定数 (pbh.py) | ソース |
|---------|----|--------------------|--------|
| `PBH_TABLE_INTERFACE_LIST` | `"interface_list"` | (直接リテラル使用) | `pbhschema.h:5` |
| `PBH_TABLE_DESCRIPTION` | `"description"` | (直接リテラル使用) | `pbhschema.h:6` |
| `PBH_RULE_PACKET_ACTION_SET_ECMP_HASH` | `"SET_ECMP_HASH"` | — | `pbhschema.h:8` |
| `PBH_RULE_PACKET_ACTION_SET_LAG_HASH` | `"SET_LAG_HASH"` | — | `pbhschema.h:9` |
| `PBH_RULE_FLOW_COUNTER_ENABLED` | `"ENABLED"` | — | `pbhschema.h:11` |
| `PBH_RULE_FLOW_COUNTER_DISABLED` | `"DISABLED"` | — | `pbhschema.h:12` |
| `PBH_RULE_PRIORITY` | `"priority"` | `PBH_RULE_PRIORITY` | `pbhschema.h:14` |
| `PBH_RULE_GRE_KEY` | `"gre_key"` | `PBH_RULE_GRE_KEY` | `pbhschema.h:15` |
| `PBH_RULE_ETHER_TYPE` | `"ether_type"` | `PBH_RULE_ETHER_TYPE` | `pbhschema.h:16` |
| `PBH_RULE_IP_PROTOCOL` | `"ip_protocol"` | `PBH_RULE_IP_PROTOCOL` | `pbhschema.h:17` |
| `PBH_RULE_IPV6_NEXT_HEADER` | `"ipv6_next_header"` | `PBH_RULE_IPV6_NEXT_HEADER` | `pbhschema.h:18` |
| `PBH_RULE_L4_DST_PORT` | `"l4_dst_port"` | `PBH_RULE_L4_DST_PORT` | `pbhschema.h:19` |
| `PBH_RULE_INNER_ETHER_TYPE` | `"inner_ether_type"` | `PBH_RULE_INNER_ETHER_TYPE` | `pbhschema.h:20` |
| `PBH_RULE_HASH` | `"hash"` | `PBH_RULE_HASH` | `pbhschema.h:21` |
| `PBH_RULE_PACKET_ACTION` | `"packet_action"` | `PBH_RULE_PACKET_ACTION` | `pbhschema.h:22` |
| `PBH_RULE_FLOW_COUNTER` | `"flow_counter"` | `PBH_RULE_FLOW_COUNTER` | `pbhschema.h:23` |

### hash / hash-field 関連

| C++ 定数 | 値 | Python 定数 (pbh.py) | ソース |
|---------|----|--------------------|--------|
| `PBH_HASH_HASH_FIELD_LIST` | `"hash_field_list"` | `PBH_HASH_HASH_FIELD_LIST` | `pbhschema.h:25` |
| `PBH_HASH_FIELD_HASH_FIELD_INNER_IP_PROTOCOL` | `"INNER_IP_PROTOCOL"` | — | `pbhschema.h:27` |
| `PBH_HASH_FIELD_HASH_FIELD_INNER_L4_DST_PORT` | `"INNER_L4_DST_PORT"` | — | `pbhschema.h:28` |
| `PBH_HASH_FIELD_HASH_FIELD_INNER_L4_SRC_PORT` | `"INNER_L4_SRC_PORT"` | — | `pbhschema.h:29` |
| `PBH_HASH_FIELD_HASH_FIELD_INNER_DST_IPV4` | `"INNER_DST_IPV4"` | — | `pbhschema.h:30` |
| `PBH_HASH_FIELD_HASH_FIELD_INNER_SRC_IPV4` | `"INNER_SRC_IPV4"` | — | `pbhschema.h:31` |
| `PBH_HASH_FIELD_HASH_FIELD_INNER_DST_IPV6` | `"INNER_DST_IPV6"` | — | `pbhschema.h:32` |
| `PBH_HASH_FIELD_HASH_FIELD_INNER_SRC_IPV6` | `"INNER_SRC_IPV6"` | — | `pbhschema.h:33` |
| `PBH_HASH_FIELD_HASH_FIELD` | `"hash_field"` | `PBH_HASH_FIELD_HASH_FIELD` | `pbhschema.h:35` |
| `PBH_HASH_FIELD_IP_MASK` | `"ip_mask"` | `PBH_HASH_FIELD_IP_MASK` | `pbhschema.h:36` |
| `PBH_HASH_FIELD_SEQUENCE_ID` | `"sequence_id"` | `PBH_HASH_FIELD_SEQUENCE_ID` | `pbhschema.h:37` |

---

## 6. Python 側固有定数 (pbh.py L72–85)

`sonic-utilities` の `pbh.py` がコンシューマ側で参照する定数（C++ 定数とは独立に定義）。

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PBH_CAPABILITIES_SDB` | `"PBH_CAPABILITIES"` | STATE_DB テーブル名（`STATE_PBH_CAPABILITIES_TABLE_NAME` の Python 側ミラー）| `pbh.py:72` |
| `PBH_ADD` | `"ADD"` | フィールド操作能力チェックトークン | `pbh.py:82` |
| `PBH_UPDATE` | `"UPDATE"` | 同上 | `pbh.py:83` |
| `PBH_REMOVE` | `"REMOVE"` | 同上 | `pbh.py:84` |

---

## 特記事項

1. **YANG スキーマなし**: `PBH_CAPABILITIES` は STATE_DB テーブルであり、CONFIG_DB / YANG の管理対象外。テーブル名・フィールド名・値の文字列はすべて C++ `#define` / Python 変数としてコードに埋め込まれている。
2. **`PBH_STATE_DB_TIMEOUT = 0`**: `DBConnector` への接続はブロッキング（タイムアウトなし）。起動時に Redis が応答しなければ `stateDb` static member の初期化でハングする。
3. **`toStr()` のソート順**: `PbhFieldCapability::ADD=0, UPDATE=1, REMOVE=2` の enum 値順に `std::set` が昇順ソートされるため、3 つすべてが有効な場合の STATE_DB 書き込み値は `"ADD,REMOVE,UPDATE"` ではなく `"ADD,UPDATE,REMOVE"` となる（テスト fixture と一致）。
4. **C++/Python の定数二重管理**: `pbhschema.h` と `pbh.py` は独立して同値を定義している。コードレビュー外での一方変更がバグを引き起こすリスクがある。

---

## 出典

- `sonic-net/sonic-swss/orchagent/pbh/pbhcap.cpp` L20–36, L288–289, L451
- `sonic-net/sonic-swss/orchagent/pbh/pbhschema.h` L5–37
- `sonic-net/sonic-swss-common/common/schema.h` L419
- `sonic-net/sonic-utilities/config/plugins/pbh.py` L55–85
