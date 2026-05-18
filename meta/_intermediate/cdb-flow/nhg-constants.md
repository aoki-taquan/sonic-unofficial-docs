# NEXTHOP_GROUP_TABLE — ハードコード定数 (Phase E)

## 調査対象

- `sonic-swss/orchagent/routeorch.cpp` L37-38
- `sonic-swss/orchagent/nexthopkey.h` L17-19
- `sonic-swss/orchagent/orch.h` L42

## 定数一覧

### ECMP グループ数上限

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `DEFAULT_NUMBER_OF_ECMP_GROUPS` | `128` | `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` の取得に失敗した場合のフォールバック上限値 | `routeorch.cpp:37` |
| `DEFAULT_MAX_ECMP_GROUP_SIZE` | `32` | Mellanox プラットフォームで `m_maxNextHopGroupCount` を割るサイズ。Mellanox の SAI が返す値は ECMP group size=1 時の最大数であるため除算が必要 | `routeorch.cpp:38,86` |

### 内部キー区切り文字

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `NHG_DELIMITER` | `','` | `nexthop`/`ifname`/`weight` 等の comma-separated フィールドの区切り。また `NextHopGroupKey` の内部文字列表現にも使用 | `nexthopkey.h:19` |
| `NH_DELIMITER` | `'@'` | `NextHopKey` の IP アドレスとインタフェース名の区切り (例: `10.0.0.1@Ethernet0`) | `nexthopkey.h:18` |
| `LABELSTACK_DELIMITER` | `'+'` | MPLS ラベルスタック内の区切り (例: `100+200`) | `nexthopkey.h:17` |

### プラットフォーム識別子

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `MLNX_PLATFORM_SUBSTRING` | `"mellanox"` | 環境変数 `platform` 内に含まれるか検索し Mellanox プラットフォームを識別。Mellanox 専用の ECMP グループ数再計算ロジックを有効化 | `orch.h:42` |

## 動作ロジック補足

1. `RouteOrch` 初期化時に `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` を ASIC から取得する。取得失敗時は `DEFAULT_NUMBER_OF_ECMP_GROUPS = 128` をフォールバックとして使用。
2. Mellanox プラットフォームでは取得値を `DEFAULT_MAX_ECMP_GROUP_SIZE = 32` で除算する (ASIC が group size=1 前提の最大数を返すため)。
3. 最終値は `SWITCH_TABLE:switch:MAX_NEXTHOP_GROUP_COUNT` として STATE\_DB に書き込まれる (`routeorch.cpp:90`)。
4. `NHG_DELIMITER`/`NH_DELIMITER`/`LABELSTACK_DELIMITER` は APPL\_DB フィールド値 (comma-separated 文字列) のパース専用。CONFIG\_DB には露出しない内部表現。
