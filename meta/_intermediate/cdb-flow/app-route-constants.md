# APPL_DB ROUTE_TABLE — Phase E: ハードコード定数 詳細トレース

生成日: 2026-05-15
対象ページ: `docs/reference/config-db/app-route.md`

## 目的

`fpmsyncd` / `routeorch` / `CrmOrch` が `APPL_DB:ROUTE_TABLE` 経路で使用するハードコード定数（ECMP 上限、プラットフォーム識別子、key プレフィクス、SAI 属性 ID 紐付け、threshold/counter 文字列）をソースコードから抽出し、evidence 行付きで一覧化する。

## 訪問ファイル

| ファイル | 内容 |
|---------|------|
| `sonic-swss/orchagent/routeorch.cpp` | ECMP 上限マクロ、VOQ 強制値、Mellanox 補正 |
| `sonic-swss/orchagent/routeorch.h` | `LOOPBACK_PREFIX` マクロ |
| `sonic-swss/orchagent/orch.h` | プラットフォーム識別子マクロ群 |
| `sonic-swss/orchagent/nexthopkey.h` | `VRF_PREFIX` マクロ |
| `sonic-swss/orchagent/crmorch.cpp` | CRM resource / SAI 属性 / threshold/counter 文字列マップ |

## 1. ECMP 上限デフォルト（`routeorch.cpp`）

| マクロ | 値 | 行 | 用途 |
|--------|----|----|------|
| `DEFAULT_NUMBER_OF_ECMP_GROUPS` | `128` | `routeorch.cpp:37` | SAI クエリ失敗時の `m_maxNextHopGroupCount` フォールバック |
| `DEFAULT_MAX_ECMP_GROUP_SIZE` | `32` | `routeorch.cpp:38` | Mellanox 補正の除数（SAI 戻り値をこの値で割る） |

参照箇所:

- L66-68: `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` の get が失敗 → `m_maxNextHopGroupCount = DEFAULT_NUMBER_OF_ECMP_GROUPS`（128 にフォールバック）
- L84-87: `strstr(platform, MLNX_PLATFORM_SUBSTRING)` が true のとき `m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE`
- L90: `fvTuple.emplace_back("MAX_NEXTHOP_GROUP_COUNT", to_string(m_maxNextHopGroupCount))` で STATE_DB `SWITCH_CAPABILITY` に公開

## 2. VOQ chassis での `SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT` 強制値

`routeorch.cpp:95-122`:

- L96: `attr.id = SAI_SWITCH_ATTR_MAX_ECMP_MEMBER_COUNT` を get
- L109: `if (gMySwitchType == "voq" && maxEcmpGroupSize >= 128)`
- L111: `maxEcmpGroupSize = 128`（強制）
- L112: `attr.id = SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT`
- L114: `set_switch_attribute` で書き戻し

ハードコード値: **128**（マジック数、`#define` ではない）。`gMySwitchType` の値 `"voq"` も文字列リテラル比較。

## 3. プラットフォーム識別子マクロ（`orch.h`）

| マクロ | 値 | 行 |
|--------|----|----|
| `MLNX_PLATFORM_SUBSTRING` | `"mellanox"` | `orch.h:42` |

routeorch.cpp L84 で `strstr(platform, MLNX_PLATFORM_SUBSTRING)` 部分一致比較に使用。`platform` は `getenv("platform")` 経由で取得され、`DEVICE_METADATA|localhost.platform` を反映する。

他のプラットフォーム識別子（`BRCM_PLATFORM_SUBSTRING`, `VS_PLATFORM_SUBSTRING`, `XS_PLATFORM_SUBSTRING` 等）は routeorch.cpp 内では参照されない。Mellanox 以外は全て補正なし。

## 4. key プレフィクスマクロ

| マクロ | 値 | 行 | 用途 |
|--------|----|----|------|
| `VRF_PREFIX` | `"Vrf"` | `nexthopkey.h:20` | ROUTE_TABLE key の VRF 部分判定（`<vrf>:<prefix>` 形式） |
| `LOOPBACK_PREFIX` | `"Loopback"` | `routeorch.h:28` | ifname が `lo` または `Loopback*` のとき特別扱い |

参照箇所:

- `routeorch.cpp:706`: `if (!key.compare(0, strlen(VRF_PREFIX), VRF_PREFIX))` — VRF 付き key 判定
- `routeorch.cpp:905`: `alias == "lo" || !alias.compare(0, strlen(LOOPBACK_PREFIX), LOOPBACK_PREFIX)` — Loopback IF への到達性扱い
- `routeorch.cpp:1035`: 同様に `VRF_PREFIX` 判定

## 5. デフォルトルート判定リテラル

`routeorch.cpp:126-127, 287-295` で STATE_DB `ROUTE_TABLE` のデフォルトルート到達性を更新する際、対象 prefix を文字列リテラルで決め打ち:

- IPv4 デフォルトルート: `"0.0.0.0/0"`
- IPv6 デフォルトルート: `"::/0"`
- 状態値: `"ok"` / `"na"`（フィールド `state`）

非デフォルトルートの到達性は STATE_DB に書かない。

## 6. CRM resource ↔ SAI 属性マップ（`crmorch.cpp`）

`crmResSaiAvailAttrMap` (`crmorch.cpp:74-77`):

| CRM resource | SAI 属性 |
|--------------|---------|
| `CrmResourceType::CRM_IPV4_ROUTE` | `SAI_SWITCH_ATTR_AVAILABLE_IPV4_ROUTE_ENTRY` |
| `CrmResourceType::CRM_IPV6_ROUTE` | `SAI_SWITCH_ATTR_AVAILABLE_IPV6_ROUTE_ENTRY` |

`crmResTypeNameMap` (`crmorch.cpp:28-31`):

| enum | 文字列 |
|------|--------|
| `CRM_IPV4_ROUTE` | `"IPV4_ROUTE"` |
| `CRM_IPV6_ROUTE` | `"IPV6_ROUTE"` |

`crmResSaiObjAttrMap` (`crmorch.cpp:95-98`):

| CRM resource | SAI オブジェクト型 |
|--------------|------------------|
| `CRM_IPV4_ROUTE` | `SAI_OBJECT_TYPE_ROUTE_ENTRY` |
| `CRM_IPV6_ROUTE` | `SAI_OBJECT_TYPE_ROUTE_ENTRY` |

`crmResAddrFamilyValMap` (`crmorch.cpp:151-154`):

| CRM resource | SAI 値 |
|--------------|--------|
| `CRM_IPV4_ROUTE` | `SAI_IP_ADDR_FAMILY_IPV4` |
| `CRM_IPV6_ROUTE` | `SAI_IP_ADDR_FAMILY_IPV6` |

## 7. CRM threshold / counter 文字列キー（`crmorch.cpp`）

CONFIG_DB `CRM` テーブルおよび COUNTERS_DB `CRM:STATS` のフィールド名はすべてハードコード文字列:

| 文字列 | マップ | 行 | 用途 |
|--------|--------|----|------|
| `"ipv4_route_threshold_type"` | `crmThreshTypeResMap` | 163 | CONFIG_DB threshold 種別キー (IPv4) |
| `"ipv6_route_threshold_type"` | `crmThreshTypeResMap` | 164 | CONFIG_DB threshold 種別キー (IPv6) |
| `"ipv4_route_low_threshold"` | `crmThreshLowResMap` | 209 | CONFIG_DB low 閾値 (IPv4) |
| `"ipv6_route_low_threshold"` | `crmThreshLowResMap` | 210 | CONFIG_DB low 閾値 (IPv6) |
| `"ipv4_route_high_threshold"` | `crmThreshHighResMap` | 255 | CONFIG_DB high 閾値 (IPv4) |
| `"ipv6_route_high_threshold"` | `crmThreshHighResMap` | 256 | CONFIG_DB high 閾値 (IPv6) |
| `"crm_stats_ipv4_route_available"` | `crmAvailCntsTableMap` | 308 | COUNTERS_DB available 値 |
| `"crm_stats_ipv6_route_available"` | `crmAvailCntsTableMap` | 309 | COUNTERS_DB available 値 |
| `"crm_stats_ipv4_route_used"` | `crmUsedCntsTableMap` | 354 | COUNTERS_DB used 値 (routeorch L148/168/257/280 で inc/dec) |
| `"crm_stats_ipv6_route_used"` | `crmUsedCntsTableMap` | 355 | COUNTERS_DB used 値 |

## 8. その他関連定数（参考、本文には含めない）

| 名前 | 値 | 場所 | 備考 |
|------|----|------|------|
| `gMaxBulkSize` | SAI bulker 既定値（switchorch から伝播） | `routeorch.cpp:40-43` constructor 初期化リスト | ECMP/route 一括 SAI 呼び出しのバッチサイズ |
| `m_nextHopGroupCount` 上限判定 | `m_nextHopGroupCount + NhgOrch::getSyncedNhgCount() >= m_maxNextHopGroupCount` | L1096, L1424, L1478 | NHG 作成可否判定（マジック数なし） |
| ZMQ 経路フラグ | `ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` | 環境変数 / build config | 本ページ範囲外 |

これらは本文 `<!-- constants -->` ブロックには含めない（マジック数なし or 設計時に動的決定される値）。

## まとめ

ページ `app-route.md` 本文の `<!-- constants -->` ブロックでは以下を網羅する:

1. ECMP 上限マクロ 2 種（`DEFAULT_NUMBER_OF_ECMP_GROUPS=128`, `DEFAULT_MAX_ECMP_GROUP_SIZE=32`）と Mellanox 補正
2. VOQ chassis 強制値 `SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT=128`
3. プラットフォーム識別子 `MLNX_PLATFORM_SUBSTRING="mellanox"`
4. key プレフィクス `VRF_PREFIX="Vrf"`, `LOOPBACK_PREFIX="Loopback"`
5. デフォルトルート判定リテラル `"0.0.0.0/0"` / `"::/0"` / `"ok"` / `"na"`
6. CRM resource ↔ SAI 属性 / オブジェクト型 / アドレスファミリの 4 マップ
7. CRM threshold / counter 文字列キー 10 種（CONFIG_DB `CRM` + COUNTERS_DB `CRM:STATS`）
